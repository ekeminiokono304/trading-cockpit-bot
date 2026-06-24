"""
Market data fetcher — stocks (yfinance) and crypto (CoinGecko).
No API key needed for basic use.
"""

import yfinance as yf
import requests
import pandas as pd
from typing import Optional
from config.settings import get_settings

s = get_settings()


# ── Stocks ────────────────────────────────────────────────────────────────────

def get_stock_candles(symbol: str, period: str = "3mo", interval: str = "1d") -> Optional[pd.DataFrame]:
    """Fetch OHLCV candlestick data for a stock/ETF."""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            return None
        df.reset_index(inplace=True)
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
        return df
    except Exception:
        return None


def get_stock_info(symbol: str) -> Optional[dict]:
    """Fetch current price, market cap, volume, etc."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        price = ticker.fast_info.last_price
        return {
            "symbol": symbol.upper(),
            "price": price,
            "currency": info.get("currency", "USD"),
            "market_cap": info.get("market_cap", 0),
            "volume": info.get("last_volume", 0),
            "exchange": info.get("exchange", "UNKNOWN"),
        }
    except Exception:
        try:
            data = yf.download(symbol, period="1d", interval="1m", progress=False)
            if not data.empty:
                return {
                    "symbol": symbol.upper(),
                    "price": float(data['Close'].iloc[-1]),
                    "currency": "USD",
                    "market_cap": 0,
                    "volume": int(data['Volume'].iloc[-1]) if 'Volume' in data.columns else 0,
                    "exchange": "UNKNOWN",
                }
        except Exception:
            pass
        return None


# ── Crypto ────────────────────────────────────────────────────────────────────

def get_crypto_candles(coin_id: str = "bitcoin", days: int = 90) -> Optional[pd.DataFrame]:
    """Fetch OHLCV data for a crypto coin from CoinGecko."""
    url = f"{s.coingecko_base_url}/coins/{coin_id}/ohlc"
    params = {"vs_currency": "usd", "days": days}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df
    except Exception:
        return None


def get_crypto_price(coin_id: str = "bitcoin") -> Optional[dict]:
    """Fetch current price and 24h stats."""
    url = f"{s.coingecko_base_url}/simple/price"
    params = {
        "ids": coin_id,
        "vs_currencies": "usd",
        "include_24hr_change": "true",
        "include_market_cap": "true",
        "include_24hr_vol": "true",
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json().get(coin_id, {})
        return {
            "coin": coin_id,
            "price": data.get("usd", 0),
            "change_24h": data.get("usd_24h_change", 0),
            "market_cap": data.get("usd_market_cap", 0),
            "volume_24h": data.get("usd_24h_vol", 0),
        }
    except Exception:
        return None


def search_coin(query: str) -> Optional[list]:
    """Search for a coin by name or symbol."""
    url = f"{s.coingecko_base_url}/search"
    params = {"query": query}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        coins = resp.json().get("coins", [])[:5]
        return [{"id": c["id"], "symbol": c["symbol"], "name": c["name"]} for c in coins]
    except Exception:
        return None


# ── Auto-detect ────────────────────────────────────────────────────────────────

def resolve_ticker(query: str) -> dict:
    """
    Auto-detect asset type and return data.
    query like: 'BTC', 'bitcoin', 'AAPL', '$SPY'
    """
    q = query.strip().upper().lstrip("$")
    crypto_map = {
        "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
        "DOGE": "dogecoin", "ADA": "cardano", "XRP": "ripple",
        "DOT": "polkadot", "AVAX": "avalanche-2", "MATIC": "matic-network",
        "LINK": "chainlink", "UNI": "uniswap",
    }
    if q in crypto_map or query.lower() in ["bitcoin", "ethereum", "solana"]:
        coin_id = crypto_map.get(q, query.lower())
        price_data = get_crypto_price(coin_id)
        candles = get_crypto_candles(coin_id)
        return {"type": "crypto", "id": coin_id, "price_data": price_data, "candles": candles}

    candles = get_stock_candles(q)
    info = get_stock_info(q)
    return {"type": "stock", "symbol": q, "info": info, "candles": candles}
