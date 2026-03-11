const API_BASE = "http://localhost:8000";
const DEFAULT_PAIRS = [
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
];
const DEFAULT_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"];

const elements = {
  form: document.getElementById("backtestForm"),
  runMode: document.getElementById("runMode"),
  symbol: document.getElementById("symbol"),
  timeframe: document.getElementById("timeframe"),
  start: document.getElementById("start"),
  end: document.getElementById("end"),
  rsiPeriod: document.getElementById("rsiPeriod"),
  rsiLower: document.getElementById("rsiLower"),
  rsiUpper: document.getElementById("rsiUpper"),
  mode: document.getElementById("mode"),
  slopeLookback: document.getElementById("slopeLookback"),
  slopeMin: document.getElementById("slopeMin"),
  slopeMax: document.getElementById("slopeMax"),
  divergence: document.getElementById("divergence"),
  divLookback: document.getElementById("divLookback"),
  initialCapital: document.getElementById("initialCapital"),
  feeRate: document.getElementById("feeRate"),
  slippage: document.getElementById("slippage"),
  allowShort: document.getElementById("allowShort"),
  maxCandles: document.getElementById("maxCandles"),
  optPeriods: document.getElementById("optPeriods"),
  optLowers: document.getElementById("optLowers"),
  optUppers: document.getElementById("optUppers"),
  optObjective: document.getElementById("optObjective"),
  optTopN: document.getElementById("optTopN"),
  wfTrain: document.getElementById("wfTrain"),
  wfTest: document.getElementById("wfTest"),
  wfStep: document.getElementById("wfStep"),
  wfCarry: document.getElementById("wfCarry"),
  optimizationFields: document.getElementById("optimizationFields"),
  walkforwardFields: document.getElementById("walkforwardFields"),
  resultsBody: document.getElementById("resultsBody"),
  runButton: document.getElementById("runBacktest"),
  statusPill: document.getElementById("statusPill"),
  statusText: document.getElementById("statusText"),
  metricReturn: document.getElementById("metricReturn"),
  metricWinRate: document.getElementById("metricWinRate"),
  metricSharpe: document.getElementById("metricSharpe"),
  metricDrawdown: document.getElementById("metricDrawdown"),
  metricProfitFactor: document.getElementById("metricProfitFactor"),
  metricExpectancy: document.getElementById("metricExpectancy"),
  metricKelly: document.getElementById("metricKelly"),
  metricTrades: document.getElementById("metricTrades"),
};

let priceChart;
let rsiChart;
let equityChart;
let priceSeries;
let rsiSeries;
let equitySeries;
const priceContainer = document.getElementById("priceChart");
const rsiContainer = document.getElementById("rsiChart");
const equityContainer = document.getElementById("equityChart");

const formatPercent = (value) => `${(value * 100).toFixed(2)}%`;
const formatNumber = (value) => Number(value).toFixed(2);

function parseList(value, parser) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0)
    .map((item) => parser(item))
    .filter((item) => !Number.isNaN(item));
}

function setMode(mode) {
  elements.optimizationFields.classList.toggle("is-visible", mode === "optimize" || mode === "walkforward");
  elements.walkforwardFields.classList.toggle("is-visible", mode === "walkforward");
  if (mode === "optimize") {
    elements.runButton.textContent = "Run Optimization";
    elements.resultsBody.textContent = "Run optimization to see the top parameter sets.";
  } else if (mode === "walkforward") {
    elements.runButton.textContent = "Run Walk-Forward";
    elements.resultsBody.textContent = "Run walk-forward to see window performance.";
  } else {
    elements.runButton.textContent = "Run Backtest";
    elements.resultsBody.textContent = "Run a backtest to see details.";
  }
}

function setStatus(state, text) {
  elements.statusPill.textContent = state;
  elements.statusText.textContent = text;
  if (state === "Running") {
    elements.statusPill.style.background = "rgba(244, 181, 40, 0.18)";
    elements.statusPill.style.color = "#f4b528";
    elements.statusPill.style.borderColor = "rgba(244, 181, 40, 0.6)";
  } else if (state === "Error") {
    elements.statusPill.style.background = "rgba(245, 90, 90, 0.18)";
    elements.statusPill.style.color = "#ff8a8a";
    elements.statusPill.style.borderColor = "rgba(245, 90, 90, 0.6)";
  } else {
    elements.statusPill.style.background = "rgba(61, 214, 192, 0.15)";
    elements.statusPill.style.color = "#3dd6c0";
    elements.statusPill.style.borderColor = "rgba(61, 214, 192, 0.5)";
  }
}

