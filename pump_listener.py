import os
import time
import requests
import logging

# Nastavitev dnevnika (logging)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Konfiguracija
N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL")  # Ali sem direktno vpiši svoj n8n Webhook URL
MIN_MARKET_CAP = 20000  # Nastavljeno na $20,000 MC za ulov kovancev še na pump.funu

processed_mints = set()

def fetch_and_process_tokens():
    try:
        # Pridobivanje podatkov o novih/trendovskih žetonih (primer API klica)
        response = requests.get("https://api.dexscreener.com/token-profiles/latest/v1", timeout=10)
        if response.status_code != 200:
            logger.error(f"Napaka pri pridobivanju podatkov: {response.status_code}")
            return

        tokens = response.json()
        
        for token in tokens:
            mint = token.get("tokenAddress")
            if not mint or mint in processed_mints:
                continue

            # Pridobimo podrobnejše podatke o paru/trgu
            pair_response = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{mint}", timeout=10)
            if pair_response.status_code != 200:
                continue
                
            pair_data = pair_response.json().get("pairs")
            if not pair_data:
                continue

            # Uzamemo primarni par (Solana / Raydium ali PumpSwap)
            main_pair = pair_data[0]
            market_cap = float(main_pair.get("marketCap", 0) or main_pair.get("fdv", 0))

            # 1. PREVERJANJE PRAGA ($20.000 MC)
            if market_cap < MIN_MARKET_CAP:
                continue

            # 2. ISKANJE TWITTER / X POVEZAVE (Fallback na X search)
            info = main_pair.get("info", {})
            socials = info.get("socials", [])
            
            twitter_url = None
            if socials:
                for social in socials:
                    if social.get("type") == "twitter" or "x.com" in social.get("url", ""):
                        twitter_url = social.get("url")
                        break
            
            # Če uradne povezave ni na DexScreenerju, ustvarimo X search link za CA
            if not twitter_url:
                twitter_url = f"https://x.com/search?q={mint}"
                logger.info(f"DexScreener nima Twitterja za {mint}. Uporabljam X search query.")

            name = main_pair.get("baseToken", {}).get("name", "Unknown")
            symbol = main_pair.get("baseToken", {}).get("symbol", "UNKNOWN")
            pair_url = main_pair.get("url", f"https://dexscreener.com/solana/{mint}")

            # Priprava podatkov za n8n Webhook
            payload = {
                "name": name,
                "symbol": symbol,
                "market_cap": f"{market_cap:,.0f}",
                "mint": mint,
                "pair_url": pair_url,
                "twitter": twitter_url
            }

            logger.info(f"🚀 TOKEN PASSED ($20k+ MC)! Sent to n8n: {name} (${symbol}) | MCap: ${market_cap:,.0f}")
            
            # Pošiljanje na n8n
            if N8N_WEBHOOK_URL:
                try:
                    requests.post(N8N_WEBHOOK_URL, json=payload, timeout=5)
                except Exception as e:
                    logger.error(f"Napaka pri pošiljanju na n8n Webhook: {e}")

            processed_mints.add(mint)

    except Exception as e:
        logger.error(f"Splošna napaka v zanki: {e}")

if __name__ == "__main__":
    logger.info("Zaganjam pump-listener skripto z $20k MC pragom...")
    while True:
        fetch_and_process_tokens()
        time.sleep(10)  # Osveževanje na vsakih 10 sekund
