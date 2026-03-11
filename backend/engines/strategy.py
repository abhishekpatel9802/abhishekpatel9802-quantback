from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .rsi import compute_rsi
from ..models import StrategyConfig


@dataclass
class Signal:
    index: int
    action: str  # "buy" or "sell"


def _slope_ok(rsi: List[Optional[float]], idx: int, lookback: int, minimum: Optional[float], maximum: Optional[float], side: str) -> bool:
    if lookback <= 0 or idx - lookback < 0:
        return True
    if rsi[idx] is None or rsi[idx - lookback] is None:
        return True
    slope = rsi[idx] - rsi[idx - lookback]
    if side == "buy" and minimum is not None:
        return slope >= minimum
    if side == "sell" and maximum is not None:
        return slope <= maximum
    return True


def _divergence_ok(closes: List[float], rsi: List[Optional[float]], idx: int, lookback: int, side: str) -> bool:
    if lookback <= 4 or idx < lookback:
        return True
    half = lookback // 2
    old_slice = range(idx - lookback, idx - half)
    new_slice = range(idx - half, idx + 1)

    def _min_pair(indices):
        lows = [(closes[i], rsi[i]) for i in indices if rsi[i] is not None]
        if not lows:
            return None
        return min(lows, key=lambda x: x[0])

    def _max_pair(indices):
        highs = [(closes[i], rsi[i]) for i in indices if rsi[i] is not None]
        if not highs:
            return None
        return max(highs, key=lambda x: x[0])

    if side == "buy":
        old_low = _min_pair(old_slice)
        new_low = _min_pair(new_slice)
        if old_low is None or new_low is None:
            return True
        price_lower = new_low[0] < old_low[0]
        rsi_higher = new_low[1] > old_low[1]
        return price_lower and rsi_higher

    old_high = _max_pair(old_slice)
    new_high = _max_pair(new_slice)
    if old_high is None or new_high is None:
        return True
    price_higher = new_high[0] > old_high[0]
    rsi_lower = new_high[1] < old_high[1]
    return price_higher and rsi_lower


def generate_signals(closes: List[float], config: StrategyConfig) -> tuple[List[Optional[float]], List[Signal]]:
    rsi = compute_rsi(closes, config.rsi_period)
    signals: List[Signal] = []

    for i in range(1, len(closes)):
        if rsi[i] is None or rsi[i - 1] is None:
            continue

        if config.mode == "crossing":
            buy_cond = rsi[i - 1] < config.lower and rsi[i] >= config.lower
            sell_cond = rsi[i - 1] > config.upper and rsi[i] <= config.upper
        else:
            buy_cond = rsi[i] < config.lower
            sell_cond = rsi[i] > config.upper

        if buy_cond:
            if _slope_ok(rsi, i, config.slope_lookback, config.slope_min, None, "buy"):
                if not config.use_divergence or _divergence_ok(closes, rsi, i, config.divergence_lookback, "buy"):
                    signals.append(Signal(index=i, action="buy"))

        if sell_cond:
            if _slope_ok(rsi, i, config.slope_lookback, None, config.slope_max, "sell"):
                if not config.use_divergence or _divergence_ok(closes, rsi, i, config.divergence_lookback, "sell"):
                    signals.append(Signal(index=i, action="sell"))

    return rsi, signals
