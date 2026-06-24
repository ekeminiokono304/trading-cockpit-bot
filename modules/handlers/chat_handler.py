"""
Chat handler — freeform AI trading assistant.
Routes to the AI agent. Shows the response with optional inline chart.
"""

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.filters import Command
import io

from modules.ai.agent import chat, parse_json_response
from modules.market.fetcher import resolve_ticker, get_stock_info, get_crypto_price
from modules.charts.generator import candlestick_chart, build_indicators

router = Router()


# ── /chat ─────────────────────────────────────────────────────────────────────

@router.message(Command("chat"))
async def cmd_chat(message: Message):
    await message.answer(
        "💬 **Trading Chat**\n\n"
        "Ask me anything about markets, trades, or strategy.\n\n"
        "_Example: 'What do you think about BTC now?'_",
        parse_mode="Markdown",
    )


@router.message(F.text, F.chat.type == "private")
async def handle_chat(message: Message, state: dict):
    user_text = message.text.strip()
    if not user_text:
        return

    # Extract potential ticker mentions
    words = user_text.upper().split()
    tickers_mentioned = [
        w for w in words
        if len(w) <= 5 and w.isalpha()
        and w not in ("BTC", "ETH", "USD", "EUR", "GBP", "THE", "AND", "FOR", "YOU", "ARE", "BUT", "NOT")
    ]

    chart_buf = None
    extra_info = ""

    # If they mention a ticker, fetch quick info
    if tickers_mentioned:
        ticker = tickers_mentioned[0]
        data = resolve_ticker(ticker)
        if data["type"] == "crypto":
            pd_ = data["price_data"]
            if pd_:
                change = pd_["change_24h"]
                emoji = "🟢" if change >= 0 else "🔴"
                extra_info = (
                    f"\n\n{emoji} **{ticker.upper()}** — ${pd_['price']:,.2f} "
                    f"({change:+.2f}% 24h)\n"
                    f"MCap: ${pd_['market_cap']:,.0f} | Vol: ${pd_['volume_24h']:,.0f}"
                )
                # Also try to get a chart
                if data["candles"] is not None and len(data["candles"]) > 5:
                    indicators = build_indicators(data["candles"])
                    chart_buf = candlestick_chart(
                        data["candles"], symbol=ticker, indicators=indicators,
                        title=f"📊 {ticker} — 24h Chart"
                    )
        elif data["type"] == "stock":
            info = data["info"]
            if info and info.get("price"):
                extra_info = (
                    f"\n\n📊 **{info['symbol']}** — ${info['price']:.2f}\n"
                    f"MCap: ${info['market_cap'] or 0:,.0f} | Vol: {info['volume'] or 0:,.0f}"
                )
                if data["candles"] is not None and len(data["candles"]) > 5:
                    indicators = build_indicators(data["candles"])
                    chart_buf = candlestick_chart(
                        data["candles"], symbol=info["symbol"], indicators=indicators
                    )

    await message.answer("🤔 Thinking...")
    response = chat(user_text, mode="chat")
    response += extra_info

    if chart_buf:
        chart_buf.seek(0)
        await message.answer_photo(photo=chart_buf, caption=response, parse_mode="Markdown")
    else:
        await message.answer(response, parse_mode="Markdown")
