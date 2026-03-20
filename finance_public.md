# Finance Bundle — Trading Intelligence
> Skills: Alpha Vantage · FRED · Polygon · Finnhub · EDGARTools · Hedge Fund Monitor · US Fiscal Data
> Trading: Intermarket Flow · Carry Unwind · XGBoost ML · Options · Covered Calls
> Usage: Loaded at session start for all financial data and trading tasks.
> API keys stored in Claude Project instructions — not in this file.

---

## TRADING SYSTEM QUICK REFERENCE

### Portfolio
| Ticker | Shares | Avg Cost | CC Contracts |
|--------|--------|----------|--------------|
| TSLA   | 700    | $204.68  | 7 |
| AMD    | 400    | $129.86  | 4 |
| NVDA   | 200    | $125.94  | 2 |
| SOFI   | 2,000  | $21.09   | 20 |
| AMZN   | 200    | $40.44   | 2 |
| HOOD   | 100    | $45.00   | 1 |
| BTC    | 0.0120392 | $92,551 | — |
| ETH    | 0.40   | $2,829   | — |

**Portfolio value:** $117,125 | **Buying power:** $24,514
**Open options:** PLTR BUY CALL — 1 contract, expires 1/21/2028 (LEAPS)

### API Keys
> Keys are stored in Claude Project instructions only — never hardcoded here.
> At session start Claude loads keys from project instructions automatically.

| API | Variable Name | Use |
|-----|--------------|-----|
| Polygon.io | `POLYGON_KEY` | Bars, options chain, VWAP, snapshot |
| Alpha Vantage | `AV_KEY` | RSI, MACD, CCI, ADX, ATR, EMA, STOCH, OVERVIEW |
| Finnhub | `FINNHUB_KEY` | Quotes, news, insider sentiment, earnings |
| FRED | `FRED_KEY` | VIX, yield curve, CPI, oil, GDP, Wilshire |

### Bot Files
```
signal_engine.py   — full 10-indicator stack + XGBoost + ARIMA
backtester.py      — VectorBT RSI optimizer + covered call backtest
alerts.py          — Telegram morning brief scheduler
READMEforstocks.md — full documentation + roadmap
```

---

## 1. Alpha Vantage — Market Data + All 10 Indicators
**Trigger:** "stock price", "technical indicators", "company fundamentals", "forex rate"
**Rate limit:** 25 calls/day on free tier — prioritize top 3–5 tickers per scan

