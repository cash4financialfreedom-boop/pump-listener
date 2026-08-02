import os
import time
import json
import requests
import threading
import asyncio
import websockets
from flask import Flask

# ------------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------------
N8N_WEBHOOK_URL = "https://n8n-app-ok4t.onrender.com/webhook/jYXi3ljaQnh9xOpG"
MIN_MARKET_CAP_USD = 50000.0
PUMP_WS_URL = "wss://pumpportal.fun/api/data"

# Set to store recently processed tokens to prevent duplicates
processed_mints = set()

# Flask server to satisfy Render port check
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Pump Listener Bot is active and listening!", 200

def run_flask_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ------------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------------
def get_token_market_cap(mint_address):
    """
    Fetches Market Cap / FDV from DexScreener API.
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
        print(f"[ERROR] Price check failed for {mint_address}: {e}")
    return 0.0

def process_token_migration(token_data):
    """
    Evaluates token Market Cap and sends payload to n8n if threshold ($50k) is met.
    """
    mint = token_data.get('mint', token_data.get('address', ''))
    name = token_data.get('name', 'Unknown')
    symbol = token_data.get('symbol', 'UNKNOWN')

    if not mint or mint in processed_mints:
        return
    
    # Mark as processed to prevent duplicates
    processed_mints.add(mint)
    if len(processed_mints) > 1000:
        processed_mints.clear()

    print(f"\n🚀 [RAYDIUM MIGRATION DETECTED] {name} (${symbol}) | Mint: {mint}")

    # Delay to allow DexScreener indexing
    time.sleep(3)

    market_cap = get_token_market_cap(mint)
    print(f"📊 [MARKET CAP CHECK] {symbol}: ${market_cap:,.2f}")

    if market_cap >= MIN_MARKET_CAP_USD:
        print(f"✅ [PASSED FILTER] Market Cap (${market_cap:,.2f}) >= ${MIN_MARKET_CAP_USD:,.0f}. Sending to n8n...")
        
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
            print(f"--> [N8N SUCCESS] Response Status: {res.status_code}")
        except Exception as e:
            print(f"--> [N8N ERROR] Push failed: {e}")
    else:
        print(f"⛔ [REJECTED] Market Cap (${market_cap:,.2f}) is below ${MIN_MARKET_CAP_USD:,.0f}.")

# ------------------------------------------------------------------
# WEBSOCKET LISTENER (SOLANA / PUMP.FUN MIGRATIONS)
# ------------------------------------------------------------------
async def listen_pump_migrations():
    while True:
        try:
            async with websockets.connect(PUMP_WS_URL) as websocket:
                # Subscribe to migration events (raydium / pumpswap)
                payload = {"method": "subscribeRaydiumLiquidity"}
                await websocket.send(json.dumps(payload))
                print("📡 [WEBSOCKET CONNECTED] Listening for Raydium migrations...")

                while True:
                    message = await websocket.recv()
                    data = json.loads(message)
                    
                    # Extract migration payload
                    if isinstance(data, dict):
                        # Process in thread so websocket doesn't block on price delay
                        threading.Thread(target=process_token_migration, args=(data,), daemon=True).start()

        except Exception as e:
            print(f"⚠️ [WEBSOCKET DISCONNECTED] Reconnecting in 3s... ({e})")
            await asyncio.sleep(3)

# ------------------------------------------------------------------
# MAIN EXECUTION
# ------------------------------------------------------------------
if __name__ == "__main__":
    # Start Flask background server for Render Port Check
    threading.Thread(target=run_flask_server, daemon=True).start()

    print("🟢 [SYSTEM STARTED] Solana Pump.fun Listener initializing...")
    print(f"🎯 [FILTER SET] Minimum Market Cap threshold: ${MIN_MARKET_CAP_USD:,.0f} USD")

    # Start WebSocket event loop
    asyncio.run(listen_pump_migrations())
