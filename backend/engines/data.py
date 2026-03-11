from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from typing import List, Optional

import httpx

from ..config import BINANCE_BASE_URL, DATABASE_URL, MAX_CANDLES, TIMEFRAME_MAP
from ..models import Candle, Trade

try:
    import psycopg
except Exception:  # pragma: no cover - optional dependency
    psycopg = None


def _dt_to_ms(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _parse_kline(item) -> Candle:
    return Candle(
        timestamp=int(item[0]),
        open=float(item[1]),
        high=float(item[2]),
        low=float(item[3]),
        close=float(item[4]),
        volume=float(item[5]),
    )


class Database:
    def __init__(self, url: Optional[str]):
        self.url = url
        self.enabled = bool(url) and psycopg is not None

    def _connect(self):
        if not self.enabled:
            return None
        return psycopg.connect(self.url, autocommit=True)

    def load_candles(self, symbol: str, interval: str, start_ms: int, end_ms: int) -> List[Candle]:
        if not self.enabled:
            return []
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT ts, open, high, low, close, volume
                    FROM crypto_candles
                    WHERE symbol = %s AND interval = %s AND ts BETWEEN %s AND %s
                    ORDER BY ts ASC
                    """,
                    (symbol, interval, start_ms, end_ms),
                )
                rows = cur.fetchall()
        return [Candle(timestamp=row[0], open=row[1], high=row[2], low=row[3], close=row[4], volume=row[5]) for row in rows]

    def store_candles(self, symbol: str, interval: str, candles: List[Candle]) -> None:
        if not self.enabled or not candles:
            return
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO crypto_candles (ts, symbol, interval, open, high, low, close, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (ts, symbol, interval) DO UPDATE
                    SET open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume
                    """,
                    [
                        (
                            c.timestamp,
                            symbol,
                            interval,
                            c.open,
                            c.high,
                            c.low,
                            c.close,
                            c.volume,
                        )
                        for c in candles
                    ],
                )

    def store_backtest(self, symbol: str, interval: str, params: dict, metrics: dict) -> Optional[str]:
        if not self.enabled:
            return None
        cleaned_metrics = {}
        for key, value in metrics.items():
            if isinstance(value, float) and (math.isinf(value) or math.isnan(value)):
                cleaned_metrics[key] = None
            else:
                cleaned_metrics[key] = value
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO backtests (symbol, interval, params, metrics)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (symbol, interval, json.dumps(params), json.dumps(cleaned_metrics)),
                )
                row = cur.fetchone()
                return str(row[0]) if row else None

    def store_trades(self, backtest_id: str, trades: List[Trade]) -> None:
        if not self.enabled or not trades:
            return
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO trades (backtest_id, side, entry_time, exit_time, entry_price, exit_price, qty, pnl)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            backtest_id,
                            t.side,
                            t.entry_time,
                            t.exit_time,
                            t.entry_price,
                            t.exit_price,
                            t.qty,
                            t.pnl,
                        )
                        for t in trades
                    ],
                )


class DataEngine:
    def __init__(self, base_url: str = BINANCE_BASE_URL, database_url: Optional[str] = DATABASE_URL):
        self.base_url = base_url
        self.db = Database(database_url)

    def fetch_from_binance(
        self,
        symbol: str,
        interval: str,
        start_ms: Optional[int],
        end_ms: Optional[int],
        limit: int,
    ) -> List[Candle]:
        params = {"symbol": symbol, "interval": interval, "limit": min(limit, 1000)}
        if start_ms is not None:
            params["startTime"] = start_ms
        if end_ms is not None:
            params["endTime"] = end_ms

        response = httpx.get(f"{self.base_url}/api/v3/klines", params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return [_parse_kline(item) for item in data]

    def get_candles(
        self,
        symbol: str,
        timeframe: str,
        start: Optional[datetime],
        end: Optional[datetime],
        max_candles: int = MAX_CANDLES,
    ) -> List[Candle]:
        interval = TIMEFRAME_MAP[timeframe]
        start_ms = _dt_to_ms(start) if start else None
        end_ms = _dt_to_ms(end) if end else None

        candles: List[Candle] = []
        if start_ms is not None and end_ms is not None:
            cached = self.db.load_candles(symbol, interval, start_ms, end_ms)
            if cached:
                candles = cached

        if not candles:
            if start_ms is None and end_ms is None:
                candles = self.fetch_from_binance(symbol, interval, None, None, max_candles)
                self.db.store_candles(symbol, interval, candles)
                return candles

            remaining = max_candles
            cursor = start_ms
            while remaining > 0:
                batch = self.fetch_from_binance(symbol, interval, cursor, end_ms, remaining)
                if not batch:
                    break
                candles.extend(batch)
                remaining -= len(batch)
                cursor = batch[-1].timestamp + 1
                if end_ms is not None and cursor >= end_ms:
                    break

            self.db.store_candles(symbol, interval, candles)

        return candles
