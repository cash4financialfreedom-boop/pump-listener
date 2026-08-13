from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/", methods=["GET"])
def home():
    return "MemeCollab & Viral Vault Backend is Running"

@app.route("/api/create-token", methods=["POST"])
def create_token():
    try:
        data = request.json
        token_name = data.get("name")
        token_symbol = data.get("symbol")
        wallet_address = data.get("wallet")

        if not token_name or not token_symbol or not wallet_address:
            return jsonify({"error": "Missing required fields"}), 400

        print(f"Received token creation request: {token_name} ({token_symbol}) for wallet {wallet_address}")

        return jsonify({
            "success": True,
            "message": f"Token {token_name} successfully registered in the system! (1% (Viral Vault included))"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/trends", methods=["GET"])
def get_trends():
    # Simulated live viral trends feed for the app dashboard
    mock_trends = [
        {
            "id": 1,
            "trend": "Mars Colonization Update",
            "suggested_name": "Mars Rover Dog",
            "symbol": "MRD",
            "description": "The latest breakthrough in interplanetary exploration and canine space travel."
        },
        {
            "id": 2,
            "trend": "Global Coffee Shortage",
            "suggested_name": "Caffeine Panic",
            "symbol": "BREW",
            "description": "When the world runs out of coffee, this token powers the awake community."
        }
    ]
    return jsonify({"success": True, "trends": mock_trends}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
