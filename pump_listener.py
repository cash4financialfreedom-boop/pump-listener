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
DEXSCREENER_LATEST_PROFILES_URL = "https://api.dexscreener.com/token-profiles/latest/v1"
DEXSCREENER_PAIRS_URL = "https://api.dexscreener.com/latest/dex/tokens/"
MIN_MARKET_CAP_USD = 35000.0  # Threshold: Min $35,000 Market Cap on DEX
CHECK_INTERVAL_SECONDS = 10
PORT = int(os.environ.get("PORT", 8080))

# Memory cache to prevent duplicate processing of the same token
processed_tokens = set()


# Health Check Handler for Web Hosting Platforms (e.g., Render)
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


# Forward rich payload to n8n
async def send_to_n8n(session, payload):
    try:
        async with session.post(N8N_WEBHOOK_URL, json=payload) as response:
            if response.status == 200:
                logging.info(
                    f"🚀 DEX TOKEN WITH TWITTER PASSED (>35k MC)! Sent to n8n: {payload.get('symbol', 'N/A')} "
                    f"| MCap: ${payload.get('market_cap', 0):,.2f} | Twitter: {payload.get('twitter')} | Mint: {payload.get('mint', '')}"
                )
            else:
                logging.error(f"Failed to send to n8n. Status: {response.status}")
    except Exception as e:
        logging.error(f"Error forwarding payload to n8n: {e}")


# Process token on DEX
async def process_dex_token(session, profile):
    token_address = profile.get("tokenAddress")
    chain_id = profile.get("chainId")

    # Target only Solana tokens that have not been processed yet
    if chain_id != "solana" or not token_address or token_address in processed_tokens:
        return

    try:
        # Fetch detailed market data from DexScreener
        async with session.get(f"{DEXSCREENER_PAIRS_URL}{token_address}", timeout=5) as response:
            if response.status == 200:
                res_data = await response.json()
                pairs = res_data.get("pairs") or []
                if not pairs:
                    return

                # Select the highest volume / main Solana pair
                main_pair = pairs[0]
                market_cap = float(main_pair.get("marketCap") or main_pair.get("fdv") or 0)

                # 1. Check Market Cap (>= $35,000 USD)
                if market_cap >= MIN_MARKET_CAP_USD:
                    info = main_pair.get("info", {})
                    socials = info.get("socials", [])
                    websites = info.get("websites", [])

                    twitter = next((s.get("url") for s in socials if s.get("type") == "twitter"), "")

                    # 2. STRICT REQUIREMENT: Must have a valid Twitter/X link!
                    if not twitter:
                        logging.info(f"Skipping {token_address} (>35k MC) - No Twitter/X link found.")
                        return

                    processed_tokens.add(token_address)
                    telegram = next((s.get("url") for s in socials if s.get("type") == "telegram"), "")
                    website = websites[0].get("url") if websites else ""

                    enriched_data = {
                        "mint": token_address,
                        "name": main_pair.get("baseToken", {}).get("name", "Unknown"),
                        "symbol": main_pair.get("baseToken", {}).get("symbol", "Unknown"),
                        "market_cap": market_cap,
                        "liquidity_usd": main_pair.get("liquidity", {}).get("usd", 0),
                        "volume_24h": main_pair.get("volume", {}).get("h24", 0),
                        "dex": main_pair.get("dexId", "raydium"),
                        "pair_url": main_pair.get("url", ""),
                        "description": profile.get("description", "No description provided"),
                        "twitter": twitter,
                        "telegram": telegram,
                        "website": website,
                        "image": profile.get("icon", "")
                    }

                    await send_to_n8n(session, enriched_data)
    except Exception as e:
        logging.warning(f"Error processing token {token_address}: {e}")


# Main DexScreener Scanner Loop
async def scan_dexscreener():
    health_thread = threading.Thread(target=run_health_check_server, daemon=True)
    health_thread.start()

    async with aiohttp.ClientSession() as session:
        logging.info("Starting DexScreener scanner for Solana DEX tokens (>35k MC + MUST HAVE TWITTER)...")
        while True:
            try:
                async with session.get(DEXSCREENER_LATEST_PROFILES_URL, timeout=10) as response:
                    if response.status == 200:
                        profiles = await response.json()
                        tasks = [process_dex_token(session, p) for p in profiles]
                        await asyncio.gather(*tasks)
            except Exception as e:
                logging.error(f"Error fetching DexScreener profiles: {e}")

            await asyncio.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        asyncio.run(scan_dexscreener())
    except KeyboardInterrupt:
        logging.info("Program stopped.")
