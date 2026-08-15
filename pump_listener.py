import os
import urllib.parse
from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

# In-memory storage for trends
TRENDS = []

# YOUR n8n Webhook URL (Production URL)
N8N_WEBHOOK_URL = "https://n8n-app-ok4t.onrender.com/webhook/pump-data"

def clean_search_term(text):
    """Clean and format text for searching."""
    if not text:
        return ""
    return text.strip().replace('"', '')

def send_to_n8n(trend_data):
    """Automatically push new trend data to n8n webhook."""
    try:
        payload = {
            "name": trend_data.get("suggested_name", "Meme Coin"),
            "description": trend_data.get("description", ""),
            "market_cap": trend_data.get("market_cap", 75000),  # Default or fetched value
            "twitter": trend_data.get("twitter", ""),
            "address": trend_data.get("address", "PlaceholderSolanaAddress123")
        }
        print(f"INFO: Sending data to n8n for token: {payload['name']} (Market Cap: ${payload['market_cap']})")
        response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=5)
        if response.status_code == 200:
            print("SUCCESS: Data successfully sent and received by n8n!")
        else:
            print(f"WARNING: n8n responded with status code {response.status_code}")
    except Exception as e:
        print(f"ERROR: Failed sending data to n8n: {e}")

@app.route("/api/trends", methods=["GET"])
def get_trends():
    """API endpoint that returns current trends and handles simulation/addition."""
    print("INFO: Received request on /api/trends endpoint...")
    try:
        data = request.args.to_dict()
        if data:
            print(f"INFO: Found incoming trend parameters: {data}")
            data["suggested_name"] = clean_search_term(data.get("suggested_name", "Meme"))
            data["description"] = clean_search_term(data.get("description", ""))
            
            query_string = urllib.parse.quote(data["description"])
            data["source_url"] = f"https://www.tiktok.com/search?q={query_string}"
            
            data["id"] = len(TRENDS) + 1
            TRENDS.insert(0, data)
            
            # Send the new trend directly to n8n workflow
            send_to_n8n(data)
            
            print(f"SUCCESS: Added ultra-fresh 1-5 day trend: {data['suggested_name']}")
        else:
            print("INFO: /api/trends called, but no query parameters provided.")
    except Exception as e:
        print(f"ERROR: Exception during trend processing: {e}")

    return jsonify({"success": True, "trends": TRENDS})

@app.route("/")
def home():
    return "Pump.fun Fresh Alpha Radar is active."

if __name__ == "__main__":
    print("INFO: Starting Pump.fun listener service on port 10000...")
    app.run(host="0.0.0.0", port=10000)