```python
import requests
AV_KEY = "YOUR_AV_KEY"  # loaded from Claude Project instructions
BASE   = "https://www.alphavantage.co/query"

def av(function, **params):
    r = requests.get(BASE, params={"function": function, "apikey": AV_KEY, **params})
    return r.json()

# ── ALL 10 INDICATORS ─────────────────────────────────────────────────────────

# 1. RSI — normalized: <30=90pts, 30-40=70, 40-50=55, 50-60=45, 60-70=30, >70=10
rsi   = av("RSI",   symbol="NVDA", interval="daily", time_period=14, series_type="close")

# 2. MACD — bullish crossover = +signal, histogram expanding = momentum confirmed
macd  = av("MACD",  symbol="NVDA", interval="daily", series_type="close")

# 3. Bollinger Bands — %B < 0.2 = near lower ✅ | %B > 0.8 = near upper ❌
bb    = av("BBANDS", symbol="NVDA", interval="daily", time_period=20, series_type="close")

# 4. ADX — >25 = strong trend (trade) | <20 = ranging (use spreads/condors)
adx   = av("ADX",   symbol="NVDA", interval="daily", time_period=14)

# 5. Stochastic (NEW) — %K crosses %D below 20 = buy | above 80 = sell
stoch = av("STOCH", symbol="NVDA", interval="daily",
           fastkperiod=5, slowkperiod=3, slowdperiod=3)

# 6. CCI(50) + CCI(5) — below -100 + CCI(5) crossing up = strong buy
cci50 = av("CCI",   symbol="NVDA", interval="daily", time_period=50)
cci5  = av("CCI",   symbol="NVDA", interval="daily", time_period=5)

# 7. ATR — stop = entry - (1.5 × ATR). Never a flat % stop
atr   = av("ATR",   symbol="NVDA", interval="daily", time_period=14)

# 8. EMA 20/50/200 — price above all 3 = uptrend. Golden cross (50>200) = buy
ema20  = av("EMA",  symbol="NVDA", interval="daily", time_period=20,  series_type="close")
ema50  = av("EMA",  symbol="NVDA", interval="daily", time_period=50,  series_type="close")
ema200 = av("EMA",  symbol="NVDA", interval="daily", time_period=200, series_type="close")

# 9. Volume — via Polygon bars (see Section 3)

# 10. Relative Strength vs SPY — via Polygon 30-day returns (see Section 3)

# ── FUNDAMENTALS (Buffett lens — actual data) ─────────────────────────────────
# P/E, PEG, EPS growth, profit margins, analyst targets
overview = av("OVERVIEW", symbol="NVDA")
# Key fields: PERatio, PEGRatio, EPS, QuarterlyEarningsGrowthYOY,
#             ProfitMargin, AnalystTargetPrice, Beta

# Earnings calendar
earnings_cal = av("EARNINGS_CALENDAR", symbol="NVDA", horizon="3month")

# Forex — USD/JPY for carry unwind monitoring
fx_daily = av("FX_DAILY", from_symbol="USD", to_symbol="JPY")
fx_rate  = av("CURRENCY_EXCHANGE_RATE", from_currency="USD", to_currency="JPY")

# Stochastic RSI — more sensitive, better for crypto swing trades
stochrsi = av("STOCHRSI", symbol="BTCUSD", interval="daily",
              time_period=14, series_type="close", fastkperiod=5, fastdperiod=3)
```

**Stochastic signal rules:**
| Condition | Signal |
|-----------|--------|
| %K crosses above %D below 20 | 🔥 Strong buy — oversold reversal |
| %K crosses below %D above 80 | 🔥 Strong sell — overbought |
| Both below 20, turning up | Confirming buy |
| Stoch + CCI(5) both bullish | Double confirmation = upgrade size |

---

## 2. FRED — Federal Reserve Economic Data + Macro Snapshot
**Trigger:** "GDP", "unemployment", "inflation", "interest rates", "macro snapshot"

