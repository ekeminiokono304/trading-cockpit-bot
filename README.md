# Trading Cockpit Bot

> A 6-panel AI-powered Telegram trading terminal. Chart generation, technical
> analysis, price predictions, sentiment analysis, portfolio tracking, and
> trading education — all in one bot.

---

## The 6 Panels

| Panel | Command | What it does |
|-------|---------|-------------|
| 💬 **Chat** | `/chat` | Freeform AI trading assistant |
| 📊 **Predict** | `/predict btc 1w` | AI price forecast + confidence bands |
| 📈 **Signals** | `/signals btc` | RSI, MACD, EMA crossovers + buy/sell markers |
| 📰 **Sentiment** | `/sentiment btc` | News impact, market mood, bull/bear factors |
| 💰 **Portfolio** | `/add btc 0.5` | Track holdings, allocation pie chart, P&L |
| 🎓 **Learn** | `/learn rsi` | Trading education — 9 built-in lessons |

---

## Setup

### 1. Create your Telegram bot

1. Open [BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot`
3. Follow the prompts — copy the **bot token**
4. You'll add this to `.env` below

### 2. Clone and install

```bash
git clone <your-repo>
cd trading-cockpit-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your tokens
```

**Minimum required in `.env`:**
```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...   # from BotFather
OPENROUTER_API_KEY=sk-or-v1-...         # free $1 credit at openrouter.ai
```

### 4. Run

```bash
source .venv/bin/activate
python -m bot.main
```

### 5. Message your bot

Open Telegram, find your bot, send `/start`.

---

## API Keys Reference

| Key | Required? | Where to get | Cost |
|-----|-----------|--------------|------|
| `TELEGRAM_BOT_TOKEN` | ✅ | [BotFather](https://t.me/BotFather) | Free |
| `OPENROUTER_API_KEY` | ✅ | [OpenRouter](https://openrouter.ai/credits) | $1 free, then pay-per-use |
| `NEWS_API_KEY` | ❌ | [NewsAPI](https://newsapi.org/register) | Free tier |
| `POLYGON_API_KEY` | ❌ | [Polygon.io](https://polygon.io) | Free tier |
| `BINANCE_API_KEY` | ❌ | Binance | Free |

---

## Commands Reference

### Chat
```
/chat
What do you think about BTC now?
```

### Predict
```
/predict btc       # short-term (1d)
/predict eth 1w    # 1 week horizon
/predict aapl 1m  # 1 month horizon
```

### Signals
```
/signals btc
/signals eth
/signals aapl
```

### Sentiment
```
/sentiment btc
/sentiment eth
```

### Portfolio
```
/add btc 0.5          # add 0.5 BTC
/add eth 2.0          # add 2.0 ETH
/add aapl 10          # add 10 shares of AAPL
/remove btc 0.1       # remove 0.1 BTC
/portfolio            # view chart
/clearportfolio       # wipe portfolio
```

### Learn
```
/learn                 # list all topics
/learn rsi             # RSI explained
/learn risk           # risk management
/learn bollinger      # Bollinger Bands
/learn strategies     # trading strategies
/learn What is MACD?  # ask anything
```

---

## Project Structure

```
trading-cockpit-bot/
├── bot/
│   └── main.py              # Bot entry point + keyboard UI
├── config/
│   └── settings.py          # All config (API keys, base URLs)
├── modules/
│   ├── ai/
│   │   └── agent.py         # OpenRouter LLM client + mode prompts
│   ├── charts/
│   │   └── generator.py     # Matplotlib chart generation
│   ├── handlers/
│   │   ├── chat_handler.py      # 💬 Freeform AI chat
│   │   ├── predict_handler.py   # 📊 Price predictions
│   │   ├── signals_handler.py   # 📈 Technical signals
│   │   ├── sentiment_handler.py # 📰 Sentiment analysis
│   │   ├── portfolio_handler.py # 💰 Portfolio tracker
│   │   └── learn_handler.py     # 🎓 Trading academy
│   └── market/
│       └── fetcher.py       # yfinance + CoinGecko data fetcher
├── data/                     # Portfolio data (auto-created)
├── tests/
│   └── test_market.py        # Basic data fetching tests
├── requirements.txt
├── .env.example
└── README.md
```

---

## Chart Types

- **Candlestick charts** — OHLCV with EMA overlays (20/50/200)
- **Prediction chart** — historical line + AI forecast + confidence band
- **Signals chart** — candlestick + MACD panel + RSI panel + buy/sell arrows
- **Sentiment bar chart** — bull/bear score per asset
- **Portfolio pie chart** — allocation % + P&L bar chart

All charts are generated with **pure matplotlib** — no Plotly account, no external service.

---

## Customising

### Change the LLM model

```env
DEFAULT_MODEL=anthropic/claude-3.5-sonnet
# or
DEFAULT_MODEL=google/gemini-2.0-flash
```

### Add a new trading pair

Edit `modules/market/fetcher.py` — the `resolve_ticker()` function handles
auto-detection. Add your symbol to `crypto_map` or use the search endpoint.

### Add a new built-in lesson

Edit `modules/handlers/learn_handler.py` — add to the `LESSONS` dict.

---

## Disclaimer

This bot provides **analysis and education only** — not financial advice.
All predictions, signals, and chart outputs are for informational purposes.
**Never trade more than you can afford to lose.**