function initCharts() {
  const commonOptions = {
    layout: {
      background: { color: "#151b21" },
      textColor: "#cdd5df",
      fontFamily: "IBM Plex Sans",
    },
    grid: {
      horzLines: { color: "rgba(255,255,255,0.05)" },
      vertLines: { color: "rgba(255,255,255,0.05)" },
    },
    timeScale: { borderColor: "rgba(255,255,255,0.1)" },
    rightPriceScale: { borderColor: "rgba(255,255,255,0.1)" },
  };

  priceChart = LightweightCharts.createChart(priceContainer, {
    ...commonOptions,
    height: priceContainer.clientHeight,
    crosshair: { mode: LightweightCharts.CrosshairMode.Magnet },
  });
  priceSeries = priceChart.addCandlestickSeries({
    upColor: "#3dd6c0",
    downColor: "#f57c00",
    borderVisible: false,
    wickUpColor: "#3dd6c0",
    wickDownColor: "#f57c00",
  });

  rsiChart = LightweightCharts.createChart(rsiContainer, {
    ...commonOptions,
    height: rsiContainer.clientHeight,
    crosshair: { mode: LightweightCharts.CrosshairMode.Magnet },
  });
  rsiSeries = rsiChart.addLineSeries({ color: "#f4b528", lineWidth: 2 });

  equityChart = LightweightCharts.createChart(equityContainer, {
    ...commonOptions,
    height: equityContainer.clientHeight,
    crosshair: { mode: LightweightCharts.CrosshairMode.Magnet },
  });
  equitySeries = equityChart.addLineSeries({ color: "#3dd6c0", lineWidth: 2 });

  window.addEventListener("resize", () => {
    priceChart.applyOptions({ width: priceContainer.clientWidth });
    rsiChart.applyOptions({ width: rsiContainer.clientWidth });
    equityChart.applyOptions({ width: equityContainer.clientWidth });
  });
}

function populateSelect(select, values) {
  select.innerHTML = "";
  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.appendChild(option);
  });
}

async function loadOptions() {
  try {
    const [pairsRes, timeframeRes] = await Promise.all([
      fetch(`${API_BASE}/api/pairs`),
      fetch(`${API_BASE}/api/timeframes`),
    ]);

    const pairs = pairsRes.ok ? await pairsRes.json() : DEFAULT_PAIRS;
    const timeframes = timeframeRes.ok ? await timeframeRes.json() : DEFAULT_TIMEFRAMES;

    populateSelect(elements.symbol, pairs);
    populateSelect(elements.timeframe, timeframes);

    elements.symbol.value = pairs[0] ?? "BTCUSDT";
    elements.timeframe.value = timeframes.includes("1h") ? "1h" : timeframes[0];
  } catch (error) {
    populateSelect(elements.symbol, DEFAULT_PAIRS);
    populateSelect(elements.timeframe, DEFAULT_TIMEFRAMES);
  }
}

function setDefaultDates() {
  const now = new Date();
  const start = new Date(now.getTime() - 1000 * 60 * 60 * 24 * 30);
  elements.start.value = start.toISOString().slice(0, 16);
  elements.end.value = now.toISOString().slice(0, 16);
}

function updateMetrics(metrics) {
  elements.metricReturn.textContent = formatPercent(metrics.total_return ?? 0);
  elements.metricWinRate.textContent = formatPercent(metrics.win_rate ?? 0);
  elements.metricSharpe.textContent = formatNumber(metrics.sharpe_ratio ?? 0);
  elements.metricDrawdown.textContent = formatPercent(metrics.max_drawdown ?? 0);
  elements.metricProfitFactor.textContent =
    metrics.profit_factor === Infinity ? "∞" : formatNumber(metrics.profit_factor ?? 0);
  elements.metricExpectancy.textContent = formatNumber(metrics.expectancy ?? 0);
  elements.metricKelly.textContent = formatPercent(metrics.kelly_criterion ?? 0);
  elements.metricTrades.textContent = metrics.trade_count ?? 0;
}

