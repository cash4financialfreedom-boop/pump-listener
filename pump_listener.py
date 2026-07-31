import asyncio
import json
import os
import sys
import threading
import websockets
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler

# Immediate line buffering for logs in Render
sys.stdout.reconfigure(line_buffering=True)

# 1. MINIMAL HEALTH CHECK SERVER FOR RENDER (Port 10000)
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
        
    def log_message(self, format, *args):
        return  # Suppress HTTP health check log noise

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"--> Health check server running on port {port}")
    server.serve_forever()

# 2. PUMPPORTAL WEBSOCKET LISTENER FOR RAYDIUM MIGRATIONS
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "https://n8n-app-ok4t.onrender.com/webhook/pump-data")

async def listen_raydium_migrations():
    uri = "wss://pumpportal.fun/api/data"
    
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print("--> Connected to PumpPortal WebSocket. Subscribing to Raydium migrations...")
                
                # Subscribe exclusively to Raydium liquidity migration events
                payload = {
                    "method": "subscribeRaydiumLiquidity"
                }
                await websocket.send(json.dumps(payload))
                
                async for message in websocket:
                    data = json.loads(message)
                    
                    # Verify if liquidity was successfully added to Raydium
                    if "signature" in data or "mint" in data:
                        mint = data.get("mint", "Unknown Mint")
                        print(f"🚀 [RAYDIUM MIGRATION DETECTED] Token: {mint} -> Sending to n8n...")
                        
                        try:
                            # Forward event payload to n8n for GPT analysis
                            response = requests.post(N8N_WEBHOOK_URL, json=data, timeout=5)
                            print(f"--> [N8N RESPONSE] Status: {response.status_code}")
                        except Exception as e:
                            print(f"--> Error sending data to n8n: {e}")
                            
        except Exception as e:
            print(f"--> Connection dropped ({e}). Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    # Start health server in a background thread for Render
    threading.Thread(target=run_health_server, daemon=True).start()
    
    # Run the WebSocket listener
    asyncio.run(listen_raydium_migrations())
