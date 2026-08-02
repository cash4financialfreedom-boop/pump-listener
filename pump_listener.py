import asyncio
import logging
import aiohttp

# ==========================================
# CONFIGURATION SETTINGS
# ==========================================
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"

# Filter Thresholds
MIN_MARKET_CAP_USD = 40000.0  # Minimum $40k Market Cap
CHECK_INTERVAL_SECONDS = 5    # Polling frequency in seconds

# API Endpoints
DEX_SCREENER_API = "https://api.dexscreener.com/latest/dex/tokens/"
# Add any specific list of newly migrated contract addresses to monitor, or hook into your WebSocket/RPC feed
WATCH_LIST = [
    # Example Contract Addresses (CAs) to track
]

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Keep track of already notified tokens to prevent spam
notified_tokens = set()


async def send_telegram_alert(token_data: dict):
    """
    Sends a formatted alert message to Telegram.
    """
    message = (
        f"🚨 **HIGH-VALUE MIGRATION DETECTED** 🚨\n\n"
        f"🪙 **Token:** {token_data['name']} (`${token_data['symbol']}`)\n"
        f"💰 **Market Cap:** ${token_data['market_cap']:,.2f}\n"
        f"💧 **Liquidity:** ${token_data['liquidity']:,.2f}\n"
        f"📊 **5M Volume:** ${token_data['volume_5m']:,.2f}\n"
        f"🔄 **5M Transactions:** {token_data['buys_5m']} Buys / {token_data['sells_5m']} Sells\n\n"
        f"📝 **CA:** `{token_data['address']}`\n\n"
        f"🔗 [View on DEX Screener](https://dexscreener.com/solana/{token_data['address']})"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    logging.info(f"Successfully sent Telegram alert for {token_data['symbol']}")
                else:
                    logging.error(f"Failed to send Telegram alert: Status {response.status}")
    except Exception as e:
        logging.error(f"Error sending Telegram message: {e}")


async def fetch_token_metrics(session: aiohttp.ClientSession, token_address: str):
    """
    Fetches live token data from DEX Screener API and checks criteria.
    """
    url = f"{DEX_SCREENER_API}{token_address}"
    try:
        async with session.get(url) as response:
            if response.status != 200:
                return

            data = await response.json()
            pairs = data.get("pairs")

            if not pairs:
                return

            # Grab the primary DEX pair (PumpSwap or Raydium)
            pair = pairs[0]
            market_cap = float(pair.get("fdv", 0) or 0)

            # Filter Check: Must be >= $40,000 USD Market Cap
            if market_cap >= MIN_MARKET_CAP_USD and token_address not in notified_tokens:
                token_info = {
                    "name": pair.get("baseToken", {}).get("name", "Unknown"),
                    "symbol": pair.get("baseToken", {}).get("symbol", "UNKNOWN"),
                    "address": token_address,
                    "market_cap": market_cap,
                    "liquidity": float(pair.get("liquidity", {}).get("usd", 0) or 0),
                    "volume_5m": float(pair.get("volume", {}).get("m5", 0) or 0),
                    "buys_5m": pair.get("txns", {}).get("m5", {}).get("buys", 0),
                    "sells_5m": pair.get("txns", {}).get("m5", {}).get("sells", 0),
                }

                # Mark as notified to prevent duplicate alerts
                notified_tokens.add(token_address)
                await send_telegram_alert(token_info)

    except Exception as e:
        logging.error(f"Error checking token {token_address}: {e}")


async def main():
    """
    Main execution loop.
    """
    logging.info("Starting pump_listener.py with DEX migration filter ($40,000+ MCAP)...")
    
    async with aiohttp.ClientSession() as session:
        while True:
            tasks = [fetch_token_metrics(session, ca) for ca in WATCH_LIST]
            if tasks:
                await asyncio.gather(*tasks)
            
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Listener stopped manually.")
