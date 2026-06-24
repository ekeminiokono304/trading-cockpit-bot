"""
AI Agent layer — routes prompts to OpenRouter (GPT-4o, Claude, Gemini, etc.)
Single unified client. Falls back gracefully on missing API key.
"""

import json
import httpx
from typing import Optional
from config.settings import get_settings

s = get_settings()

DEFAULT_MODEL = s.default_model or "openai/gpt-4o"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _build_client() -> httpx.Client:
    headers = {
        "Authorization": f"Bearer {s.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://trading-cockpit.local",
        "X-Title": "Trading Cockpit Bot",
    }
    return httpx.Client(headers=headers, timeout=60)


# ── System prompts per chat mode ──────────────────────────────────────────────

SYSTEM_PROMPTS = {
    "chat": """You are a sharp, no-nonsense trading analyst assistant.
You help users understand markets, evaluate trades, and think through risk.
Be direct. Give specific numbers. Never say 'it depends' without resolving what it depends on.
Keep answers concise — a few paragraphs max. Use bullet points for tradeoffs.
Never give financial advice that could be construed as professional. Always include: 'This is analysis, not advice.'""",

    "predict": """You are a quantitative price analyst.
Given historical OHLCV data and current market conditions, produce:
1. A price forecast for 1 day, 1 week, and 1 month ahead
2. A confidence score (0–100%) for each horizon
3. Key supporting reasons (trend, volume, macro, RSI level)
4. Key risks / what could invalidate the forecast

Output strictly valid JSON:
{
  "predictions": [
    {"horizon": "1d", "price": 0.00, "confidence": 0},
    {"horizon": "1w", "price": 0.00, "confidence": 0},
    {"horizon": "1m", "price": 0.00, "confidence": 0}
  ],
  "reasoning": ["reason1", "reason2"],
  "risks": ["risk1", "risk2"]
}

Use realistic prices. If you can't determine a trend from the data, say so.""",

    "signals": """You are a technical analysis specialist.
Given recent OHLCV data and computed indicators (RSI, MACD, EMA crossovers),
identify:
1. Current trend direction (bullish / bearish / neutral)
2. Key support and resistance levels
3. The most compelling buy and sell signals right now
4. Overall signal strength (Strong Buy / Buy / Neutral / Sell / Strong Sell)

Output strictly valid JSON:
{
  "trend": "bullish|bearish|neutral",
  "signal": "Strong Buy|Buy|Neutral|Sell|Strong Sell",
  "signal_strength": 0-100,
  "support": 0.00,
  "resistance": 0.00,
  "reasons": ["reason1", "reason2"]
}""",

    "sentiment": """You are a macro market sentiment analyst.
Analyze the current sentiment for the given asset or market.
Consider: recent news tone, social media trends, on-chain data hints, macro context.
Produce:
1. Sentiment score: -1.0 (extremely bearish) to +1.0 (extremely bullish)
2. A brief 2-sentence sentiment summary
3. Key bullish factors (list)
4. Key bearish factors (list)

Output strictly valid JSON:
{
  "score": 0.00,
  "summary": "...",
  "bullish_factors": ["..."],
  "bearish_factors": ["..."]
}""",

    "portfolio": """You are a portfolio analysis assistant.
Given a user's portfolio allocation and current prices, provide:
1. Overall portfolio health score (0-100)
2. Risk assessment (concentrated / diversified / overexposed)
3. Rebalancing suggestions
4. Any red flags (e.g. >50% in one asset, heavy stablecoin allocation)

Respond in clean markdown. Use emojis. Keep it scannable.""",

    "learn": """You are a patient trading educator.
Explain the requested concept clearly and practically.
Use analogies. Show the formula if relevant.
Give one concrete example of how a retail trader would use this.
Keep it digestible — 3–5 key points max.""",
}


# ── Core LLM call ─────────────────────────────────────────────────────────────

