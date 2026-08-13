from flask import Flask, jsonify
from flask_cors import CORS
import os
import requests
import json
import urllib.parse

app = Flask(__name__)
CORS(app)

TRENDS = [{"id": 1, "trend": "Pesto the Baby King Penguin", "suggested_name": "Pesto", "symbol": "PESTO", "description": "Viral penguin.", "source_url": "https://www.tiktok.com/search?q=Pesto"}]

@app.route("/api/trends", methods=["GET"])
def get_trends():
    print("--- FETCHING NEW TREND ---")
    api_key = os.environ.get("AI_API_KEY")
    
    if api_key:
        try:
            # Zberemo obstoječe trende, da jih AI ne ponavlja
            existing_trends = ", ".join([t["trend"] for t in TRENDS])
            
            url = "https://api.perplexity.ai/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "sonar",
                "messages": [
                    {"role": "system", "content": "Return ONLY raw JSON: {'trend': '...', 'suggested_name': '...', 'symbol': '...', 'description': '...'}"},
                    {"role": "user", "content": f"Find ONE brand new, different viral animal or internet trend from the last 24h. Do NOT use any of these already found trends: {existing_trends}. Make it unique."}
                ]
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                clean_content = content.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_content)
                
                # Dodaj samo, če trend še ne obstaja v bazi
                if not any(t["trend"].lower() in data["trend"].lower() or data["trend"].lower() in t["trend"].lower() for t in TRENDS):
                    data["id"] = len(TRENDS) + 1
                    data["source_url"] = f"https://www.tiktok.com/search?q={urllib.parse.quote(data['trend'])}"
                    TRENDS.insert(0, data)
                    print(f"ADDED NEW UNIQUE TREND: {data['trend']}")
        except Exception as e:
            print(f"Error: {e}")
            
    return jsonify({"success": True, "trends": TRENDS})

@app.route("/")
def home():
    return "Radar is running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
