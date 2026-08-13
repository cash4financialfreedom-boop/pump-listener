from flask import Flask, jsonify
from flask_cors import CORS
import os
import requests
import json
import urllib.parse
import re

app = Flask(__name__)
CORS(app)

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

def clean_search_term(text):
    cleaned = re.sub(r'[\*\#_`"“”]', '', text)
    return cleaned.strip()

@app.route("/api/trends", methods=["GET"])
def get_trends():
    api_key = os.environ.get("AI_API_KEY")
    
    if api_key:
        try:
            existing_trends = ", ".join([t["trend"] for t in TRENDS])
            
            url = "https://api.perplexity.ai/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "sonar",
                "messages": [
                    {
                        "role": "system", 
                        "content": (
                            "You are an elite meme coin alpha hunter for Pump.fun. "
                            "Find ONE hyper-viral trend that exploded STRICTLY within the last 1 to 5 days. "
                            "STRICT RULES:\n"
                            "1. FRESHNESS: The viral clip, animal moment, or news must be brand new (maximum 5 days old). Reject anything older, recycled, or historical.\n"
                            "2. ANIMALS: Focus ONLY on a single, specific, individual animal (e.g., one particular famous cat, dog, raccoon) featured in a specific fresh viral video clip with massive traction (10k+ views). No general species or groups.\n"
                            "3. ALTERNATIVE: A major, breaking viral statement or moment from Donald Trump or Elon Musk from the last 1-5 days.\n"
                            "Return ONLY raw JSON with keys: 'trend' (short clean title specifying the fresh viral moment), 'suggested_name' (clean token name), 'symbol' (uppercase ticker max 6 chars, NO emojis or symbols), 'description' (short degen hype text emphasizing its recent 1-5 day traction). No markdown formatting."
                        )
                    },
                    {
                        "user": "Find ONE unique, ultra-fresh trend from the last 1-5 days. Do not repeat these: " + existing_trends
                    }
                ]
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                clean_content = content.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_content)
                
                raw_trend = data.get("trend", "Viral Trend")
                cleaned_trend = clean_search_term(raw_trend)
                
                if not any(t["trend"].lower() == cleaned_trend.lower() for t in TRENDS):
                    data["trend"] = cleaned_trend
                    data["symbol"] = re.sub(r'[^A-Z]', '', data.get("symbol", "MEME").upper())[:6]
                    data["suggested_name"] = clean_search_term(data.get("suggested_name", "Meme"))
                    data["description"] = clean_search_term(data.get("description", ""))
                    
                    query_string = urllib.parse.quote(cleaned_trend)
                    data["source_url"] = f"https://www.tiktok.com/search?q={query_string}"
                    
                    data["id"] = len(TRENDS) + 1
                    TRENDS.insert(0, data)
                    print(f"SUCCESS: Added ultra-fresh 1-5 day trend -> {cleaned_trend}")
        except Exception as e:
            print(f"Error during generation: {e}")
            
    return jsonify({"success": True, "trends": TRENDS})

@app.route("/")
def home():
    return "Pump.fun Fresh Alpha Radar is active."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
