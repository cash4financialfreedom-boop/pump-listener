import requests

def get_dev_history_summary(dev_address, helius_api_key):
    """
    Traces dev wallet and funding source. Safe execution that never crashes the bot.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        if not dev_address or not helius_api_key:
            return "Fresh Wallet (First Launch) 🆕"

        # 1. Fetch transactions for the dev wallet from Helius
        url = f"https://api.helius.xyz/v0/addresses/{dev_address}/transactions?api-key={helius_api_key}"
        try:
            resp = requests.get(url, headers=headers, timeout=4)
            txs = resp.json() if resp.status_code == 200 and isinstance(resp.json(), list) else []
        except Exception:
            txs = []
        
        target_wallet = dev_address

        # 2. If fresh wallet, trace funding address
        if len(txs) < 5:
            for tx in reversed(txs):
                if isinstance(tx, dict):
                    for transfer in tx.get("nativeTransfers", []):
                        if transfer.get("toUserAccount") == dev_address:
                            funder = transfer.get("fromUserAccount")
                            if funder and funder != dev_address:
                                target_wallet = funder
                                break
                if target_wallet != dev_address:
                    break
            
            # Fetch transactions for parent wallet
            if target_wallet != dev_address:
                try:
                    parent_url = f"https://api.helius.xyz/v0/addresses/{target_wallet}/transactions?api-key={helius_api_key}"
                    p_resp = requests.get(parent_url, headers=headers, timeout=4)
                    txs = p_resp.json() if p_resp.status_code == 200 and isinstance(p_resp.json(), list) else []
                except Exception:
                    pass

        # 3. Analyze past token launches
        migrated = 0
        rugged = 0
        max_ath = 0
        total_launches = 0

        for tx in txs:
            if isinstance(tx, dict) and (tx.get("type") == "CREATE" or "pump" in str(tx).lower()):
                total_launches += 1
                
                # Check token details via DexScreener safely
                token_mint = None
                events = tx.get("events", {})
                if isinstance(events, dict):
                    nfts = events.get("nft", {}).get("nfts", [])
                    if nfts and isinstance(nfts, list) and len(nfts) > 0:
                        token_mint = nfts[0].get("mint")

                if token_mint:
                    try:
                        dex_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_mint}"
                        d_resp = requests.get(dex_url, headers=headers, timeout=2)
                        if d_resp.status_code == 200:
                            data = d_resp.json()
                            pairs = data.get("pairs")
                            if pairs and len(pairs) > 0:
                                migrated += 1
                                mcap = float(pairs[0].get("fdv", 0) or pairs[0].get("marketCap", 0) or 0)
                                if mcap > max_ath:
                                    max_ath = mcap
                                if mcap < 1000:
                                    rugged += 1
                            else:
                                rugged += 1
                        else:
                            rugged += 1
                    except Exception:
                        pass

        # 4. Return clean string
        if total_launches <= 1 and migrated == 0:
            return "Fresh Wallet (First Launch) 🆕"
        
        if max_ath >= 1_000_000:
            ath_str = f"${max_ath / 1_000_000:.1f}M"
        elif max_ath >= 1_000:
            ath_str = f"${max_ath / 1_000:.0f}K"
        else:
            ath_str = f"${max_ath:.0f}"

        return f"Linked Dev ({migrated} Migrated | {rugged} Rugged | Top ATH: {ath_str})"

    except Exception as e:
        print(f"Dev history error (handled): {e}")
        return "Fresh Wallet (First Launch) 🆕"
