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
        "trend": "Global Viral Megatrend",
        "suggested_name": "MegaPump",
        "symbol": "MEGA",
        "description": "A top-tier meme coin capturing major viral headlines and internet hype worldwide.",
        "source_url": "https://news.google.com",
        "image_url": "https://image.pollinations.ai/prompt/epic%20viral%20news%20headline%20crypto%20meme,%20vibrant%20colors,4k"
    }
]

@app.route("/", methods=["GET"])
def home():
    return "MemeCollab & Viral Vault Backend is Running with Global & Meme Radar"

def clean_text(text):
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
                "content": "You are an elite crypto meme and global trend hunter. Search across major breaking world news (like Trump, Elon Musk, tech, global shifts) AND viral internet culture (TikTok, X, Reddit). Find a high-impact viral story or breaking news event that has massive meme potential. Return ONLY a raw JSON object with keys: trend, suggested_name, symbol, description, source_url, image_prompt. 'trend' must be a short clean headline. 'source_url' must be a direct link to the article or post. No markdown formatting, no backticks."
            },
            {
                "role": "user",
                "content": "Find one massive breaking world news story or viral internet trend right now, get its exact source URL, and turn it into a top-tier degen meme coin concept."
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
        print("Scanning global news & viral internet culture...")
        new_data = fetch_real_trend_from_perplexity()
        
        if new_data and "trend" in new_data:
            clean_trend_title = clean_text(new_data.get("trend"))
            raw_prompt = new_data.get("image_prompt", clean_trend_title)
            encoded_prompt = urllib.parse.quote(raw_prompt + ", funny high-impact crypto meme style, vibrant colors, 4k")
            
            s_url = new_data.get("source_url", "https://news.google.com")
            if len(s_url) < 15 or s_url.count('/') < 3:
                s_url = "https://news.google.com"

            new_item = {
                "id": len(TRENDS_DATABASE) + 1,
                "trend": clean_trend_title,
                "suggested_name": clean_text(new_data.get("suggested_name")),
                "symbol": clean_text(new_data.get("symbol")),
                "description": clean_text(new_data.get("description")),
                "source_url": s_url,
                "image_url": f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            }
            
            if not any(t['trend'] == new_item['trend'] for t in TRENDS_DATABASE):
                TRENDS_DATABASE.append(new_item)
                print(f"Successfully added global/viral trend: {new_item['trend']}")

        time.sleep(60)

@app.route("/api/trends", methods=["GET"])
def get_trends():
    return jsonify({"success": True, "trends": list(reversed(TRENDS_DATABASE))}), 200

if __name__ == "__main__":
    scanner_thread = threading.Thread(target=auto_news_scanner, daemon=True)
    scanner_thread.start()
    app.run(host="0.0.0.0", port=10000)
