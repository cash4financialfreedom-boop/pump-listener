import os
import time
import threading
import requests
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health_check():
    return "Raydium Sniper is Running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")
BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY", "")

def fetch_raydium_market(seen_mints):
    # Uporabljamo drug endpoint za pregled trendov/tokenov
    url = "https://public-api.birdeye.so/defi/token_trending"
    headers = {"X-API-KEY": BIRDEYE_API_KEY, "accept": "application/json", "x-chain": "solana"}
    
    print("Scanning trending Raydium tokens...", flush=True)
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"API Status Code: {resp.status_code}", flush=True)
        
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("data", {}).get("tokens", [])
            print(f"Total trending items received: {len(items)}", flush=True)
            
            for item in items:
                mint = item.get("address")
                name = item.get("name", "Unknown")
                mcap = float(item.get("market_cap", 0) or item.get("marketCap", 0) or 0)
                
                print(f"-> Token: {name} | MCAP: ${mcap:.1f}", flush=True)
                
                # Testni pas (pustimo širše, da vidimo, kaj vrne)
                if mcap < 1000 or mcap > 1000000:
                    continue
                
                if mint in seen_mints:
                    continue
                
                seen_mints.add(mint)
                payload = {
                    "tokenName": name,
                    "marketCap": mcap,
                    "mint": mint,
                    "twitterUrl": f"https://twitter.com/search?q={mint}",
                    "pair_url": f"https://birdeye.so/token/{mint}?chain=solana"
                }
                
                if N8N_WEBHOOK_URL:
                    requests.post(N8N_WEBHOOK_URL, json=payload, timeout=5)
                    print(f"SUCCESSFULLY SENT TRENDING TOKEN: {name} (${mcap/1000:.0f}K)", flush=True)
                    
        elif resp.status_code == 429:
            print("Rate limit 429, resting...", flush=True)
            time.sleep(30)
    except Exception as e:
        print(f"Error: {e}", flush=True)

def main():
    print("Sniper Active on Trending API...", flush=True)
    seen_mints = set()
    while True:
        fetch_raydium_market(seen_mints)
        time.sleep(30)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()
