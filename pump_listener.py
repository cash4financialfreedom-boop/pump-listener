import os
import time
import threading
import requests
from flask import Flask

# --- FLASK SERVER FOR RENDER HEALTH CHECK ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Pump Listener is Running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()

# --- SPREMENLJIVKE IN KONFIGURACIJA ---
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")

def get_dev_history(dev_address):
    """
    Stabilno preverjanje zgodovine Deva:
    1. Poskusi prebrati Pump.fun API z imitacijo brskalnika.
    2. Če Pump.fun blokira Render IP (403), uporabi HELIUS API preko transakcij.
    """
    if not dev_address:
        return "Fresh Wallet (First Launch) 🆕"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://pump.fun/"
    }
    
    # 1. POSKUS: Pump.fun API
    try:
        url = f"https://frontend-api.pump.fun/coins/user-created-coins/{dev_address}?offset=0&limit=50&sort=created_timestamp&order=DESC"
        resp = requests.get(url, headers=headers, timeout=3)
        
        if resp.status_code == 200:
            coins = resp.json()
            if isinstance(coins, list) and len(coins) > 0:
                migrated = sum(1 for c in coins if c.get("complete") is True)
                rugged = len(coins) - migrated
                if migrated > 0 or len(coins) > 1:
                    return f"Linked Dev ({migrated} Migrated | {rugged} Rugged)"
    except Exception as e:
        print(f"Pump.fun API direct check failed: {e}")

    # 2. POSKUS: HELIUS API (Fallback, ko Render IP naleti na Cloudflare blokado)
    if HELIUS_API_KEY:
        try:
            h_url = f"https://api.helius.xyz/v0/addresses/{dev_address}/transactions?api-key={HELIUS_API_KEY}"
            h_resp = requests.get(h_url, timeout=4)
            if h_resp.status_code == 200:
                txs = h_resp.json()
                if isinstance(txs, list) and len(txs) > 0:
                    launches = 0
                    for tx in txs:
                        tx_str = str(tx).lower()
                        if "pump" in tx_str or "mint" in tx_str or tx.get("type") == "CREATE":
                            launches += 1
                    
                    if launches > 1:
                        return f"Linked Dev ({launches} Past Launches Detected)"
        except Exception as e:
            print(f"Helius API check failed: {e}")

    return "Fresh Wallet (First Launch) 🆕"


def process_and_send_token(token_data):
    try:
        mint = token_data.get("mint")
        name = token_data.get("name", "Unknown Token")
        symbol = token_data.get("symbol", "TOKEN")
        dev_address = token_data.get("dev", "")
        mcap = token_data.get("market_cap", 0)

        dev_history_str = get_dev_history(dev_address) if dev_address else "Fresh Wallet (First Launch) 🆕"

        payload = {
            "name": name,
            "symbol": symbol,
            "market_cap": f"${mcap / 1000:.2f}K" if mcap > 0 else "$0K",
            "dev_history": dev_history_str,
            "mint": mint,
            "pair_url": f"https://dexscreener.com/solana/{mint}" if mint else ""
        }

        if N8N_WEBHOOK_URL:
            resp = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=5)
            print(f"TOKEN PASSED (${mcap / 1000:.2f}K)! Sent to n8n: {name} (${symbol}) | Status: {resp.status_code}")
        else:
            print("Warning: N8N_WEBHOOK_URL is not set!")

    except Exception as e:
        print(f"Error processing token payload: {e}")


def is_viral_token(coin):
    has_website = bool(coin.get("website"))
    has_twitter = bool(coin.get("twitter"))
    has_telegram = bool(coin.get("telegram"))
    
    desc = str(coin.get("description", "")).lower()
    name = str(coin.get("name", "")).lower()
    symbol = str(coin.get("symbol", "")).lower()
    
    full_text = f"{name} {symbol} {desc}"

    viral_keywords = [
        "elon", "musk", "tweet", "x.com", "post", "grok", "tesla", "spacex", "doge",
        "trump", "maga", "kamala", "biden", "president", "usa", "election",
        "tiktok", "instagram", "ig", "reel", "youtube", "yt", "viral",
        "cat", "dog", "shib", "pepe", "frog", "hippo", "moo", "trend", "meme", "ai", "pump"
    ]
    
    has_viral_keyword = any(keyword in full_text for keyword in viral_keywords)
    has_valid_desc = len(desc.strip()) > 15

    return has_website or has_twitter or has_telegram or has_viral_keyword or has_valid_desc


def fetch_pump_fun_coins(seen_mints):
    url = "https://frontend-api.pump.fun/coins?offset=0&limit=50&sort=last_trade_timestamp&order=DESC"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            coins = resp.json()
            if isinstance(coins, list):
                for coin in coins:
                    mint = coin.get("mint")
                    if not mint or mint in seen_mints:
                        continue

                    mcap = float(coin.get("usd_market_cap", 0) or 0)
                    
                    if 15000 <= mcap <= 50000:
                        if is_viral_token(coin):
                            seen_mints.add(mint)
                            token_payload = {
                                "mint": mint,
                                "name": coin.get("name"),
                                "symbol": coin.get("symbol"),
                                "dev": coin.get("creator"),
                                "market_cap": mcap
                            }
                            process_and_send_token(token_payload)
    except Exception as e:
        print(f"Napaka Pump.fun zanke: {e}")


def check_migrated_dex_tokens(seen_mints):
    try:
        url = "https://api.dexscreener.com/token-profiles/recent-updates/v1"
        headers = {"User-Agent": "Mozilla/5.0"}
        
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            profiles = resp.json()
            if isinstance(coins := profiles, list):
                for item in profiles:
                    if item.get("chainId") == "solana":
                        token_address = item.get("tokenAddress")
                        if not token_address or token_address in seen_mints:
                            continue
                        
                        pair_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
                        p_resp = requests.get(pair_url, headers=headers, timeout=4)
                        if p_resp.status_code == 200:
                            data = p_resp.json()
                            pairs = data.get("pairs", [])
                            if pairs and len(pairs) > 0:
                                pair = pairs[0]
                                mcap = float(pair.get("fdv", 0) or pair.get("marketCap", 0) or 0)
                                
                                if 15000 <= mcap <= 50000:
                                    seen_mints.add(token_address)
                                    base_token = pair.get("baseToken", {})
                                    
                                    dev_creator = ""
                                    try:
                                        pf_url = f"https://frontend-api.pump.fun/coins/{token_address}"
                                        pf_resp = requests.get(pf_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
                                        if pf_resp.status_code == 200:
                                            dev_creator = pf_resp.json().get("creator", "")
                                    except Exception:
                                        pass

                                    token_payload = {
                                        "mint": token_address,
                                        "name": base_token.get("name", "Migrated Token"),
                                        "symbol": base_token.get("symbol", "DEX"),
                                        "dev": dev_creator,
                                        "market_cap": mcap
                                    }
                                    process_and_send_token(token_payload)
    except Exception as e:
        print(f"Napaka DexScreener zanke: {e}")


def main():
    print("Starting pump_listener active scanning loop ($15k-$50k | Direct Dev Check + Helius Fallback)...")
    seen_mints = set()
    
    while True:
        try:
            fetch_pump_fun_coins(seen_mints)
            check_migrated_dex_tokens(seen_mints)

            if len(seen_mints) > 1000:
                seen_mints.clear()

            time.sleep(3)

        except Exception as e:
            print(f"Error in active listener loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
