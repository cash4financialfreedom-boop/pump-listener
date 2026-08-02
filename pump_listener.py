import os
import time
import json
import requests
import threading
import asyncio
import websockets
from flask import Flask

# ------------------------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------------------------
N8N_WEBHOOK_URL = "https://n8n-app-ok4t.onrender.com/webhook/jyxi3ljaQnh9xOpG"
MIN_MARKET_CAP_USD = 20000.0  # Updated threshold to $20k USD
PUMP_WS_URI = "wss://pumpportal.fun/api/data"

# Set to store recently processed tokens to prevent duplicate alerts
processed_mints = set()

# ------------------------------------------------------------------------------
# FLASK SERVER (Satisfies Render Port Check)
# ------------------------------------------------------------------------------
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Pump Listener is running healthy!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ------------------------------------------------------------------------------
# WEBSOCKET & SIGNAL PROCESSING
# ------------------------------------------------------------------------------
def process_token_data(data):
    """Processes incoming token payload without GPT interference."""
    mint = data.get("mint")
    if not mint or mint in processed_mints:
        return

    # Extract market cap or valuation parameters
    market_cap = data.get("marketCapSol") or data.get("usd_market_cap") or data.get("vTokensInBondingCurve", 0)
    
    # Check if market cap meets the updated $20k threshold
    if market_cap and float(market_cap) >= MIN_MARKET_CAP_USD:
        print(f"[MATCH FOUND] Token: {mint} | Market Cap: {market_cap}", flush=True)
        processed_mints.add(mint)
        
        # Send payload straight to n8n Webhook / Telegram Pipeline
        try:
            response = requests.post(N8N_WEBHOOK_URL, json=data, timeout=10)
            print(f"[SENT TO N8N] Status Code: {response.status_code}", flush=True)
        except Exception as e:
            print(f"[ERROR] Failed to send webhook: {e}", flush=True)

async def listen_pump_websocket():
    """Connects to PumpPortal WebSocket and listens for token events."""
    while True:
        try:
            async with websockets.connect(PUMP_WS_URI) as websocket:
                print("[CONNECTED] Listening to PumpPortal WebSocket...", flush=True)
                
                # Subscribe to new token trades / migration events
                payload = {
                    "method": "subscribeNewToken"
                }
                await websocket.send(json.dumps(payload))

                async for message in websocket:
                    try:
                        data = json.loads(message)
                        process_token_data(data)
                    except Exception as parse_error:
                        print(f"[PARSE ERROR] {parse_error}", flush=True)

        except Exception as ws_error:
            print(f"[WEBSOCKET DISCONNECTED] Retrying in 5 seconds... Error: {ws_error}", flush=True)
            await asyncio.sleep(5)

def start_async_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(listen_pump_websocket())

# ------------------------------------------------------------------------------
# MAIN ENTRY POINT
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    # Start Flask server in background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Start WebSocket listener in main loop
    start_async_loop()
