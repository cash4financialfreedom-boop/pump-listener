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
    # Uporabimo endpoint za zadnje dodane profile/kovance na DexScreenerju
    url = "https://api.dexscreener.com/token-profiles/latest/v1"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        
        if resp.status_code == 200:
            profiles = resp.json()
            if not profiles or not isinstance(profiles, list):
                return
            
            for profile in profiles:
                if profile.get("chainId") != "solana":
                    continue
                
                mint = profile.get("tokenAddress")
                if not mint or mint in seen_mints:
                    continue

                # Sedaj za vsak najden svež token povlečemo še njegove dejanske podatke parov
                pair_url = f"https://api.dexscreener.com/latest/dex/tokens/{mint}"
                pair_resp = requests.get(pair_url, headers=headers, timeout=3)
                
                if pair_resp.status_code == 200:
                    pair_data = pair_resp.json()
                    pairs = pair_data.get("pairs", [])
                    if not pairs:
                        continue
                    
                    # Vzamemo prve solana pare
                    pair = next((p for p in pairs if p.get("chainId") == "solana"), None)
                    if not pair:
                        continue
                    
                    mcap = float(pair.get("fdv", 0) or pair.get("marketCap", 0) or 0)
                    base_token = pair.get("baseToken", {})
                    name = base_token.get("name", "Unknown")
                    
                    # Check for Twitter
                    socials = pair.get("info", {}).get("socials", [])
                    twitter = next((s.get("url") for s in socials if s.get("type") == "twitter"), "")
                    
                    # Če je MCAP med 15k in 100k ter ima Twitter, je točno to to!
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
                            print(f"✅ FOUND & SENT (${mcap / 1000:.2f}K): {name} | Twitter: {twitter}", flush=True)

        else:
            print(f"⚠️ API error status: {resp.status_code}", flush=True)

    except Exception as e:
        print(f"❌ Scanner fetch error: {e}", flush=True)

def main():
    print("🚀 Direct Token Profiles Scanner running...", flush=True)
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
