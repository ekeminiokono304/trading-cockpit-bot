"""
Learn handler — trading education, strategy explanations, risk management.
Covers: SMA, EMA, RSI, MACD, Bollinger Bands, risk management, position sizing.
"""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from modules.ai.agent import chat

router = Router()

# Built-in lessons (no API needed)
LESSONS = {
    "sma": {
        "title": "📈 Simple Moving Average (SMA)",
        "content": """The **SMA** averages closing prices over a set period.

**How it works:**
- SMA(20) = average of last 20 closing prices
- SMA(50), SMA(200) are common for trends

**Trading signals:**
• Price > SMA(20) → short-term bullish
• Price > SMA(50) → medium-term bullish
• SMA(20) crosses above SMA(50) → **Golden Cross** 🟢
• SMA(20) crosses below SMA(50) → **Death Cross** 🔴

**Formula:**
```
SMA = (P1 + P2 + ... + Pn) / n
```

**Limitation:** All prices weighted equally — reacts slowly.""",
    },
    "ema": {
        "title": "📈 Exponential Moving Average (EMA)",
        "content": """The **EMA** gives more weight to recent prices — reacts faster than SMA.

**How it works:**
- EMA(12), EMA(26) are most common for short-term
- EMA(50), EMA(200) for long-term trends

**Trading signals:**
• Price > EMA(20) → short-term bullish
• EMA(12) > EMA(26) → short-term momentum bullish
• EMA crosses above/below price → trend change

**Formula:**
```
EMA = Price × k + EMA_prev × (1 - k)
k = 2 / (period + 1)
```

**Best for:** Short-term traders, breakout strategies.""",
    },
    "rsi": {
        "title": "📊 Relative Strength Index (RSI)",
        "content": """The **RSI** measures momentum on a 0–100 scale.

**Readings:**
• RSI > 70 → **Overbought** — potential pullback 🔴
• RSI < 30 → **Oversold** — potential bounce 🟢
• RSI = 50 → Neutral

**How to use RSI:**
1. **Divergence:** Price makes new high but RSI doesn't → bearish reversal
2. **Swing rejections:** RSI bounces from 30/70 → confirmation
3. **Trend ID:** In an uptrend, buy when RSI pulls back to 40

**Formula:**
```
RS = Average Gain / Average Loss
RSI = 100 - (100 / (1 + RS))
```
Default period: **14**""",
    },
    "macd": {
        "title": "📊 MACD (Moving Average Convergence Divergence)",
        "content": """The **MACD** shows relationship between two EMAs.

**Components:**
- **MACD Line** = EMA(12) - EMA(26)
- **Signal Line** = EMA(9) of MACD Line
- **Histogram** = MACD Line - Signal Line

**Signals:**
• MACD crosses above Signal → 🟢 **Bullish**
• MACD crosses below Signal → 🔴 **Bearish**
• Histogram shrinking → momentum weakening
• MACD divergence from price → reversal warning

**Best use:** Confirming trend direction, not timing entries alone.""",
    },
    "bollinger": {
        "title": "📉 Bollinger Bands",
        "content": """**Bollinger Bands** show volatility around a price.

**Structure:**
- Middle Band = SMA(20)
- Upper Band = SMA + 2× standard deviation
- Lower Band = SMA - 2× standard deviation

**Trading with Bollinger Bands:**
• Price touches upper band + RSI overbought → **Sell signal**
• Price touches lower band + RSI oversold → **Buy signal**
• Bands narrow (squeeze) → big move incoming
• Bands widen → high volatility

**Width indicator:** BandWidth < 2% of price → squeeze breakout coming.""",
    },
    "risk": {
        "title": "🛡️ Risk Management Essentials",
        "content": """**Never risk more than 1–2% per trade.**

**Position sizing formula:**
```
Position Size = Account × Risk% / Stop Loss Distance%
```
Example: $10,000 account, 1% risk, 5% stop = $20,000 / 5% = **$400 position**

**The 2% Rule:**
```
Max Risk Per Trade = Account × 0.02
```
$10,000 account → $200 max loss per trade

**Risk:Reward ratio:**
• Always target minimum **1:2** (risk $1, make $2)
• Ideal: 1:3 or higher
• Never enter a trade without knowing your exit

**Common mistakes:**
❌ Risking 5–10% per trade (blow up your account fast)
❌ No stop loss
❌ Adding to losing positions (doubling down)
✅ Always know your max loss before entering""",
    },
    "position": {
        "title": "📐 Position Sizing",
        "content": """**Position sizing** is the most important skill in trading.

** Kelly Criterion (simplified):**
```
f = (bp - q) / b
f = fraction of bankroll to bet
b = odds received
p = win probability
q = loss probability
```
Most traders use **Kelly fractions** (25–50%) to be conservative.

**Steps to size a position:**
1. Know your account size
2. Set max risk % (use 1–2%)
3. Calculate max $ loss per trade
4. Place stop loss at technical level
5. Calculate position size from stop distance

**Example ($5,000 account, 2% risk, BTC at $60k, stop at $57k):**
```
Max loss = $5,000 × 0.02 = $100
Stop distance = ($60k - $57k) / $60k = 5%
Position = $100 / 5% = $2,000 = 0.033 BTC
```""",
    },
    "sentiment2": {
        "title": "🧠 Sentiment Analysis Basics",
        "content": """**Market sentiment** = collective mood of all traders.

**Sentiment indicators:**
- **Fear & Greed Index** (Alternative.me) — 0-100
- **BTC Dominance** rising → money flowing to Bitcoin
- **Funding rates** (交易所 funding > 0.1% → extremely greedy, top signal)
- **Open interest** — rising = new money entering

**Contrarian signals:**
🟢 **Extreme Fear** (F&G < 20) → Buy opportunity
🟢 **Funding deeply negative** → capitulation, potential bounce
🔴 **Extreme Greed** (F&G > 80) → Top signal, take profit
🔴 **Funding extremely positive** → top is near

**On-chain basics:**
- Exchange outflows → "hodling" (bullish)
- Exchange inflows → selling pressure""",
    },
    "strategies": {
        "title": "🎯 Common Trading Strategies",
        "content": """**1. Trend Following (EMA crossover)**
- Entry: EMA(20) crosses above EMA(50)
- Exit: EMA(20) crosses below EMA(50)
- Best for: Strong trends

**2. Mean Reversion (Bollinger + RSI)**
- Entry: Price hits lower band + RSI < 30
- Exit: Price returns to middle band
- Best for: Ranging markets

**3. Breakout Trading**
- Entry: Price closes above resistance + volume spike
- Stop: Below breakout level
- Best for: Volatile markets

**4. Dollar-Cost Averaging (DCA)**
- Buy fixed $ amount at regular intervals
- Ignores price — removes emotion
- Best for: Long-term investors

**5. Swing Trading**
- Hold positions 2–14 days
- Capture medium-term moves
- Use 4h–daily charts""",
    },
}


