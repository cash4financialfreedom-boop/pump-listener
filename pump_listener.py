import os
import time
import threading
import requests
from flask import Flask

# --- FLASK SERVER ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Pump Listener is Running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# --- SCANNER LOGIC ---
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")

def fetch_and_filter(seen_mints):
    url = "https://api.dexscreener.com/latest/dex/search?q=solana"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        print("🔄 Sending request to DexScreener...", flush=True)
        resp = requests.get(url, headers=headers, timeout=5)
        
        if resp.status_code == 200:
            data = resp.json()
            if not data or not isinstance(data, dict):
                return
            
            pairs = data.get("pairs")
            if not pairs or not isinstance(pairs, list):
                return
            
            print(f"📊 Total pairs found: {len(pairs)}", flush=True)
            
            for pair in pairs:
                if pair.get("chainId") != "solana":
                    continue
                
                base_token = pair.get("baseToken", {})
                mint = base_token.get("address")
                if not mint or mint in seen_mints:
                    continue

                mcap = float(pair.get("fdv", 0) or pair.get("marketCap", 0) or 0)
                name = base_token.get("name", "Unknown")
                
                # Check for Twitter
                socials = pair.get("info", {}).get("socials", [])
                twitter = next((s.get("url") for s in socials if s.get("type") == "twitter"), "")
                
                print(f"Checked: {name} | MCAP: ${mcap:.2f} | Twitter: {'YES' if twitter else 'NO'}", flush=True)

                # Target condition: $15k - $100k market cap and mandatory Twitter
                if 15000 <= mcap <= 100000 and twitter:
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
            print(f"⚠️ DexScreener error status: {resp.status_code}", flush=True)

    except Exception as e:
        print(f"❌ Scanner fetch error: {e}", flush=True)

def main():
    print("🚀 Main scanner loop successfully started!", flush=True)
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
