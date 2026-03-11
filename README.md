# Crypto RSI Backtester

![CI](https://github.com/abhishekpatel9802/abhishekpatel9802-quantback/actions/workflows/ci.yml/badge.svg)

A lightweight crypto strategy research app with a charting UI and a FastAPI backend. It computes RSI from scratch, generates signals, and runs fee + slippage-aware backtests with long/short support.

## Features
- Binance OHLCV ingestion with optional TimescaleDB caching
- RSI (Wilder’s smoothing) implemented from scratch
- Strategy rules: threshold, crossing, slope filters, RSI divergence
- Backtesting engine with fees, slippage, long/short support
- Metrics: total return, win rate, Sharpe, max drawdown, profit factor, expectancy, Kelly
- Grid-search optimization and walk-forward testing

## Architecture
See `ARCHITECTURE.md` for the system diagram and data flow.

## Quickstart

### Backend
1. Create a virtual environment and install dependencies.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

2. Optional: set a database URL for TimescaleDB/Postgres.

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/crypto"
```

3. Start the API server.

```bash
uvicorn backend.main:app --reload --port 8000
```

### Frontend
1. Open `index.html` in a browser.
2. The UI expects the API at `http://localhost:8000`. If you run it elsewhere, update `API_BASE` in `app.js`.

## API

### Backtest
```bash
curl -X POST http://localhost:8000/api/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "max_candles": 2000,
    "strategy": {
      "rsi_period": 14,
      "lower": 30,
      "upper": 70,
      "mode": "threshold",
      "use_divergence": false,
      "divergence_lookback": 20,
      "slope_lookback": 5,
      "slope_min": null,
      "slope_max": null
    },
    "backtest": {
      "initial_capital": 10000,
      "fee_rate": 0.001,
      "slippage_bps": 5,
      "allow_short": true,
      "position_size_pct": 1.0
    }
  }'
```

### Optimize (Grid Search)
```bash
curl -X POST http://localhost:8000/api/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "max_candles": 2000,
    "backtest": {
      "initial_capital": 10000,
      "fee_rate": 0.001,
      "slippage_bps": 5,
      "allow_short": true,
      "position_size_pct": 1.0
    },
    "optimization": {
      "rsi_periods": [10, 14, 21],
      "lowers": [20, 30, 40],
      "uppers": [60, 70, 80],
      "modes": ["threshold"],
      "objective": "total_return",
      "top_n": 10
    }
  }'
```

### Walk-Forward
```bash
curl -X POST http://localhost:8000/api/walkforward \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "max_candles": 2000,
    "walkforward": {
      "train_candles": 500,
      "test_candles": 200,
      "step_candles": 200,
      "carry_capital": true,
      "optimization": {
        "rsi_periods": [10, 14, 21],
        "lowers": [20, 30, 40],
        "uppers": [60, 70, 80],
        "modes": ["threshold"],
        "objective": "total_return",
        "top_n": 5
      },
      "backtest": {
        "initial_capital": 10000,
        "fee_rate": 0.001,
        "slippage_bps": 5,
        "allow_short": true,
        "position_size_pct": 1.0
      }
    }
  }'
```

## Database
Apply the schema in `backend/db/schema.sql` to create the TimescaleDB tables for OHLCV caching and backtest storage.

## Environment Variables
- `DATABASE_URL` for TimescaleDB/Postgres caching
- `BINANCE_BASE_URL` if you need a proxy or a custom API base
- `MAX_CANDLES` to clamp ingestion size

## Notes
- Binance data is fetched via `/api/v3/klines`.
- RSI is computed manually using Wilder’s smoothing.
- Strategies support threshold/crossing logic, slope filters, and basic divergence.
- The UI Run Mode selector toggles backtest, optimization, and walk-forward.
