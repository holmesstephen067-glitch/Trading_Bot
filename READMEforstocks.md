# Trading Bot — Signal Engine for Stocks, Options & Crypto

Personal AI-powered trading signal engine built on a full 10-indicator stack, XGBoost ML predictions, ARIMA forecasting, carry unwind detection, and intermarket flow analysis (Crude → DXY → USD/JPY → Stocks).

---

## File Structure

```
trading_bot/
├── signal_engine.py    — Core brain: data fetch, indicators, XGBoost, TPS, report
├── backtester.py       — VectorBT strategy optimization + covered call backtest
├── alerts.py           — Telegram morning brief scheduler + carry unwind monitor
├── requirements.txt    — All Python dependencies
└── READMEforstocks.md  — This file
```

---

## Quick Start

```bash
# Install dependencies
pip install -r trading_bot/requirements.txt

# Full morning scan
python trading_bot/signal_engine.py

# Save results to JSON
python trading_bot/signal_engine.py --save

# Scan specific tickers
python trading_bot/signal_engine.py --tickers TSLA NVDA AMD

# Optimize RSI thresholds for a ticker
python trading_bot/backtester.py TSLA

# Test Telegram connection
export TELEGRAM_TOKEN=your_token_here
export TELEGRAM_CHAT_ID=your_chat_id_here
python trading_bot/alerts.py test

# Start scheduled 7:30 AM daily briefs
python trading_bot/alerts.py
```

---

## Portfolio Configuration

Update these values in `signal_engine.py` when positions change.

```python
PORTFOLIO = {
    "TSLA": {"shares": 700,  "avg_cost": 204.68, "contracts": 7},
    "AMD":  {"shares": 400,  "avg_cost": 129.86, "contracts": 4},
    "NVDA": {"shares": 200,  "avg_cost": 125.94, "contracts": 2},
    "SOFI": {"shares": 2000, "avg_cost": 21.09,  "contracts": 20},
    "AMZU": {"shares": 200,  "avg_cost": 40.44,  "contracts": 2},
    "ROBN": {"shares": 100,  "avg_cost": 45.00,  "contracts": 1},
}

PORTFOLIO_VALUE = 117125
BUYING_POWER    = 24514   # Update after every trade
```

---

## API Keys

| API | Key | Use |
|-----|-----|-----|
| Polygon.io | `zgI7pxcaymBCYt8NsPEp35FCJvhAksXz` | OHLCV bars, options chain, VWAP |
| Alpha Vantage | `PXFEPVSDRGKWVSYU` | All 10 technical indicators (25 calls/day) |
| Finnhub | `d6r2q5pr01qgdhqcut90d6r2q5pr01qgdhqcut9g` | Live quotes, earnings, insider, news |
| FRED | `1897439c3462a95e33dfa3e739f69ced` | VIX, yield curve, CPI, oil, Buffett Indicator |
| alternative.me | No key needed | Crypto Fear & Greed index |

---

## What signal_engine.py Does

### Data Layer
- 400 days of daily OHLCV from Polygon.io per ticker
- Live quotes from Finnhub
- Full FRED macro suite — VIX, yield curve, CPI, oil, gold, unemployment
- Buffett Indicator (Wilshire 5000 / GDP) from FRED
- Crypto Fear & Greed from alternative.me

### All 10 Indicators (via pandas-ta)
1. RSI(14) — normalized scoring (< 30 = score 90, > 70 = score 10)
2. MACD — crossover + histogram expansion
3. Bollinger Bands — %B position
4. ADX(14) — trend strength (> 25 = real trend, < 20 = noise)
5. Stochastic %K/%D — oversold/overbought crossover signals
6. CCI(50) + CCI(5) — divergence detection and confirmation
7. ATR(14) — dynamic stop at 1.5×ATR
8. EMA 20/50/200 — trend structure + golden cross
9. Volume ratio — today vs 30-day average
10. Relative Strength vs SPY — 30-day momentum

### ML Layer
- XGBoost classifier trained on all 10 indicators (TimeSeriesSplit CV — no lookahead)
- ARIMA(2,1,2) — 5-day price forecast with 95% confidence interval
- Feature importance output per ticker
- TPS score = XGBoost (35%) + ARIMA (15%) + Stoch (10%) + RSI (10%) + Macro (20%) + ADX bonus (10%)
- Edge = TPS − Market-Implied Probability (Polygon ATM delta × 100)
- Minimum edge to trade: 10%

