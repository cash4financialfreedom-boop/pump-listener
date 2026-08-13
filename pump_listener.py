from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import threading
import time
import json

app = Flask(__name__)
CORS(app)

AI_API_KEY = os.environ.get("AI_API_KEY", "")

TRENDS_DATABASE = [
    {
        "id": 1,
        "trend": "Mars Colonization Update",
        "suggested_name": "Mars Rover Dog",
        "symbol": "MRD",
        "description": "The latest breakthrough in interplanetary exploration and canine space travel.",
        "source_url": "https://www.nasa.gov"
    }
]

@app.route("/", methods=["GET"])
def home():
    return "MemeCollab & Viral Vault Backend is Running with AI"

def fetch_real_trend_from_perplexity():
    if not AI_API_KEY:
        print("No AI API key found!")
        return None

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": "You are a crypto trend hunter. Return ONLY a raw JSON object with keys: trend, suggested_name, symbol, description, source_url. No markdown formatting, no backticks."
            },
            {
                "role": "user",
                "content": "Find one major breaking viral news event right now and turn it into a meme coin concept with name, 3-5 letter symbol, short description, and the news source URL."
            }
        ]
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            content = content.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(content)
            return parsed
    except Exception as e:
        print(f"Error fetching from Perplexity: {e}")
    
    return None

def auto_news_scanner():
    while True:
        print("Polling Perplexity for fresh viral news...")
        new_data = fetch_real_trend_from_perplexity()
        
        if new_data and "trend" in new_data:
            new_item = {
                "id": len(TRENDS_DATABASE) + 1,
                "trend": new_data.get("trend"),
                "suggested_name": new_data.get("suggested_name"),
                "symbol": new_data.get("symbol"),
                "description": new_data.get("description"),
                "source_url": new_data.get("source_url", "https://news.google.com")
            }
            
            if not any(t['trend'] == new_item['trend'] for t in TRENDS_DATABASE):
                TRENDS_DATABASE.append(new_item)
                print(f"Successfully added new AI trend: {new_item['trend']}")

        time.sleep(60)

@app.route("/api/trends", methods=["GET"])
def get_trends():
    return jsonify({"success": True, "trends": list(reversed(TRENDS_DATABASE))}), 200

if __name__ == "__main__":
    scanner_thread = threading.Thread(target=auto_news_scanner, daemon=True)
    scanner_thread.start()
    app.run(host="0.0.0.0", port=10000)
