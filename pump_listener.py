import asyncio
import websockets
import json
import aiohttp
import os
from aiohttp import web

# Your new Webhook URL from your Render n8n server:
N8N_WEBHOOK_URL = "https://n8n-app-ok4t.onrender.com/webhook/6bf47bed-b6a7-4bfa-acea-e49deebdbe34"

async def listen_pump():
    uri = "wss://pumpportal.fun/api/data"
    
    async for websocket in websockets.connect(uri):
        try:
            # Subscribe to new tokens on pump.fun
            payload = {
                "method": "subscribeNewToken"
            }
            await websocket.send(json.dumps(payload))
            print("Connected to PumpPortal WebSocket... Listening for new tokens.")

            async for message in websocket:
                data = json.loads(message)
                
                # Check if data contains info about a new token
                if "signature" in data or "mint" in data:
                    print(f"New token detected: {data.get('mint', 'Unknown')}")
                    
                    # Send data to n8n Webhook
                    async with aiohttp.ClientSession() as session:
                        try:
                            async with session.post(N8N_WEBHOOK_URL, json=data) as response:
                                print(f"Sent to n8n! Status: {response.status}")
                        except Exception as e:
                            print(f"Error sending to n8n: {e}")

        except websockets.ConnectionClosed:
            print("Connection closed, reconnecting in 5 seconds...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Unexpected error: {e}")
            await asyncio.sleep(5)

async def handle_ping(request):
    return web.Response(text="Pump Listener is running!")

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
