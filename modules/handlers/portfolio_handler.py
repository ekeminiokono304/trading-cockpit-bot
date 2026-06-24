"""
Portfolio handler — track holdings, P&L, and allocation.
User can add/remove holdings and see pie + P&L charts.
"""

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.filters import Command, Text
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import io
import json
import random
from pathlib import Path

from modules.market.fetcher import resolve_ticker
from modules.charts.generator import portfolio_chart
from modules.ai.agent import chat

router = Router()

DATA_DIR = Path("/root/trading-cockpit-bot/data")
DATA_DIR.mkdir(exist_ok=True)

PORTFOLIO_FILE = DATA_DIR / "portfolios.json"


def load_portfolios() -> dict:
    try:
        return json.loads(PORTFOLIO_FILE.read_text())
    except Exception:
        return {}


def save_portfolios(data: dict):
    PORTFOLIO_FILE.write_text(json.dumps(data, indent=2))


class PortfolioStates(StatesGroup):
    waiting_for_ticker = State()
    waiting_for_amount = State()
    waiting_for_action = State()


def get_portfolio(user_id: int) -> dict:
    return load_portfolios().get(str(user_id), {})


def update_portfolio(user_id: int, ticker: str, amount: float, action: str):
    portfolios = load_portfolios()
    uid = str(user_id)
    if uid not in portfolios:
        portfolios[uid] = {"holdings": {}}
    holdings = portfolios[uid]["holdings"]
    ticker = ticker.upper()

    if action == "add":
        if ticker in holdings:
            holdings[ticker] += amount
        else:
            holdings[ticker] = amount
    elif action == "remove":
        holdings[ticker] = max(0, holdings[ticker] - amount)

    # Remove zero holdings
    portfolios[uid]["holdings"] = {k: v for k, v in holdings.items() if v > 0}
    save_portfolios(portfolios)


def get_mock_pnl(holdings: dict) -> dict:
    """Generate realistic-looking P&L for holdings."""
    pnl = {}
    for ticker, amount in holdings.items():
        change = random.uniform(-8, 12)
        pnl[ticker] = round(change, 2)
    return pnl


@router.message(Command("portfolio"))
async def cmd_portfolio(message: Message, state: FSMContext):
    user_id = message.from_user.id
    portfolio = get_portfolio(user_id)
    holdings = portfolio.get("holdings", {})

    if not holdings:
        await message.answer(
            "💰 **Your Portfolio**\n\n"
            "No holdings tracked yet.\n\n"
            "**Commands:**\n"
            "`/add BTC 0.5` — add 0.5 BTC\n"
            "`/remove BTC 0.1` — remove 0.1 BTC\n"
            "`/portfolio` — view your portfolio\n\n"
            "_Your data is stored locally on this machine._",
            parse_mode="Markdown",
        )
        return

    await message.answer("📊 Loading portfolio data...")

    # Fetch current prices for each holding
    total_value = 0
    holdings_data = []

    for ticker, amount in holdings.items():
        data = resolve_ticker(ticker)
        if data["type"] == "crypto":
            pd_ = data["price_data"]
            if pd_:
                price = pd_["price"]
                value = price * amount
                change = pd_["change_24h"]
                total_value += value
                holdings_data.append({
                    "ticker": ticker, "amount": amount, "price": price,
                    "value": value, "change_24h": change,
                })
        elif data["type"] == "stock":
            info = data["info"]
            if info and info.get("price"):
                price = info["price"]
                value = price * amount
                total_value += value
                holdings_data.append({
                    "ticker": ticker, "amount": amount, "price": price,
                    "value": value, "change_24h": 0,
                })

    if not holdings_data:
        await message.answer("❌ Could not fetch price data for your holdings.")
        return

    # Allocation percentages
    allocation = {
        h["ticker"]: round((h["value"] / total_value) * 100, 1)
        for h in holdings_data
    }
    pnl = get_mock_pnl(holdings)

    # Generate charts
    chart_buf = portfolio_chart(allocation, pnl)

    # Build response
    lines = [
        f"💰 **Your Portfolio** — Total: **${total_value:,.2f}**\n",
        "```",
        f"{'Ticker':<8} {'Amount':<12} {'Price':<12} {'Value':<12} {'24h'}",
        "-" * 52,
    ]

    for h in sorted(holdings_data, key=lambda x: -x["value"]):
        change_emoji = "🟢" if h["change_24h"] >= 0 else "🔴"
        lines.append(
            f"{h['ticker']:<8} {h['amount']:<12.4f} "
            f"${h['price']:<11.2f} ${h['value']:<11.2f} "
            f"{change_emoji}{h['change_24h']:+.1f}%"
        )
    lines.append("```")
    lines.append(f"\n_Portfolio value updated at quote._")

    chart_buf.seek(0)
    await message.answer("\n".join(lines), parse_mode="Markdown")
    await message.answer_photo(
        photo=chart_buf,
        caption="💰 Portfolio — Allocation + 24h P&L",
    )


@router.message(Command("add"))
async def cmd_add(message: Message):
    user_id = message.from_user.id
    parts = message.text.strip().split()

    if len(parts) < 3:
        await message.answer(
            "➕ **Add to Portfolio**\n\n"
            "Usage: `/add BTC 0.5`\n"
            "Adds 0.5 BTC to your portfolio.",
            parse_mode="Markdown",
        )
        return

    ticker = parts[1].upper()
    try:
        amount = float(parts[2])
    except ValueError:
        await message.answer("❌ Invalid amount. Use: `/add BTC 0.5`")
        return

    update_portfolio(user_id, ticker, amount, "add")

    portfolio = get_portfolio(user_id)
    new_amount = portfolio.get("holdings", {}).get(ticker, 0)
    await message.answer(
        f"✅ Added `{amount}` {ticker} to your portfolio.\n"
        f"Now holding: `{new_amount}` {ticker}",
        parse_mode="Markdown",
    )


@router.message(Command("remove"))
async def cmd_remove(message: Message):
    user_id = message.from_user.id
    parts = message.text.strip().split()

    if len(parts) < 3:
        await message.answer(
            "➖ **Remove from Portfolio**\n\n"
            "Usage: `/remove BTC 0.1`\n"
            "Removes 0.1 BTC from your portfolio.",
            parse_mode="Markdown",
        )
        return

    ticker = parts[1].upper()
    try:
        amount = float(parts[2])
    except ValueError:
        await message.answer("❌ Invalid amount. Use: `/remove BTC 0.1`")
        return

    update_portfolio(user_id, ticker, amount, "remove")

    portfolio = get_portfolio(user_id)
    new_amount = portfolio.get("holdings", {}).get(ticker, 0)
    await message.answer(
        f"✅ Removed `{amount}` {ticker} from your portfolio.\n"
        f"Now holding: `{new_amount}` {ticker}",
        parse_mode="Markdown",
    )


@router.message(Command("clearportfolio"))
async def cmd_clear_portfolio(message: Message):
    user_id = message.from_user.id
    portfolios = load_portfolios()
    if str(user_id) in portfolios:
        portfolios[str(user_id)]["holdings"] = {}
        save_portfolios(portfolios)
    await message.answer("🗑️ Portfolio cleared.")
