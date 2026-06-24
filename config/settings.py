"""
Config management — all API keys and settings live here.
Copy .env.example to .env and fill in your keys.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── Telegram ──────────────────────────────────────────────────────────────
    telegram_bot_token: str = ""

    # ── AI Layer (OpenRouter) ─────────────────────────────────────────────────
    # Get free credits: https://openrouter.ai/credits
    # Models: openai/gpt-4o, anthropic/claude-3.5-sonnet, google/gemini-2.0-flash
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    default_model: str = "openai/gpt-4o"

    # ── Market Data ───────────────────────────────────────────────────────────
    # CoinGecko (crypto) — no key needed for basic use
    coingecko_base_url: str = "https://api.coingecko.com/api/v3"

    # Polygon.io — free tier at polygon.io/getting-started
    polygon_api_key: str = ""

    # NewsAPI — free dev key at newsapi.org/register
    news_api_key: str = ""

    # ── Exchange APIs (optional — for real trading) ────────────────────────────
    binance_api_key: str = ""
    binance_api_secret: str = ""

    # ── App ───────────────────────────────────────────────────────────────────
    debug: bool = False
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()