def chat(
    prompt: str,
    mode: str = "chat",
    model: str = DEFAULT_MODEL,
    history: Optional[list[dict]] = None,
) -> str:
    """
    Send a prompt to the LLM via OpenRouter.

    Args:
        prompt:      The user message
        mode:        Which system prompt to use (chat / predict / signals / etc.)
        model:       Model slug from OpenRouter
        history:     Optional list of {"role": "user"|"assistant", "content": "..."}

    Returns:
        The model's text response.
    """
    if not s.openrouter_api_key:
        return _mock_response(mode, prompt)

    system = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["chat"])

    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7 if mode == "chat" else 0.3,
        "max_tokens": 1024,
    }

    try:
        with _build_client() as client:
            resp = client.post(OPENROUTER_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return "⚠️ OpenRouter API key is invalid or expired. Check your .env file."
        return f"⚠️ API error: {e.response.status_code} — {e.response.text[:200]}"
    except Exception as e:
        return f"⚠️ LLM call failed: {str(e)}"


def parse_json_response(response: str) -> Optional[dict]:
    """Extract JSON from LLM output, handling markdown code fences."""
    text = response.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        # Try finding JSON within the text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        return None


# ── Mode-specific helpers ───────────────────────────────────────────────────────

def ai_predict(asset: str, price_data: dict, candles_df) -> dict:
    """Get AI price prediction for an asset."""
    prompt = f"""Asset: {asset}
Current price data: {price_data}
Recent OHLCV data (last 10 candles):
{candles_df.tail(10).to_string() if candles_df is not None else 'No candle data available.'}

Provide your price prediction analysis in JSON format."""
    response = chat(prompt, mode="predict")
    parsed = parse_json_response(response)
    if parsed:
        return parsed
    return {"raw": response, "error": "Could not parse JSON from model"}


def ai_signals(asset: str, candles_df, indicators: dict) -> dict:
    """Get AI technical signal analysis."""
    prompt = f"""Asset: {asset}
Recent 20 candles:
{candles_df.tail(20).to_string() if candles_df is not None else 'No data.'}

Indicators (RSI, EMA): {indicators}

Provide signal analysis in JSON format."""
    response = chat(prompt, mode="signals")
    parsed = parse_json_response(response)
    if parsed:
        return parsed
    return {"raw": response, "error": "Could not parse JSON from model"}


def ai_sentiment(asset: str, news_items: list) -> dict:
    """Get AI sentiment analysis."""
    news_text = "\n".join([f"- {n}" for n in news_items]) if news_items else "No recent news."
    prompt = f"""Asset: {asset}
Recent news:\n{news_text}

Provide sentiment analysis in JSON format."""
    response = chat(prompt, mode="sentiment")
    parsed = parse_json_response(response)
    if parsed:
        return parsed
    return {"raw": response, "error": "Could not parse JSON from model"}


# ── Mock response (no API key) ───────────────────────────────────────────────

def _mock_response(mode: str, prompt: str) -> str:
    return {
        "chat": (
            "🤖 **OpenRouter API key not set.** Add your key to `.env` to enable AI responses.\n\n"
            "Get a free key at https://openrouter.ai/credits\n\n"
            "For now, here's what I'd tell you:\n\n"
            f"> {prompt[:200]}{'...' if len(prompt) > 200 else ''}\n\n"
            "**Setup:**\n"
            "1. Copy `.env.example` → `.env`\n"
            "2. Add `OPENROUTER_API_KEY=sk-...`\n"
            "3. Restart the bot"
        ),
        "predict": json.dumps({
            "predictions": [
                {"horizon": "1d", "price": None, "confidence": 0},
                {"horizon": "1w", "price": None, "confidence": 0},
                {"horizon": "1m", "price": None, "confidence": 0}
            ],
            "reasoning": ["API key not configured"],
            "risks": ["Set OPENROUTER_API_KEY in .env to enable predictions"]
        }),
        "signals": json.dumps({
            "trend": "unknown", "signal": "Unknown", "signal_strength": 0,
            "support": None, "resistance": None, "reasons": ["Set OPENROUTER_API_KEY"]
        }),
        "sentiment": json.dumps({
            "score": 0, "summary": "Configure API key for real sentiment.",
            "bullish_factors": [], "bearish_factors": []
        }),
        "portfolio": "⚠️ Set `OPENROUTER_API_KEY` in `.env` to enable portfolio analysis.",
        "learn": "⚠️ Set `OPENROUTER_API_KEY` in `.env` to access the Learn module.",
    }.get(mode, "Configure your OpenRouter API key in `.env` to use this feature.")
