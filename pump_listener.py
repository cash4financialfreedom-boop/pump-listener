import os
import time
import threading
import requests
from flask import Flask

# --- FLASK SERVER FOR RENDER HEALTH CHECK ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Pump Listener is Running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()

# --- CONFIG ---
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")

def process_and_send_token(token_data):
    try:
        mint = token_data.get("mint")
        name = token_data.get("name", "Unknown Token")
        mcap = token_data.get("market_cap", 0)
        
        payload = {
            "tokenName": name,
            "tokenSymbol": token_data.get("symbol"),
            "market_cap": f"${mcap / 1000:.2f}K",
            "marketCap": mcap,
            "mint": mint,
            "twitterUrl": token_data.get("twitterUrl", ""),
            "pair_url": f"https://dexscreener.com/solana/{mint}"
        }

        if N8N_WEBHOOK_URL:
            requests.post(N8N_WEBHOOK_URL, json=payload, timeout=4)
            print(f"✅ TOKEN PASSED (${mcap / 1000:.2f}K): {name}", flush=True)
    except Exception as e:
        print(f"Error: {e}", flush=True)

def fetch_dexscreener_coins(seen_mints):
    url = "https://api.dexscreener.com/latest/dex/search?q=pump"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            pairs = data.get("pairs", [])
            for pair in pairs:
                if pair.get("chainId") != "solana":
                    continue
                
                base_token = pair.get("baseToken", {})
                mint = base_token.get("address")
                if not mint or mint in seen_mints:
                    continue

                mcap = float(pair.get("fdv", 0) or pair.get("marketCap", 0) or 0)
                is_target = (15000 <= mcap <= 50000) or (mcap <= 100000)
                
                socials = pair.get("info", {}).get("socials", [])
                twitter = next((s.get("url") for s in socials if s.get("type") == "twitter"), "")

                if is_target and twitter:
                    seen_mints.add(mint)
                    process_and_send_token({
                        "mint": mint,
                        "name": base_token.get("name"),
                        "symbol": base_token.get("symbol"),
                        "market_cap": mcap,
                        "twitterUrl": twitter
                    })
    except Exception as e:
        print(f"DexScreener API Error: {e}", flush=True)

def main():
    print("Scanner active via DexScreener API...", flush=True)
    seen_mints = set()
    while True:
        fetch_dexscreener_coins(seen_mints)
        if len(seen_mints) > 1000:
            seen_mints.clear()
        time.sleep(5)

if __name__ == "__main__":
    main()
