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

def get_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_scan": 0, "trends": [{"id": 1, "trend": "Pesto the Baby King Penguin", "suggested_name": "Pesto", "symbol": "PESTO", "description": "Viral penguin.", "source_url": "https://www.tiktok.com/search?q=Pesto"}]}

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4)

@app.route("/api/trends", methods=["GET"])
def get_trends():
    db = get_db()
    now = time.time()
    
    # Preveri, če je čas za nov scan (vsakih 120s)
    if now - db["last_scan"] > 120:
        print("Sprožam nov scan...")
        db["last_scan"] = now
        
        # Klic na AI
        url = "https://api.perplexity.ai/chat/completions"
        headers = {"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "sonar",
            "messages": [
                {"role": "system", "content": "Return ONLY raw JSON: {'trend': '...', 'suggested_name': '...', 'symbol': '...', 'description': '...'}. No other text."},
                {"role": "user", "content": "Find one new viral animal or meme trend from last 24h. No disasters."}
            ]
        }
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=20)
            if resp.status_code == 200:
                data = json.loads(resp.json()["choices"][0]["message"]["content"].replace("```json", "").replace("```", ""))
                # Dodaj v bazo, če še ne obstaja
                if not any(t["trend"] == data["trend"] for t in db["trends"]):
                    data["id"] = len(db["trends"]) + 1
                    data["source_url"] = f"https://www.tiktok.com/search?q={urllib.parse.quote(data['trend'])}"
                    db["trends"].insert(0, data) # Najnovejši prvi
                    save_db(db)
                    print(f"Nov trend dodan: {data['trend']}")
        except Exception as e:
            print(f"Napaka pri scanu: {e}")
            
    return jsonify({"success": True, "trends": db["trends"]})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
