import asyncio
import json
import requests
import websockets

# Tvoj n8n Production Webhook URL:
N8N_WEBHOOK_URL = (
    "https://alphasniffer.app.n8n.cloud/webhook/6bf47bed-b6a7-4bfa-acea-e49debdbe34"
)


async def subscribe_pumpfun():
    uri = "wss://pumpportal.fun/api/data"
    async with websockets.connect(uri) as websocket:
        # Naročimo se na vse nove ustvarjene žetone
        payload = {"method": "subscribeNewToken"}
        await websocket.send(json.dumps(payload))
        print("✅ Povezano na Pump.fun! Poslušam nove kovance...")

        # Nova zanka, ki deluje brez napak v vseh verzijah:
        async for message in websocket:
            try:
                data = json.loads(message)

                if "mint" in data:
                    print(
                        f"🚀 Nov kovanec: {data.get('name')} ({data.get('symbol')}) | CA: {data.get('mint')}"
                    )
                    try:
                        requests.post(N8N_WEBHOOK_URL, json=data, timeout=5)
                    except Exception as e:
                        print(f"Napaka pri pošiljanju na n8n: {e}")

            except Exception as e:
                print(f"Napaka pri obdelavi: {e}")


if __name__ == "__main__":
    asyncio.run(subscribe_pumpfun())