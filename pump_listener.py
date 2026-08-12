import os
import time
import threading
import requests
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health_check():
    return "Raydium Sniper is Running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")

# Uporabimo uradni javni Solana RPC node (brezplačen, brez API ključev in kvot)
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

def fetch_solana_onchain(seen_mints):
    print("Checking Solana RPC blockchain directly...", flush=True)
    
    # JSON-RPC klic za zadnje transakcije / podpisane unose na Raydium Liquidity Pool programu
    # Raydium AMM Program ID: 675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [
            "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
            {"limit": 5}
        ]
    }
    
    try:
        resp = requests.post(SOLANA_RPC_URL, json=payload, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            signatures = data.get("result", [])
            
            for sig_info in signatures:
                sig = sig_info.get("signature")
                if not sig or sig in seen_mints:
                    continue
                
                seen_mints.add(sig)
                
                # Ko najdemo novo transakcijo na Raydiumu, jo pošljemo naprej v n8n z direktnim linkom na verigo
                hook_payload = {
                    "tokenName": f"Solana-Raydium-Tx",
                    "marketCap": 50000,
                    "mint": sig,
                    "twitterUrl": f"https://twitter.com/search?q={sig}",
                    "pair_url": f"https://solscan.io/tx/{sig}"
                }
                
                if N8N_WEBHOOK_URL:
                    try:
                        requests.post(N8N_WEBHOOK_URL, json=hook_payload, timeout=5)
                        print(f"SUCCESSFULLY SENT ON-CHAIN TX TO N8N: {sig[:10]}...", flush=True)
                    except Exception as err:
                        print(f"Webhook error: {err}", flush=True)
                
                break
    except Exception as e:
        print(f"RPC Error: {e}", flush=True)

def main():
    print("Sniper Active via Direct Solana RPC...", flush=True)
    seen_mints = set()
    while True:
        fetch_solana_onchain(seen_mints)
        time.sleep(15)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()
