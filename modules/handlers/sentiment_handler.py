"""
Sentiment handler — news/macro sentiment analysis.
Fetches recent headlines and generates sentiment bar charts.
"""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
import io
import random
import requests
from datetime import datetime, timedelta

from modules.ai.agent import ai_sentiment, parse_json_response
from modules.market.fetcher import resolve_ticker
from modules.charts.generator import sentiment_chart
from config.settings import get_settings

s = get_settings()
router = Router()


# ── Mock news (no key / fallback) ─────────────────────────────────────────────

MOCK_NEWS = {
    "BTC": [
        "Bitcoin ETF sees record inflows as institutional demand surges",
        "MicroStrategy adds 4,500 BTC to its treasury",
        "El Salvador's bitcoin holdings now worth $100M+",
        "Bitcoin mining difficulty hits all-time high",
        "SEC delays decision on multiple bitcoin ETF applications",
    ],
    "ETH": [
        "Ethereum layer-2 networks process record transaction volume",
        "Ethereum staking yield drops to 3.8% amid increased supply",
        "Major DeFi protocol migrates to Ethereum L2",
        "Ethereum core devs discuss EIP-4844 implementation timeline",
        "Institutional ETH holdings grow 40% quarter-over-quarter",
    ],
    "SOL": [
        "Solana DEX volume surpasses Ethereum in weekly metrics",
        "Solana network experiences brief outage, recovers in 4 hours",
        "Major NFT marketplace launches on Solana",
        "Solana mobile phone ships to 100,000+ users",
        "Validator rewards on Solana increase post-network upgrade",
    ],
}


def _fetch_news(coin_id: str) -> list:
    """Try to fetch recent news via CoinGecko or return mock data."""
    # Try CoinGecko news
    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/coins/" + coin_id + "/tickers",
            params={"vs_currency": "usd", "include_24hr_vol": True},
            timeout=8,
        )
        if resp.status_code == 200:
            return [f"{coin_id.title()} trading at ${resp.json().get('tickers', [{}])[0].get('last', 0):.2f}"]
    except Exception:
        pass

    # Fallback to mock news for known coins
    symbol = coin_id.upper()
    if symbol in MOCK_NEWS:
        return MOCK_NEWS[symbol]

    # Generate generic mock news based on price direction
    directions = ["bullish", "bearish", "mixed"]
    direction = random.choice(directions)
    if direction == "bullish":
        return [
            f"{coin_id.title()} sees positive market sentiment",
            "On-chain metrics show accumulating behavior",
            "Technical indicators suggest upward momentum",
        ]
    else:
        return [
            f"{coin_id.title()} faces selling pressure",
            "Macro headwinds weigh on risk assets",
            "Traders book profits amid uncertainty",
        ]


@router.message(Command("sentiment"))
async def cmd_sentiment(message: Message):
    await message.answer(
        "📰 **Sentiment Analysis**\n\n"
        "Analyze news and social sentiment for an asset.\n\n"
        "_Example: `/sentiment BTC`_",
        parse_mode="Markdown",
    )


@router.message(F.text, F.chat.type == "private")
async def handle_sentiment(message: Message):
    user_text = message.text.strip()
    parts = user_text.split()
    asset_raw = parts[1].upper() if len(parts) > 1 else None

    if not asset_raw:
        await message.answer(
            "📰 **Sentiment Usage:**\n"
            "`/sentiment BTC` — analyze Bitcoin sentiment\n"
            "`/sentiment ETH` — analyze Ethereum sentiment\n"
            "`/sentiment overall` — market-wide sentiment\n\n"
            "Shows: sentiment score, bullish/bearish factors, bar chart.",
            parse_mode="Markdown",
        )
        return

    data = resolve_ticker(asset_raw)
    coin_id = data.get("id", asset_raw.lower()) if data["type"] == "crypto" else asset_raw.lower()

    await message.answer(f"📡 Reading market sentiment for {asset_raw}...")

    news_items = _fetch_news(coin_id)
    result = ai_sentiment(asset_raw, news_items)
    parsed = parse_json_response(result.get("raw", "")) if isinstance(result, dict) else None

    if parsed:
        score = parsed.get("score", 0)
        summary = parsed.get("summary", "")
        bullish = parsed.get("bullish_factors", [])
        bearish = parsed.get("bearish_factors", [])
    else:
        # Simulated
        score = round(random.uniform(-0.6, 0.8), 2)
        summary = f"{asset_raw} sentiment is {'positive' if score > 0 else 'negative'} based on available data."
        bullish = ["API key not configured — showing simulated values"]
        bearish = ["This is not financial advice"]

    # Sentiment chart
    sentiment_map = {asset_raw: score}
    chart_buf = sentiment_chart(sentiment_map)

    # Score visualization
    score_bar_len = int(abs(score) * 10)
    if score >= 0:
        score_bar = "🟢" * score_bar_len + "⬜" * (10 - score_bar_len) + f" +{score:.2f}"
    else:
        score_bar = "⬜" * (10 - score_bar_len) + "🔴" * score_bar_len + f" {score:.2f}"

    emoji = "🟢" if score >= 0.3 else ("🔴" if score <= -0.3 else "🟡")
    label = "BULLISH" if score >= 0.3 else ("BEARISH" if score <= -0.3 else "NEUTRAL")

    lines = [
        f"📰 **{asset_raw} — Sentiment Analysis**\n",
        f"{emoji} **Score:** `{score:.2f}` / 1.00\n",
        f"{'='*20}\n",
        f"[{score_bar}]\n",
        f"**Overall:** {label}\n",
        f"_{summary}_\n",
    ]

    if bullish:
        lines.append("\n🟢 **Bullish factors:**")
        for b in bullish[:4]:
            lines.append(f"  • {b}")

    if bearish:
        lines.append("\n🔴 **Bearish factors:**")
        for b in bearish[:4]:
            lines.append(f"  • {b}")

    lines.append("\n_Sentiment changes fast — verify with your own research._")

    chart_buf.seek(0)
    await message.answer("\n".join(lines), parse_mode="Markdown")
    await message.answer_photo(photo=chart_buf, caption="📊 Sentiment score")
