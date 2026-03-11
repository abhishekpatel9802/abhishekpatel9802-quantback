from __future__ import annotations

import math
from typing import List


def max_drawdown(equity: List[float]) -> float:
    peak = equity[0]
    max_dd = 0.0
    for value in equity:
        peak = max(peak, value)
        if peak == 0:
            continue
        dd = (peak - value) / peak
        max_dd = max(max_dd, dd)
    return max_dd


def sharpe_ratio(returns: List[float], periods_per_year: int) -> float:
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return (mean / std) * math.sqrt(periods_per_year)


def profit_factor(trade_pnls: List[float]) -> float:
    gross_profit = sum(p for p in trade_pnls if p > 0)
    gross_loss = abs(sum(p for p in trade_pnls if p < 0))
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def expectancy(trade_pnls: List[float]) -> float:
    wins = [p for p in trade_pnls if p > 0]
    losses = [p for p in trade_pnls if p < 0]
    total = len(trade_pnls)
    if total == 0:
        return 0.0
    win_rate = len(wins) / total
    loss_rate = 1 - win_rate
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = abs(sum(losses) / len(losses)) if losses else 0.0
    return (avg_win * win_rate) - (avg_loss * loss_rate)


def kelly_criterion(trade_pnls: List[float]) -> float:
    wins = [p for p in trade_pnls if p > 0]
    losses = [p for p in trade_pnls if p < 0]
    total = len(trade_pnls)
    if total == 0 or not losses or not wins:
        return 0.0
    win_rate = len(wins) / total
    loss_rate = 1 - win_rate
    avg_win = sum(wins) / len(wins)
    avg_loss = abs(sum(losses) / len(losses))
    if avg_loss == 0:
        return 0.0
    payoff = avg_win / avg_loss
    return win_rate - (loss_rate / payoff)
