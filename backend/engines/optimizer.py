from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional

from .backtest import compute_metrics, run_backtest
from ..models import BacktestConfig, Candle, StrategyConfig, Trade


Objective = Literal[
    "total_return",
    "sharpe_ratio",
    "max_drawdown",
    "profit_factor",
    "expectancy",
    "kelly_criterion",
]


@dataclass
class OptimizationResultItem:
    strategy: StrategyConfig
    metrics: dict


def _objective_score(metrics: dict, objective: Objective) -> float:
    value = metrics.get(objective, 0.0)
    if objective == "max_drawdown":
        return -value
    return value


def grid_search(
    candles: List[Candle],
    backtest: BacktestConfig,
    rsi_periods: List[int],
    lowers: List[float],
    uppers: List[float],
    modes: List[str],
    use_divergence: bool,
    divergence_lookback: int,
    slope_lookback: int,
    slope_min: Optional[float],
    slope_max: Optional[float],
    objective: Objective,
    timeframe: str,
) -> List[OptimizationResultItem]:
    results: List[OptimizationResultItem] = []
    if not rsi_periods or not lowers or not uppers or not modes:
        return results
    for period in rsi_periods:
        for lower in lowers:
            for upper in uppers:
                for mode in modes:
                    if lower >= upper:
                        continue
                    strategy = StrategyConfig(
                        rsi_period=period,
                        lower=lower,
                        upper=upper,
                        mode=mode,
                        use_divergence=use_divergence,
                        divergence_lookback=divergence_lookback,
                        slope_lookback=slope_lookback,
                        slope_min=slope_min,
                        slope_max=slope_max,
                    )
                    _, equity, trades, metrics = run_backtest(candles, strategy, backtest, timeframe)
                    results.append(OptimizationResultItem(strategy=strategy, metrics=metrics))

    results.sort(key=lambda item: _objective_score(item.metrics, objective), reverse=True)
    return results


def run_walkforward(
    candles: List[Candle],
    backtest: BacktestConfig,
    timeframe: str,
    train_candles: int,
    test_candles: int,
    step_candles: int,
    rsi_periods: List[int],
    lowers: List[float],
    uppers: List[float],
    modes: List[str],
    use_divergence: bool,
    divergence_lookback: int,
    slope_lookback: int,
    slope_min: Optional[float],
    slope_max: Optional[float],
    objective: Objective,
    carry_capital: bool,
):
    windows = []
    equity_series: List[Optional[float]] = [None for _ in candles]
    combined_trades: List[Trade] = []

    cursor = 0
    current_capital = backtest.initial_capital
    step = step_candles if step_candles > 0 else test_candles

    if train_candles <= 0 or test_candles <= 0:
        return equity_series, combined_trades, {}, []

    while cursor + train_candles + test_candles <= len(candles):
        train_slice = candles[cursor : cursor + train_candles]
        test_slice = candles[cursor + train_candles : cursor + train_candles + test_candles]

        train_results = grid_search(
            train_slice,
            backtest,
            rsi_periods,
            lowers,
            uppers,
            modes,
            use_divergence,
            divergence_lookback,
            slope_lookback,
            slope_min,
            slope_max,
            objective,
            timeframe,
        )
        if not train_results:
            break
        best = train_results[0]

        test_config = backtest
        if carry_capital:
            test_config = BacktestConfig(
                initial_capital=current_capital,
                fee_rate=backtest.fee_rate,
                slippage_bps=backtest.slippage_bps,
                allow_short=backtest.allow_short,
                position_size_pct=backtest.position_size_pct,
            )

        _rsi, equity, trades, metrics = run_backtest(test_slice, best.strategy, test_config, timeframe)

        if carry_capital and equity:
            current_capital = equity[-1]

        for offset, value in enumerate(equity):
            equity_series[cursor + train_candles + offset] = value

        combined_trades.extend(trades)

        windows.append(
            {
                "train_start": train_slice[0].timestamp,
                "train_end": train_slice[-1].timestamp,
                "test_start": test_slice[0].timestamp,
                "test_end": test_slice[-1].timestamp,
                "strategy": best.strategy,
                "metrics": metrics,
            }
        )

        cursor += step

    compact_equity = [value for value in equity_series if value is not None]
    overall_metrics = compute_metrics(compact_equity, combined_trades, timeframe, backtest.initial_capital)

    return equity_series, combined_trades, overall_metrics, windows
