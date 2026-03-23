"""
Deterministic AI Trading Bot (LLM = explanation only)
"""

from flask import Flask, request, jsonify
import requests
import os
import sqlite3
import json
import re
from datetime import datetime, timedelta
from core.decision_engine import (
    generate_trade_signal,
    options_strategy_selector
)
app = Flask(__name__)

# =========================
# 🔐 API KEYS (UNCHANGED)
# =========================
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
OPENAI_API_KEY    = os.environ.get("OPENAI_API_KEY")
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY")

POLYGON_KEY = os.environ.get("POLYGON_KEY")
AV_KEY      = os.environ.get("AV_KEY")
FRED_KEY    = os.environ.get("FRED_KEY")
FINNHUB_KEY = os.environ.get("FINNHUB_KEY")

# =========================
# 📋 CONFIG
# =========================
PORTFOLIO_VALUE = 117125
BUYING_POWER    = 24514

MAX_POSITION_PCT = 0.05

# =========================
# 🗄️ DB
# =========================
conn = sqlite3.connect("trading_memory.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    ticker TEXT,
    action TEXT,
    entry REAL,
    stop REAL,
    target REAL
)
""")
conn.commit()

# =========================
# 🧰 TOOL WRAPPERS (UNCHANGED APIs)
# =========================

def finnhub_quote(ticker):
    url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_KEY}"
    return requests.get(url).json()

def polygon_snapshot(ticker):
    url = f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}?apiKey={POLYGON_KEY}"
    return requests.get(url).json()

def av_rsi(ticker):
    url = f"https://www.alphavantage.co/query?function=RSI&symbol={ticker}&interval=daily&time_period=14&apikey={AV_KEY}"
    return requests.get(url).json()

def fred_vix():
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id=VIXCLS&api_key={FRED_KEY}&file_type=json"
    return requests.get(url).json()

# =========================
# 🧠 DETERMINISTIC ENGINE
# =========================

def compute_rsi(data):
    try:
        values = list(data["Technical Analysis: RSI"].values())
        return float(values[0]["RSI"])
    except:
        return 50

def get_price(quote):
    return quote.get("c", 0)

def regime(vix, rsi):
    if vix > 30:
        return "high_vol"
    if rsi > 60:
        return "bullish"
    if rsi < 40:
        return "bearish"
    return "neutral"

def position_size(price):
    return round((PORTFOLIO_VALUE * MAX_POSITION_PCT) / price, 2)

def stop_loss(price):
    return price * 0.97

def take_profit(price):
    return price * 1.06

def decision_engine(ticker):
    quote = finnhub_quote(ticker)
    price = get_price(quote)

    rsi_data = av_rsi(ticker)
    rsi = compute_rsi(rsi_data)

    vix_data = fred_vix()
    try:
        vix = float(vix_data["observations"][-1]["value"])
    except:
        vix = 20

    current_regime = regime(vix, rsi)

    action = "HOLD"

    if current_regime == "bullish" and rsi < 40:
        action = "BUY"
    elif current_regime == "bearish" and rsi > 60:
        action = "SELL"

    return {
        "ticker": ticker,
        "price": price,
        "rsi": rsi,
        "vix": vix,
        "regime": current_regime,
        "action": action,
        "position_size": position_size(price),
        "stop_loss": stop_loss(price),
        "take_profit": take_profit(price)
    }

# =========================
# 🤖 LLM (EXPLANATION ONLY)
# =========================

def call_claude(prompt):
    if not ANTHROPIC_API_KEY:
        return None
    try:
        res = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=20
        )
        return res.json()["content"][0]["text"]
    except:
        return None

def explain(signal):
    prompt = f"Explain this trade decision clearly:\n{json.dumps(signal, indent=2)}"
    return call_claude(prompt)

# =========================
# 🌐 ENDPOINTS
# =========================

@app.route("/brain", methods=["POST"])
def brain():
    data = request.get_json()
    ticker = data.get("ticker")

    quote = tool_finnhub_quote(ticker)
    price = quote.get("c")

    atr_data = tool_av_indicator("ATR", ticker)
    atr = 1  # fallback (we’ll refine this next)

    rsi_data = tool_av_indicator("RSI", ticker)
    rsi = 50  # parse properly next step

    carry_data = tool_carry_unwind_score()
    carry_score = carry_data.get("score", 0)

    vix_data = tool_fred_series("VIXCLS")
    vix = float(vix_data.get("value", 20))

    signal = generate_trade_signal(
        ticker, price, atr, rsi, carry_score, vix
    )

    options = options_strategy_selector(ticker, price, PORTFOLIO)

    return jsonify({
        "signal": signal,
        "options": options,
        "carry": carry_data
    })

@app.route("/positions")
def positions():
    results = {}
    for t in POSITIONS:
        results[t] = decision_engine(t)
    return jsonify(results)

@app.route("/")
def home():
    return jsonify({
        "status": "running",
        "mode": "deterministic",
        "portfolio_value": PORTFOLIO_VALUE
    })

# =========================
# 🚀 RUN
# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)