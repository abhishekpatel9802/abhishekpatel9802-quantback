from __future__ import annotations

import os

BINANCE_BASE_URL = os.getenv("BINANCE_BASE_URL", "https://api.binance.com")
DEFAULT_SYMBOL = os.getenv("DEFAULT_SYMBOL", "BTCUSDT")
DEFAULT_TIMEFRAME = os.getenv("DEFAULT_TIMEFRAME", "1h")
MAX_CANDLES = int(os.getenv("MAX_CANDLES", "5000"))

DATABASE_URL = os.getenv("DATABASE_URL")

TIMEFRAME_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}

TRADING_DAYS = 365

TIMEFRAME_PERIODS_PER_YEAR = {
    "1m": TRADING_DAYS * 24 * 60,
    "5m": TRADING_DAYS * 24 * 60 // 5,
    "15m": TRADING_DAYS * 24 * 60 // 15,
    "1h": TRADING_DAYS * 24,
    "4h": TRADING_DAYS * 24 // 4,
    "1d": TRADING_DAYS,
}
