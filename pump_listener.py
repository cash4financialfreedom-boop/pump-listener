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
        "trend": "Early Viral Trend Radar Active",
        "suggested_name": "EarlyPulse",
        "symbol": "EARLY",
        "description": "Scanning fresh TikTok, Instagram, and breaking lighthearted global news with strong early traction.",
        "source_url": "https://www.tiktok.com/search?q=viral+trending"
    }
]

@app.route("/", methods=["GET"])
def home():
    return "MemeCollab Clean Omni-Radar is Running"

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
                "content": f"Today is {current_date}. You are an elite meme coin and trend hunter. Look for brand new, rising viral internet memes, TikTok/Instagram animal clips starting to trend, or lighthearted breaking global news (like Trump, Elon Musk funny or viral moments) from the last 24 hours. SAFETY RULE: NEVER select earthquakes, disasters, accidents, deaths, tragedies, wars, or heavy suffering. ONLY focus on fun, viral, early-stage traction content. Return ONLY a raw JSON object with keys: trend, suggested_name, symbol, description. No markdown formatting, no backticks."
            },
            {
                "user": "Find one fresh, early-rising viral TikTok, Instagram, or lighthearted global news trend starting to gain traction and turn it into a meme coin concept."
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
        print("Scanning for fresh early-stage viral trends & news...")
        new_data = fetch_real_trend_from_perplexity()
        
        if new_data and "trend" in new_data:
            clean_trend_title = clean_text(new_data.get("trend"))
            
            if "content" in clean_trend_title.lower() or len(clean_trend_title.split()) > 15:
                time.sleep(10)
                continue

            lower_title = clean_trend_title.lower()
            forbidden_words = ["earthquake", "potres", "death", "kill", "tragedy", "disaster", "accident", "war", "crash"]
            if any(word in lower_title for word in forbidden_words):
                continue
            
            search_query = urllib.parse.quote(clean_trend_title)
            safe_source_url = f"https://www.tiktok.com/search?q={search_query}"

            new_item = {
                "id": len(TRENDS_DATABASE) + 1,
                "trend": clean_trend_title,
                "suggested_name": clean_text(new_data.get("suggested_name")),
                "symbol": clean_text(new_data.get("symbol")),
                "description": clean_text(new_data.get("description")),
                "source_url": safe_source_url
            }
            
            if not any(t['trend'].lower() == new_item['trend'].lower() for t in TRENDS_DATABASE):
                TRENDS_DATABASE.append(new_item)
                print(f"Successfully added clean early trend: {new_item['trend']}")

        time.sleep(60)

@app.route("/api/trends", methods=["GET"])
def get_trends():
    return jsonify({"success": True, "trends": list(reversed(TRENDS_DATABASE))}), 200

if __name__ == "__main__":
    scanner_thread = threading.Thread(target=auto_news_scanner, daemon=True)
    scanner_thread.start()
    app.run(host="0.0.0.0", port=10000)
