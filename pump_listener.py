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

# --- CONFIG ---
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")

def process_and_send_token(token_data):
    try:
        mint = token_data.get("mint")
        name = token_data.get("name", "Unknown Token")
        mcap = token_data.get("market_cap", 0)
        
        payload = {
            "tokenName": name,
            "tokenSymbol": token_data.get("symbol"),
            "market_cap": f"${mcap / 1000:.2f}K",
            "marketCap": mcap,
            "mint": mint,
            "twitterUrl": token_data.get("twitterUrl", ""),
            "pair_url": f"https://dexscreener.com/solana/{mint}"
        }

        if N8N_WEBHOOK_URL:
            requests.post(N8N_WEBHOOK_URL, json=payload, timeout=4)
            print(f"✅ TOKEN PASSED (${mcap / 1000:.2f}K): {name}", flush=True)
    except Exception as e:
        print(f"Error: {e}", flush=True)

def fetch_pump_fun_coins(seen_mints):
    # UPORABA GLAVNEGA DOMENSKEGA ENDPOINTA (ta deluje)
    url = "https://pump.fun/api/coins" 
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Referer": "https://pump.fun/"
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            coins = resp.json()
            for coin in coins:
                mint = coin.get("mint")
                if not mint or mint in seen_mints:
                    continue

                mcap = float(coin.get("usd_market_cap", 0))
                migrated = coin.get("complete", False)
                
                # POGOJI: 15k-50k ALI migrirani do 100k
                is_target = (15000 <= mcap <= 50000) or (migrated and mcap <= 100000)
                twitter = coin.get("twitter")

                if is_target and twitter:
                    seen_mints.add(mint)
                    process_and_send_token({
                        "mint": mint,
                        "name": coin.get("name"),
                        "symbol": coin.get("symbol"),
                        "market_cap": mcap,
                        "twitterUrl": twitter
                    })
    except Exception as e:
        print(f"API Error (using main domain): {e}", flush=True)

def main():
    print("Scanner active on main domain...", flush=True)
    seen_mints = set()
    while True:
        fetch_pump_fun_coins(seen_mints)
        time.sleep(5)

if __name__ == "__main__":
    main()
