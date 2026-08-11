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

def fetch_raydium_pairs(seen_mints):
    # Birdeye endpoint za Raydium pare
    url = "https://public-api.birdeye.so/defi/v2/tokens/new_listing"
    headers = {"X-API-KEY": BIRDEYE_API_KEY, "accept": "application/json", "x-chain": "solana"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("data", {}).get("items", [])
            for item in items:
                # Filtriranje: samo Raydium (source)
                if item.get("source") != "raydium":
                    continue
                
                mint = item.get("address")
                mcap = float(item.get("marketCap", 0) or 0)
                
                # Filter za tvoj pas: 50k - 150k
                if mcap < 50000 or mcap > 150000:
                    continue
                
                if mint in seen_mints:
                    continue
                
                # Preverjanje Twitterja (extensions)
                twitter = item.get("extensions", {}).get("twitter", "")
                if not twitter:
                    continue
                
                seen_mints.add(mint)
                payload = {
                    "tokenName": item.get("name"),
                    "marketCap": mcap,
                    "mint": mint,
                    "twitterUrl": twitter,
                    "pair_url": f"https://birdeye.so/token/{mint}?chain=solana"
                }
                
                if N8N_WEBHOOK_URL:
                    requests.post(N8N_WEBHOOK_URL, json=payload, timeout=5)
                    print(f"🎯 RAYDIUM SNIPE: {item.get('name')} (${mcap/1000:.0f}K)", flush=True)
        
    except Exception as e:
        print(f"❌ Error: {e}", flush=True)

def main():
    print("🚀 Raydium Sniper Active...", flush=True)
    seen_mints = set()
    while True:
        fetch_raydium_pairs(seen_mints)
        time.sleep(10)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(1)
    main()
