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
    url = "https://frontend-api.pump.fun/coins?offset=0&limit=50&sort=created_timestamp&order=DESC"
    
    # Izboljšane glave, da Cloudflare ne blokira zahteve (status 530)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://pump.fun",
        "Referer": "https://pump.fun/"
    }
    
    try:
        print("🔄 Fetching fresh tokens from Pump.fun API...", flush=True)
        resp = requests.get(url, headers=headers, timeout=5)
        
        if resp.status_code == 200:
            coins = resp.json()
            if not coins or not isinstance(coins, list):
                return
            
            print(f"📊 Total coins found: {len(coins)}", flush=True)
            
            for coin in coins:
                mint = coin.get("mint")
                if not mint or mint in seen_mints:
                    continue

                mcap = float(coin.get("usd_market_cap", 0) or 0)
                name = coin.get("name", "Unknown")
                symbol = coin.get("symbol", "UNKNOWN")
                twitter = coin.get("twitter", "")
                
                # Target range: $15k - $100k market cap and mandatory Twitter
                if 15000 <= mcap <= 100000 and twitter:
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
                        res = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=4)
                        print(f"✅ SENT TO N8N (${mcap / 1000:.2f}K): {name} (Status: {res.status_code})", flush=True)

        else:
            print(f"⚠️ Pump.fun API error status: {resp.status_code}", flush=True)

    except Exception as e:
        print(f"❌ Scanner fetch error: {e}", flush=True)

def main():
    print("🚀 Real-time Pump.fun scanner running...", flush=True)
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
