import asyncio
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import aiohttp

# Logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# ==============================================================================
# CONFIGURATION SETTINGS
# ==============================================================================
N8N_WEBHOOK_URL = "https://n8n-app-ok4t.onrender.com/webhook/pump-data"
PUMP_FUN_WS_URL = "wss://pumpportal.fun/api/data"
PORT = int(os.environ.get("PORT", 8080))


# Health Check Handler for Web Hosting Platforms (e.g., Render)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        return  # Suppress health check HTTP server logs


def run_health_check_server():
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, HealthCheckHandler)
    logging.info(f"Health check server running on port {PORT}")
    httpd.serve_forever()


# ==============================================================================
# N8N FORWARDER
# ==============================================================================
async def send_to_n8n(session, payload):
    try:
        async with session.post(N8N_WEBHOOK_URL, json=payload) as response:
            if response.status == 200:
                logging.info(f"Successfully sent data to n8n: {payload.get('mint', 'N/A')}")
            else:
                logging.error(f"Failed to send to n8n. Status: {response.status}")
    except Exception as e:
        logging.error(f"Error forwarding payload to n8n: {e}")


# ==============================================================================
# WEBSOCKET LISTENER
# ==============================================================================
async def listen_pump_fun():
    # Start health check server in background thread
    health_thread = threading.Thread(target=run_health_check_server, daemon=True)
    health_thread.start()

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                logging.info(f"Connecting to Pump.fun WebSocket: {PUMP_FUN_WS_URL}")
                async with session.ws_connect(PUMP_FUN_WS_URL) as ws:
                    logging.info("Connected to WebSocket. Subscribing to new token events...")
                    
                    # Subscribe payload
                    subscribe_payload = {"method": "subscribeNewToken"}
                    await ws.send_json(subscribe_payload)

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = msg.json()
                            logging.info(f"New token detected: {data.get('symbol', 'Unknown')}")
                            # Forward payload asynchronously to n8n
                            asyncio.create_task(send_to_n8n(session, data))
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logging.error(f"WebSocket connection closed with error: {ws.exception()}")
                            break
            except Exception as e:
                logging.error(f"WebSocket connection error: {e}. Reconnecting in 5 seconds...")
                await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(listen_pump_fun())
    except KeyboardInterrupt:
        logging.info("Program stopped by user.")