### Macro Intelligence
- Buffett Indicator — market cap / GDP
- Carry unwind early warning — 7-signal scoring (0–21)
- USD/JPY 160 framework — Scenario A (risk-on) vs B (risk exiting)
- Market regime — 5-class (Bull / Choppy / Bear / Vol Spike / Recession)
- Intermarket flow — Crude → DXY → USD/JPY → Stocks echo timing

---

## Carry Unwind Early Warning

| Score | Risk Level | Action |
|-------|-----------|--------|
| 0–3 🟢 | None | Trade normally |
| 4–7 🟡 | Early | Reduce new sizes 25% |
| 8–12 🟠 | Elevated | No new longs — covered calls only |
| 13+ 🔴 | In progress | Reduce all positions 25–50%, hedge immediately |

**7 signals scored:**
1. USD/JPY behavior at 160 (stalling/no retest = +3 | clean break = 0)
2. BOJ hawkish statement or rate hike (+3)
3. Nikkei −2%+ single session (+2) | below 50d MA (+1)
4. VIX velocity spike — > 30 (+3) | 25–30 (+3) | 20–25 (+2)
5. BTC −5%+ while SPY flat (+3) | F&G falling rapidly (+1)
6. BTC + Nikkei + SPY + crude all dropping simultaneously (+3)
7. BOJ meeting within 7 days (+1)

August 2024 reference: Score hit 8+ five days before Nikkei −12.4%, BTC −20%, VIX spiked to 65.

---

## Alert System (alerts.py)

### Setup Telegram (5 minutes)
1. Message @BotFather → `/newbot` → copy API token
2. Message @userinfobot → copy chat ID
3. Set environment variables:
```bash
export TELEGRAM_TOKEN=your_bot_token_here
export TELEGRAM_CHAT_ID=your_chat_id_here
```

### Alert Schedule
- 7:30 AM daily — morning brief: top trade, covered call income, carry unwind score
- Every 2 hours — carry unwind monitor (immediate alert if score > 8)
- High conviction only — trade alerts fire when edge ≥ 15%

### Thresholds (configurable in alerts.py)
```python
MIN_EDGE_TO_ALERT = 10    # TPS edge % to surface a trade
MIN_CC_YIELD      = 12    # Annualized covered call yield % to surface
MAX_CARRY_SCORE   = 8     # Carry unwind score that triggers immediate alert
```

---

## Backtester (backtester.py)

### RSI Threshold Optimization
Tests all entry/exit RSI combinations (20–45 entry, 55–80 exit) on 2 years of data.
Output: top 5 combinations ranked by Sharpe ratio with win rate and max drawdown.

```bash
python trading_bot/backtester.py TSLA
```

### Covered Call Backtest
Simulates 12 months of monthly call selling on any position.
Output: total income collected, average monthly income, assignment frequency, combined return.

---

## Roadmap

**Phase 1 — Signal Engine (Current)**
- [x] All 10 indicators via pandas-ta
- [x] XGBoost ML predictions with TimeSeriesSplit CV
- [x] ARIMA 5-day price forecasting
- [x] Carry unwind 7-signal early warning
- [x] Covered call income analyzer
- [x] Telegram morning briefs at 7:30 AM
- [x] Buffett Indicator macro overlay
- [x] Intermarket flow framework

**Phase 2 — Live Execution**
- [ ] Alpaca API integration (stocks + options)
- [ ] Semi-auto mode (Telegram confirm before execute)
- [ ] 30-day paper trading validation
- [ ] Trade journal auto-update
- [ ] PyFolio performance analytics

**Phase 3 — Advanced ML**
- [ ] LSTM sequence model for crypto and forex
- [ ] QuantLib precise options pricing
- [ ] XGBoost regime classifier
- [ ] VaR dynamic risk management (riskfolio-lib)
- [ ] OANDA forex integration (USD/JPY live trades)
- [ ] Binance crypto bot (BTC/ETH swing trades)
- [ ] IBKR futures (COT-based crude signals)

---

## ML Library Stack

| Library | Purpose |
|---------|---------|
| xgboost | Primary ML model |
| scikit-learn | Cross-validation, scaling, metrics |
| statsmodels | ARIMA forecasting |
| pandas-ta | All 10 technical indicators |
| vectorbt | Backtesting + optimization |

---

> Research and signal generation only — not financial advice. Verify all prices before executing. Options involve substantial risk. Past performance does not guarantee future results.
