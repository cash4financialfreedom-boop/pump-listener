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

def fetch_raydium_migrated_tokens(seen_mints):
    # Uporabimo javni vir, ki nam vrne pare in njihovo kapitalizacijo
    url = "https://api.dexscreener.com/latest/dex/tokens/solana"
    
    print("Scanning Raydium migrated tokens (30k - 100k MC)...", flush=True)
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            if not isinstance(data, dict):
                return
            
            pairs = data.get("pairs")
            if not pairs or not isinstance(pairs, list):
                return
            
            for pair in pairs:
                if not isinstance(pair, dict):
                    continue
                
                # Gledamo izključno Raydium pare
                dex_id = pair.get("dexId", "")
                if dex_id not in ["raydium", "raydium_clamm"]:
                    continue
                
                base_token = pair.get("baseToken", {})
                mint = base_token.get("address")
                name = base_token.get("name")
                
                if not mint or not name or mint in seen_mints:
                    continue
                
                # Preverimo tržno kapitalizacijo (market cap ali fdv)
                market_cap = pair.get("marketCap") or pair.get("fdv", 0)
                
                # Filter: točno med 30.000 in 100.000 USD
                if not (30000 <= market_cap <= 100000):
                    continue
                
                seen_mints.add(mint)
                
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
                        print(f"SUCCESSFULLY SENT MIGRATED TOKEN: {name} ({market_cap} MC)", flush=True)
                    except Exception as err:
                        print(f"Webhook error: {err}", flush=True)
                
                break
    except Exception as e:
        print(f"Error: {e}", flush=True)

def main():
    print("Raydium Range Sniper Active...", flush=True)
    seen_mints = set()
    while True:
        fetch_raydium_migrated_tokens(seen_mints)
        time.sleep(20)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()
