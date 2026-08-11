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

def send_test_ping():
    time.sleep(5)
    if N8N_WEBHOOK_URL:
        test_payload = {
            "tokenName": "TEST_COIN_VIP",
            "marketCap": 50000,
            "mint": "TestMintAddress123",
            "twitterUrl": "https://twitter.com/test",
            "pair_url": "https://birdeye.so"
        }
        try:
            requests.post(N8N_WEBHOOK_URL, json=test_payload, timeout=5)
            print("🧪 Testni klic poslan v n8n!", flush=True)
        except Exception as e:
            print(f"❌ Napaka pri testnem klicu: {e}", flush=True)

def fetch_raydium_pairs(seen_mints):
    url = "https://public-api.birdeye.so/defi/v2/tokens/new_listing"
    headers = {"X-API-KEY": BIRDEYE_API_KEY, "accept": "application/json", "x-chain": "solana"}
    
    print("🔍 Preverjam nove Raydium pare...", flush=True)
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("data", {}).get("items", [])
            print(f"📊 Najdenih {len(items)} skupnih vnosov. Filtriram...", flush=True)
            for item in items:
                if item.get("source") != "raydium":
                    continue
                
                mint = item.get("address")
                mcap = float(item.get("marketCap", 0) or 0)
                
                if mcap < 30000 or mcap > 300000:
                    continue
                
                if mint in seen_mints:
                    continue
                
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
                    
        elif resp.status_code == 429:
            print("⚠️ Rate limit reached (429), pausing longer...", flush=True)
            time.sleep(30)
        else:
            print(f"⚠️ Birdeye API error: {resp.status_code}", flush=True)
        
    except Exception as e:
        print(f"❌ Error: {e}", flush=True)

def main():
    print("🚀 Raydium Sniper Active...", flush=True)
    seen_mints = set()
    while True:
        fetch_raydium_pairs(seen_mints)
        time.sleep(15)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=send_test_ping, daemon=True).start()
    main()
