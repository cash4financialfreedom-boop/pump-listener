import asyncio
import json
import os
import websockets
import requests
from aiohttp import web

N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "https://alphasniffer.app.n8n.cloud/webhook/6bf47bed-b6a7-4bfa-acea-e49debdbe34")

# Basic HTTP handler for Render health checks
async def handle_ping(request):
    return web.Response(text="Pump Listener is active!")

async def send_to_n8n(data):
    try:
        # Run blocking post request in default executor so asyncio loop stays fast
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: requests.post(N8N_WEBHOOK_URL, json=data, timeout=5))
    except Exception as e:
        print(f"Error sending payload to n8n: {e}")

async def listen_pump():
    uri = "wss://pumpportal.fun/api/data"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print("Connected to Pump.fun! Listening for new tokens...")
                payload = {"method": "subscribeNewToken"}
                await websocket.send(json.dumps(payload))

                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if "mint" in data:
                            token_name = data.get('name', 'Unknown')
                            token_symbol = data.get('symbol', '')
                            print(f"New token detected: {token_name} ({token_symbol})")
                            asyncio.create_task(send_to_n8n(data))

                    except Exception as e:
                        print(f"Error processing message: {e}")

        except Exception as e:
            print(f"Connection dropped ({e}), retrying in 5 seconds...")
            await asyncio.sleep(5)

async def start_background_tasks(app):
    app['pump_task'] = asyncio.create_task(listen_pump())

async def cleanup_background_tasks(app):
    app['pump_task'].cancel()
    await app['pump_task']

def main():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)

    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
