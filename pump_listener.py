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
    # Uporabimo DexScreenerjev javni API za Solana tokene, ki ga Cloudflare ne blokira
    url = "https://api.dexscreener.com/token-pairs/v1/solana"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        print("🔄 Fetching Solana pairs from DexScreener API...", flush=True)
        resp = requests.get(url, headers=headers, timeout=5)
        
        if resp.status_code == 200:
            pairs = resp.json()
            if not pairs or not isinstance(pairs, list):
                print("⚠️ Received empty data from DexScreener.", flush=True)
                return
            
            print(f"📊 Total pairs fetched: {len(pairs)}", flush=True)
            
            for pair in pairs:
                if pair.get("chainId") != "solana":
                    continue
                
                base_token = pair.get("baseToken", {})
                mint = base_token.get("address")
                if not mint or mint in seen_mints:
                    continue

                mcap = float(pair.get("fdv", 0) or pair.get("marketCap", 0) or 0)
                name = base_token.get("name", "Unknown")
                
                # Izločimo vse izven našega obsega 15k - 100k
                if mcap < 15000 or mcap > 100000:
                    continue
                
                # Preverimo obstoj Twitterja
                socials = pair.get("info", {}).get("socials", [])
                twitter = next((s.get("url") for s in socials if s.get("type") == "twitter"), "")
                
                print(f"🎯 Target Found: {name} | MCAP: ${mcap:.2f} | Twitter: {'YES' if twitter else 'NO'}", flush=True)

                if twitter:
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
                        res = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=4)
                        print(f"✅ SENT TO N8N (${mcap / 1000:.2f}K): {name} (Status: {res.status_code})", flush=True)

        else:
            print(f"⚠️ DexScreener API error status: {resp.status_code}", flush=True)

    except Exception as e:
        print(f"❌ Error: {e}", flush=True)

def main():
    print("🚀 Stable Solana API scanner running...", flush=True)
    seen_mints = set()
    while True:
        fetch_and_filter(seen_mints)
        if len(seen_mints) > 1000:
            seen_mints.clear()
        time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(1)
    main()
