# 📈 Trading Bot — Signal Engine for Stocks, Options & Crypto

Personal AI-powered trading signal engine built on a full 10-indicator stack, XGBoost ML predictions, ARIMA forecasting, carry unwind detection, and intermarket flow analysis (Crude → DXY → USD/JPY → Stocks).

Part of the `my_AI_brain` system. For the full repo overview see:
```
https://raw.githubusercontent.com/holmesstephen067-glitch/my_AI_brain/refs/heads/main/README.md
```

---

## Raw URLs — This Bot

| File | Raw URL |
|------|---------|
| signal_engine.py | `https://raw.githubusercontent.com/holmesstephen067-glitch/my_AI_brain/refs/heads/main/trading_bot/signal_engine.py` |
| READMEforstocks.md | `https://raw.githubusercontent.com/holmesstephen067-glitch/my_AI_brain/refs/heads/main/trading_bot/READMEforstocks.md` |
| backtester.py | `https://raw.githubusercontent.com/holmesstephen067-glitch/my_AI_brain/refs/heads/main/trading_bot/backtester.py` |
| alerts.py | `https://raw.githubusercontent.com/holmesstephen067-glitch/my_AI_brain/refs/heads/main/trading_bot/alerts.py` |
| requirements.txt | `https://raw.githubusercontent.com/holmesstephen067-glitch/my_AI_brain/refs/heads/main/trading_bot/requirements.txt` |

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
# 1. Install dependencies
pip install -r trading_bot/requirements.txt

# 2. Run full morning scan on your portfolio
python trading_bot/signal_engine.py

# 3. Save results to JSON
python trading_bot/signal_engine.py --save

# 4. Scan specific tickers only
python trading_bot/signal_engine.py --tickers TSLA NVDA AMD

# 5. Optimize RSI thresholds for a ticker
python trading_bot/backtester.py TSLA

# 6. Test Telegram connection
export TELEGRAM_TOKEN=your_token_here
export TELEGRAM_CHAT_ID=your_chat_id_here
python trading_bot/alerts.py test

# 7. Start scheduled 7:30 AM daily briefs
python trading_bot/alerts.py
```

---

## What signal_engine.py Does

### Data Layer
- Fetches 400 days of daily OHLCV from Polygon.io for each ticker
- Live quotes from Finnhub
- Full FRED macro suite — VIX, yield curve, CPI, oil, gold, unemployment
- Buffett Indicator (Wilshire 5000 / GDP) from FRED
- Crypto Fear & Greed from alternative.me

### All 10 Indicators (calculated fresh every run via pandas-ta)
1. **RSI(14)** — normalized scoring table (RSI<30 = score 90, RSI>70 = score 10)
2. **MACD** — crossover detection + histogram expansion momentum check
3. **Bollinger Bands** — %B position (near lower = long bias, near upper = overbought)
4. **ADX(14)** — trend strength filter (>25 = real trend, <20 = noise/ranging)
5. **Stochastic %K/%D** — oversold/overbought crossover signals for swing entries
6. **CCI(50) + CCI(5)** — divergence detection and signal confirmation
7. **ATR(14)** — dynamic stop placement at 1.5×ATR (never a flat % stop)
8. **EMA 20/50/200** — trend structure + golden cross detection
9. **Volume ratio** — today vs 30-day average (1.5x+ = confirms move)
10. **Relative Strength vs SPY** — 30-day momentum vs market

### ML Layer
- **XGBoost classifier** trained on all 10 indicators as features
- **TimeSeriesSplit cross-validation** — no lookahead bias, ever
- **Feature importance** output — tells you which indicators matter most per ticker
- **ARIMA(2,1,2) forecast** — 5-day price direction with 95% confidence interval
- **ML probability replaces hand-coded TPS** — data-learned weights, not guesses

### Macro Intelligence
- **Buffett Indicator** — market cap / GDP — overvaluation gauge
- **Carry unwind early warning** — 7-signal scoring system (0–21)
- **USD/JPY 160 framework** — risk premium gauge (Scenario A vs B)
- **Market regime** — 5-class classification (Bull / Choppy / Bear / Vol Spike / Recession)
- **Intermarket flow** — Crude → DXY → USD/JPY → Stocks echo timing

### Trade Output Per Ticker
- Covered call analysis — exact strike, premium estimate, annualized yield, total income
- Position sizing via ATR-based risk management (1.5% portfolio risk max)
- Full TPS score with explicit edge calculation vs market-implied probability
- ARIMA 5-day forecast with direction and confidence interval
- Feature importance — which signals drove the XGBoost prediction

---

## Portfolio Configuration (signal_engine.py)

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
BUYING_POWER    = 24514
```

Update these values directly in `signal_engine.py` when positions change.

---

## API Keys (already configured in signal_engine.py)

| API | Key | Use |
|-----|-----|-----|
| Polygon.io | zgI7pxcaymBCYt8NsPEp35FCJvhAksXz | OHLCV bars, options chain, VWAP |
| Alpha Vantage | PXFEPVSDRGKWVSYU | All 10 technical indicators (25 calls/day) |
| Finnhub | d6r2q5pr01qgdhqcut90d6r2q5pr01qgdhqcut9g | Live quotes, earnings, insider, news |
| FRED | 1897439c3462a95e33dfa3e739f69ced | VIX, yield curve, CPI, oil, Buffett Indicator |
| alternative.me | No key needed | Crypto Fear & Greed index |

---

## ML Library Stack

