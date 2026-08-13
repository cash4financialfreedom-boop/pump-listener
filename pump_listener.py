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
        "trend": "TikTok Viral Animal Radar",
        "suggested_name": "ViralPaws",
        "symbol": "PAWS",
        "description": "Scanning top viral animal moments and internet memes with guaranteed working search links.",
        "source_url": "https://www.google.com/search?q=funny+tiktok+animals+viral",
        "image_url": "https://image.pollinations.ai/prompt/funny%20viral%20cat%20tiktok%20meme,%20vibrant%20colors,4k"
    }
]

@app.route("/", methods=["GET"])
def home():
    return "MemeCollab Radar with Verified Search Links is Running"

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
                "content": f"Today is {current_date}. You are an elite meme trend hunter. STRICT SAFETY: No disasters, tragedies, wars, or accidents. ONLY focus on fun, lighthearted viral internet culture, TikTok/Instagram viral animal moments, funny memes, or amusing celebrity moments from the last 24 hours. Return ONLY a raw JSON object with keys: trend, suggested_name, symbol, description, image_prompt. Do not include source_url in JSON. No markdown formatting, no backticks."
            },
            {
                "user": "Find one top viral TikTok animal, meme, or fun trend from the last 24 hours and turn it into a degen meme coin concept."
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
        print("Scanning for fresh viral animal & meme trends...")
        new_data = fetch_real_trend_from_perplexity()
        
        if new_data and "trend" in new_data:
            clean_trend_title = clean_text(new_data.get("trend"))
            
            # Filter proti neprimernim vsebinam
            lower_title = clean_trend_title.lower()
            forbidden_words = ["earthquake", "potres", "death", "kill", "tragedy", "disaster", "accident", "war", "crash"]
            if any(word in lower_title for word in forbidden_words):
                continue

            raw_prompt = new_data.get("image_prompt", clean_trend_title)
            encoded_prompt = urllib.parse.quote(raw_prompt + ", funny high-impact crypto meme style, vibrant colors, 4k")
            
            # Namesto ugibanja URL-ja ustvarimo direktno pametno iskalno povezavo, ki vedno deluje in točno ustreza novici!
            verified_search_url = f"https://www.google.com/search?q={urllib.parse.quote(clean_trend_title + ' viral tiktok meme')}"

            new_item = {
                "id": len(TRENDS_DATABASE) + 1,
                "trend": clean_trend_title,
                "suggested_name": clean_text(new_data.get("suggested_name")),
                "symbol": clean_text(new_data.get("symbol")),
                "description": clean_text(new_data.get("description")),
                "source_url": verified_search_url,
                "image_url": f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            }
            
            if not any(t['trend'].lower() == new_item['trend'].lower() for t in TRENDS_DATABASE):
                TRENDS_DATABASE.append(new_item)
                print(f"Successfully added trend with working search link: {new_item['trend']}")

        time.sleep(60)

@app.route("/api/trends", methods=["GET"])
def get_trends():
    return jsonify({"success": True, "trends": list(reversed(TRENDS_DATABASE))}), 200

if __name__ == "__main__":
    scanner_thread = threading.Thread(target=auto_news_scanner, daemon=True)
    scanner_thread.start()
    app.run(host="0.0.0.0", port=10000)