```python
import requests
FRED_KEY = "YOUR_FRED_KEY"  # loaded from Claude Project instructions
BASE     = "https://api.stlouisfed.org/fred"

def fred(series_id, limit=1):
    r = requests.get(f"{BASE}/series/observations", params={
        "series_id": series_id, "sort_order": "desc",
        "limit": limit, "api_key": FRED_KEY, "file_type": "json"
    })
    obs = r.json()["observations"]
    return float(obs[0]["value"]) if obs else None

# ── FULL MACRO SNAPSHOT (run every scan in this order) ───────────────────────
macro = {
    "vix":          fred("VIXCLS"),           # regime classifier
    "yield_curve":  fred("T10Y2Y"),            # inverted = recession risk 🟣
    "fed_rate":     fred("FEDFUNDS"),          # current Fed funds rate
    "cpi":          fred("CPIAUCSL"),          # inflation
    "core_cpi":     fred("CPILFESL"),          # core CPI
    "pce":          fred("PCEPI"),             # Fed's preferred inflation gauge
    "unemployment": fred("UNRATE"),            # jobs market
    "oil_wti":      fred("DCOILWTICO"),        # crude — LEADS stocks 1-3 sessions
    "gold":         fred("GOLDAMGBD228NLBM"),  # safe haven signal
    "mortgage":     fred("MORTGAGE30US"),      # relevant: SOFI, HOOD
    "nat_gas":      fred("DHHNGSP"),           # Iran war LNG export risk
    "wilshire5000": fred("WILL5000PR"),        # total market cap proxy
    "gdp":          fred("GDP"),               # GDP — Buffett Indicator denominator
}

# ── BUFFETT INDICATOR (NEW) ───────────────────────────────────────────────────
# < 80%  = undervalued | 80-100% = fair | 100-120% = slightly over
# > 120% = overvalued  | > 200%  = "playing with fire" — no new spec longs
buffett = (macro["wilshire5000"] / macro["gdp"]) * 100

# ── MACRO OUTPUT FORMAT ───────────────────────────────────────────────────────
# 🌡️ MACRO SNAPSHOT
# Fed rate:          X.XX%
# CPI:               X.X% YoY [rising/falling/stable]
# Yield curve:       +/-X.X bps [normal/flat/inverted 🔴]
# VIX:               XX.X [low/elevated/high/extreme]
# Oil WTI:           $XX.XX [war premium / normal]
# Gold:              $X,XXX [safe haven bid / neutral]
# Buffett Indicator: XXX% [undervalued/fair/overvalued/extreme 🔴]
# Macro regime:      [Risk-on / Neutral / Risk-off / Stagflation]

# ── REGIME CLASSIFICATION ─────────────────────────────────────────────────────
# SPY vs 200 EMA | VIX   | Yield Curve | Regime           | Strategy
# Above           | <20   | Positive    | 🟢 Bull Trend    | Buy calls / Sell puts
# Above           | 20-30 | Any         | 🟡 Choppy Bull   | Spreads / Covered calls
# Below           | 20-30 | Any         | 🟠 Bear/Sideways  | Buy puts / Credit spreads
# Any             | >30   | Any         | 🔴 Vol Spike     | Iron condors / Cash
# Any             | Any   | Negative    | 🟣 Recession     | Defensive
```

---

## 3. Polygon.io — Bars, Options, VWAP, Snapshot
**Trigger:** "live price", "options chain", "historical bars", "VWAP", "volume"

```python
import requests, pandas as pd
POLY_KEY = "YOUR_POLYGON_KEY"  # loaded from Claude Project instructions

def polygon_bars(ticker, days=400):
    end   = pd.Timestamp.today().strftime('%Y-%m-%d')
    start = (pd.Timestamp.today() - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
    url   = (f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/"
             f"{start}/{end}?adjusted=true&sort=asc&limit=500&apiKey={POLY_KEY}")
    r = requests.get(url, timeout=10)
    return r.json().get("results", [])

def polygon_snapshot(ticker):
    url = (f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/"
           f"tickers/{ticker}?apiKey={POLY_KEY}")
    return requests.get(url).json()

def options_chain(ticker, limit=50):
    url = (f"https://api.polygon.io/v3/snapshot/options/{ticker}"
           f"?limit={limit}&apiKey={POLY_KEY}")
    return requests.get(url).json()

# ── RELATIVE STRENGTH vs SPY (30-day) ────────────────────────────────────────
# RS > 1.0 = outperforming = long bias
# RS < 1.0 = underperforming = avoid long / short candidate
def calc_rs_spy(ticker_bars, spy_bars):
    ticker_ret = (ticker_bars[-1]["c"] - ticker_bars[-30]["c"]) / ticker_bars[-30]["c"]
    spy_ret    = (spy_bars[-1]["c"]    - spy_bars[-30]["c"])    / spy_bars[-30]["c"]
    return ticker_ret / spy_ret if spy_ret != 0 else 1.0

# ── EARNINGS CALENDAR (free — no key needed) ──────────────────────────────────
def nasdaq_earnings(date_str):
    url = f"https://api.nasdaq.com/api/calendar/earnings?date={date_str}"
    return requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).json()
```

