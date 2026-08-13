from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import threading
import time
import json
import urllib.parse
import re
from datetime import datetime

app = Flask(__name__)
CORS(app)

AI_API_KEY = os.environ.get("AI_API_KEY", "")

TRENDS_DATABASE = [
    {
        "id": 1,
        "trend": "Omni-Radar Initialized",
        "suggested_name": "OmniPump",
        "symbol": "OMNI",
        "description": "Scanning both breaking global news (Trump, Musk, markets) and viral social media meme culture (TikTok, Reddit, Instagram).",
        "source_url": "https://news.google.com",
        "image_url": "https://image.pollinations.ai/prompt/cyberpunk%20radar%20scanning%20global%20news%20and%20tiktok%20memes,vibrant,4k"
    }
]

@app.route("/", methods=["GET"])
def home():
    return "MemeCollab Omni-Radar Backend is Running"

def clean_text(text):
    return re.sub(r'\[\d+\]', '', text).strip()

def fetch_real_trend_from_perplexity():
    if not AI_API_KEY:
        print("No AI API key found!")
        return None

    current_date = datetime.now().strftime("%Y-%m-%d")
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
                "content": f"Today is {current_date}. You are an elite multi-channel trend hunter scanning BOTH major breaking world news (Trump, Elon Musk, tech, politics, markets) AND viral social media culture (TikTok animal trends, Instagram reels, Reddit r/memes or r/wallstreetbets). Find a high-impact story from either world news or viral social media that happened in the last 24 hours and has massive meme coin potential. CRITICAL: Provide the exact direct article or post link in 'source_url'. Return ONLY a raw JSON object with keys: trend, suggested_name, symbol, description, source_url, image_prompt. No markdown formatting, no backticks."
            },
            {
                "role": "user",
                "content": "Find one top-tier breaking global news story or viral social media meme trend from the last 24 hours, get its exact direct source URL, and turn it into a degen meme coin concept."
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
    while Time := True:
        print("Scanning global news & viral social media trends...")
        new_data = fetch_real_trend_from_perplexity()
        
        if new_data and "trend" in new_data:
            clean_trend_title = clean_text(new_data.get("trend"))
            raw_prompt = new_data.get("image_prompt", clean_trend_title)
            encoded_prompt = urllib.parse.quote(raw_prompt + ", funny high-impact crypto meme style, vibrant colors, 4k")
            
            s_url = new_data.get("source_url", "https://news.google.com")
            if len(s_url) < 20 or s_url.count('/') < 3 or s_url.endswith('.com'):
                s_url = f"https://www.google.com/search?q={urllib.parse.quote(clean_trend_title)}"

            new_item = {
                "id": len(TRENDS_DATABASE) + 1,
                "trend": clean_trend_title,
                "suggested_name": clean_text(new_data.get("suggested_name")),
                "symbol": clean_text(new_data.get("symbol")),
                "description": clean_text(new_data.get("description")),
                "source_url": s_url,
                "image_url": f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            }
            
            if not any(t['trend'].lower() == new_item['trend'].lower() for t in TRENDS_DATABASE):
                TRENDS_DATABASE.append(new_item)
                print(f"Successfully added omni-trend: {new_item['trend']}")

        time.sleep(60)

@app.route("/api/trends", methods=["GET"])
def get_trends():
    return jsonify({"success": True, "trends": list(reversed(TRENDS_DATABASE))}), 200

if __name__ == "__main__":
    scanner_thread = threading.Thread(target=auto_news_scanner, daemon=True)
    scanner_thread.start()
    app.run(host="0.0.0.0", port=10000)
