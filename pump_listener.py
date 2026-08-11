import os
import time
import threading
import requests
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health_check():
    return "Pump Listener is Running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")
BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY", "")

def fetch_and_filter(seen_mints):
    # Pravilen in preverjen Birdeye endpoint za novoustanovljene tokene
    url = "https://public-api.birdeye.so/defi/v2/tokens/newly_listed?limit=50"
    
    headers = {
        "X-API-KEY": BIRDEYE_API_KEY,
        "accept": "application/json",
        "x-chain": "solana"
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("data", {}).get("items", [])
            if not items:
                return
            
            for item in items:
                mint = item.get("address") or item.get("mint")
                if not mint or mint in seen_mints:
                    continue

                mcap = float(item.get("marketCap", 0) or item.get("fdv", 0) or 0)
                name = item.get("name", "Unknown")
                symbol = item.get("symbol", "UNKNOWN")
                
                # Filtriranje: 15k - 100k
                if mcap < 15000 or mcap > 100000:
                    continue
                
                extensions = item.get("extensions", {})
                twitter = extensions.get("twitter", "") if isinstance(extensions, dict) else ""
                
                if twitter:
                    seen_mints.add(mint)
                    payload = {
                        "tokenName": name,
                        "tokenSymbol": symbol,
                        "market_cap": f"${mcap / 1000:.2f}K",
                        "marketCap": mcap,
                        "mint": mint,
                        "twitterUrl": twitter,
                        "pair_url": f"https://dexscreener.com/solana/{mint}"
                    }
                    if N8N_WEBHOOK_URL:
                        res = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=5)
                        print(f"✅ SENT TO N8N (${mcap / 1000:.2f}K): {name} (Status: {res.status_code})", flush=True)

        else:
            print(f"⚠️ Birdeye API error: {resp.status_code} - {resp.text}", flush=True)

    except Exception as e:
        print(f"❌ Error: {e}", flush=True)

def main():
    print("🚀 Birdeye newly listed scanner running...", flush=True)
    seen_mints = set()
    while True:
        fetch_and_filter(seen_mints)
        if len(seen_mints) > 1000:
            seen_mints.clear()
        time.sleep(10)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(1)
    main()
