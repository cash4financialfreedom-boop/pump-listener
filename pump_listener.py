import os
import time
import requests
import logging
from threading import Thread
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health_check():
    return "Pump Listener is active and running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL")
MIN_MARKET_CAP = 20000

processed_mints = set()

def format_mcap(value):
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.2f}K"
    return f"{value:.0f}"

def fetch_and_process_tokens():
    try:
        response = requests.get("https://api.dexscreener.com/token-profiles/latest/v1", timeout=10)
        if response.status_code != 200:
            return

        tokens = response.json()
        
        for token in tokens:
            chain_id = token.get("chainId", "").lower()
            if chain_id != "solana":
                continue

            mint = token.get("tokenAddress")
            if not mint or mint in processed_mints:
                continue

            pair_response = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{mint}", timeout=10)
            if pair_response.status_code != 200:
                continue
                
            pair_data = pair_response.json().get("pairs")
            if not pair_data:
                continue

            solana_pairs = [p for p in pair_data if p.get("chainId") == "solana"]
            if not solana_pairs:
                continue
                
            main_pair = solana_pairs[0]
            market_cap = float(main_pair.get("marketCap", 0) or main_pair.get("fdv", 0))

            if market_cap < MIN_MARKET_CAP:
                continue

            info = main_pair.get("info", {})
            socials = info.get("socials", [])
            
            twitter_url = None
            if socials:
                for social in socials:
                    if social.get("type") == "twitter" or "x.com" in social.get("url", ""):
                        twitter_url = social.get("url")
                        break
            
            if not twitter_url:
                twitter_url = f"https://x.com/search?q={mint}"

            name = main_pair.get("baseToken", {}).get("name", "Unknown")
            symbol = main_pair.get("baseToken", {}).get("symbol", "UNKNOWN")
            pair_url = main_pair.get("url", f"https://dexscreener.com/solana/{mint}")

            payload = {
                "name": name,
                "symbol": symbol,
                "market_cap": format_mcap(market_cap),
                "mint": mint,
                "pair_url": pair_url,
                "twitter": twitter_url
            }

            logger.info(f"🚀 SOLANA TOKEN PASSED ($20k+ MC)! Sent to n8n: {name} (${symbol}) | MCap: {format_mcap(market_cap)}")
            
            if N8N_WEBHOOK_URL:
                try:
                    requests.post(N8N_WEBHOOK_URL, json=payload, timeout=5)
                except Exception as e:
                    logger.error(f"Napaka pri pošiljanju na n8n Webhook: {e}")

            processed_mints.add(mint)

    except Exception as e:
        logger.error(f"Splošna napaka v zanki: {e}")

if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

    while True:
        fetch_and_process_tokens()
        time.sleep(10)
