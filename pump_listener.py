from flask import Flask, jsonify
from flask_cors import CORS
import os
import requests
import json
import time
import urllib.parse

app = Flask(__name__)
CORS(app)

# In-memory database
TRENDS = [{"id": 1, "trend": "Pesto the Baby King Penguin", "suggested_name": "Pesto", "symbol": "PESTO", "description": "Viral penguin.", "source_url": "https://www.tiktok.com/search?q=Pesto"}]
LAST_SCAN = 0

@app.route("/api/trends", methods=["GET"])
def get_trends():
    global LAST_SCAN
    # Scan only if 2 minutes passed since last scan
    if time.time() - LAST_SCAN > 120:
        LAST_SCAN = time.time()
        print(">>> TRIGGERING SCAN NOW <<<")
        api_key = os.environ.get("AI_API_KEY")
        if api_key:
            try:
                url = "https://api.perplexity.ai/chat/completions"
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                payload = {
                    "model": "sonar",
                    "messages": [
                        {"role": "system", "content": "Return ONLY raw JSON: {'trend': '...', 'suggested_name': '...', 'symbol': '...', 'description': '...'}"},
                        {"role": "user", "content": "Find one new viral animal trend."}
                    ]
                }
                resp = requests.post(url, json=payload, headers=headers, timeout=30)
                if resp.status_code == 200:
                    data = json.loads(resp.json()["choices"][0]["message"]["content"].replace("```json", "").replace("```", ""))
                    if not any(t["trend"] == data["trend"] for t in TRENDS):
                        data["id"] = len(TRENDS) + 1
                        data["source_url"] = f"https://www.tiktok.com/search?q={urllib.parse.quote(data['trend'])}"
                        TRENDS.insert(0, data)
                        print(f">>> NEW TREND ADDED: {data['trend']} <<<")
            except Exception as e:
                print(f"Scan error: {e}")
    
    return jsonify({"success": True, "trends": TRENDS})

@app.route("/")
def home():
    return "Radar is active and waiting for requests."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
