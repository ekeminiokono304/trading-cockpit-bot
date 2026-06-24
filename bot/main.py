"""
Trading Cockpit Bot — Main entry point
A 6-panel AI-powered Telegram trading bot.

Run:
    pip install -r requirements.txt
    cp .env.example .env  # fill in your keys
    python -m bot.main
"""

import logging
import sys
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.types import (
    Message, ReplyKeyboardMarkup, ReplyKeyboardRemove,
    KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.filters import Command, Text
from aiogram.enums import ParseMode
from aiogram.utils.markdown import hbold, hitalic

from config.settings import get_settings
from modules.handlers import (
    chat_handler,
    predict_handler,
    signals_handler,
    sentiment_handler,
    portfolio_handler,
    learn_handler,
)

s = get_settings()

# ── Logging ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, s.log_level, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("trading-cockpit-bot")


# ── Bot & Dispatcher ───────────────────────────────────────────────────────────

bot = Bot(token=s.telegram_bot_token, parse_mode=ParseMode.MARKDOWN)
dp = Dispatcher()


# ── Keyboards ──────────────────────────────────────────────────────────────────

def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="💬 Chat"),
                KeyboardButton(text="📊 Predict"),
                KeyboardButton(text="📈 Signals"),
            ],
            [
                KeyboardButton(text="📰 Sentiment"),
                KeyboardButton(text="💰 Portfolio"),
                KeyboardButton(text="🎓 Learn"),
            ],
            [
                KeyboardButton(text="🗑️ Clear"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Choose a panel or type a command...",
    )


def panel_keyboard(panel: str) -> InlineKeyboardMarkup:
    """Per-panel quick-action buttons."""
    panels = {
        "chat": ["📊 Predict", "📈 Signals", "🎓 Learn"],
        "predict": ["💬 Chat", "📈 Signals", "📰 Sentiment"],
        "signals": ["📊 Predict", "💬 Chat", "💰 Portfolio"],
        "sentiment": ["📊 Predict", "💬 Chat", "🎓 Learn"],
        "portfolio": ["📈 Signals", "📊 Predict", "💬 Chat"],
        "learn": ["💬 Chat", "📰 Sentiment", "📈 Signals"],
    }
    row = [
        InlineKeyboardButton(text=name, callback_data=f"panel:{cmd}")
        for name, cmd in zip(panels.get(panel, []), ["predict", "signals", "sentiment", "portfolio", "learn", "chat"])
    ]
    return InlineKeyboardMarkup(inline_keyboard=[row])


# ── Panel descriptions ─────────────────────────────────────────────────────────

PANEL_INFO = {
    "chat": (
        "💬 **Trading Chat**\n\n"
        "Freeform AI assistant for any trading question.\n"
        "Ask about: market analysis, trade ideas, terminology.\n\n"
        "_Example: What do you think about BTC right now?_"
    ),
    "predict": (
        "📊 **Price Prediction**\n\n"
        "AI-powered price forecasts with confidence bands.\n"
        "Usage: `/predict btc` or `/predict btc 1w`\n"
        "_Available: 1d, 1w, 1m horizons_"
    ),
    "signals": (
        "📈 **Technical Signals**\n\n"
        "RSI, MACD, EMA crossover analysis.\n"
        "Usage: `/signals btc`\n"
        "_Real indicators + AI signal interpretation_"
    ),
    "sentiment": (
        "📰 **Sentiment Analysis**\n\n"
        "News impact and market mood.\n"
        "Usage: `/sentiment btc`\n"
        "_Shows: score, bullish/bearish factors_"
    ),
    "portfolio": (
        "💰 **Portfolio Tracker**\n\n"
        "Track holdings, allocation, and P&L.\n\n"
        "`/add btc 0.5` — add 0.5 BTC\n"
        "`/remove btc 0.1` — remove 0.1 BTC\n"
        "`/portfolio` — view chart"
    ),
    "learn": (
        "🎓 **Trading Academy**\n\n"
        "Learn trading concepts and strategies.\n\n"
        "Built-in lessons: `sma`, `ema`, `rsi`, `macd`, `bollinger`, `risk`, `position`, `sentiment2`, `strategies`\n\n"
        "Or ask: `/learn What is RSI?`"
    ),
}


# ── Start / Help ───────────────────────────────────────────────────────────────

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 **Welcome to Trading Cockpit!**\n\n"
        "Your 6-panel AI trading terminal:\n\n"
        "💬 **Chat** — Freeform AI trading assistant\n"
        "📊 **Predict** — AI price forecasts + confidence bands\n"
        "📈 **Signals** — Technical indicator analysis (RSI/MACD/EMA)\n"
        "📰 **Sentiment** — News and macro mood analysis\n"
        "💰 **Portfolio** — Track holdings and P&L\n"
        "🎓 **Learn** — Trading education and strategy guides\n\n"
        "Choose a panel below or tap a command.",
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await cmd_start(message)


@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    await cmd_start(message)


# ── Keyboard button handler ─────────────────────────────────────────────────────

@dp.message(Text)
async def handle_keyboard_buttons(message: Message, state=None):
    text = message.text

    # Panel buttons
    panel_map = {
        "💬 Chat": "chat",
        "📊 Predict": "predict",
        "📈 Signals": "signals",
        "📰 Sentiment": "sentiment",
        "💰 Portfolio": "portfolio",
        "🎓 Learn": "learn",
        "🗑️ Clear": "clear",
    }

    panel = panel_map.get(text)

    if panel == "clear":
        await message.answer("✅ Cleared.", reply_markup=ReplyKeyboardRemove())
        await asyncio.sleep(0.3)
        await cmd_start(message)
        return

    if panel:
        info = PANEL_INFO.get(panel, "")
        await message.answer(info, parse_mode="Markdown", reply_markup=main_keyboard())
        return

    # Unknown text — default to chat
    await chat_handler.handle_chat(message, {})


# ── Callback query (inline panel switching) ────────────────────────────────────

@dp.callback_query()
async def handle_callback(callback):
    from aiogram.types import CallbackQuery
    if not isinstance(callback, CallbackQuery):
        return

    data = callback.data
    if data and data.startswith("panel:"):
        panel = data.split(":", 1)[1]
        info = PANEL_INFO.get(panel, "")
        await callback.message.answer(info, parse_mode="Markdown")
        await callback.answer()


# ── Error handler ──────────────────────────────────────────────────────────────

@dp.error()
async def error_handler(event):
    log.error("Unhandled error: %s", event, exc_info=event.errors if hasattr(event, "errors") else None)


# ── Register routers ───────────────────────────────────────────────────────────

dp.include_router(chat_handler.router)
dp.include_router(predict_handler.router)
dp.include_router(signals_handler.router)
dp.include_router(sentiment_handler.router)
dp.include_router(portfolio_handler.router)
dp.include_router(learn_handler.router)


# ── Run ────────────────────────────────────────────────────────────────────────

async def main():
    if not s.telegram_bot_token:
        log.error("❌ TELEGRAM_BOT_TOKEN not set. Add it to .env")
        sys.exit(1)

    log.info("🚀 Trading Cockpit Bot starting...")
    log.info("📋 Panels: Chat | Predict | Signals | Sentiment | Portfolio | Learn")
    log.info("💬 Send /start to your bot on Telegram")

    try:
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
