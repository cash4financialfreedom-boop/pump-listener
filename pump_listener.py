from flask import Flask, jsonify
from flask_cors import CORS
import os
import requests
import json
import urllib.parse

app = Flask(__name__)
CORS(app)

# Osnovna baza s Pestom
TRENDS = [{"id": 1, "trend": "Pesto the Baby King Penguin", "suggested_name": "Pesto", "symbol": "PESTO", "description": "Viral penguin.", "source_url": "https://www.tiktok.com/search?q=Pesto"}]

@app.route("/api/trends", methods=["GET"])
def get_trends():
    print("--- ZAHTEVA ZA TRENDS SPREJETA ---")
    
    api_key = os.environ.get("AI_API_KEY")
    if not api_key:
        print("NAPAKA: Manjka AI_API_KEY v okolju Renderja!")
    else:
        try:
            print("Pošiljam zahtevo na Perplexity AI...")
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
            print(f"Perplexity status: {resp.status_code}")
            
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                clean_content = content.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_content)
                
                # Dodaj v seznam, če še ne obstaja
                if not any(t["trend"].lower() == data["trend"].lower() for t in TRENDS):
                    data["id"] = len(TRENDS) + 1
                    data["source_url"] = f"https://www.tiktok.com/search?q={urllib.parse.quote(data['trend'])}"
                    TRENDS.insert(0, data)
                    print(f"USPEH! Dodan nov trend: {data['trend']}")
                else:
                    print("Trend že obstaja v bazi.")
            else:
                print(f"Napaka API-ja: {resp.text}")
        except Exception as e:
            print(f"Izjema pri klicu AI: {e}")
            
    return jsonify({"success": True, "trends": TRENDS})

@app.route("/")
def home():
    return "Radar API is running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