@router.message(Command("learn"))
async def cmd_learn(message: Message):
    topics = ", ".join(f"`{k}`" for k in LESSONS.keys())
    await message.answer(
        "🎓 **Trading Academy**\n\n"
        "Learn core trading concepts.\n\n"
        f"**Topics:** {topics}\n\n"
        "_Usage: `/learn rsi`_",
        parse_mode="Markdown",
    )


@router.message(F.text, F.chat.type == "private")
async def handle_learn(message: Message):
    user_text = message.text.strip().lower()

    # Parse /learn command or just keyword
    parts = user_text.split()
    topic = parts[1].lower() if len(parts) > 1 else None

    if not topic:
        topics = "\n".join(f"  `/learn {k}`" for k in LESSONS.keys())
        await message.answer(
            "🎓 **Trading Academy**\n\n"
            f"{topics}\n\n"
            "Or ask: `/learn What is RSI?`",
            parse_mode="Markdown",
        )
        return

    # Check built-in lessons
    for key, lesson in LESSONS.items():
        if key == topic or topic in lesson["title"].lower():
            await message.answer(
                f"{lesson['title']}\n\n{lesson['content']}",
                parse_mode="Markdown",
            )
            return

    # Not found — use AI to explain
    await message.answer(f"🤔 Let me explain '{topic}'...")
    response = chat(
        f"Explain '{topic}' to a beginner trader. "
        "Include: what it is, how to use it, formula if applicable, trading signal. "
        "Keep it practical and concise.",
        mode="learn",
    )
    await message.answer(response, parse_mode="Markdown")
