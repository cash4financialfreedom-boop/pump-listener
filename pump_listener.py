import os
import time
import threading
import requests
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health_check():
    return "Pump.fun Sniper is Running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")

def fetch_pumpfun_tokens(seen_mints):
    # Uporabimo uradni Pump.fun endpoint za najnovejše ustvarjene kovance
    url = "https://frontend-api.pump.fun/coins?offset=0&limit=10&sort=created_timestamp&order=DESC"
    
    print("Fetching directly from Pump.fun...", flush=True)
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            coins = resp.json()
            if not isinstance(coins, list):
                return
            
            for coin in coins:
                mint = coin.get("mint")
                name = coin.get("name")
                symbol = coin.get("symbol", "")
                
                if not mint or not name or mint in seen_mints:
                    continue
                
                seen_mints.add(mint)
                
                # Izračunamo ali poberemo tržno kapitalizacijo (USD market cap)
                market_cap = coin.get("usd_market_cap", 15000)
                if not market_cap:
                    market_cap = 15000
                
                payload = {
                    "tokenName": f"{name} ({symbol})",
                    "marketCap": market_cap,
                    "mint": mint,
                    "twitterUrl": coin.get("twitter") or f"https://twitter.com/search?q={mint}",
                    "pair_url": f"https://pump.fun/coin/{mint}"
                }
                
                if N8N_WEBHOOK_URL:
                    try:
                        requests.post(N8N_WEBHOOK_URL, json=payload, timeout=5)
                        print(f"SUCCESSFULLY SENT PUMPFUN TOKEN: {name}", flush=True)
                    except Exception as err:
                        print(f"Webhook error: {err}", flush=True)
                
                break
    except Exception as e:
        print(f"Error: {e}", flush=True)

def main():
    print("Pump.fun Sniper Active...", flush=True)
    seen_mints = set()
    while True:
        fetch_pumpfun_tokens(seen_mints)
        time.sleep(15)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()
