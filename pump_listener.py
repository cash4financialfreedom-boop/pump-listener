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
        "trend": "Pesto the Baby King Penguin",
        "suggested_name": "Pesto",
        "symbol": "PESTO",
        "description": "The massive baby king penguin dominating TikTok feeds and viral pet culture with huge early traction.",
        "source_url": "https://www.tiktok.com/search?q=Pesto%20penguin"
    }
]

@app.route("/", methods=["GET"])
def home():
    return "MemeCollab Precise Trend Radar is Running"

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
                "content": f"Today is {current_date}. You are an elite meme coin alpha hunter. STRICT RULE: You must pick ONE specific, named viral animal, individual meme character, or trending lighthearted topic from TikTok, Instagram, or global news that is gaining traction. NEVER write generic titles like 'viral trending' or 'animal content'. Give it a precise name, symbol, and short degen description. SAFETY: No tragedies, wars, or disasters. Return ONLY a raw JSON object with keys: trend, suggested_name, symbol, description. No markdown formatting, no backticks."
            },
            {
                "user": "Find one specific viral animal, meme, or lighthearted trend starting to explode on TikTok/Instagram and turn it into a meme coin concept."
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
        print("Scanning for precise individual viral trends...")
        new_data = fetch_real_trend_from_perplexity()
        
        if new_data and "trend" in new_data:
            clean_trend_title = clean_text(new_data.get("trend"))
            
            if len(clean_trend_title.split()) > 15 or "viral" in clean_trend_title.lower() and len(clean_trend_title.split()) < 3:
                time.sleep(10)
                continue

            lower_title = clean_trend_title.lower()
            forbidden_words = ["earthquake", "potres", "death", "kill", "tragedy", "disaster", "accident", "war", "crash"]
            if any(word in lower_title for word in forbidden_words):
                continue
            
            # Pravilno kodiranje URL-ja, da TikTok iskanje takoj deluje
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
                print(f"Successfully added precise trend: {new_item['trend']}")

        time.sleep(60)

@app.route("/api/trends", methods=["GET"])
def get_trends():
    return jsonify({"success": True, "trends": list(reversed(TRENDS_DATABASE))}), 200

if __name__ == "__main__":
    scanner_thread = threading.Thread(target=auto_news_scanner, daemon=True)
    scanner_thread.start()
    app.run(host="0.0.0.0", port=10000)
