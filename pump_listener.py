from flask import Flask, jsonify
from flask_cors import CORS
import os
import requests
import json
import urllib.parse
import time
import threading
from datetime import datetime

app = Flask(__name__)
CORS(app)

AI_API_KEY = os.environ.get("AI_API_KEY", "")
DB_FILE = "trends.json"

def scan_worker():
    while True:
        try:
            print("--- Skener se zažene ---")
            url = "https://api.perplexity.ai/chat/completions"
            headers = {"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": "sonar",
                "messages": [
                    {"role": "system", "content": "Return ONLY JSON: {'trend': 'Name', 'suggested_name': 'Name', 'symbol': 'SYM', 'description': 'Short desc'}"},
                    {"role": "user", "content": "Find one new viral animal or lighthearted trend."}
                ]
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            if resp.status_code == 200:
                data = json.loads(resp.json()["choices"][0]["message"]["content"].replace("```json", "").replace("```", ""))
                
                # Preberi in posodobi bazo
                db = []
                if os.path.exists(DB_FILE):
                    with open(DB_FILE, "r") as f: db = json.load(f)
                
                if not any(t["trend"] == data["trend"] for t in db):
                    data["source_url"] = f"https://www.tiktok.com/search?q={urllib.parse.quote(data['trend'])}"
                    db.insert(0, data)
                    with open(DB_FILE, "w") as f: json.dump(db, f)
                    print(f"Dodano: {data['trend']}")
        except Exception as e:
            print(f"Napaka v workerju: {e}")
        
        time.sleep(120) # Počakaj 2 minuti

@app.route("/api/trends", methods=["GET"])
def get_trends():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f: return jsonify({"success": True, "trends": json.load(f)})
    return jsonify({"success": True, "trends": []})

if __name__ == "__main__":
    threading.Thread(target=scan_worker, daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
