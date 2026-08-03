import asyncio
import logging
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import aiohttp

# Logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# ==========================================
# CONFIGURATION SETTINGS
# ==========================================
# Fetch n8n Webhook URL from environment variables or fallback to default
N8N_WEBHOOK_URL = os.getenv(
    "N8N_WEBHOOK_URL",
    "https://n8n-app-ok4t.onrender.com/webhook/pump-token-check",
)

MIN_MARKET_CAP_USD = 40000.0  # Minimum $40k Market Cap
CHECK_INTERVAL_SECONDS = 10  # Polling interval in seconds

# Set to track processed tokens to avoid duplicate triggers
seen_tokens = set()


# Lightweight HTTP server to satisfy Render health checks
class HealthCheckHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Pump Listener Service is Running")


def run_health_check_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logging.info(f"Health check server running on port {port}")
    server.serve_forever()


async def send_to_n8n(session, token_data):
    """Sends token payload to n8n Webhook."""
    try:
        async with session.post(N8N_WEBHOOK_URL, json=token_data) as resp:
            if resp.status == 200:
                logging.info(
                    f"Successfully sent to n8n: {token_data.get('symbol')}"
                )
            else:
                logging.error(f"Failed to send to n8n: HTTP Status {resp.status}")
    except Exception as e:
        logging.error(f"Exception occurred while sending to n8n: {e}")


async def fetch_and_process_tokens(session):
    """Fetches latest token profiles from Solana network and filters Market Cap >= $40k."""
    try:
        url = "https://api.dexscreener.com/token-profiles/latest/v1"
        async with session.get(url) as resp:
            if resp.status != 200:
                return

            profiles = await resp.json()
            if not isinstance(profiles, list):
                return

            for item in profiles:
                if item.get("chainId") != "solana":
                    continue

                token_address = item.get("tokenAddress")
                if not token_address or token_address in seen_tokens:
                    continue

                # Fetch detailed pair and market cap info
                pair_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
                async with session.get(pair_url) as pair_resp:
                    if pair_resp.status != 200:
                        continue

                    pair_data = await pair_resp.json()
                    pairs = pair_data.get("pairs", [])
                    if not pairs:
                        continue

                    # Process primary pair
                    main_pair = pairs[0]
                    market_cap = main_pair.get("fdv", 0) or main_pair.get(
                        "marketCap", 0
                    )

                    if market_cap >= MIN_MARKET_CAP_USD:
                        seen_tokens.add(token_address)

                        info = main_pair.get("baseToken", {})
                        websites = main_pair.get("info", {}).get("websites", [])
                        socials = main_pair.get("info", {}).get("socials", [])

                        payload = {
                            "name": info.get("name", "Unknown"),
                            "symbol": info.get("symbol", "Unknown"),
                            "tokenAddress": token_address,
                            "marketCap": market_cap,
                            "pairUrl": main_pair.get("url", ""),
                            "description": main_pair.get("info", {})
                            .get("header", "")
                            .strip(),
                            "websites": [
                                w.get("url") for w in websites if "url" in w
                            ],
                            "socials": [
                                s.get("url") for s in socials if "url" in s
                            ],
                            "dex": main_pair.get("dexId", ""),
                        }

                        logging.info(
                            f"Qualified token found: {payload['symbol']} (MC: ${market_cap:,.2f})"
                        )
                        await send_to_n8n(session, payload)

    except Exception as e:
        logging.error(f"Error in token processing loop: {e}")


async def main_loop():
    async with aiohttp.ClientSession() as session:
        while True:
            await fetch_and_process_tokens(session)
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    # Start health check server in background thread for Render
    health_thread = threading.Thread(
        target=run_health_check_server, daemon=True
    )
    health_thread.start()

    # Start main event loop
    logging.info("Starting Pump Listener service...")
    asyncio.run(main_loop())
