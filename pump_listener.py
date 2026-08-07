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

# Start Flask health check in a background thread
threading.Thread(target=run_flask, daemon=True).start()

# --- CONFIGURATION & ENVIRONMENT VARIABLES ---
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")

def get_dev_history(dev_address):
    """
    Traces the dev wallet + parent funding wallet and analyzes past launches.
    Outputs a clean English string for Telegram HTML formatting.
    """
    if not dev_address or not HELIUS_API_KEY:
        return "Fresh Wallet (First Launch) 🆕"

    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        # 1. Fetch transactions for the dev wallet
        url = f"https://api.helius.xyz/v0/addresses/{dev_address}/transactions?api-key={HELIUS_API_KEY}"
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            txs = resp.json() if resp.status_code == 200 and isinstance(resp.json(), list) else []
        except Exception:
            txs = []
        
        target_wallet = dev_address

        # 2. Trace parent funding wallet if dev wallet is fresh
        if len(txs) < 5:
            for tx in reversed(txs):
                if isinstance(tx, dict):
                    for transfer in tx.get("nativeTransfers", []):
                        if transfer.get("toUserAccount") == dev_address:
                            funder = transfer.get("fromUserAccount")
                            if funder and funder != dev_address:
                                target_wallet = funder
                                break
                if target_wallet != dev_address:
                    break
            
            if target_wallet != dev_address:
                try:
                    parent_url = f"https://api.helius.xyz/v0/addresses/{target_wallet}/transactions?api-key={HELIUS_API_KEY}"
                    p_resp = requests.get(parent_url, headers=headers, timeout=5)
                    txs = p_resp.json() if p_resp.status_code == 200 and isinstance(p_resp.json(), list) else []
                except Exception:
                    pass

        # 3. Analyze past token launches
        migrated = 0
        rugged = 0
        max_ath = 0
        total_launches = 0

        for tx in txs:
            if not isinstance(tx, dict):
                continue
            
            tx_str = str(tx).lower()
            if tx.get("type") in ["CREATE", "SWAP"] or "pump" in tx_str or "mint" in tx_str:
                total_launches += 1
                
                token_mint = None
                events = tx.get("events", {})
                if isinstance(events, dict):
                    nfts = events.get("nft", {}).get("nfts", [])
                    if nfts and isinstance(nfts, list) and len(nfts) > 0:
                        token_mint = nfts[0].get("mint")

                if token_mint:
                    try:
                        dex_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_mint}"
                        d_resp = requests.get(dex_url, headers=headers, timeout=4)
                        if d_resp.status_code == 200:
                            data = d_resp.json()
                            pairs = data.get("pairs")
                            if pairs and len(pairs) > 0:
                                migrated += 1
                                mcap = float(pairs[0].get("fdv", 0) or pairs[0].get("marketCap", 0) or 0)
                                if mcap > max_ath:
                                    max_ath = mcap
                                if mcap < 1000:
                                    rugged += 1
                            else:
                                rugged += 1
                        else:
                            rugged += 1
                    except Exception:
                        pass

        # 4. Format Output String
        if total_launches <= 1 and migrated == 0:
            return "Fresh Wallet (First Launch) 🆕"
        
        if max_ath >= 1_000_000:
            ath_str = f"${max_ath / 1_000_000:.1f}M"
        elif max_ath >= 1_000:
            ath_str = f"${max_ath / 1_000:.0f}K"
        else:
            ath_str = f"${max_ath:.0f}"

        return f"Linked Dev ({migrated} Migrated | {rugged} Rugged | Top ATH: {ath_str})"

    except Exception as e:
        print(f"Error checking dev history: {e}")
        return "Fresh Wallet (First Launch) 🆕"


def process_and_send_token(token_data):
    """
    Formats the token payload, fetches dev info, and sends it to n8n Webhook.
    """
    try:
        mint = token_data.get("mint")
        name = token_data.get("name", "Unknown Token")
        symbol = token_data.get("symbol", "TOKEN")
        dev_address = token_data.get("dev", "")
        mcap = token_data.get("market_cap", 0)

        # Get dev launch history
        dev_history_str = get_dev_history(dev_address)

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
            print("Warning: N8N_WEBHOOK_URL environment variable is not set!")

    except Exception as e:
        print(f"Error processing token payload: {e}")


def main():
    print("Starting pump_listener active scanning loop...")
    
    # Track processed mints to avoid duplicates
    seen_mints = set()
    
    while True:
        try:
            # Fetch latest tokens from frontend API/Helius
            url = "https://frontend-api.pump.fun/coins?offset=0&limit=10&sort=created_timestamp&order=DESC"
            headers = {"User-Agent": "Mozilla/5.0"}
            
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                coins = resp.json()
                if isinstance(coins, list):
                    for coin in coins:
                        mint = coin.get("mint")
                        if mint and mint not in seen_mints:
                            seen_mints.add(mint)
                            
                            # Keep set size small
                            if len(seen_mints) > 1000:
                                seen_mints.clear()

                            mcap = float(coin.get("usd_market_cap", 0) or 0)
                            
                            # Filter threshold (e.g., $10K+ market cap or new listings)
                            if mcap >= 10000:
                                token_payload = {
                                    "mint": mint,
                                    "name": coin.get("name"),
                                    "symbol": coin.get("symbol"),
                                    "dev": coin.get("creator"),
                                    "market_cap": mcap
                                }
                                process_and_send_token(token_payload)

            time.sleep(4)

        except Exception as e:
            print(f"Error in active listener loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
