from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Candle(BaseModel):
    timestamp: int = Field(..., description="Unix timestamp in milliseconds")
    open: float
    high: float
    low: float
    close: float
    volume: float


class StrategyConfig(BaseModel):
    rsi_period: int = 14
    lower: float = 30
    upper: float = 70
    mode: Literal["threshold", "crossing"] = "threshold"
    use_divergence: bool = False
    divergence_lookback: int = 20
    slope_lookback: int = 5
    slope_min: Optional[float] = None
    slope_max: Optional[float] = None


class BacktestConfig(BaseModel):
    initial_capital: float = 10_000
    fee_rate: float = 0.001
    slippage_bps: float = 5
    allow_short: bool = True
    position_size_pct: float = 1.0


class BacktestRequest(BaseModel):
    symbol: str
    timeframe: Literal["1m", "5m", "15m", "1h", "4h", "1d"]
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    max_candles: int = 2000
    strategy: StrategyConfig = StrategyConfig()
    backtest: BacktestConfig = BacktestConfig()


class Trade(BaseModel):
    side: Literal["long", "short"]
    entry_time: int
    exit_time: int
    entry_price: float
    exit_price: float
    qty: float
    pnl: float
    return_pct: float


class BacktestResult(BaseModel):
    symbol: str
    timeframe: str
    start: int
    end: int
    candles: list[Candle]
    rsi: list[Optional[float]]
    equity: list[float]
    trades: list[Trade]
    metrics: dict


class OptimizationConfig(BaseModel):
    rsi_periods: list[int] = [10, 14, 21]
    lowers: list[float] = [30]
    uppers: list[float] = [70]
    modes: list[Literal["threshold", "crossing"]] = ["threshold"]
    use_divergence: bool = False
    divergence_lookback: int = 20
    slope_lookback: int = 5
    slope_min: Optional[float] = None
    slope_max: Optional[float] = None
    objective: Literal[
        "total_return",
        "sharpe_ratio",
        "max_drawdown",
        "profit_factor",
        "expectancy",
        "kelly_criterion",
    ] = "total_return"
    top_n: int = 10


class OptimizationRequest(BaseModel):
    symbol: str
    timeframe: Literal["1m", "5m", "15m", "1h", "4h", "1d"]
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    max_candles: int = 2000
    backtest: BacktestConfig = BacktestConfig()
    optimization: OptimizationConfig = OptimizationConfig()


class OptimizationItem(BaseModel):
    strategy: StrategyConfig
    metrics: dict


class OptimizationResult(BaseModel):
    symbol: str
    timeframe: str
    start: int
    end: int
    candles: list[Candle]
    rsi: list[Optional[float]]
    equity: list[float]
    trades: list[Trade]
    metrics: dict
    best_strategy: StrategyConfig
    results: list[OptimizationItem]


class WalkForwardConfig(BaseModel):
    train_candles: int = 500
    test_candles: int = 200
    step_candles: int = 200
    carry_capital: bool = True
    optimization: OptimizationConfig = OptimizationConfig()
    backtest: BacktestConfig = BacktestConfig()


class WalkForwardRequest(BaseModel):
    symbol: str
    timeframe: Literal["1m", "5m", "15m", "1h", "4h", "1d"]
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    max_candles: int = 2000
    walkforward: WalkForwardConfig = WalkForwardConfig()


class WalkForwardWindow(BaseModel):
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    strategy: StrategyConfig
    metrics: dict


class WalkForwardResult(BaseModel):
    symbol: str
    timeframe: str
    start: int
    end: int
    candles: list[Candle]
    equity: list[Optional[float]]
    trades: list[Trade]
    metrics: dict
    windows: list[WalkForwardWindow]
