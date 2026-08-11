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

# --- VARIABLES & CONFIGURATION ---
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")

def get_dev_history(dev_address):
    """
    Fast and safe developer history checker.
    """
    if not dev_address:
        return "Fresh Wallet (First Launch) 🆕"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    # 1. TRY: Direct Pump.fun API
    try:
        url = f"https://frontend-api.pump.fun/coins/user-created-coins/{dev_address}?offset=0&limit=100&sort=created_timestamp&order=DESC"
        resp = requests.get(url, headers=headers, timeout=3)
        
        if resp.status_code == 200:
            coins = resp.json()
            if isinstance(coins, list) and len(coins) > 0:
                migrated = sum(1 for c in coins if c.get("complete") is True)
                rugged = len(coins) - migrated
                if migrated > 0 or len(coins) > 1:
                    return f"Linked Dev ({migrated} Migrated | {rugged} Rugged)"
    except Exception:
        pass

    # 2. TRY: Helius API Fallback
    if HELIUS_API_KEY:
        try:
            h_url = f"https://api.helius.xyz/v0/addresses/{dev_address}/transactions?api-key={HELIUS_API_KEY}"
            h_resp = requests.get(h_url, timeout=3)
            if h_resp.status_code == 200:
                txs = h_resp.json()
                if isinstance(txs, list) and len(txs) > 0:
                    launches = len(txs)
                    if launches > 1:
                        return f"Linked Dev ({launches} Past Transactions/Launches)"
        except Exception:
            pass

    return "Fresh Wallet (First Launch) 🆕"


def process_and_send_token(token_data):
    try:
        mint = token_data.get("mint")
        name = token_data.get("name", "Unknown Token")
        symbol = token_data.get("symbol", "TOKEN")
        dev_address = token_data.get("dev", "")
        mcap = token_data.get("market_cap", 0)
        twitter_url = token_data.get("twitterUrl", "")
        dex_paid = token_data.get("dexPaid", False)

        dev_history_str = get_dev_history(dev_address) if dev_address else "Fresh Wallet (First Launch) 🆕"

        payload = {
            "tokenName": name,
            "tokenSymbol": symbol,
            "market_cap": f"${mcap / 1000:.2f}K" if mcap > 0 else "$0K",
            "marketCap": mcap,
            "dev_history": dev_history_str,
            "mint": mint,
            "twitterUrl": twitter_url,
            "dexPaid": "Paid" if dex_paid else "Not Paid Yet",
            "pair_url": f"https://dexscreener.com/solana/{mint}" if mint else ""
        }

        if N8N_WEBHOOK_URL:
            resp = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=4)
            print(f"✅ TOKEN PASSED (${mcap / 1000:.2f}K)! Sent to n8n: {name} (${symbol})", flush=True)
        else:
            print("Warning: N8N_WEBHOOK_URL is not set!", flush=True)

    except Exception as e:
        print(f"Error processing token payload: {e}", flush=True)


def fetch_pump_fun_coins(seen_mints):
    url = "https://frontend-api.pump.fun/coins?offset=0&limit=50&sort=last_trade_timestamp&order=DESC"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=3)
        if resp.status_code == 200:
            coins = resp.json()
            if isinstance(coins, list):
                for coin in coins:
                    mint = coin.get("mint")
                    if not mint or mint in seen_mints:
                        continue

                    mcap = float(coin.get("usd_market_cap", 0) or 0)
                    
                    # CILJNI RANG: 10k do 30k na Pump.fun
                    if 10000 <= mcap <= 30000:
                        twitter = coin.get("twitter")
                        if not twitter:
                            continue  # Obvezen Twitter

                        seen_mints.add(mint)
                        
                        # Preverimo še DexScreener za status dex-a / booste
                        dex_paid = False
                        try:
                            ds_url = f"https://api.dexscreener.com/latest/dex/tokens/{mint}"
                            ds_resp = requests.get(ds_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=2)
                            if ds_resp.status_code == 200:
                                ds_data = ds_resp.json()
                                pairs = ds_data.get("pairs", [])
                                if pairs:
                                    dex_paid = bool(pairs[0].get("boosts"))
                        except Exception:
                            pass

                        token_payload = {
                            "mint": mint,
                            "name": coin.get("name"),
                            "symbol": coin.get("symbol"),
                            "dev": coin.get("creator"),
                            "market_cap": mcap,
                            "twitterUrl": twitter,
                            "dexPaid": dex_paid
                        }
                        process_and_send_token(token_payload)
    except Exception:
        pass


def main():
    print("Starting pump_listener active scanning loop (Pump.fun | $10k-$30k | Twitter Required)...", flush=True)
    seen_mints = set()
    loop_count = 0
    
    while True:
        try:
            fetch_pump_fun_coins(seen_mints)

            if len(seen_mints) > 1000:
                seen_mints.clear()

            loop_count += 1
            if loop_count % 300 == 0:
                print("🔍 Scanner heartbeat: Loop actively checking 10k-30k pump.fun coins...", flush=True)

            time.sleep(3)

        except Exception as e:
            print(f"Error in main loop: {e}", flush=True)
            time.sleep(5)

if __name__ == "__main__":
    main()
