# Crypto RSI Backtester

This repo contains a lightweight frontend and a FastAPI backend for RSI-driven crypto strategy backtesting.

## Quickstart

### Backend
1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

2. (Optional) Set database URL for TimescaleDB/Postgres:

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/crypto"
```

3. Start the API server:

```bash
uvicorn backend.main:app --reload --port 8000
```

### Frontend
Open `index.html` in a browser (or serve with any static server). The UI expects the API at `http://localhost:8000` (adjust `API_BASE` in `app.js` if needed).

## Database
Apply the schema from `backend/db/schema.sql` to create the TimescaleDB tables for OHLCV caching.

## Notes
- Binance data is fetched via `/api/v3/klines`.
- RSI is computed manually using Wilder’s smoothing.
- Strategies support threshold/crossing logic, slope filters, and basic divergence.
- Additional endpoints: `/api/optimize` for grid search and `/api/walkforward` for walk-forward testing.
 - Use the Run Mode selector in the UI to switch between backtest, optimization, and walk-forward.