**Options liquidity filter (mandatory — skip illiquid):**
```
Bid/ask spread < 5% of mid price ✅
Open interest > 500 ✅
Volume today > 100 ✅
Volume/OI > 1.0 = new positions opening = smart money signal ✅
```

---

## 4. Finnhub — Quotes, News, Insider, Earnings
**Trigger:** "live quote", "company news", "insider buying", "earnings date"

```python
import requests
FH_KEY = "YOUR_FINNHUB_KEY"  # loaded from Claude Project instructions

def finnhub(endpoint, **params):
    r = requests.get(f"https://finnhub.io/api/v1/{endpoint}",
                     params={"token": FH_KEY, **params})
    return r.json()

# Live quote — c=current, h=high, l=low, o=open, pc=prev close, dp=% change
quote   = finnhub("quote", symbol="TSLA")

# Company news — scan for earnings/buyback/CEO change within 7 days
news    = finnhub("company-news", symbol="NVDA",
                  **{"from": "2026-03-12", "to": "2026-03-19"})

# Insider sentiment — net buying = bullish Buffett signal
insider = finnhub("stock/insider-sentiment", symbol="TSLA")

# Earnings calendar — check ALL holdings before any trade
earnings = finnhub("calendar/earnings",
                   **{"from": "2026-03-19", "to": "2026-03-27"})

# Analyst consensus — strongBuy, buy, hold, sell, strongSell
recs    = finnhub("stock/recommendation", symbol="NVDA")

# ── EVENT DETECTION (overrides all other signals) ────────────────────────────
# Earnings within 5 days  → flag, no new entries
# Guidance change         → strong directional signal
# CEO/CFO change          → bearish until confirmed stable
# Share buyback           → bullish signal
# M&A target              → immediate spike play
# Dividend cut            → strong bearish
```

---

## 5. Intermarket Flow Analysis
**Trigger:** "market direction", "macro bias", "crude oil", "dollar", "intermarket"

### Flow Sequence — Always Run In This Order
```
WTI Crude → US Dollar (DXY) → USD/JPY 160 gauge → Stocks
```

```python
# Panel 1 — Crude Oil proxy (already fetched from FRED)
wti_spot = macro["oil_wti"]
uso_bars = polygon_bars("USO", days=90)

# Panel 2 — Dollar Index proxy
uup_bars = polygon_bars("UUP", days=90)

# Panel 3 — USD/JPY (Alpha Vantage forex)
usdjpy = av("FX_DAILY", from_symbol="USD", to_symbol="JPY")

# ── INTERMARKET SIGNAL MATRIX ─────────────────────────────────────────────────
# Crude ↑ + DXY ↓ = Risk-on  ✅ → long equities, full size
# Crude ↑ + DXY ↑ = Stagflation 🟠 → defensive, covered calls
# Crude ↓ + DXY ↑ = Deflationary ❌ → bearish equities
# Crude ↓ + DXY ↓ = Recession 🔴 → cash/bonds
# Both flat        = 🟡 Wait for crude to move first

# ── ECHO LAG TIMING ──────────────────────────────────────────────────────────
# 0–1 days since crude moved = BEST entry window ✅
# 2–3 days = echo in progress — enter if technicals confirm
# 4–5 days = likely priced in — reduce size 50%
# 5+ days  = wait for next crude inflection
```

**Output format:**
```
📊 INTERMARKET FLOW PANEL
Crude:       $XX.XX [trend] | echo age: X sessions
DXY/UUP:    $XX.XX [above/below 20 EMA]
USD/JPY:    XXX.XX [vs 160 level]
Correlation: [Inverse=normal / Both up=stagflation🟠 / Both down=recession🔴]
Echo status: [Early ✅ / On time / Late — wait]
─────────────────────────────────────────────────
Intermarket bias: [🟢 Risk-on / 🟡 Choppy / 🟠 Stagflation / 🔴 Risk-off]
Size override:    [Full / 50% — flow against / Skip]
```

---

