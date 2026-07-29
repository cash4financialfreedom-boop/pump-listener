import os
import json
import asyncio
import requests
from threading import Thread
from flask import Flask
import websockets

# --- FLASK SERVER ZARADI RENDER BREZPLAČNEGA PORTA ---
app = Flask('')

@app.route('/')
def home():
    return "Pump listener is running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_flask, daemon=True).start()

# --- PUMP.FUN POSLUŠALEC ---
N8N_WEBHOOK_URL = "https://alphasniffer.app.n8n.cloud/webhook/6bf47bed-b6a7-4bfa-acea-e49debdbe34"

async def listen_pump():
    uri = "wss://pumpportal.fun/api/data"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print("✅ Povezano na Pump.fun! Poslušam nove kovance...")
                
                # Naročimo se na nove ustvarjene token-e
                payload = {"method": "subscribeNewToken"}
                await websocket.send(json.dumps(payload))
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if "mint" in data:
                            print(f"🚀 Nov kovanec zaznan: {data.get('name', 'Neznano')} ({data.get('symbol', '')})")
                            # Pošljemo podatke na n8n Webhook
                            requests.post(N8N_WEBHOOK_URL, json=data, timeout=5)
                    except Exception as e:
                        print(f"Napaka pri obdelavi sporočila: {e}")
                        
        except Exception as e:
            print(f"Povezava prekineja ({e}), ponovni poskus čez 5 sekund...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(listen_pump())
