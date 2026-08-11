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
    url = "https://api.dexscreener.com/latest/dex/search?q=pump"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if not data or not isinstance(data, dict):
                return
            
            pairs = data.get("pairs", [])
            if not pairs or not isinstance(pairs, list):
                return
            
            for pair in pairs:
                if pair.get("chainId") != "solana":
                    continue
                
                base_token = pair.get("baseToken", {})
                mint = base_token.get("address")
                if not mint or mint in seen_mints:
                    continue

                mcap = float(pair.get("fdv", 0) or pair.get("marketCap", 0) or 0)
                name = base_token.get("name", "Unknown")
                
                # Check for Twitter (Mandatory)
                socials = pair.get("info", {}).get("socials", [])
                twitter = next((s.get("url") for s in socials if s.get("type") == "twitter"), "")
                if not twitter:
                    continue

                # Target ranges: 15k - 100k market cap
                if 15000 <= mcap <= 100000:
                    seen_mints.add(mint)
                    payload = {
                        "tokenName": name,
                        "tokenSymbol": base_token.get("symbol"),
                        "market_cap": f"${mcap / 1000:.2f}K",
                        "marketCap": mcap,
                        "mint": mint,
                        "twitterUrl": twitter,
                        "pair_url": f"https://dexscreener.com/solana/{mint}"
                    }
                    if N8N_WEBHOOK_URL:
                        requests.post(N8N_WEBHOOK_URL, json=payload, timeout=4)
                        print(f"✅ SENT TOKEN (${mcap / 1000:.2f}K): {name} | Twitter: {twitter}", flush=True)

    except Exception as e:
        print(f"Fetch error: {e}", flush=True)

def main():
    print("🚀 Scanner running securely...", flush=True)
    seen_mints = set()
    while True:
        fetch_and_filter(seen_mints)
        if len(seen_mints) > 1000:
            seen_mints.clear()
        time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()
