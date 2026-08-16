import os
import time
import threading
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configuration from environment variables
N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "INSERT_N8N_WEBHOOK_URL_HERE")

# Storage to avoid sending the same token multiple times
processed_tokens = set()

def fetch_and_push_trends():
    """Background loop that periodically checks the market and pushes data to n8n."""
    while True:
        try:
            print("Checking market for new tokens...")
            url = "https://api.dexscreener.com/latest/dex/search?q=solana"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                pairs = data.get("pairs", [])
                
                for pair in pairs[:20]:  # Review the first 20 results
                    token_address = pair.get("baseToken", {}).get("address")
                    
                    if not token_address or token_address in processed_tokens:
                        continue
                        
                    # Extract data
                    market_cap = float(pair.get("marketCap") or pair.get("fdv") or 0)
                    name = pair.get("baseToken", {}).get("name", "Unknown")
                    symbol = pair.get("baseToken", {}).get("symbol", "UNKNOWN")
                    
                    # Check for Twitter / X socials
                    info = pair.get("info", {})
                    socials = info.get("socials", [])
                    twitter_url = ""
                    for social in socials:
                        if social.get("type") == "twitter":
                            twitter_url = social.get("url")
                            break
                    
                    # Filter removed: now checking only if Twitter exists to ensure a steady flow of data
                    if twitter_url:
                        payload = {
                            "name": f"{name} ({symbol})",
                            "market_cap": str(market_cap),
                            "market_cap_phase": "Early",
                            "twitter": twitter_url,
                            "source_url": pair.get("url", "")
                        }
                        
                        # Send data to n8n Webhook
                        webhook_res = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=10)
                        if webhook_res.status_code == 200:
                            print(f"Successfully sent token to n8n: {name}")
                            processed_tokens.add(token_address)
                            
            else:
                print(f"API error: {response.status_code}")
                
        except Exception as e:
            print(f"Error in background loop: {e}")
            
        # Wait 60 seconds before the next check
        time.sleep(60)

@app.route("/", methods=["GET"])
def home():
    return "Pump Listener is active and running!"

@app.route("/api/trends", methods=["GET"])
def manual_trend():
    """Manual endpoint for browser testing."""
    sample_data = {
        "success": True,
        "trends": [{
            "id": 1,
            "description": "Cute dog meme coin trending on tiktok today",
            "market_cap": "50000",
            "twitter": "https://x.com/test",
            "source_url": "https://www.tiktok.com/search?q=TestCoin"
        }]
    }
    return jsonify(sample_data)

if __name__ == "__main__":
    # Start the background loop in a separate thread so the Flask server works normally
    t = threading.Thread(target=fetch_and_push_trends, daemon=True)
    t.start()
    
    # Start the Flask application
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