| Library | Purpose | Tier |
|---------|---------|------|
| xgboost | Primary ML model — direction prediction | ✅ Core |
| scikit-learn | Cross-validation, scaling, metrics | ✅ Core |
| statsmodels | ARIMA price forecasting | ✅ Core |
| pandas-ta | All 10 technical indicators | ✅ Core |
| vectorbt | Backtesting + parameter optimization | ✅ Core |
| backtrader | Live trading integration | 🔜 Phase 2 |
| pyfolio-reloaded | Portfolio performance analytics | 🔜 Phase 2 |
| tensorflow/keras | LSTM sequence models for crypto/forex | 🔜 Phase 3 |
| QuantLib | Precise options pricing (Black-Scholes) | 🔜 Phase 3 |
| riskfolio-lib | VaR, Expected Shortfall, stress testing | 🔜 Phase 3 |

---

## Alert System (alerts.py)

### Setup Telegram Bot (5 minutes)
1. Open Telegram → message **@BotFather** → type `/newbot`
2. Follow the steps → copy the API token
3. Message **@userinfobot** → copy your chat ID
4. Set environment variables:
```bash
export TELEGRAM_TOKEN=your_bot_token_here
export TELEGRAM_CHAT_ID=your_chat_id_here
```

### Alert Schedule
- **7:30 AM daily** — Morning brief with top trade, covered call income, carry unwind score
- **Every 2 hours** — Carry unwind monitor (alerts immediately if score > 8)
- **High conviction only** — Individual trade alerts only fire when edge ≥ 15%

### Alert Thresholds (configurable in alerts.py)
```python
MIN_EDGE_TO_ALERT = 10    # TPS edge % to surface a trade
MIN_CC_YIELD      = 12    # Annualized covered call yield % to surface
MAX_CARRY_SCORE   = 8     # Carry unwind score that triggers immediate alert
```

---

## Carry Unwind Early Warning System

The most important macro signal in the system. Scores 7 inputs on a 0–21 scale.

| Score | Risk Level | Action |
|-------|-----------|--------|
| 0–3 | 🟢 No risk | Trade normally |
| 4–7 | 🟡 Early warning | Reduce new position sizes 25% |
| 8–12 | 🟠 Elevated | No new longs — covered calls only |
| 13+ | 🔴 In progress | Reduce all positions 25–50%, hedge immediately |

**The 7 signals scored:**
1. USD/JPY behavior at the 160 level (stalling vs breakthrough)
2. BOJ hawkish statements or rate hikes
3. Nikkei 225 single-session drops (-2%+)
4. VIX velocity spike (level AND rate of change)
5. BTC leading equities down (-5%+ while SPY flat)
6. Cross-asset correlation break (BTC + Nikkei + SPY + crude all dropping)
7. BOJ meeting within 7 days (pre-emptive caution)

**August 2024 reference:** Score was 8+ five days before Nikkei -12.4%, BTC -20%, VIX spiked to 65.

---

## USD/JPY 160 — Risk Premium Gauge

The single most important macro level to watch.

```
USD/JPY approaching 160 → dollar softens preemptively → contained risk premium

USD/JPY stalls at 160, turns south, NO retest
→ Risk premium LEAVING the market
→ Yen carry trade unwinding
→ Defensive mode on all positions

USD/JPY breaks clean through 160 (close above + volume confirmed)
→ Risk premium still IN the market
→ Risk-on confirmed
→ Carry trade still crowded
```

---

## Backtester (backtester.py)

### RSI Threshold Optimization
Tests all entry/exit RSI combinations (20–45 entry, 55–80 exit) on 2 years of data.
Answers: "Is RSI 30/70 actually optimal for TSLA, or is 35/65 better?"

```bash
python trading_bot/backtester.py TSLA
```

Output shows top 5 combinations ranked by Sharpe ratio with win rate and max drawdown.

### Covered Call Backtest
Simulates 12 months of monthly call selling on any position.
Shows: total income collected, average monthly income, assignment frequency, combined return.

---

## Alert Modes

### Mode 1 — Signal Only (Default — Recommended First)
Bot runs full analysis, sends Telegram brief, you execute manually.
Zero additional risk beyond your own trading decisions.

### Mode 2 — Semi-Auto (Coming in Phase 2)
Bot identifies trade, sends Telegram alert with full details.
You reply YES or NO. Bot executes only after confirmation.

### Mode 3 — Full Auto (Phase 2+)
Bot executes without input. Hard-coded safety rules always enforced:
- Never exceeds 5% position size
- Never exceeds 20% total portfolio risk
- Carry unwind score > 15 = covered calls only
- Buffett Indicator > 200% = no new long positions
- 3 consecutive losses = Defensive Mode, no new trades

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

**Phase 3 — Advanced ML + Multi-Asset**
- [ ] LSTM sequence model for crypto and forex
- [ ] QuantLib precise options pricing
- [ ] XGBoost regime classifier (replaces manual regime table)
- [ ] VaR dynamic risk management (riskfolio-lib)
- [ ] OANDA forex integration (USD/JPY live trades)
- [ ] Binance crypto bot (BTC/ETH swing trades)
- [ ] IBKR futures (COT-based crude signals)

---

## Disclaimer

> Research and signal generation only — not financial advice.
> All data from Polygon.io, Finnhub, Alpha Vantage, and FRED.
> Verify all prices and premiums before executing.
> Options involve substantial risk.
> Past performance does not guarantee future results.
