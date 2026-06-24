"""
Chart generation — candlesticks, technical indicators, price lines,
sentiment bars, portfolio pie charts. Pure Python + matplotlib.
No Plotly account needed.
"""

import io
import math
import re
from typing import Optional
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec


def _strip_emoji(text: str) -> str:
    """Remove emoji codepoints so they don't break matplotlib rendering."""
    return re.sub(r"[\U00010000-\U0010ffff]", "", text)

# Colours
CLR_BULL = "#26A69A"   # green
CLR_BEAR = "#EF5350"  # red
CLR_NEUT = "#78909C"  # grey
CLR_ACCENT = "#42A5F5"  # blue
CLR_BG = "#0D1117"
CLR_GRID = "#21262D"
CLR_TEXT = "#E6EDF3"
CLR_PANEL = "#161B22"


def _style_axis(ax, figsize=(10, 5)):
    """Dark-theme styling for a single axis."""
    ax.set_facecolor(CLR_PANEL)
    ax.tick_params(colors=CLR_TEXT, labelsize=7)
    ax.xaxis.label.set_color(CLR_TEXT)
    ax.yaxis.label.set_color(CLR_TEXT)
    for spine in ax.spines.values():
        spine.set_edgecolor(CLR_GRID)
    ax.grid(color=CLR_GRID, linewidth=0.5, alpha=0.7)


def _make_buffer() -> io.BytesIO:
    return io.BytesIO()


def _save(fig, buf: io.BytesIO, dpi: int = 100):
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig)


# ── Candlestick chart ─────────────────────────────────────────────────────────

