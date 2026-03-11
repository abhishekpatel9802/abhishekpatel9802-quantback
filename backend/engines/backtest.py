from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .metrics import expectancy, kelly_criterion, max_drawdown, profit_factor, sharpe_ratio
from .strategy import Signal, generate_signals
from ..config import TIMEFRAME_PERIODS_PER_YEAR
from ..models import BacktestConfig, Candle, StrategyConfig, Trade


@dataclass
class Position:
    side: str  # "long" | "short"
    entry_price: float
    qty: float
    entry_time: int


def _apply_slippage(price: float, side: str, slippage_bps: float) -> float:
    slip = slippage_bps / 10_000
    if side == "buy":
        return price * (1 + slip)
    return price * (1 - slip)


def compute_metrics(equity: List[float], trades: List[Trade], timeframe: str, initial_capital: float) -> dict:
    final_equity = equity[-1] if equity else initial_capital
    total_return = (final_equity - initial_capital) / initial_capital

    trade_pnls = [t.pnl for t in trades]
    wins = [p for p in trade_pnls if p > 0]
    win_rate = len(wins) / len(trade_pnls) if trade_pnls else 0.0

    returns = []
    for i in range(1, len(equity)):
        if equity[i - 1] == 0:
            continue
        returns.append((equity[i] - equity[i - 1]) / equity[i - 1])

    return {
        "total_return": total_return,
        "win_rate": win_rate,
        "sharpe_ratio": sharpe_ratio(returns, TIMEFRAME_PERIODS_PER_YEAR.get(timeframe, 365)),
        "max_drawdown": max_drawdown(equity) if equity else 0.0,
        "profit_factor": profit_factor(trade_pnls),
        "expectancy": expectancy(trade_pnls),
        "kelly_criterion": kelly_criterion(trade_pnls),
        "trade_count": len(trades),
        "ending_equity": final_equity,
    }


def run_backtest(candles: List[Candle], strategy: StrategyConfig, config: BacktestConfig, timeframe: str):
    closes = [c.close for c in candles]
    rsi, signals = generate_signals(closes, strategy)

    equity: List[float] = []
    trades: List[Trade] = []
    capital = config.initial_capital
    position: Position | None = None

    signal_map = {s.index: s.action for s in signals}

    for i, candle in enumerate(candles):
        if position:
            if position.side == "long":
                unrealized = (candle.close - position.entry_price) * position.qty
            else:
                unrealized = (position.entry_price - candle.close) * position.qty
            equity.append(capital + unrealized)
        else:
            equity.append(capital)

        if i not in signal_map:
            continue

        action = signal_map[i]
        if action == "buy":
            if position and position.side == "long":
                continue
            if position and position.side == "short":
                exit_price = _apply_slippage(candle.close, "buy", config.slippage_bps)
                pnl = (position.entry_price - exit_price) * position.qty
                fee = (position.entry_price + exit_price) * position.qty * config.fee_rate
                pnl -= fee
                capital += pnl
                trades.append(
                    Trade(
                        side="short",
                        entry_time=position.entry_time,
                        exit_time=candle.timestamp,
                        entry_price=position.entry_price,
                        exit_price=exit_price,
                        qty=position.qty,
                        pnl=pnl,
                        return_pct=pnl / config.initial_capital,
                    )
                )
                position = None

            qty = (capital * config.position_size_pct) / candle.close
            entry_price = _apply_slippage(candle.close, "buy", config.slippage_bps)
            fee = entry_price * qty * config.fee_rate
            capital -= fee
            position = Position(side="long", entry_price=entry_price, qty=qty, entry_time=candle.timestamp)

        if action == "sell":
            if position and position.side == "short":
                continue
            if position and position.side == "long":
                exit_price = _apply_slippage(candle.close, "sell", config.slippage_bps)
                pnl = (exit_price - position.entry_price) * position.qty
                fee = (position.entry_price + exit_price) * position.qty * config.fee_rate
                pnl -= fee
                capital += pnl
                trades.append(
                    Trade(
                        side="long",
                        entry_time=position.entry_time,
                        exit_time=candle.timestamp,
                        entry_price=position.entry_price,
                        exit_price=exit_price,
                        qty=position.qty,
                        pnl=pnl,
                        return_pct=pnl / config.initial_capital,
                    )
                )
                position = None

            if config.allow_short:
                qty = (capital * config.position_size_pct) / candle.close
                entry_price = _apply_slippage(candle.close, "sell", config.slippage_bps)
                fee = entry_price * qty * config.fee_rate
                capital -= fee
                position = Position(side="short", entry_price=entry_price, qty=qty, entry_time=candle.timestamp)

    if position:
        last = candles[-1]
        if position.side == "long":
            exit_price = _apply_slippage(last.close, "sell", config.slippage_bps)
            pnl = (exit_price - position.entry_price) * position.qty
            fee = (position.entry_price + exit_price) * position.qty * config.fee_rate
            pnl -= fee
            trades.append(
                Trade(
                    side="long",
                    entry_time=position.entry_time,
                    exit_time=last.timestamp,
                    entry_price=position.entry_price,
                    exit_price=exit_price,
                    qty=position.qty,
                    pnl=pnl,
                    return_pct=pnl / config.initial_capital,
                )
            )
            capital += pnl
        else:
            exit_price = _apply_slippage(last.close, "buy", config.slippage_bps)
            pnl = (position.entry_price - exit_price) * position.qty
            fee = (position.entry_price + exit_price) * position.qty * config.fee_rate
            pnl -= fee
            trades.append(
                Trade(
                    side="short",
                    entry_time=position.entry_time,
                    exit_time=last.timestamp,
                    entry_price=position.entry_price,
                    exit_price=exit_price,
                    qty=position.qty,
                    pnl=pnl,
                    return_pct=pnl / config.initial_capital,
                )
            )
            capital += pnl

    metrics = compute_metrics(equity, trades, timeframe, config.initial_capital)

    return rsi, equity, trades, metrics
