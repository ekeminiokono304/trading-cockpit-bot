"""
Predict handler — AI-powered price forecasting.
Shows line chart with confidence bands + structured JSON prediction.
"""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
import io
import json
import random

from modules.ai.agent import ai_predict, parse_json_response
from modules.market.fetcher import resolve_ticker
from modules.charts.generator import prediction_chart, build_indicators

router = Router()


def _simulate_prediction(price: float, horizon: str) -> tuple[float, float, float]:
    """Generate simulated prediction when no API key."""
    volatilities = {"1d": 0.02, "1w": 0.05, "1m": 0.12}
    vol = volatilities.get(horizon, 0.05)
    conf = {"1d": 65, "1w": 50, "1m": 35}.get(horizon, 40)

    drift = random.uniform(-vol, vol)
    pred = price * (1 + drift)
    band = price * vol * 0.8
    return round(pred, 4), round(band, 4), conf


@router.message(Command("predict"))
async def cmd_predict(message: Message):
    await message.answer(
        "📊 **Price Prediction**\n\n"
        "Get AI-powered price forecasts with confidence bands.\n\n"
        "_Example: `/predict btc 1w`_",
        parse_mode="Markdown",
    )


@router.message(F.text, F.chat.type == "private")
async def handle_predict(message: Message):
    user_text = message.text.strip()

    # Parse: /predict ASSET [horizon]
    parts = user_text.split()
    if len(parts) < 2:
        await message.answer(
            "📊 **Predict Usage:**\n"
            "`/predict BTC` — short-term prediction\n"
            "`/predict btc 1w` — 1-week horizon\n"
            "`/predict aapl 1m` — 1-month horizon\n\n"
            "_Available horizons: 1d, 1w, 1m_",
            parse_mode="Markdown",
        )
        return

    asset_raw = parts[1].upper()
    horizon = parts[2].lower() if len(parts) > 2 else "1w"

    data = resolve_ticker(asset_raw)

    if data["type"] == "crypto":
        pd_ = data["price_data"]
        if not pd_:
            await message.answer(f"❌ Could not fetch data for `{asset_raw}`", parse_mode="Markdown")
            return
        price = pd_["price"]
        candles = data["candles"]
    elif data["type"] == "stock":
        info = data["info"]
        if not info or not info.get("price"):
            await message.answer(f"❌ Could not fetch data for `{asset_raw}`", parse_mode="Markdown")
            return
        price = info["price"]
        candles = data["candles"]
    else:
        await message.answer("❌ Unknown asset type.")
        return

    await message.answer(f"🔮 Analyzing {asset_raw}... (may take a few seconds)")

    # Get AI prediction
    result = ai_predict(asset_raw, {"price": price}, candles)
    parsed = parse_json_response(result.get("raw", "")) if isinstance(result, dict) else None

    if parsed and "predictions" in parsed:
        preds = parsed["predictions"]
        reasons = parsed.get("reasoning", [])
        risks = parsed.get("risks", [])
    else:
        # Fallback: simulate
        preds = []
        for h in ["1d", "1w", "1m"]:
            p, band, conf = _simulate_prediction(price, h)
            preds.append({"horizon": h, "price": p, "confidence": conf})
        reasons = ["API key not configured — showing simulated values"]
        risks = ["Simulated prediction — not financial advice"]

    # Build chart
    horizons_map = {"1d": "1 Day", "1w": "1 Week", "1m": "1 Month"}
    pred_prices = []
    conf_upper = []
    conf_lower = []

    for p in preds:
        pred_prices.append(p["price"])
        band = p["price"] * 0.05
        conf_upper.append(p["price"] + band)
        conf_lower.append(p["price"] - band)

    chart_buf = prediction_chart(
        candles, asset_raw,
        pred_prices=pred_prices,
        confidence_upper=conf_upper,
        confidence_lower=conf_lower,
    )

    # Format response
    horizon_label = horizons_map.get(horizon, horizon)
    current_price_str = f"${price:,.2f}"

    lines = [f"📊 **{asset_raw} — Price Prediction**\n"]
    lines.append(f"💵 Current: **{current_price_str}**\n")
    lines.append("**Forecast:**\n")

    for p in preds:
        h = horizons_map.get(p["horizon"], p["horizon"])
        emoji = "🟢" if p["price"] >= price else "🔴"
        change = ((p["price"] - price) / price) * 100
        conf_bar = "█" * int(p["confidence"] / 10) + "░" * (10 - int(p["confidence"] / 10))
        lines.append(
            f"  {emoji} {h}: **${p['price']:,.2f}** "
            f"({change:+.1f}%) · [{conf_bar}] {p['confidence']}%"
        )

    if reasons:
        lines.append("\n**Key reasons:**")
        for r in reasons[:3]:
            lines.append(f"  • {r}")

    if risks:
        lines.append("\n⚠️ **Risks:**")
        for r in risks[:3]:
            lines.append(f"  • {r}")

    lines.append("\n_This is analysis, not financial advice._")

    chart_buf.seek(0)
    await message.answer("\n".join(lines), parse_mode="Markdown")
    await message.answer_photo(photo=chart_buf, caption=f"📈 {asset_raw} forecast chart")
