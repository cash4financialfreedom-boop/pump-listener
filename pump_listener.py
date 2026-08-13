from flask import Flask, jsonify
from flask_cors import CORS
import os
import requests
import json
import time
import threading
import urllib.parse

app = Flask(__name__)
CORS(app)

# Database of trends
TRENDS = [
    {
        "id": 1,
        "trend": "Pesto the Baby King Penguin",
        "suggested_name": "Pesto",
        "symbol": "PESTO",
        "description": "The massive baby king penguin dominating TikTok feeds.",
        "source_url": "https://www.tiktok.com/search?q=Pesto%20penguin"
    }
]

def fetch_ai_trends():
    """Fetches new viral trends using Perplexity API."""
    api_key = os.environ.get("AI_API_KEY")
    if not api_key:
        print("Error: AI_API_KEY environment variable not set.")
        return None

    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": "Return ONLY raw JSON: {'trend': '...', 'suggested_name': '...', 'symbol': '...', 'description': '...'}. No markdown, no extra text."},
            {"role": "user", "content": "Find one new, early-stage viral animal or lighthearted trend from the last 24 hours. No disasters."}
        ]
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            clean_content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_content)
    except Exception as e:
        print(f"Fetch error: {e}")
    return None

def scanner_worker():
    """Background task to update trends every 3 minutes."""
    while True:
        print("Starting trend scan...")
        new_trend = fetch_ai_trends()
        if new_trend:
            # Avoid duplicates
            if not any(t["trend"] == new_trend["trend"] for t in TRENDS):
                new_trend["id"] = len(TRENDS) + 1
                new_trend["source_url"] = f"https://www.tiktok.com/search?q={urllib.parse.quote(new_trend['trend'])}"
                TRENDS.insert(0, new_trend)
                print(f"New trend added: {new_trend['trend']}")
        time.sleep(180) # 3 minutes

def self_ping():
    """Keeps the service alive by pinging itself."""
    while True:
        try:
            requests.get("https://pump-listener.onrender.com")
            print("Self-ping performed.")
        except:
            pass
        time.sleep(300) # 5 minutes

@app.route("/api/trends", methods=["GET"])
def get_trends():
    return jsonify({"success": True, "trends": TRENDS})

if __name__ == "__main__":
    # Start background threads
    threading.Thread(target=scanner_worker, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()
    
    # Run Flask app
    app.run(host="0.0.0.0", port=10000)
