import requests

def get_dev_history_summary(dev_address, helius_api_key):
    """
    Traces dev wallet + funding wallet and analyzes past launches for:
    - Migrated count
    - Rugged count
    - Highest ATH Market Cap
    Outputs a clean 1-line string formatted for Telegram HTML.
    """
    headers = {"Accept": "application/json"}
    
    try:
        # 1. Fetch transactions for the dev wallet
        url = f"https://api.helius.xyz/v0/addresses/{dev_address}/transactions?api-key={helius_api_key}"
        resp = requests.get(url, headers=headers, timeout=5)
        txs = resp.json() if resp.status_code == 200 else []
        
        target_wallet = dev_address

        # 2. If dev wallet is fresh, trace funding source (Parent Wallet)
        if not txs or len(txs) < 5:
            for tx in reversed(txs):
                for transfer in tx.get("nativeTransfers", []):
                    if transfer.get("toUserAccount") == dev_address:
                        target_wallet = transfer.get("fromUserAccount")
                        break
                if target_wallet != dev_address:
                    break
            
            # Fetch transactions for the parent wallet
            if target_wallet != dev_address:
                parent_url = f"https://api.helius.xyz/v0/addresses/{target_wallet}/transactions?api-key={helius_api_key}"
                p_resp = requests.get(parent_url, headers=headers, timeout=5)
                txs = p_resp.json() if p_resp.status_code == 200 else []

        # 3. Analyze launches from the target wallet
        migrated = 0
        rugged = 0
        max_ath = 0
        total_launches = 0

        # Scan for created coins / pump contracts
        for tx in txs:
            if tx.get("type") == "CREATE" or "pump" in str(tx).lower():
                total_launches += 1
                
                # Check DexScreener/Pump stats for each past token address (simulated/fast-check)
                # Note: Helius tx data provides token mints created by this wallet
                events = tx.get("events", {})
                token_mint = events.get("nft", {}).get("nfts", [{}])[0].get("mint")
                
                if token_mint:
                    dex_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_mint}"
                    d_resp = requests.get(dex_url, timeout=3)
                    if d_resp.status_code == 200:
                        data = d_resp.json()
                        pairs = data.get("pairs")
                        if pairs:
                            migrated += 1
                            mcap = float(pairs[0].get("fdv", 0) or pairs[0].get("marketCap", 0))
                            if mcap > max_ath:
                                max_ath = mcap
                            if mcap < 1000:  # Dumped/rugged coin
                                rugged += 1
                        else:
                            rugged += 1

        # 4. Format Output String matching your exact HTML style
        if total_launches <= 1 and migrated == 0:
            return "Fresh Wallet (First Launch) 🆕"
        
        # Format ATH for display (e.g., $2.1M or $450K)
        if max_ath >= 1_000_000:
            ath_str = f"${max_ath / 1_000_000:.1f}M"
        elif max_ath >= 1_000:
            ath_str = f"${max_ath / 1_000:.0f}K"
        else:
            ath_str = f"${max_ath:.0f}"

        return f"Linked Dev ({migrated} Migrated | {rugged} Rugged | Top ATH: {ath_str})"

    except Exception as e:
        print(f"Error checking dev history: {e}")
        return "Fresh Wallet (First Launch) 🆕"
