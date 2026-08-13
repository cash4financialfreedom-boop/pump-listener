from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import threading
import time
import json
import urllib.parse
import re

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
        "source_url": "https://www.nasa.gov",
        "image_url": "https://image.pollinations.ai/prompt/cute%20dog%20astronaut%20on%20mars,%20crypto%20meme%20style,vibrant"
    }
]

@app.route("/", methods=["GET"])
def home():
    return "MemeCollab & Viral Vault Backend is Running Clean"

def clean_text(text):
    # Odstrani oklepaje s številkami virov, npr. [7][8]
    return re.sub(r'\[\d+\]', '', text).strip()

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
                "content": "You are a crypto trend hunter. Return ONLY a raw JSON object with keys: trend, suggested_name, symbol, description, source_url, image_prompt. 'trend' must be a short, clean news headline (max 8 words). Do not include citation brackets like [1]. No markdown formatting, no backticks."
            },
            {
                "role": "user",
                "content": "Find one major breaking viral news event right now and turn it into a meme coin concept with a short headline for 'trend', name, 3-5 letter symbol, short description, news source URL, and a funny image_prompt."
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
            clean_trend_title = clean_text(new_data.get("trend"))
            raw_prompt = new_data.get("image_prompt", clean_trend_title)
            encoded_prompt = urllib.parse.quote(raw_prompt + ", funny crypto meme style, vibrant colors, 4k")
            
            new_item = {
                "id": len(TRENDS_DATABASE) + 1,
                "trend": clean_trend_title,
                "suggested_name": clean_text(new_data.get("suggested_name")),
                "symbol": clean_text(new_data.get("symbol")),
                "description": clean_text(new_data.get("description")),
                "source_url": new_data.get("source_url", "https://news.google.com"),
                "image_url": f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            }
            
            if not any(t['trend'] == new_item['trend'] for t in TRENDS_DATABASE):
                TRENDS_DATABASE.append(new_item)
                print(f"Successfully added clean trend: {new_item['trend']}")

        time.sleep(60)

@app.route("/api/trends", methods=["GET"])
def get_trends():
    return jsonify({"success": True, "trends": list(reversed(TRENDS_DATABASE))}), 200

if __name__ == "__main__":
    scanner_thread = threading.Thread(target=auto_news_scanner, daemon=True)
    scanner_thread.start()
    app.run(host="0.0.0.0", port=10000)
