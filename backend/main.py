from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import DEFAULT_SYMBOL, DEFAULT_TIMEFRAME, MAX_CANDLES, TIMEFRAME_MAP
from .engines.backtest import run_backtest
from .engines.data import DataEngine
from .engines.optimizer import grid_search, run_walkforward
from .models import (
    BacktestRequest,
    BacktestResult,
    OptimizationItem,
    OptimizationRequest,
    OptimizationResult,
    WalkForwardRequest,
    WalkForwardResult,
)

app = FastAPI(title="Crypto RSI Backtester", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

data_engine = DataEngine()


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/pairs")
async def pairs():
    return [
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "BNBUSDT",
        "ADAUSDT",
        "XRPUSDT",
        "DOGEUSDT",
        "AVAXUSDT",
        "MATICUSDT",
        "LINKUSDT",
    ]


@app.get("/api/timeframes")
async def timeframes():
    return list(TIMEFRAME_MAP.keys())


@app.post("/api/backtest", response_model=BacktestResult)
async def backtest(request: BacktestRequest):
    max_candles = min(request.max_candles, MAX_CANDLES)

    try:
        candles = data_engine.get_candles(
            symbol=request.symbol,
            timeframe=request.timeframe,
            start=request.start,
            end=request.end,
            max_candles=max_candles,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if len(candles) < request.strategy.rsi_period + 5:
        raise HTTPException(status_code=400, detail="Not enough candles for RSI period")

    rsi, equity, trades, metrics = run_backtest(
        candles=candles,
        strategy=request.strategy,
        config=request.backtest,
        timeframe=request.timeframe,
    )

    backtest_id = data_engine.db.store_backtest(
        request.symbol,
        request.timeframe,
        params={"strategy": request.strategy.model_dump(), "backtest": request.backtest.model_dump()},
        metrics=metrics,
    )
    if backtest_id:
        data_engine.db.store_trades(backtest_id, trades)

    return BacktestResult(
        symbol=request.symbol,
        timeframe=request.timeframe,
        start=candles[0].timestamp,
        end=candles[-1].timestamp,
        candles=candles,
        rsi=rsi,
        equity=equity,
        trades=trades,
        metrics=metrics,
    )


@app.post("/api/optimize", response_model=OptimizationResult)
async def optimize(request: OptimizationRequest):
    max_candles = min(request.max_candles, MAX_CANDLES)
    try:
        candles = data_engine.get_candles(
            symbol=request.symbol,
            timeframe=request.timeframe,
            start=request.start,
            end=request.end,
            max_candles=max_candles,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if len(candles) < request.optimization.rsi_periods[0] + 5:
        raise HTTPException(status_code=400, detail="Not enough candles for optimization")
    results = grid_search(
        candles=candles,
        backtest=request.backtest,
        rsi_periods=request.optimization.rsi_periods,
        lowers=request.optimization.lowers,
        uppers=request.optimization.uppers,
        modes=request.optimization.modes,
        use_divergence=request.optimization.use_divergence,
        divergence_lookback=request.optimization.divergence_lookback,
        slope_lookback=request.optimization.slope_lookback,
        slope_min=request.optimization.slope_min,
        slope_max=request.optimization.slope_max,
        objective=request.optimization.objective,
        timeframe=request.timeframe,
    )

    if not results:
        raise HTTPException(status_code=400, detail="Optimization grid is empty")

    top_results = results[: request.optimization.top_n]
    best = top_results[0]
    rsi, equity, trades, metrics = run_backtest(
        candles=candles,
        strategy=best.strategy,
        config=request.backtest,
        timeframe=request.timeframe,
    )

    return OptimizationResult(
        symbol=request.symbol,
        timeframe=request.timeframe,
        start=candles[0].timestamp,
        end=candles[-1].timestamp,
        candles=candles,
        rsi=rsi,
        equity=equity,
        trades=trades,
        metrics=metrics,
        best_strategy=best.strategy,
        results=[OptimizationItem(strategy=item.strategy, metrics=item.metrics) for item in top_results],
    )


@app.post("/api/walkforward", response_model=WalkForwardResult)
async def walkforward(request: WalkForwardRequest):
    max_candles = min(request.max_candles, MAX_CANDLES)
    try:
        candles = data_engine.get_candles(
            symbol=request.symbol,
            timeframe=request.timeframe,
            start=request.start,
            end=request.end,
            max_candles=max_candles,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    wf = request.walkforward
    if len(candles) < wf.train_candles + wf.test_candles:
        raise HTTPException(status_code=400, detail="Not enough candles for walk-forward")
    equity, trades, metrics, windows = run_walkforward(
        candles=candles,
        backtest=wf.backtest,
        timeframe=request.timeframe,
        train_candles=wf.train_candles,
        test_candles=wf.test_candles,
        step_candles=wf.step_candles,
        rsi_periods=wf.optimization.rsi_periods,
        lowers=wf.optimization.lowers,
        uppers=wf.optimization.uppers,
        modes=wf.optimization.modes,
        use_divergence=wf.optimization.use_divergence,
        divergence_lookback=wf.optimization.divergence_lookback,
        slope_lookback=wf.optimization.slope_lookback,
        slope_min=wf.optimization.slope_min,
        slope_max=wf.optimization.slope_max,
        objective=wf.optimization.objective,
        carry_capital=wf.carry_capital,
    )

    if not windows:
        raise HTTPException(status_code=400, detail="Walk-forward produced no windows")

    return WalkForwardResult(
        symbol=request.symbol,
        timeframe=request.timeframe,
        start=candles[0].timestamp,
        end=candles[-1].timestamp,
        candles=candles,
        equity=equity,
        trades=trades,
        metrics=metrics,
        windows=windows,
    )
