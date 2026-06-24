"""
Signals handler — technical indicator alerts (RSI, MACD, EMA crossovers).
Generates annotated candlestick charts with buy/sell markers.
"""

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import io

from modules.ai.agent import ai_signals, parse_json_response
from modules.market.fetcher import resolve_ticker
from modules.charts.generator import (
    signals_chart, detect_signals, build_indicators
)

router = Router()


@router.message(Command("signals"))
async def cmd_signals(message: Message):
    await message.answer(
        "📈 **Technical Signals**\n\n"
        "Get RSI, MACD, EMA crossover analysis for any asset.\n\n"
        "_Example: `/signals btc`_",
        parse_mode="Markdown",
    )


@router.message(F.text, F.chat.type == "private")
async def handle_signals(message: Message):
    user_text = message.text.strip()

    # Parse /signals or just a ticker
    parts = user_text.split()
    asset_raw = parts[1].upper() if len(parts) > 1 else None

    if not asset_raw:
        await message.answer(
            "📈 **Signals Usage:**\n"
            "`/signals BTC` — analyze Bitcoin\n"
            "`/signals ETH` — analyze Ethereum\n"
            "`/signals AAPL` — analyze Apple stock\n\n"
            "Shows: RSI, MACD, EMA crossovers, support/resistance.",
            parse_mode="Markdown",
        )
        return

    data = resolve_ticker(asset_raw)

    if data["type"] == "crypto":
        price_info = data["price_data"]
        candles = data["candles"]
    elif data["type"] == "stock":
        price_info = data["info"]
        candles = data["candles"]
    else:
        await message.answer("❌ Could not resolve that asset.")
        return

    if candles is None or len(candles) < 20:
        await message.answer(
            f"❌ Not enough candle data for `{asset_raw}` to compute indicators.",
            parse_mode="Markdown",
        )
        return

    await message.answer(f"📡 Scanning {asset_raw} for signals...")

    # Compute indicators locally
    indicators = build_indicators(candles)
    buy_signals, sell_signals = detect_signals(candles)

    # Get AI signal analysis
    result = ai_signals(asset_raw, candles, indicators)
    parsed = parse_json_response(result.get("raw", "")) if isinstance(result, dict) else None

    # Generate chart
    chart_buf = signals_chart(candles, asset_raw, buy_signals, sell_signals)

    # Format signal text
    emoji_map = {
        "Strong Buy": "🟢🟢",
        "Buy": "🟢",
        "Neutral": "🟡",
        "Sell": "🔴",
        "Strong Sell": "🔴🔴",
        "bullish": "📈",
        "bearish": "📉",
        "neutral": "➡️",
    }

    if parsed:
        trend = emoji_map.get(parsed.get("trend", ""), "➡️") + f" {parsed.get('trend', 'unknown').capitalize()}"
        signal = emoji_map.get(parsed.get("signal", ""), "⚪") + f" {parsed.get('signal', 'Unknown')}"
        strength = parsed.get("signal_strength", 0)
        support = parsed.get("support")
        resistance = parsed.get("resistance")
        reasons = parsed.get("reasons", [])
    else:
        trend = "➡️ Calculating..."
        signal = "⚪ Neutral"
        strength = 50
        support = None
        resistance = None
        reasons = ["Set OPENROUTER_API_KEY for AI signal analysis"]

    # Build response
    price_str = ""
    if price_info:
        if data["type"] == "crypto":
            price_str = f"💵 **${price_info.get('price', 0):,.2f}** ({price_info.get('change_24h', 0):+.2f}% 24h)"
        else:
            price_str = f"💵 **${price_info.get('price', 0):,.2f}**"

    signal_bar = "█" * int(strength / 10) + "░" * (10 - int(strength / 10))

    lines = [
        f"📈 **{asset_raw} — Technical Signals**\n",
        f"{price_str}\n" if price_str else "",
        f"**Trend:** {trend}",
        f"**Signal:** {signal}",
        f"**Strength:** [{signal_bar}] {strength}%\n",
    ]

    if support:
        lines.append(f"🛡️ **Support:** ${support:,.2f}")
    if resistance:
        lines.append(f"🔴 **Resistance:** ${resistance:,.2f}")

    if reasons:
        lines.append("\n**Analysis:**")
        for r in reasons[:4]:
            lines.append(f"  • {r}")

    lines.append(f"\n🟢 Buy signals: **{len(buy_signals)}**")
    lines.append(f"🔴 Sell signals: **{len(sell_signals)}**")
    lines.append("\n_This is analysis, not financial advice._")

    chart_buf.seek(0)
    await message.answer("\n".join(lines), parse_mode="Markdown")
    await message.answer_photo(photo=chart_buf, caption=f"📊 {asset_raw} signals chart")
