import asyncio
import json
import os
import sys
import threading
import websockets
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler

# Prisilni takojšnji izpis vseh dnevnikov v Render
sys.stdout.reconfigure(line_buffering=True)

# 1. MINIMALNI STREŽNIK ZA RENDER (Port 10000)
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        return

def start_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"--> [SYSTEM] Port {port} sproščen in aktiven.", flush=True)
    server.serve_forever()

# Zaženemo v ozadju
threading.Thread(target=start_health_server, daemon=True).start()

# 2. WEBSOCKET LISTENER ZA PUMP.FUN
N8N_URL = os.environ.get("N8N_WEBHOOK_URL", "https://n8n-app-ok4t.onrender.com/webhook/57fb4234-1188-44a0-a61d-381a17fa6b70")
PUMP_URL = "wss://pumpportal.fun/api/data"

async def main():
    print("--> [START] Skripta se zaganja...", flush=True)
    while True:
        try:
            print("--> [PUMP] Povezovanje na WebSocket...", flush=True)
            async with websockets.connect(PUMP_URL) as ws:
                await ws.send(json.dumps({"method": "subscribeNewToken"}))
                print("--> [PUMP] POVEZANO! Poslušam nove kovance...", flush=True)

                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    sym = data.get("symbol", "N/A")
                    print(f"--> [ZAZNAN KOVANEC] {sym} -> Pošiljam v n8n...", flush=True)

                    try:
                        res = requests.post(N8N_URL, json=data, timeout=5)
                        print(f"--> [N8N ODGOVOR] Status: {res.status_code}", flush=True)
                    except Exception as err:
                        print(f"--> [N8N NAPAKA] {err}", flush=True)

        except Exception as e:
            print(f"--> [NAPAKA PREKINITVE] {e}. Ponoven poskus čez 5s...", flush=True)
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
