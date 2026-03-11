from __future__ import annotations

from typing import List, Optional


def compute_rsi(closes: List[float], period: int = 14) -> List[Optional[float]]:
    """Compute RSI from scratch using Wilder's smoothing.

    Returns a list aligned with closes. Values before period are None.
    """
    if period <= 0:
        raise ValueError("period must be positive")
    if len(closes) < period + 1:
        return [None for _ in closes]

    gains = [0.0]
    losses = [0.0]
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(abs(min(delta, 0.0)))

    # First average gain/loss
    avg_gain = sum(gains[1 : period + 1]) / period
    avg_loss = sum(losses[1 : period + 1]) / period

    rsi: List[Optional[float]] = [None] * len(closes)

    def rs_to_rsi(rs_value: float) -> float:
        return 100 - (100 / (1 + rs_value))

    if avg_loss == 0:
        rsi[period] = 100.0
    else:
        rsi[period] = rs_to_rsi(avg_gain / avg_loss)

    for i in range(period + 1, len(closes)):
        gain = gains[i]
        loss = losses[i]
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

        if avg_loss == 0:
            rsi[i] = 100.0
        else:
            rsi[i] = rs_to_rsi(avg_gain / avg_loss)

    return rsi
