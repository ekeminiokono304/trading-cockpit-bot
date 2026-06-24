"""
Basic tests — run with: python -m pytest tests/ -v
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.market.fetcher import (
    resolve_ticker, get_crypto_price, get_crypto_candles,
    get_stock_candles, get_stock_info,
)
from modules.charts.generator import (
    build_indicators, detect_signals,
    candlestick_chart, portfolio_chart, sentiment_chart,
)


def test_resolve_crypto():
    data = resolve_ticker("BTC")
    assert data["type"] == "crypto"
    assert data["id"] == "bitcoin"
    assert data["price_data"] is not None
    assert data["price_data"]["price"] > 0


def test_resolve_stock():
    data = resolve_ticker("AAPL")
    assert data["type"] == "stock"
    assert data["symbol"] == "AAPL"


def test_candles_not_empty():
    df = get_crypto_candles("bitcoin", days=30)
    assert df is not None
    assert len(df) > 0
    assert "close" in df.columns


def test_indicators():
    df = get_crypto_candles("ethereum", days=90)
    if df is not None and len(df) >= 50:
        ind = build_indicators(df)
        assert "ema_20" in ind
        assert len(ind["rsi"]) == len(df)


def test_signals():
    df = get_crypto_candles("bitcoin", days=60)
    if df is not None and len(df) >= 20:
        buy, sell = detect_signals(df)
        assert isinstance(buy, list)
        assert isinstance(sell, list)


def test_candlestick_chart():
    df = get_crypto_candles("bitcoin", days=30)
    if df is not None:
        buf = candlestick_chart(df, symbol="BTC")
        assert buf is not None
        buf.seek(0)
        data = buf.read(8)
        assert data.startswith(b"\x89PNG"), "Chart should be PNG"


def test_portfolio_chart():
    buf = portfolio_chart(
        allocation={"BTC": 40, "ETH": 35, "USDT": 25},
        pnl={"BTC": 2.5, "ETH": -1.2, "USDT": 0.0},
    )
    assert buf is not None
    buf.seek(0)
    assert buf.read(8).startswith(b"\x89PNG")


def test_sentiment_chart():
    buf = sentiment_chart({"Bitcoin": 0.72, "Ethereum": -0.15, "Solana": 0.45})
    assert buf is not None
    buf.seek(0)
    assert buf.read(8).startswith(b"\x89PNG")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