## 6. USD/JPY 160 — Risk Premium Gauge
**Trigger:** "USD/JPY", "carry trade", "yen", "risk premium", "BOJ"

```python
# The single most important macro level to watch
# Fetch: av("FX_DAILY", from_symbol="USD", to_symbol="JPY")
# Or search: "USD/JPY rate today"

# SCENARIO A — Break clean through 160 (close above + volume confirmed)
# Risk premium IN market → risk-on confirmed → carry trade crowded
# Action: trade normally, watch for crowding

# SCENARIO B — Stalls at 160, turns south, NO retest
# Risk premium LEAVING market → carry unwind → DEFENSIVE MODE
# Action: tighten stops to 1×ATR, reduce positions, covered calls only

# Sector sensitivity to DXY rising (bad for your holdings):
# TSLA, NVDA, AMD  → NEGATIVE (growth stocks, global revenue)
# SOFI, AMZN, HOOD → NEGATIVE (dollar headwind)
# BTC/ETH          → STRONGLY NEGATIVE (inverse DXY relationship)
```

---

## 7. Carry Unwind Early Warning System
**Trigger:** "risk assessment", "carry unwind", "yen unwind", "market stress"

```python
# 7-signal scoring — run BEFORE every scan
# Score 0–3:   🟢 Trade normally
# Score 4–7:   🟡 Reduce new position sizes 25%
# Score 8–12:  🟠 No new longs — covered calls only
# Score 13+:   🔴 Defensive — reduce 25-50%, hedge immediately

def carry_unwind_score(macro):
    score = 0

    # Signal 1: USD/JPY at 160 wall
    # Stalling + heading south + no retest = +3
    # Search: "USD/JPY rate today"

    # Signal 2: BOJ hawkish signals
    # Search: "BOJ rate decision today"
    # Hawkish statement or hike = +3

    # Signal 3: Nikkei -2%+ single session
    # Search: "Nikkei 225 today"
    # -2%+ = +2 | below 50-day MA = +1

    # Signal 4: VIX velocity (level AND rate of change)
    vix = macro.get("vix", 20)
    if vix > 30:   score += 3
    elif vix > 25: score += 3
    elif vix > 20: score += 2

    # Signal 5: BTC leading equities down
    # BTC -5% while SPY flat = +3
    # Crypto F&G falling rapidly = +1

    # Signal 6: Cross-asset correlation break
    # BTC + Nikkei + SPY + crude all dropping = +3

    # Signal 7: BOJ meeting within 7 days = +1 (pre-emptive)
    # Search: "Bank of Japan meeting schedule"

    return score

# August 2024 template — reference pattern:
# Day -7: BOJ JGB yields drift up. USD/JPY stalls ~155.
# Day -4: Nikkei underperforms SPY. BTC -8% in 2 sessions.
# Day -2: USD/JPY breaks 152. VIX 19. BTC -6% more.
# Day -1: BOJ surprise hike 15bps. USD/JPY collapses through 150.
# Day 0:  VIX 65. Nikkei -12.4%. BTC -20%. SPY -4.25%.
# Score was 8+ five days before the crash.
```

---

## 8. XGBoost ML Signal Engine
**Trigger:** "ML prediction", "probability", "XGBoost", "train model", "TPS score"
**Full code:** signal_engine.py in this repo

```python
# Quick reference — key functions
from signal_engine import (
    fetch_polygon_bars,      # Polygon OHLCV data
    calculate_indicators,    # All 10 indicators via pandas-ta
    build_features,          # Feature matrix + target variable
    train_xgboost,           # XGBoost with TimeSeriesSplit CV
    predict_proba,           # P(price higher in 5 days)
    arima_forecast,          # ARIMA(2,1,2) 5-day price forecast
    calculate_tps,           # ML-enhanced TPS score
    analyze_covered_call,    # Covered call income calculator
    calculate_position_size, # ATR-based position sizing
    carry_unwind_score,      # 0-21 carry unwind risk score
    detect_regime,           # 5-class market regime classifier
    run_full_scan,           # Master scan — runs everything
    print_report,            # Formatted trade block output
)

# Full scan
scan = run_full_scan(tickers=["TSLA","AMD","NVDA","SOFI","AMZN","HOOD"])
print_report(scan)
```

