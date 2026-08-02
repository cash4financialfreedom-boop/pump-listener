import os
import time
import json
import requests
import threading
from flask import Flask

# ------------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------------
N8N_WEBHOOK_URL = "https://n8n-app-ok4t.onrender.com/webhook/jYXi3ljaQnh9xOpG"
MIN_MARKET_CAP_USD = 50000.0

# Flask server to pass Render's health check & prevent service shutdowns
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Pump Listener Bot is active and running!", 200

def run_flask_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ------------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------------
def get_token_market_cap(mint_address):
    """
    Fetches the actual Market Cap / FDV from DexScreener API.
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

def process_migration_event(token_data):
    """
    Evaluates token Market Cap and sends payload to n8n if threshold ($50k) is met.
    """
    mint = token_data.get('mint', token_data.get('address', ''))
    name = token_data.get('name', 'Unknown Token')
    symbol = token_data.get('symbol', 'UNKNOWN')

    if not mint:
        return

    print(f"\n🚀 [RAYDIUM MIGRATION DETECTED] Token: {name} (${symbol}) | Mint: {mint}")

    # Allow DexScreener 3 seconds to index liquidity pools after migration
    time.sleep(3)

    market_cap = get_token_market_cap(mint)
    print(f"📊 [MARKET CAP CHECK] {symbol}: ${market_cap:,.2f}")

    if market_cap >= MIN_MARKET_CAP_USD:
        print(f"✅ [PASSED FILTER] Market cap (${market_cap:,.2f}) >= ${MIN_MARKET_CAP_USD:,.0f}. Sending to n8n...")
        
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
            res = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=5)
            print(f"--> [N8N SUCCESS] Response Status Code: {res.status_code}")
        except Exception as e:
            print(f"--> [N8N ERROR] Failed to push data: {e}")
    else:
        print(f"⛔ [REJECTED] Market cap (${market_cap:,.2f}) is below ${MIN_MARKET_CAP_USD:,.0f} threshold.")

# ------------------------------------------------------------------
# MAIN EXECUTION
# ------------------------------------------------------------------
if __name__ == "__main__":
    # Start Flask background thread for Render Port Binding
    threading.Thread(target=run_flask_server, daemon=True).start()

    print("🟢 [SYSTEM INITIALIZED] Solana Pump.fun Migration Listener Started.")
    print(f"🎯 [FILTER THRESHOLD] Min Market Cap: ${MIN_MARKET_CAP_USD:,.0f} USD")

    # Main application loop
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            print("Shutting down listener...")
            break
