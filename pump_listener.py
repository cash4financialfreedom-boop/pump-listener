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
    url = "https://public-api.birdeye.so/defi/v2/tokens/new_listing"
    headers = {"X-API-KEY": BIRDEYE_API_KEY, "accept": "application/json", "x-chain": "solana"}
    
    print("Scanning Raydium market safely...", flush=True)
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("data", {}).get("items", [])
            
            # Vzmemo samo prvi neraziskani kovanec, da ne zamašimo n8n-a
            for item in items:
                source = item.get("source")
                mint = item.get("address")
                name = item.get("name", "Unknown")
                
                if source not in ["raydium", "raydium_clamm"]:
                    continue
                
                if mint in seen_mints:
                    continue
                
                seen_mints.add(mint)
                payload = {
                    "tokenName": name,
                    "marketCap": 50000,
                    "mint": mint,
                    "twitterUrl": f"https://twitter.com/search?q={mint}",
                    "pair_url": f"https://birdeye.so/token/{mint}?chain=solana"
                }
                
                if N8N_WEBHOOK_URL:
                    try:
                        requests.post(N8N_WEBHOOK_URL, json=payload, timeout=5)
                        print(f"SUCCESSFULLY SENT 1 TOKEN TO N8N: {name}", flush=True)
                    except Exception as err:
                        print(f"Webhook error: {err}", flush=True)
                
                # Posredujemo samo enega na cikel, da n8n in Claude normalno obdelata
                break
                    
        elif resp.status_code == 429:
            print("Rate limit 429, resting...", flush=True)
            time.sleep(30)
    except Exception as e:
        print(f"Error: {e}", flush=True)

def main():
    print("Sniper Active - Rate Limited Flow...", flush=True)
    seen_mints = set()
    while True:
        fetch_raydium_market(seen_mints)
        time.sleep(30) # Počakaj 30 sekund pred naslednjim preverjanjem

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()
