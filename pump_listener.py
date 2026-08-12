import os
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

@app.route('/')
def home():
    return "MemeCollab & Viral Vault Backend is Running", 200

@app.route('/api/create-token', methods=['POST'])
def create_token():
    data = request.get_json()
    if not data or 'name' not in data or 'symbol' not in data:
        return jsonify({"error": "Missing token name or symbol"}), 400
    
    token_name = data['name']
    token_symbol = data['symbol']
    creator_wallet = data.get('wallet', 'unknown')
    
    print(f"Creating viral meme token: {token_name} ({token_symbol}) for wallet {creator_wallet}", flush=True)
    
    return jsonify({
        "status": "success",
        "message": f"Token {token_name} successfully registered in the system!",
        "vault_fee_share": "1% (Viral Vault included)"
    }), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
