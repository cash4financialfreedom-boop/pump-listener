from flask import Flask, jsonify
from flask_cors import CORS
import os
import requests
import json
import urllib.parse
import re
import time
from datetime import datetime

app = Flask(__name__)
CORS(app)

AI_API_KEY = os.environ.get("AI_API_KEY", "")
DB_FILE = "trends_database.json"

# Definicija osnovne baze z vključenim časom zadnjega skeniranja
DEFAULT_DB = {
    "last_scan_time": 0,
    "trends": [
        {
            "id": 1,
            "trend": "Pesto the Baby King Penguin",
            "suggested_name": "Pesto",
            "symbol": "PESTO",
            "description": "The massive baby king penguin dominating TikTok feeds and viral pet culture with huge early traction.",
            "source_url": "https://www.tiktok.com/search?q=Pesto%20penguin"
        }
    ]
}

def load_database():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Ensure the loaded data has both required keys
                if "last_scan_time" in data and "trends" in data:
                    return data
        except Exception as e:
            print(f"Error reading database file: {e}")
    
    # Če datoteka ne obstaja ali je okvarjena, vrni privzeto
    return DEFAULT_DB.copy()

def save_database(db_data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving database: {e}")

@app.route("/", methods=["GET"])
def home():
    return "MemeCollab Robust Sync Radar is Running"

def clean_text(text):
    return re.sub(r'\[\d+\]', '', text).strip()

def fetch_real_trend_from_perplexity():
    if not AI_API_KEY:
        print("CRITICAL ERROR: No AI_API_KEY found!")
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
                "content": f"Today is {current_date}. You are an elite meme coin alpha hunter. STRICT RULE: You must pick ONE specific, named viral animal, individual meme character, or trending lighthearted topic from TikTok, Instagram, or global news that is gaining traction. NEVER write generic titles like 'viral trending'. Give it a precise name, symbol, and short degen description. SAFETY: No tragedies, wars, or disasters. Return ONLY a raw JSON object with keys: trend, suggested_name, symbol, description. No markdown formatting, no backticks."
            },
            {
                "user": "Find one specific viral animal, meme, or lighthearted trend starting to explode on TikTok/Instagram and turn it into a meme coin concept."
            }
        ]
    }

    try:
        print("--- Sending request to Perplexity API ---")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            content = content.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(content)
            print(f"Successfully fetched trend: {parsed.get('trend')}")
            return parsed
        else:
            print(f"API Error Status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Exception during fetch: {e}")
    
    return None

def check_and_add_new_trend():
    current_time = time.time()
    db_data = load_database()
    
    # Preveri, če je od zadnjega skeniranja minilo več kot 120 sekund (2 minuti)
    if current_time - db_data["last_scan_time"] > 120:
        print("Time threshold met. Triggering new scan...")
        
        # Takoj posodobi čas, da preprečiš hkratne klice
        db_data["last_scan_time"] = current_time
        save_database(db_data)
        
        new_data = fetch_real_trend_from_perplexity()
        
        if new_data and "trend" in new_data:
            clean_trend_title = clean_text(new_data.get("trend"))
            
            # Osnovna preverjanja ustreznosti
            if len(clean_trend_title.split()) <= 15:
                lower_title = clean_trend_title.lower()
                forbidden_words = ["earthquake", "potres", "death", "kill", "tragedy", "disaster", "accident", "war", "crash"]
                
                if not any(word in lower_title for word in forbidden_words):
                    search_query = urllib.parse.quote(clean_trend_title)
                    safe_source_url = f"https://www.tiktok.com/search?q={search_query}"

                    new_item = {
                        "id": len(db_data["trends"]) + 1,
                        "trend": clean_trend_title,
                        "suggested_name": clean_text(new_data.get("suggested_name")),
                        "symbol": clean_text(new_data.get("symbol")),
                        "description": clean_text(new_data.get("description")),
                        "source_url": safe_source_url
                    }
                    
                    # Prepreči podvajanje vnosov
                    if not any(t['trend'].lower() == new_item['trend'].lower() for t in db_data["trends"]):
                        db_data["trends"].append(new_item)
                        save_database(db_data)
                        print(f"+++ ADDED NEW TREND: {new_item['trend']} +++")
                    else:
                        print("Trend already exists. Skipping.")
                else:
                    print("Unsafe words detected. Skipping.")
            else:
                 print("Trend title too long. Skipping.")
    else:
        # Prikaz časa preostalega do naslednjega skeniranja (v dnevniku boš videl, da se nekaj dogaja)
        time_left = int(120 - (current_time - db_data["last_scan_time"]))
        print(f"Skipping scan. Next scan allowed in {time_left} seconds.")

@app.route("/api/trends", methods=["GET"])
def get_trends():
    check_and_add_new_trend()
    db_data = load_database()
    return jsonify({"success": True, "trends": list(reversed(db_data["trends"]))}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
