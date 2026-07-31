import asyncio
import json
import os
import threading
import websockets
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==========================================
# 1. HEALTH CHECK SERVER FOR RENDER (PORT 10000)
# ==========================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        # Onemogoči smetenje HTTP logov v Render konzoli
        return

def run_health_check():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"--> [SYSTEM] Health Check server successfully running on port {port}")
    server.serve_forever()

# Zaženemo Health Check v ločeni niti (thread-u)
threading.Thread(target=run_health_check, daemon=True).start()

# ==========================================
# 2. CONFIGURATION & WEBSOCKET LISTENER
# ==========================================
# n8n Webhook URL pridobi iz okoljskih spremenljivk na Renderju (ali uporabi rezervni URL)
N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "YOUR_N8N_WEBHOOK_URL_HERE")
PUMP_PORTAL_URL = "wss://pumpportal.fun/api/data"

async def listen_pump_portal():
    while True:
        try:
            print("--> [PUMPPORTAL] Connecting to WebSocket...")
            async with websockets.connect(PUMP_PORTAL_URL) as ws:
                # Naročimo se na ustvarjanje novih žetonov (New Tokens)
                payload = {"method": "subscribeNewToken"}
                await ws.send(json.dumps(payload))
                print("--> [PUMPPORTAL] Successfully connected! Listening for new tokens...")

                while True:
                    message = await ws.recv()
                    data = json.loads(message)

                    # Izpis v konzolo za preverjanje delovanja
                    token_symbol = data.get("symbol", "N/A")
                    mint = data.get("mint", "N/A")
                    print(f"--> [NEW TOKEN] Detected: {token_symbol} ({mint})")

                    # Pošiljanje podatkov v n8n za nadaljnjo obdelavo
                    try:
                        response = requests.post(N8N_WEBHOOK_URL, json=data, timeout=5)
                        if response.status_code == 200:
                            print(f"--> [N8N] Data for {token_symbol} successfully sent to n8n.")
                        else:
                            print(f"--> [N8N WARNING] n8n returned status code: {response.status_code}")
                    except Exception as req_err:
                        print(f"--> [N8N ERROR] Failed to send data to n8n: {req_err}")

        except Exception as e:
            print(f"[ERROR] Connection lost/failed: {e}")
            print("--> Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(listen_pump_portal())