**ML-powered TPS weights (data-learned — not hand-coded):**
```
XGBoost (all 10 indicators)  × 35%
ARIMA directional forecast   × 15%
Stochastic confirmation      × 10%
RSI normalized score         × 10%
FRED macro regime            × 20%
ADX trend bonus              × 10%

Edge = TPS − 50 (market implied probability)
Minimum edge to trade: 10%
Verdict: ≥15% = 🔥 HIGH CONVICTION | ≥10% = ✅ TRADE | ≥5% = ⚠️ BORDERLINE
```

---

## 9. Options Strategy Reference
**Trigger:** "options trade", "covered call", "put", "spread", "condor", "income"

### Strategy Labels
| Label | Regime | Capital |
|-------|--------|---------|
| BUY CALL | Bull trend | Premium paid |
| BUY PUT | Bear trend | Premium paid |
| SELL CALL (covered) | Any — income | $0 |
| SELL PUT (cash-secured) | Bull — want to own lower | Strike × 100 |
| DEBIT SPREAD (call) | Choppy bull | Net debit |
| DEBIT SPREAD (put) | Choppy bear | Net debit |
| CREDIT SPREAD (call) | Bear/sideways | Margin |
| IRON CONDOR | Sideways / vol spike | Margin |

### Covered Call Checklist
```
✅ Own 100+ shares
✅ Strike at or above avg cost basis — NEVER sell below cost
✅ Strike 5–10% OTM above current price
✅ Expiry 2–6 weeks out (optimal theta decay)
✅ Premium ≥ 1% of stock price (= 12%+ annualized)
✅ NOT within 5 days of earnings
✅ IVP > 40% preferred (elevated VIX = richer premiums)
```

### Breakout Authenticity Filter
**Genuine breakout requires 2 of 3 — never trade noise:**
1. Volume ≥ 1.5× 30-day average
2. ADX > 25 (real momentum)
3. Candle CLOSES beyond the level (wick touches do NOT count)

### Full Trade Block Format
```
Strategy:          [exact label]
Entry:             $XX.XX
Target:            $XX.XX (+X%)
Stop:              Entry − (1.5 × ATR) = $XX.XX
Position size:     $X,XXX (X% of $117,125)
Buying power used: $XXX of $24,514
Risk on trade:     $XXX (X% of portfolio)
R/R ratio:         X.X : 1
Timeframe:         X days / weeks
Correlation check: [safe / warning]
Carry unwind:      [score X/21]
Intermarket bias:  [Risk-on / Stagflation / Risk-off]
Breakout filter:   [2/3 confirmed ✅ / noise ❌]
```

---

## 10. Free Replacement Data Sources
**No new APIs needed — all free, no key required**

```python
# Max Pain / GEX pin zone
# Search: "market chameleon {TICKER} max pain {expiry}"

# Short interest (critical for SOFI squeeze monitoring)
# Search: "iborrowdesk {TICKER}"
# FINRA short volume: https://www.finra.org/finra-data/browse-catalog/short-sale-volume-data

# Congress trades — often a leading indicator
# Search: "capitol trades {TICKER} this week"
# SEC Form 4: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=4

# CBOE Put/Call ratio — market tide replacement
# Search: "CBOE equity put call ratio today"
# < 0.7 = bullish | > 1.3 = bearish

# COT Report — futures institutional positioning (free from CFTC)
# https://www.cftc.gov/dea/newcot/deahistfo.txt
# Commercials net short crude = crude likely to fall despite headlines

# Crypto whale alerts
# Search: "whale alert BTC today"
# Exchange inflows: search "glassnode BTC exchange inflows today"

# Seasonality
# Search: "equity clock {TICKER} seasonality"

# Earnings — 3 free sources, use all 3 to cross-check
nasdaq_url    = "https://api.nasdaq.com/api/calendar/earnings?date={date}"
av_earnings   = av("EARNINGS_CALENDAR", horizon="3month")  # uses AV key
finnhub_cal   = finnhub("calendar/earnings", **{"from": start, "to": end})  # uses FH key
```