function renderCharts(payload) {
  const candles = payload.candles;
  const rsi = payload.rsi || candles.map(() => null);
  const equity = payload.equity;
  const trades = payload.trades || [];

  const priceData = candles.map((c) => ({
    time: Math.floor(c.timestamp / 1000),
    open: c.open,
    high: c.high,
    low: c.low,
    close: c.close,
  }));

  priceSeries.setData(priceData);

  const rsiData = rsi
    .map((value, index) => {
      if (value === null || value === undefined) return null;
      return { time: Math.floor(candles[index].timestamp / 1000), value };
    })
    .filter(Boolean);
  rsiSeries.setData(rsiData);

  const equityData = equity
    .map((value, index) => {
      if (value === null || value === undefined) return null;
      return { time: Math.floor(candles[index].timestamp / 1000), value };
    })
    .filter(Boolean);
  equitySeries.setData(equityData);

  priceChart.timeScale().fitContent();
  rsiChart.timeScale().fitContent();
  equityChart.timeScale().fitContent();

  const markers = [];
  trades.forEach((trade) => {
    const entryTime = Math.floor(trade.entry_time / 1000);
    const exitTime = Math.floor(trade.exit_time / 1000);

    if (trade.side === "long") {
      markers.push({ time: entryTime, position: "belowBar", color: "#3dd6c0", shape: "arrowUp", text: "Long" });
      markers.push({ time: exitTime, position: "aboveBar", color: "#f57c00", shape: "arrowDown", text: "Exit" });
    } else {
      markers.push({ time: entryTime, position: "aboveBar", color: "#f57c00", shape: "arrowDown", text: "Short" });
      markers.push({ time: exitTime, position: "belowBar", color: "#3dd6c0", shape: "arrowUp", text: "Cover" });
    }
  });
  priceSeries.setMarkers(markers);
}

