import os
import time
import json
import requests
import threading
from flask import Flask

# Flask app to satisfy Render's port check
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot is running perfectly!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# Configuration
N8N_WEBHOOK_URL = "https://n8n-app-ok4t.onrender.com/webhook/jYXi3ljaQnh9xOpG"
MIN_MARKET_CAP_USD = 50000

def get_token_market_cap(mint_address):
    """
    Fetches the current Market Cap (FDV) from DexScreener API.
    """
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{mint_address}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            pairs = data.get('pairs')
            if pairs and len(pairs) > 0:
                pair = pairs[0]
                fdv = pair.get('fdv', 0)
                market_cap = pair.get('marketCap', fdv)
                return float(market_cap) if market_cap else 0.0
    except Exception as e:
        print(f"[ERROR] Failed to fetch market cap for {mint_address}: {e}")
    return 0.0

def process_token_migration(token_data):
    """
    Filters token by Market Cap threshold ($50k+) and sends valid tokens to n8n Webhook.
    """
    mint = token_data.get('mint')
    name = token_data.get('name', 'Unknown')
    symbol = token_data.get('symbol', 'UNKNOWN')

    print(f"\n🚀 [RAYDIUM MIGRATION DETECTED] Token: {name} (${symbol}) | Mint: {mint}")

    time.sleep(3)

    market_cap = get_token_market_cap(mint)
    print(f"📊 [MARKET CAP CHECK] {symbol}: ${market_cap:,.2f}")

    if market_cap >= MIN_MARKET_CAP_USD:
        print(f"✅ [PASSED FILTER] Market cap is >= ${MIN_MARKET_CAP_USD:,.0f}. Forwarding to n8n...")
        
        payload = {
            "name": name,
            "symbol": symbol,
            "mint": mint,
            "description": token_data.get('description', ''),
            "image": token_data.get('image', ''),
            "socials": token_data.get('socials', {}),
            "marketCap": market_cap
        }

        try:
            response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=5)
            print(f"--> [N8N SUCCESS] Status Code: {response.status_code}")
        except Exception as e:
            print(f"--> [N8N ERROR] Failed to send notification: {e}")
    else:
        print(f"⛔ [REJECTED] Market cap (${market_cap:,.2f}) is below the ${MIN_MARKET_CAP_USD:,.0f} threshold.")

if __name__ == "__main__":
    # Start Flask server in a background thread for Render health check
    threading.Thread(target=run_flask, daemon=True).start()
    
    print(f"🟢 [SYSTEM ACTIVE] Pump.fun migration listener started.")
    print(f"🎯 [FILTER SET] Minimum Market Cap threshold: ${MIN_MARKET_CAP_USD:,.0f}")
    
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break
