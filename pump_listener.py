from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

AI_API_KEY = os.environ.get("AI_API_KEY", "default_test_key")

# Dynamic list in memory holding our live viral trends
TRENDS_DATABASE = [
    {
        "id": 1,
        "trend": "Mars Colonization Update",
        "suggested_name": "Mars Rover Dog",
        "symbol": "MRD",
        "description": "The latest breakthrough in interplanetary exploration and canine space travel.",
        "source_url": "https://www.nasa.gov"
    },
    {
        "id": 2,
        "trend": "Global Eclipse Phenomenon",
        "suggested_name": "Solar Darkness",
        "symbol": "ECLIPSE",
        "description": "Spectators watch in wonder as a rare total solar eclipse plunges regions into total darkness.",
        "source_url": "https://www.reuters.com"
    }
]

@app.route("/", methods=["GET"])
def home():
    return "MemeCollab & Viral Vault Backend is Running"

@app.route("/api/trends", methods=["GET"])
def get_trends():
    # Returns the live list of trends, latest first
    return jsonify({"success": True, "trends": list(reversed(TRENDS_DATABASE))}), 200

@app.route("/api/add-trend", methods=["POST"])
def add_trend():
    try:
        data = request.json
        new_item = {
            "id": len(TRENDS_DATABASE) + 1,
            "trend": data.get("trend"),
            "suggested_name": data.get("suggested_name"),
            "symbol": data.get("symbol"),
            "description": data.get("description"),
            "source_url": data.get("source_url")
        }
        TRENDS_DATABASE.append(new_item)
        return jsonify({"success": True, "message": "New trend added successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
