# Crypto RSI Backtester Architecture

## System Overview
- Frontend: Static single-page UI with Lightweight Charts for candles, RSI, and equity curve.
- Backend API: FastAPI service exposing `/api/backtest`, `/api/pairs`, `/api/timeframes`.
- Data Engine: Fetches OHLCV from Binance and caches in PostgreSQL/TimescaleDB.
- Strategy Engine: Generates RSI signals (threshold, crossing, divergence, slope filters).
- Backtesting Engine: Simulates long/short trades with fees and slippage.
- Metrics Engine: Computes performance statistics for reporting.
- Optimization Engine: Grid search across RSI parameters.
- Walk-Forward Engine: Rolling train/test windows for robustness.

## Data Flow
1. User selects pair, timeframe, RSI settings, and backtest parameters in the UI.
2. Frontend calls `POST /api/backtest` with strategy and backtest config.
3. Backend pulls candles from TimescaleDB if available, otherwise from Binance API.
4. RSI is computed from scratch and signals are generated.
5. Backtest engine simulates trades, builds equity curve, and calculates metrics.
6. Results are returned to the frontend for charts and summary display.

## Scaling Notes
- TimescaleDB hypertables allow fast time-range queries on candles.
- Stateless API workers can be scaled horizontally.
- Backtests can be parallelized by symbol or parameter grid.
- A job queue can be added for optimization or walk-forward testing.

## Key Modules
- `backend/engines/data.py`: Binance ingestion + DB cache.
- `backend/engines/rsi.py`: RSI math implementation.
- `backend/engines/strategy.py`: Strategy rules and signal generation.
- `backend/engines/backtest.py`: Execution logic, fees, slippage.
- `backend/engines/metrics.py`: Performance metrics.
- `backend/engines/optimizer.py`: Grid search and walk-forward logic.

## API Contract
- `POST /api/backtest`
  - Request: symbol, timeframe, start/end, strategy config, backtest config.
  - Response: candles, RSI series, equity series, trades, metrics.
- `POST /api/optimize`
  - Request: symbol, timeframe, optimization config, backtest config.
  - Response: top strategies, best strategy backtest series, metrics.
- `POST /api/walkforward`
  - Request: symbol, timeframe, walk-forward config.
  - Response: window metrics, combined equity series, trades, metrics.
