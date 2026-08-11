{
  "model": "claude-3-5-sonnet-20240620",
  "max_tokens": 300,
  "messages": [
    {
      "role": "user",
      "content": "You are a professional, high-stakes Solana crypto analyst. Your job is to perform an immediate, aggressive audit of this token based on its current market state and social narrative. No fluff.\n\nToken Details:\n- Name: {{$json.tokenName}}\n- Market Cap: {{$json.marketCap}}\n- Twitter: {{$json.twitterUrl}}\n- Pair: {{$json.pair_url}}\n\nTask:\n1. Analyze the social narrative: Is it tied to a viral meta (Musk, Trump, TikTok, viral animals)?\n2. Provide a 'Viral Score' from 1 to 10.\n3. Give a clear, actionable 'Buy' or 'Skip' recommendation with a 1-sentence reason.\n4. Crucial: Do not use any markdown bold formatting (no **).\n\nOutput strictly in this format:\n\n🔥 SOLANA ALPHA AUDIT\n\nToken: {{$json.tokenName}}\nMarket Cap: {{$json.marketCap}}\nViral Score: X/10\nVerdict: [Buy/Skip] - [Reason]\n\nLink: {{$json.pair_url}}"
    }
  ]
}
