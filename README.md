# 📈 Trading_Bot

Personal AI-powered trading agent and signal engine. Claude-primary Flask backend with 15 live trading tools, XGBoost ML predictions, full 10-indicator stack, ARIMA forecasting, carry unwind detection, intermarket flow analysis (Crude → DXY → USD/JPY → Stocks), and Telegram morning briefs before market open.

Part of the `my_AI_brain` system. Public brain bundles live at [holmesstephen067-glitch/my_AI_brain](https://github.com/holmesstephen067-glitch/my_AI_brain).

---

## All Raw URLs

| File | Raw URL |
|------|---------|
| Main.py | `https://raw.githubusercontent.com/holmesstephen067-glitch/Trading_Bot/refs/heads/main/Main.py` |
| signal_engine.py | `https://raw.githubusercontent.com/holmesstephen067-glitch/Trading_Bot/refs/heads/main/signal_engine.py` |
| finance.md | `https://raw.githubusercontent.com/holmesstephen067-glitch/Trading_Bot/refs/heads/main/finance.md` |
| READMEforstocks.md | `https://raw.githubusercontent.com/holmesstephen067-glitch/Trading_Bot/refs/heads/main/READMEforstocks.md` |
| Claude.md-Trading_dashboard | `https://raw.githubusercontent.com/holmesstephen067-glitch/Trading_Bot/refs/heads/main/Claude.md-Trading_dashboard` |
| backtester.py | `https://raw.githubusercontent.com/holmesstephen067-glitch/Trading_Bot/refs/heads/main/backtester.py` |
| alerts.py | `https://raw.githubusercontent.com/holmesstephen067-glitch/Trading_Bot/refs/heads/main/alerts.py` |
| requirements.txt | `https://raw.githubusercontent.com/holmesstephen067-glitch/Trading_Bot/refs/heads/main/requirements.txt` |

---

## Repo Structure

```
Trading_Bot/
├── Main.py                      ← Flask AI agent — active backend (Claude-primary, 15 tools)
├── signal_engine.py             ← Portfolio config + risk constants
├── README.md                    ← This file — overview + all raw URLs
├── Claude.md-Trading_dashboard  ← Claude Code session context
├── finance.md                   ← Skill bundle — Alpha Vantage, FRED, EDGAR, Treasury
├── READMEforstocks.md           ← Full trading bot docs + setup guide
├── backtester.py                ← VectorBT RSI optimizer + covered call backtest
├── alerts.py                    ← Telegram morning brief + carry unwind monitor
└── requirements.txt             ← All Python dependencies
```

---

## Claude Session Start

Paste these URLs at the start of any trading session:

```
https://raw.githubusercontent.com/holmesstephen067-glitch/Trading_Bot/refs/heads/main/Main.py
https://raw.githubusercontent.com/holmesstephen067-glitch/Trading_Bot/refs/heads/main/signal_engine.py
https://raw.githubusercontent.com/holmesstephen067-glitch/Trading_Bot/refs/heads/main/READMEforstocks.md
```

Claude fetches all three, loads the full system (positions, tools, risk config, session protocol), and is ready to run the session start sequence — carry unwind score, Buffett Indicator, FRED macro snapshot, intermarket flow, regime detection, earnings check, and per-ticker ML analysis.

---

## Quick Start — Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set your Anthropic key (required — OpenAI/Gemini are optional fallbacks)
export ANTHROPIC_API_KEY=your_key

# Start the Flask agent
python Main.py
# Runs on http://localhost:5000

# Full morning scan on portfolio
curl -X POST http://localhost:5000/scan

# Specific tickers
curl -X POST http://localhost:5000/scan -H "Content-Type: application/json" -d '{"tickers": ["TSLA","NVDA","AMD"]}'

# Live P&L on all positions
curl http://localhost:5000/positions

# Covered call scan
curl http://localhost:5000/covered-calls

# Macro snapshot + carry unwind
curl http://localhost:5000/macro

# Ask the agent anything
curl -X POST http://localhost:5000/brain -H "Content-Type: application/json" -d '{"goal": "Should I sell a covered call on SOFI today?"}'

# Run signal_engine.py standalone (no Flask)
python signal_engine.py
python signal_engine.py --tickers TSLA NVDA AMD
python signal_engine.py --save

# Optimize RSI thresholds for a ticker
python backtester.py TSLA

# Test Telegram connection
export TELEGRAM_TOKEN=your_token
export TELEGRAM_CHAT_ID=your_chat_id
python alerts.py test

# Start daily 7:30 AM morning briefs
python alerts.py
```

---

## Main.py — Flask AI Agent

### LLM Chain
Claude (primary) → OpenAI GPT-4o-mini → Gemini Pro (fallback)

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Health check + status |
| `/brain` | POST | General trading agent — `{"goal": "..."}` |
| `/positions` | GET | Live P&L across all holdings |
| `/covered-calls` | GET | Covered call opportunity scan |
| `/macro` | GET | FRED macro snapshot + carry unwind score |
| `/scan` | POST | Full 8-section weekly scan |
| `/log-trade` | POST | Log a trade to journal |
| `/trades` | GET | Recent trades — `?n=10` |
| `/tool/<name>` | GET | Invoke any tool directly — `?input=TICKER` |
| `/tools` | GET | List all registered tools |

### Registered Tools (15)
```
polygon_snapshot    finnhub_quote       finnhub_news
finnhub_earnings    fred_series         macro_snapshot
crypto_fear_greed   polygon_options     portfolio_pnl
carry_unwind_score  covered_call_scan   av_rsi
av_macd             av_atr              calculate
```

### Trade Journal
SQLite `trading_memory.db` with two tables:
- `trades` — structured trade log (ticker, strategy, entry, target, stop, ATR, size, P&L)
- `macro_snapshots` — session-level macro state (VIX, yield curve, carry score, regime)
- `memory` — goal/response pairs for agent context

---

## What The System Does

### 10 Indicators (calculated fresh every run via pandas-ta)
1. **RSI(14)** — normalized scoring table
2. **MACD** — crossover + histogram expansion
3. **Bollinger Bands** — %B position (near lower = long bias)
4. **ADX(14)** — trend strength filter (>25 = real trend, <20 = noise)
5. **Stochastic %K/%D** — oversold/overbought crossover for swing entries
6. **CCI(50) + CCI(5)** — divergence detection and confirmation
7. **ATR(14)** — dynamic stop at 1.5×ATR (never a flat % stop)
8. **EMA 20/50/200** — trend structure + golden cross detection
9. **Volume ratio** — vs 30-day average (1.5x+ confirms the move)
10. **Relative Strength vs SPY** — 30-day momentum vs market

### ML Layer
- XGBoost classifier trained on all 10 indicators
- TimeSeriesSplit cross-validation — zero lookahead bias
- Feature importance output — which indicators matter most per ticker
- ARIMA(2,1,2) 5-day price forecast with 95% confidence interval
- ML probability replaces hand-coded scoring — data-learned weights

### Macro Intelligence
- Buffett Indicator (Wilshire 5000 / GDP) — market valuation gauge
- Carry unwind 7-signal early warning system (0–21 score)
- USD/JPY 160 risk premium framework
- Intermarket flow: Crude → DXY → USD/JPY → Stocks
- Market regime: 5-class classification

### TPS Score Weights (ML-learned)
```
XGBoost probability  × 35%
ARIMA directional    × 15%
Stochastic           × 10%
RSI normalized       × 10%
FRED macro regime    × 20%
ADX trend bonus      × 10%

Edge = TPS − 50 | Trade if edge ≥ 10%
```

---

## Carry Unwind Early Warning

The most critical macro signal. Scored before every trade.

| Score | Risk Level | Action |
|-------|-----------|--------|
| 0–3 | 🟢 None | Trade normally |
| 4–7 | 🟡 Early warning | Reduce new positions 25% |
| 8–12 | 🟠 Elevated | No new longs — covered calls only |
| 13+ | 🔴 In progress | Reduce 25–50%, hedge immediately |

**7 signals scored:** USD/JPY behavior at 160, BOJ hawkish signals, Nikkei single-session drops, VIX velocity, BTC leading equities, cross-asset correlation break, BOJ meeting proximity.

**August 2024 reference:** Score was 8+ five days before Nikkei -12.4%, BTC -20%, VIX hit 65.

---

## USD/JPY 160 — Risk Premium Gauge

```
Stalls at 160, turns south, NO retest
→ Risk premium LEAVING the market
→ Carry unwind incoming → defensive mode

Breaks clean through 160 (close above + volume confirmed)
→ Risk premium still IN market → risk-on confirmed
```

---

## Current Portfolio

| Ticker | Shares | Avg Cost | Contracts |
|--------|--------|----------|-----------|
| TSLA   | 700    | $204.68  | 7 |
| AMD    | 400    | $129.86  | 4 |
| NVDA   | 200    | $125.94  | 2 |
| SOFI   | 2,000  | $21.09   | 20 |
| AMZU   | 200    | $40.44   | 2 |
| ROBN   | 100    | $45.00   | 1 |
| BTC    | 0.0120392 | $92,551 | — |
| ETH    | 0.40   | $2,829   | — |

> Update positions in `Main.py` POSITIONS dict, `signal_engine.py` PORTFOLIO dict, and `Claude.md-Trading_dashboard` together.

---

## API Keys

Keys are **not stored in this repo**. They live in Claude Project instructions only.
`Main.py` includes project defaults that can be overridden with environment variables.

APIs used:
- **Polygon.io** — OHLCV bars, options chain, VWAP
- **Alpha Vantage** — All 10 technical indicators (25 calls/day free tier)
- **Finnhub** — Live quotes, earnings calendar, insider sentiment, news
- **FRED** — VIX, yield curve, CPI, oil, gold, Buffett Indicator components
- **Anthropic** — Claude LLM (primary agent brain)

Free sources (no key needed):
- Crypto Fear & Greed, Nasdaq earnings calendar, CBOE P/C ratio, Market Chameleon, iborrowdesk, Capitol Trades, Whale Alert

---

## Alert System

**Telegram setup (5 minutes):**
1. Message @BotFather → `/newbot` → copy token
2. Message @userinfobot → copy chat ID
3. `export TELEGRAM_TOKEN=xxx && export TELEGRAM_CHAT_ID=yyy`

**Schedule:**
- 7:30 AM daily — morning brief with top trade + covered call income
- Every 2 hours — carry unwind monitor (alerts if score > 8)
- High conviction only — individual alerts fire when edge ≥ 15%

---

## ML Library Stack

| Library | Purpose | Status |
|---------|---------|--------|
| xgboost | Primary ML — direction prediction | ✅ Core |
| scikit-learn | Cross-validation, scaling, metrics | ✅ Core |
| statsmodels | ARIMA price forecasting | ✅ Core |
| pandas-ta | All 10 technical indicators | ✅ Core |
| vectorbt | Backtesting + optimization | ✅ Core |
| flask | Agent backend (Main.py) | ✅ Core |
| anthropic | Claude LLM client | ✅ Core |
| backtrader | Live trading integration | 🔜 Phase 2 |
| pyfolio-reloaded | Portfolio analytics | 🔜 Phase 2 |
| tensorflow/keras | LSTM sequence models | 🔜 Phase 3 |
| QuantLib | Precise options pricing | 🔜 Phase 3 |
| riskfolio-lib | VaR + stress testing | 🔜 Phase 3 |

---

## Roadmap

**Phase 1 — Signal Engine + Agent ✅ Done**
- [x] Main.py Flask agent — Claude-primary, 15 tools, trade journal
- [x] All 10 indicators, XGBoost ML, ARIMA forecasting
- [x] Carry unwind 7-signal system
- [x] Covered call income analyzer
- [x] Telegram morning briefs
- [x] Buffett Indicator + intermarket flow

**Phase 2 — Live Execution**
- [ ] Frontend React dashboard (connects to Main.py endpoints)
- [ ] Alpaca API (stocks + options execution)
- [ ] Semi-auto Telegram confirm mode
- [ ] 30-day paper trading validation
- [ ] Trade journal + PyFolio analytics

**Phase 3 — Multi-Asset**
- [ ] OANDA forex (USD/JPY live trades)
- [ ] Binance crypto bot
- [ ] IBKR futures (COT-based crude)
- [ ] LSTM sequence models
- [ ] QuantLib options pricing
- [ ] VaR dynamic risk management

---

## Related

- **my_AI_brain** (public) — general skill bundles: [github.com/holmesstephen067-glitch/my_AI_brain](https://github.com/holmesstephen067-glitch/my_AI_brain)

---

## Disclaimer

> Research and signal generation only — not financial advice.
> Verify all prices and premiums before executing.
> Options involve substantial risk.
> Past performance does not guarantee future results.
