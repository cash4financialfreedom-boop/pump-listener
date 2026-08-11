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

def fetch_and_filter(seen_mints):
    # Uporabimo točen endpoint za pump.fun zadetke
    url = "https://api.dexscreener.com/latest/dex/tokens/pump"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            pairs = data.get("pairs", [])
            print(f"🔄 Checking {len(pairs)} pairs...", flush=True)
            
            for pair in pairs:
                if pair.get("chainId") != "solana":
                    continue
                
                base_token = pair.get("baseToken", {})
                mint = base_token.get("address")
                if not mint or mint in seen_mints:
                    continue

                mcap = float(pair.get("fdv", 0) or pair.get("marketCap", 0) or 0)
                name = base_token.get("name", "Unknown")
                
                # Ciljni razpon: 15k do 100k
                if 15000 <= mcap <= 100000:
                    seen_mints.add(mint)
                    payload = {
                        "tokenName": name,
                        "tokenSymbol": base_token.get("symbol"),
                        "market_cap": f"${mcap / 1000:.2f}K",
                        "marketCap": mcap,
                        "mint": mint,
                        "pair_url": f"https://dexscreener.com/solana/{mint}"
                    }
                    if N8N_WEBHOOK_URL:
                        requests.post(N8N_WEBHOOK_URL, json=payload, timeout=4)
                        print(f"✅ SENT TOKEN (${mcap / 1000:.2f}K): {name}", flush=True)

    except Exception as e:
        print(f"Fetch error: {e}", flush=True)

def main():
    print("🚀 Scanner running...", flush=True)
    seen_mints = set()
    while True:
        fetch_and_filter(seen_mints)
        if len(seen_mints) > 1000:
            seen_mints.clear()
        time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()
