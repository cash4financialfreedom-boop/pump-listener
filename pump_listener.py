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


# Health Check Handler for Render
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        return


def run_health_check_server():
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, HealthCheckHandler)
    logging.info(f"Health check server running on port {PORT}")
    httpd.serve_forever()


# Fetch metadata (Twitter, Telegram, Website, Description) from token URI
async def fetch_token_metadata(session, uri):
    if not uri:
        return {}
    try:
        async with session.get(uri, timeout=5) as response:
            if response.status == 200:
                return await response.json()
    except Exception as e:
        logging.warning(f"Could not fetch metadata from {uri}: {e}")
    return {}


# Forward rich payload to n8n
async def send_to_n8n(session, payload):
    try:
        async with session.post(N8N_WEBHOOK_URL, json=payload) as response:
            if response.status == 200:
                logging.info(f"Sent enriched token data to n8n: {payload.get('symbol', 'N/A')} ({payload.get('mint', '')})")
            else:
                logging.error(f"Failed to send to n8n. Status: {response.status}")
    except Exception as e:
        logging.error(f"Error forwarding payload to n8n: {e}")


# Process each token event
async def process_token_event(session, data):
    uri = data.get("uri", "")
    metadata = await fetch_token_metadata(session, uri)

    # Combine WebSocket data with metadata
    enriched_data = {
        "mint": data.get("mint"),
        "name": data.get("name"),
        "symbol": data.get("symbol"),
        "traderPublicKey": data.get("traderPublicKey"),
        "uri": uri,
        "description": metadata.get("description", "No description provided"),
        "twitter": metadata.get("twitter", ""),
        "telegram": metadata.get("telegram", ""),
        "website": metadata.get("website", ""),
        "image": metadata.get("image", "")
    }

    await send_to_n8n(session, enriched_data)


# WebSocket Listener
async def listen_pump_fun():
    health_thread = threading.Thread(target=run_health_check_server, daemon=True)
    health_thread.start()

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                logging.info(f"Connecting to WebSocket: {PUMP_FUN_WS_URL}")
                async with session.ws_connect(PUMP_FUN_WS_URL) as ws:
                    logging.info("Connected. Subscribing to new tokens with viral metadata tracking...")
                    await ws.send_json({"method": "subscribeNewToken"})

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = msg.json()
                            logging.info(f"New token detected: {data.get('symbol', 'Unknown')}")
                            asyncio.create_task(process_token_event(session, data))
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logging.error(f"WebSocket error: {ws.exception()}")
                            break
            except Exception as e:
                logging.error(f"Connection error: {e}. Reconnecting in 5 seconds...")
                await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(listen_pump_fun())
    except KeyboardInterrupt:
        logging.info("Program stopped.")