function renderTable(headers, rows) {
  const thead = `<thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead>`;
  const tbody = rows
    .map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`)
    .join("");
  return `<table class="results-table">${thead}<tbody>${tbody}</tbody></table>`;
}

function renderBacktestResults(trades) {
  if (!trades || trades.length === 0) {
    elements.resultsBody.textContent = "No trades executed in this run.";
    return;
  }
  const recent = trades.slice(-12);
  const rows = recent.map((trade) => [
    trade.side,
    new Date(trade.entry_time).toLocaleString(),
    new Date(trade.exit_time).toLocaleString(),
    formatNumber(trade.pnl),
  ]);
  elements.resultsBody.innerHTML = renderTable(["Side", "Entry", "Exit", "PnL"], rows);
}

function renderOptimizationResults(results) {
  if (!results || results.length === 0) {
    elements.resultsBody.textContent = "No optimization results.";
    return;
  }
  const rows = results.map((item) => [
    `RSI ${item.strategy.rsi_period}`,
    `${item.strategy.lower}/${item.strategy.upper}`,
    item.strategy.mode,
    formatPercent(item.metrics.total_return ?? 0),
    formatNumber(item.metrics.sharpe_ratio ?? 0),
  ]);
  elements.resultsBody.innerHTML = renderTable(
    ["Period", "Levels", "Mode", "Return", "Sharpe"],
    rows
  );
}

function renderWalkforwardResults(windows) {
  if (!windows || windows.length === 0) {
    elements.resultsBody.textContent = "No walk-forward windows produced.";
    return;
  }
  const rows = windows.map((window) => [
    new Date(window.test_start).toLocaleDateString(),
    new Date(window.test_end).toLocaleDateString(),
    `RSI ${window.strategy.rsi_period}`,
    formatPercent(window.metrics.total_return ?? 0),
    formatNumber(window.metrics.sharpe_ratio ?? 0),
  ]);
  elements.resultsBody.innerHTML = renderTable(
    ["Test Start", "Test End", "Strategy", "Return", "Sharpe"],
    rows
  );
}

function buildBasePayload() {
  return {
    symbol: elements.symbol.value,
    timeframe: elements.timeframe.value,
    start: elements.start.value ? new Date(elements.start.value).toISOString() : null,
    end: elements.end.value ? new Date(elements.end.value).toISOString() : null,
    max_candles: Number(elements.maxCandles.value),
  };
}

function buildStrategy() {
  return {
    rsi_period: Number(elements.rsiPeriod.value),
    lower: Number(elements.rsiLower.value),
    upper: Number(elements.rsiUpper.value),
    mode: elements.mode.value,
    use_divergence: elements.divergence.value === "true",
    divergence_lookback: Number(elements.divLookback.value),
    slope_lookback: Number(elements.slopeLookback.value),
    slope_min: elements.slopeMin.value ? Number(elements.slopeMin.value) : null,
    slope_max: elements.slopeMax.value ? Number(elements.slopeMax.value) : null,
  };
}

function buildBacktestConfig() {
  return {
    initial_capital: Number(elements.initialCapital.value),
    fee_rate: Number(elements.feeRate.value),
    slippage_bps: Number(elements.slippage.value),
    allow_short: elements.allowShort.value === "true",
    position_size_pct: 1.0,
  };
}

function buildOptimizationConfig() {
  const rsiPeriods = parseList(elements.optPeriods.value, Number);
  const lowers = parseList(elements.optLowers.value, Number);
  const uppers = parseList(elements.optUppers.value, Number);
  return {
    rsi_periods: rsiPeriods.length ? rsiPeriods : [Number(elements.rsiPeriod.value)],
    lowers: lowers.length ? lowers : [Number(elements.rsiLower.value)],
    uppers: uppers.length ? uppers : [Number(elements.rsiUpper.value)],
    modes: [elements.mode.value],
    use_divergence: elements.divergence.value === "true",
    divergence_lookback: Number(elements.divLookback.value),
    slope_lookback: Number(elements.slopeLookback.value),
    slope_min: elements.slopeMin.value ? Number(elements.slopeMin.value) : null,
    slope_max: elements.slopeMax.value ? Number(elements.slopeMax.value) : null,
    objective: elements.optObjective.value,
    top_n: Number(elements.optTopN.value),
  };
}

function buildBacktestPayload() {
  return {
    ...buildBasePayload(),
    strategy: buildStrategy(),
    backtest: buildBacktestConfig(),
  };
}

function buildOptimizationPayload() {
  return {
    ...buildBasePayload(),
    backtest: buildBacktestConfig(),
    optimization: buildOptimizationConfig(),
  };
}

function buildWalkforwardPayload() {
  return {
    ...buildBasePayload(),
    walkforward: {
      train_candles: Number(elements.wfTrain.value),
      test_candles: Number(elements.wfTest.value),
      step_candles: Number(elements.wfStep.value),
      carry_capital: elements.wfCarry.value === "true",
      optimization: buildOptimizationConfig(),
      backtest: buildBacktestConfig(),
    },
  };
}

async function runBacktest(event) {
  event.preventDefault();
  const mode = elements.runMode.value;
  if (mode === "optimize") {
    setStatus("Running", "Optimizing strategy parameters...");
  } else if (mode === "walkforward") {
    setStatus("Running", "Running walk-forward analysis...");
  } else {
    setStatus("Running", "Fetching candles and simulating trades...");
  }

  try {
    let endpoint = "/api/backtest";
    let payload = buildBacktestPayload();
    if (mode === "optimize") {
      endpoint = "/api/optimize";
      payload = buildOptimizationPayload();
    } else if (mode === "walkforward") {
      endpoint = "/api/walkforward";
      payload = buildWalkforwardPayload();
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Backtest failed");
    }

    const result = await response.json();
    renderCharts(result);
    updateMetrics(result.metrics);

    if (mode === "optimize") {
      renderOptimizationResults(result.results);
      setStatus("Idle", `Optimization complete for ${result.symbol} (${result.timeframe})`);
    } else if (mode === "walkforward") {
      renderWalkforwardResults(result.windows);
      setStatus("Idle", `Walk-forward complete for ${result.symbol} (${result.timeframe})`);
    } else {
      renderBacktestResults(result.trades);
      setStatus("Idle", `Backtest complete for ${result.symbol} (${result.timeframe})`);
    }
  } catch (error) {
    setStatus("Error", error.message || "Backtest failed");
  }
}

initCharts();
loadOptions();
setDefaultDates();

elements.form.addEventListener("submit", runBacktest);
elements.runMode.addEventListener("change", (event) => setMode(event.target.value));
setMode(elements.runMode.value);