def candlestick_chart(df: pd.DataFrame, symbol: str = "",
                      indicators: Optional[dict] = None,
                      title: Optional[str] = None) -> io.BytesIO:
    """
    Render OHLC candlestick chart with optional overlay indicators.
    indicators = {"ema_20": [...], "ema_50": [...], "rsi": [...], "macd": [...]}
    Returns PNG as BytesIO.
    """
    if df is None or len(df) < 5:
        buf = _make_buffer()
        fig, ax = plt.subplots(figsize=(10, 5), facecolor=CLR_BG)
        ax.set_facecolor(CLR_BG)
        ax.text(0.5, 0.5, "No data available", ha="center", va="center",
                color=CLR_TEXT, fontsize=14, transform=ax.transAxes)
        ax.axis("off")
        _save(fig, buf)
        return buf

    fig = plt.figure(figsize=(12, 7), facecolor=CLR_BG)
    gs = GridSpec(2, 1, height_ratios=[3, 1], hspace=0.05, figure=fig)

    ax_price = fig.add_subplot(gs[0])
    ax_rsi = fig.add_subplot(gs[1])

    n = min(len(df), 90)  # cap at 90 candles for readability
    df_s = df.iloc[-n:].reset_index(drop=True)

    # Candlesticks
    o = df_s["open"].values
    h = df_s["high"].values
    l = df_s["low"].values
    c = df_s["close"].values
    x = np.arange(n)

    # Colour
    colors = [CLR_BULL if c[i] >= o[i] else CLR_BEAR for i in range(n)]

    # Wick
    for i in range(n):
        ax_price.plot([x[i], x[i]], [l[i], h[i]], color=colors[i], linewidth=0.8)

    # Body
    width = 0.6
    ax_price.bar(x, np.abs(c - o), bottom=np.minimum(o, c),
                 color=colors, width=width, linewidth=0)

    _style_axis(ax_price)
    ax_price.set_ylabel("Price (USD)", fontsize=8)

    # EMA overlays
    if indicators:
        if "ema_20" in indicators and len(indicators["ema_20"]) == n:
            ax_price.plot(x, indicators["ema_20"], color=CLR_ACCENT,
                          linewidth=1.2, label="EMA 20", alpha=0.9)
        if "ema_50" in indicators and len(indicators["ema_50"]) == n:
            ax_price.plot(x, indicators["ema_50"], color="#FFA726",
                          linewidth=1.2, label="EMA 50", alpha=0.9)
        if "ema_200" in indicators and len(indicators["ema_200"]) == n:
            ax_price.plot(x, indicators["ema_200"], color="#AB47BC",
                          linewidth=1.2, label="EMA 200", alpha=0.9)
        ax_price.legend(fontsize=7, loc="upper left", framealpha=0.3, labelcolor=CLR_TEXT)

    # RSI panel
    if indicators and "rsi" in indicators and len(indicators["rsi"]) == n:
        rsi_vals = indicators["rsi"]
        ax_rsi.plot(x, rsi_vals, color="#FFA726", linewidth=1)
        ax_rsi.axhline(70, color=CLR_BEAR, linewidth=0.8, linestyle="--", alpha=0.6)
        ax_rsi.axhline(30, color=CLR_BULL, linewidth=0.8, linestyle="--", alpha=0.6)
        ax_rsi.fill_between(x, rsi_vals, 70, where=(rsi_vals >= 70),
                            color=CLR_BEAR, alpha=0.15)
        ax_rsi.fill_between(x, rsi_vals, 30, where=(rsi_vals <= 30),
                            color=CLR_BULL, alpha=0.15)
        ax_rsi.set_ylabel("RSI", fontsize=8)
        ax_rsi.set_ylim(0, 100)
        _style_axis(ax_rsi)
    else:
        ax_rsi.axis("off")

    # X tick labels (dates)
    step = max(1, n // 8)
    ax_price.set_xticks(x[::step])
    ax_rsi.set_xticks(x[::step])
    if "timestamp" in df_s.columns or "Date" in df_s.columns:
        date_col = "timestamp" if "timestamp" in df_s.columns else "Date"
        labels = df_s[date_col].iloc[::step].astype(str).str[:10]
        ax_price.set_xticklabels(labels, fontsize=6, rotation=30, ha="right")
        ax_rsi.set_xticklabels(labels, fontsize=6, rotation=30, ha="right")
    else:
        ax_rsi.set_xticklabels([])

    for ax_ in [ax_price, ax_rsi]:
        ax_.tick_params(colors=CLR_TEXT)

    label = title or f"{symbol} — Candlestick Chart"
    fig.suptitle(label, color=CLR_TEXT, fontsize=11, y=0.98)

    buf = _make_buffer()
    _save(fig, buf, dpi=110)
    return buf


# ── Price prediction chart ─────────────────────────────────────────────────────

def prediction_chart(df: pd.DataFrame, symbol: str,
                     pred_prices: list,
                     confidence_upper: list,
                     confidence_lower: list) -> io.BytesIO:
    """Line chart with historical price + AI forecast + confidence band."""
    if df is None or len(df) < 5:
        buf = _make_buffer()
        fig, ax = plt.subplots(figsize=(10, 5), facecolor=CLR_BG)
        ax.axis("off")
        _save(fig, buf)
        return buf

    n_hist = min(len(df), 60)
    df_s = df.iloc[-n_hist:].reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(11, 5), facecolor=CLR_BG)
    ax.set_facecolor(CLR_PANEL)

    hist_x = np.arange(n_hist)
    hist_close = df_s["close"].values

    # Historical line
    ax.plot(hist_x, hist_close, color=CLR_ACCENT, linewidth=1.8,
            label="Historical", marker=".", markersize=2)

    # Confidence band
    n_total = n_hist + len(pred_prices)
    pred_x = np.arange(n_hist - 1, n_total)
    ax.fill_between(pred_x, confidence_lower, confidence_upper,
                    color=CLR_ACCENT, alpha=0.15, label="Confidence Band")

    # Prediction line
    ax.plot(pred_x, pred_prices, color="#FFA726", linewidth=2,
            label="AI Prediction", marker="o", markersize=3)

    ax.set_ylabel("Price (USD)", fontsize=9, color=CLR_TEXT)
    ax.legend(fontsize=8, framealpha=0.3, labelcolor=CLR_TEXT)
    _style_axis(ax)

    step = max(1, n_hist // 6)
    date_col = "timestamp" if "timestamp" in df_s.columns else "Date"
    labels = df_s[date_col].iloc[::step].astype(str).str[:10]
    ax.set_xticks(hist_x[::step])
    ax.set_xticklabels(labels, fontsize=6, rotation=30, ha="right")

    ax.set_title(_strip_emoji(f"{symbol} — Price Prediction with Confidence"), color=CLR_TEXT, fontsize=11)
    fig.tight_layout()

    buf = _make_buffer()
    _save(fig, buf)
    return buf


# ── Technical signals chart ────────────────────────────────────────────────────

def signals_chart(df: pd.DataFrame, symbol: str,
                  buy_signals: list, sell_signals: list) -> io.BytesIO:
    """Chart with RSI, MACD, and buy/sell markers."""
    if df is None or len(df) < 20:
        buf = _make_buffer()
        fig, ax = plt.subplots(figsize=(10, 5), facecolor=CLR_BG)
        ax.axis("off")
        _save(fig, buf)
        return buf

    n = min(len(df), 90)
    df_s = df.iloc[-n:].reset_index(drop=True)

    fig = plt.figure(figsize=(12, 8), facecolor=CLR_BG)
    gs = GridSpec(3, 1, height_ratios=[2, 1, 1], hspace=0.05, figure=fig)

    ax_price = fig.add_subplot(gs[0])
    ax_macd = fig.add_subplot(gs[1])
    ax_rsi = fig.add_subplot(gs[2])

    closes = df_s["close"].values
    x = np.arange(n)

    # EMA 20 & 50
    ema_20 = _ema(closes, 20)
    ema_50 = _ema(closes, 50)
    ax_price.plot(x, ema_20, color=CLR_ACCENT, linewidth=1.2, label="EMA 20", alpha=0.9)
    ax_price.plot(x, ema_50, color="#FFA726", linewidth=1.2, label="EMA 50", alpha=0.9)
    ax_price.plot(x, closes, color=CLR_TEXT, linewidth=0.8, alpha=0.5, label="Close")

    # Buy / Sell markers
    for (xi, yi) in buy_signals:
        ax_price.annotate("▲", (xi, yi), color=CLR_BULL, fontsize=12, ha="center")
    for (xi, yi) in sell_signals:
        ax_price.annotate("▼", (xi, yi), color=CLR_BEAR, fontsize=12, ha="center")

    ax_price.legend(fontsize=7, framealpha=0.3, labelcolor=CLR_TEXT)
    ax_price.set_ylabel("Price", fontsize=8)
    _style_axis(ax_price)

    # MACD
    macd_line, signal_line, hist = _macd(closes)
    colors_hist = [CLR_BULL if h >= 0 else CLR_BEAR for h in hist]
    ax_macd.bar(x, hist, color=colors_hist, width=0.6, alpha=0.7)
    ax_macd.plot(x, macd_line, color=CLR_ACCENT, linewidth=1)
    ax_macd.plot(x, signal_line, color="#FFA726", linewidth=1)
    ax_macd.axhline(0, color=CLR_GRID, linewidth=0.5)
    ax_macd.set_ylabel("MACD", fontsize=8)
    _style_axis(ax_macd)

    # RSI
    rsi_vals = _rsi(closes)
    ax_rsi.plot(x, rsi_vals, color="#FFA726", linewidth=1)
    ax_rsi.axhline(70, color=CLR_BEAR, linewidth=0.8, linestyle="--", alpha=0.5)
    ax_rsi.axhline(30, color=CLR_BULL, linewidth=0.8, linestyle="--", alpha=0.5)
    ax_rsi.fill_between(x, rsi_vals, 70, where=(rsi_vals >= 70), color=CLR_BEAR, alpha=0.15)
    ax_rsi.fill_between(x, rsi_vals, 30, where=(rsi_vals <= 30), color=CLR_BULL, alpha=0.15)
    ax_rsi.set_ylabel("RSI", fontsize=8)
    ax_rsi.set_ylim(0, 100)
    _style_axis(ax_rsi)

    # X labels
    step = max(1, n // 8)
    date_col = "timestamp" if "timestamp" in df_s.columns else "Date"
    labels = df_s[date_col].iloc[::step].astype(str).str[:10]
    ax_rsi.set_xticks(x[::step])
    ax_rsi.set_xticklabels(labels, fontsize=6, rotation=30, ha="right")
    ax_price.set_xticks(x[::step])
    ax_price.set_xticklabels(labels, fontsize=6, rotation=30, ha="right")

    fig.suptitle(_strip_emoji(f"{symbol} — Technical Signals"), color=CLR_TEXT, fontsize=11)
    buf = _make_buffer()
    _save(fig, buf)
    return buf


# ── Sentiment bar chart ─────────────────────────────────────────────────────────

def sentiment_chart(sentiments: dict) -> io.BytesIO:
    """
    Bar chart of sentiment scores per asset or news source.
    sentiments = {"Bitcoin": 0.72, "Ethereum": -0.15, "Solana": 0.45}
    Score range: -1 (bearish) to +1 (bullish)
    """
    if not sentiments:
        buf = _make_buffer()
        fig, ax = plt.subplots(figsize=(8, 4), facecolor=CLR_BG)
        ax.axis("off")
        _save(fig, buf)
        return buf

    labels = list(sentiments.keys())
    scores = list(sentiments.values())
    n = len(labels)
    x = np.arange(n)

    fig, ax = plt.subplots(figsize=(max(7, n * 1.8), 4), facecolor=CLR_BG)
    ax.set_facecolor(CLR_PANEL)

    colors = [
        CLR_BULL if s >= 0 else CLR_BEAR
        for s in scores
    ]
    bars = ax.bar(x, scores, color=colors, width=0.5, alpha=0.85)

    ax.axhline(0, color=CLR_TEXT, linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, color=CLR_TEXT, fontsize=10, rotation=15, ha="right")
    ax.set_ylabel("Sentiment Score", fontsize=9, color=CLR_TEXT)
    ax.set_ylim(-1.1, 1.1)
    ax.set_yticks(np.linspace(-1, 1, 9))
    ax.yaxis.set_tick_params(labelcolor=CLR_TEXT, labelsize=8)

    for spine in ax.spines.values():
        spine.set_edgecolor(CLR_GRID)

    ax.grid(axis="y", color=CLR_GRID, linewidth=0.5, alpha=0.5)

    # Score labels on bars
    for bar, score in zip(bars, scores):
        ypos = score + 0.05 if score >= 0 else score - 0.1
        ax.text(bar.get_x() + bar.get_width() / 2, ypos,
                f"{score:.2f}", ha="center", va="bottom",
                color=CLR_TEXT, fontsize=8)

    ax.set_title(_strip_emoji("Market Sentiment Analysis"), color=CLR_TEXT, fontsize=12)
    fig.tight_layout()

    buf = _make_buffer()
    _save(fig, buf)
    return buf


# ── Portfolio allocation chart ──────────────────────────────────────────────────

def portfolio_chart(allocation: dict, pnl: Optional[dict] = None) -> io.BytesIO:
    """
    Pie chart of portfolio allocation with optional P&L overlay.
    allocation = {"BTC": 40, "ETH": 30, "USDT": 20, "SOL": 10}  # percentages
    pnl = {"BTC": 2.5, "ETH": -1.2, ...}  # percentage change
    """
    if not allocation:
        buf = _make_buffer()
        fig, ax = plt.subplots(figsize=(8, 6), facecolor=CLR_BG)
        ax.axis("off")
        _save(fig, buf)
        return buf

    labels = list(allocation.keys())
    sizes = list(allocation.values())

    palette = [
        "#26A69A", "#42A5F5", "#FFA726", "#AB47BC",
        "#EF5350", "#78909C", "#66BB6A", "#FFEE58"
    ]

    fig, (ax_pie, ax_pnl) = plt.subplots(1, 2, figsize=(12, 5),
                                          facecolor=CLR_BG,
                                          gridspec_kw={"width_ratios": [1, 1.2]})

    # Pie
    wedges, texts, autotexts = ax_pie.pie(
        sizes, labels=labels, autopct="%1.0f%%",
        colors=palette[:len(labels)],
        textprops={"color": CLR_TEXT, "fontsize": 9},
        startangle=140,
    )
    for at in autotexts:
        at.set_color(CLR_BG)
        at.set_fontsize(8)
        at.set_fontweight("bold")
    ax_pie.set_title("Allocation", color=CLR_TEXT, fontsize=10)

    # P&L bar chart
    if pnl:
        pnl_labels = list(pnl.keys())
        pnl_vals = list(pnl.values())
        pnl_colors = [CLR_BULL if v >= 0 else CLR_BEAR for v in pnl_vals]
        y_pos = np.arange(len(pnl_labels))
        bars = ax_pnl.barh(y_pos, pnl_vals, color=pnl_colors, height=0.5)
        ax_pnl.set_yticks(y_pos)
        ax_pnl.set_yticklabels(pnl_labels, color=CLR_TEXT, fontsize=9)
        ax_pnl.axvline(0, color=CLR_TEXT, linewidth=0.8)
        ax_pnl.set_xlabel("24h Change %", color=CLR_TEXT, fontsize=9)
        ax_pnl.xaxis.label.set_color(CLR_TEXT)
        ax_pnl.tick_params(colors=CLR_TEXT, labelsize=8)
        ax_pnl.set_xlim(
            min(-10, min(pnl_vals) - 2),
            max(10, max(pnl_vals) + 2)
        )
        for spine in ax_pnl.spines.values():
            spine.set_edgecolor(CLR_GRID)
        ax_pnl.grid(axis="x", color=CLR_GRID, linewidth=0.5, alpha=0.5)
        ax_pnl.set_title("24h P&L (%)", color=CLR_TEXT, fontsize=10)
    else:
        ax_pnl.axis("off")

    fig.suptitle(_strip_emoji("Portfolio Overview"), color=CLR_TEXT, fontsize=13)
    buf = _make_buffer()
    _save(fig, buf)
    return buf


# ── Inline indicator calculations ─────────────────────────────────────────────

def _ema(series: np.ndarray, period: int) -> np.ndarray:
    """Exponential moving average."""
    alpha = 2 / (period + 1)
    ema = np.zeros_like(series)
    ema[0] = series[0]
    for i in range(1, len(series)):
        ema[i] = alpha * series[i] + (1 - alpha) * ema[i - 1]
    return ema


def _rsi(closes: np.ndarray, period: int = 14) -> np.ndarray:
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.convolve(gains, np.ones(period) / period, mode="valid")
    avg_loss = np.convolve(losses, np.ones(period) / period, mode="valid")
    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return np.concatenate([np.full(period, 50), rsi])


def _macd(closes: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def detect_signals(df: pd.DataFrame) -> tuple[list, list]:
    """
    Simple EMA crossover + RSI signals.
    Returns (buy_signals, sell_signals) as lists of (x, y).
    """
    if df is None or len(df) < 60:
        return [], []

    closes = df["close"].values[-60:]
    ema20 = _ema(closes, 20)
    ema50 = _ema(closes, 50)
    rsi_vals = _rsi(closes)

    buy, sell = [], []
    for i in range(1, len(closes)):
        # EMA crossover
        if ema20[i] > ema50[i] and ema20[i - 1] <= ema50[i - 1]:
            if rsi_vals[i] < 70:
                buy.append((i, closes[i]))
        if ema20[i] < ema50[i] and ema20[i - 1] >= ema50[i - 1]:
            if rsi_vals[i] > 30:
                sell.append((i, closes[i]))

    return buy[-5:], sell[-5:]  # last 5 each


def build_indicators(df: pd.DataFrame) -> dict:
    """Build all standard indicators for chart overlays."""
    if df is None or len(df) < 50:
        return {}
    closes = df["close"].values
    n = len(closes)
    return {
        "ema_20": _ema(closes, 20) if n >= 20 else [],
        "ema_50": _ema(closes, 50) if n >= 50 else [],
        "ema_200": _ema(closes, 200) if n >= 200 else [],
        "rsi": _rsi(closes).tolist(),
    }
