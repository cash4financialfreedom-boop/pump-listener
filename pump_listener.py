import asyncio
import json
import os
import threading
import websockets
import requests
from flask import Flask

# Flask app to keep Render Web Service happy
app = Flask(__name__)

# Replace with your actual n8n Webhook URL if needed
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "https://alphasniffer.app.n8n.cloud/webhook/6bf47bed-b6a7-4bfa-acea-e49debdbe34")

@app.route('/')
def health_check():
    return "Pump Listener is active and running 24/7!", 200

def send_to_n8n(data):
    try:
        requests.post(N8N_WEBHOOK_URL, json=data, timeout=5)
    except Exception as e:
        print(f"Error sending payload to n8n: {e}")

async def listen_pump():
    uri = "wss://pumpportal.fun/api/data"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print(" Connected to Pump.fun! Listening for new tokens...")
                payload = {"method": "subscribeNewToken"}
                await websocket.send(json.dumps(payload))

                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if "mint" in data:
                            token_name = data.get('name', 'Unknown')
                            token_symbol = data.get('symbol', '')
                            print(f" New token detected: {token_name} ({token_symbol})")
                            
                            # Run HTTP request in a background thread so asyncio loop doesn't freeze
                            threading.Thread(target=send_to_n8n, args=(data,)).start()

                    except Exception as e:
                        print(f"Error processing message: {e}")

        except Exception as e:
            print(f"Connection dropped ({e}), retrying in 5 seconds...")
            await asyncio.sleep(5)

def start_async_loop():
    asyncio.run(listen_pump())

if __name__ == "__main__":
    # Start WebSocket listener in a separate background thread
    listener_thread = threading.Thread(target=start_async_loop)
    listener_thread.daemon = True
    listener_thread.start()

    # Start Flask Web Server for Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
