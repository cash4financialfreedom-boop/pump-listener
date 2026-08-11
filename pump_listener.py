import os
import time
import threading
import requests
from flask import Flask

# --- FLASK SERVER ZA RENDER ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Pump Listener is Running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# --- NASTAVITVE ---
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")

def fetch_and_filter(seen_mints):
    url = "https://api.dexscreener.com/latest/dex/search?q=pump"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            pairs = data.get("pairs", [])
            print(f"🔄 Preverjam {len(pairs)} parov iz DexScreenerja...", flush=True)
            
            for pair in pairs:
                if pair.get("chainId") != "solana":
                    continue
                
                base_token = pair.get("baseToken", {})
                mint = base_token.get("address")
                if not mint or mint in seen_mints:
                    continue

                mcap = float(pair.get("fdv", 0) or pair.get("marketCap", 0) or 0)
                name = base_token.get("name", "Unknown")
                
                # Preverimo, če obstaja Twitter v socialnih povezavah
                socials = pair.get("info", {}).get("socials", [])
                twitter = next((s.get("url") for s in socials if s.get("type") == "twitter"), "")

                # POGOJI: Tržna kapitalizacija do 100k in da ima Twitter
                is_target = (mcap <= 100000)

                if is_target and twitter:
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
                        print(f"✅ POSLAN TOKEN (${mcap / 1000:.2f}K): {name}", flush=True)

    except Exception as e:
        print(f"Napaka pri branju: {e}", flush=True)

def main():
    print("🚀 Skener deluje v čistem načinu in neprekinjeno preverja trg...", flush=True)
    seen_mints = set()
    while True:
        fetch_and_filter(seen_mints)
        if len(seen_mints) > 1000:
            seen_mints.clear()
        time.sleep(5)

if __name__ == "__main__":
    # Najprej zaženemo Flask v ozadju za Renderjeve zahteve
    threading.Thread(target=run_flask, daemon=True).start()
    # Takoj za tem pa poženemo glavno zanko skenerja
    main()