---

## 11. EDGARTools — SEC Filings
**Trigger:** "SEC filing", "10-K", "10-Q", "insider trades", "13F"

```python
from edgar import set_identity, Company
set_identity("Your Name your@email.com")

co       = Company("NVDA")
tenk     = co.get_filings(form="10-K").latest()
form4    = co.get_filings(form="4").latest()     # insider trades
f13      = co.get_filings(form="13F-HR").latest()  # institutional holdings

obj      = tenk.obj()
income   = obj.financials.income_statement()
balance  = obj.financials.balance_sheet()

# Buffett lens via Alpha Vantage OVERVIEW
overview   = av("OVERVIEW", symbol="NVDA")
peg        = float(overview.get("PEGRatio", 99))    # < 1.0 = undervalued ✅
pe         = float(overview.get("PERatio", 99))     # vs sector avg
eps_growth = overview.get("QuarterlyEarningsGrowthYOY")  # > 10% ✅
margin     = float(overview.get("ProfitMargin", 0)) # expanding ✅
```

---

## 12. Hedge Fund Monitor — OFR API
**Trigger:** "hedge fund leverage", "systemic risk", "repo volumes"

```python
import requests, pandas as pd
BASE = "https://data.financialresearch.gov/hf/v1"

r = requests.get(f"{BASE}/series/timeseries", params={
    "mnemonic": "FPF-ALLQHF_LEVERAGERATIO_GAVWMEAN",
    "start_date": "2020-01-01"
}).json()
df = pd.DataFrame(r, columns=["date", "value"])
# Rising hedge fund leverage + VIX spike = forced unwind risk
# Cross-reference with carry unwind score
```

---

## 13. US Fiscal Data — Treasury API
**Trigger:** "national debt", "treasury rates", "government spending"

```python
BASE = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"

debt = requests.get(f"{BASE}/v2/accounting/od/debt_to_penny",
    params={"sort": "-record_date", "page[size]": 1}).json()
print(f"Total debt: ${float(debt['data'][0]['tot_pub_debt_out_amt']):,.0f}")
```

---

## Session Start Checklist — Run Every Time In This Order

```
Step 0: Carry unwind score (7 signals, 0–21)
        → If score ≥ 8: no new longs, covered calls only
        → If score ≥ 13: defensive mode

Step 1: Buffett Indicator (WILL5000PR / GDP × 100)
        → If > 200%: no new speculative longs regardless of other signals

Step 2: Full FRED macro snapshot
        → VIX, yield curve, CPI, oil, gold, fed rate

Step 3: Intermarket flow panel
        → Crude → DXY → USD/JPY 160 → stocks echo timing

Step 4: Market regime classification
        → Bull / Choppy / Bear / Vol Spike / Recession

Step 5: Earnings calendar (3 sources)
        → Flag any holding with earnings within 5 days

Step 6: Per-ticker analysis
        → All 10 indicators + XGBoost ML + ARIMA forecast

Step 7: Covered call income scan
        → All 6 eligible positions, weekly vs monthly comparison

Step 8: Portfolio risk snapshot
        → Total deployed, correlation clusters, buying power remaining
```

---

## Disclaimer
> Research and signal generation only — not financial advice.
> API keys stored in Claude Project instructions only — not in this file.
> Verify all prices and premiums before executing.
> Options involve substantial risk.
> Past performance does not guarantee future results.
