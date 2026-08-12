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

def fetch_raydium_market(seen_mints):
    # Zanesljiv javni vir za sveže Solana unose z vsemi podatki
    url = "https://api.dexscreener.com/latest/dex/tokens/solana"
    
    print("Fetching active tokens with full details...", flush=True)
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            pairs = data.get("pairs", [])
            
            for pair in pairs:
                base_token = pair.get("baseToken", {})
                mint = base_token.get("address")
                name = base_token.get("name")
                
                if not mint or not name or mint in seen_mints:
                    continue
                
                seen_mints.add(mint)
                
                market_cap = pair.get("marketCap")
                if not market_cap:
                    market_cap = pair.get("fdv", 50000)
                
                payload = {
                    "tokenName": name,
                    "marketCap": market_cap,
                    "mint": mint,
                    "twitterUrl": f"https://twitter.com/search?q={mint}",
                    "pair_url": pair.get("url", f"https://dexscreener.com/solana/{mint}")
                }
                
                if N8N_WEBHOOK_URL:
                    try:
                        requests.post(N8N_WEBHOOK_URL, json=payload, timeout=5)
                        print(f"SUCCESSFULLY SENT FULL DATA TO N8N: {name}", flush=True)
                    except Exception as err:
                        print(f"Webhook error: {err}", flush=True)
                
                break
    except Exception as e:
        print(f"Error: {e}", flush=True)

def main():
    print("Sniper Active - Full Data Stream...", flush=True)
    seen_mints = set()
    while True:
        fetch_raydium_market(seen_mints)
        time.sleep(30)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()
