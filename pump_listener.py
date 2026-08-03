import os
import asyncio
import logging
import aiohttp
from flask import Flask
from threading import Thread

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- FLASK SERVER FOR RENDER (HEALTH CHECK) ---
app = Flask(__name__)

# Support both GET and HEAD requests to resolve HTTP 501 warnings on Render
@app.route('/', methods=['GET', 'HEAD'])
def health_check():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Start Flask server in a separate daemon thread
Thread(target=run_flask, daemon=True).start()


# --- PUMP LISTENER LOGIC ---
N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "")
CHECK_INTERVAL_SECONDS = int(os.environ.get("CHECK_INTERVAL_SECONDS", 10))

async def send_to_n8n(session, payload):
    if not N8N_WEBHOOK_URL:
        logging.warning("N8N_WEBHOOK_URL is not configured!")
        return
    try:
        async with session.post(N8N_WEBHOOK_URL, json=payload) as response:
            if response.status == 200:
                logging.info(f"Successfully sent to n8n: {payload.get('symbol')}")
            else:
                logging.error(f"Failed to send to n8n. Status: {response.status}")
    except Exception as e:
        logging.error(f"Error sending to n8n: {e}")

async def fetch_and_process_tokens(session):
    try:
        # Fetch and process token data here
        pass
    except Exception as e:
        logging.error(f"Error in token processing loop: {e}")

async def main_loop():
    async with aiohttp.ClientSession() as session:
        while True:
            await fetch_and_process_tokens(session)
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    asyncio.run(main_loop())
