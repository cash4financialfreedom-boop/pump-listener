import asyncio
import websockets
import json
import aiohttp
import os
from aiohttp import web

N8N_WEBHOOK_URL = "https://n8n-app-ok4t.onrender.com/webhook/6bf47bed-b6a7-4bfa-acea-e49deebdbe34"

# Set threshold in SOL (e.g. 100 SOL in bonding curve is roughly $20k MC depending on SOL price)
MIN_MARKET_CAP_SOL = 270.0

# Keep track of tokens we already alerted to avoid spamming the same token
alerted_tokens = set()

async def listen_pump():
    uri = "wss://pumpportal.fun/api/data"
    
    async for websocket in websockets.connect(uri):
        try:
            # Subscribe to trades instead of just new tokens to measure volume/MC growth
            payload = {
                "method": "subscribeTokenTrade"
            }
            await websocket.send(json.dumps(payload))
            print("Connected to PumpPortal... Monitoring trade volume for $20k+ MC.")

            async for message in websocket:
                data = json.loads(message)
                
                if isinstance(data, dict) and "mint" in data:
                    mint = data.get("mint")
                    market_cap_sol = data.get("marketCapSol", 0)
                    
                    # Check if market cap reached threshold and hasn't been sent yet
                    if market_cap_sol >= MIN_MARKET_CAP_SOL and mint not in alerted_tokens:
                        alerted_tokens.add(mint)
                        print(f"🔥 HIGH MC TOKEN DETECTED ({market_cap_sol} SOL): {data.get('symbol')} - {mint}")
                        
                        payload_to_n8n = {
                            "name": data.get("name", "Unknown"),
                            "symbol": data.get("symbol", "Unknown"),
                            "mint": mint,
                            "uri": data.get("uri", ""),
                            "marketCapSol": market_cap_sol
                        }
                        
                        async with aiohttp.ClientSession() as session:
                            try:
                                async with session.post(N8N_WEBHOOK_URL, json=payload_to_n8n) as response:
                                    print(f"Sent to n8n! Status: {response.status}")
                            except Exception as e:
                                print(f"Error sending to n8n: {e}")

        except websockets.ConnectionClosed:
            await asyncio.sleep(5)
        except Exception as e:
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
