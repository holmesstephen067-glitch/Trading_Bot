"""
🚀 DETERMINISTIC TRADING SYSTEM — CLEAN ARCHITECTURE
Pipeline enforced:
1. Data → 2. Validation → 3. Features → 4. Regime → 5. Decision → 6. Risk
"""

from flask import Flask, request, jsonify
import requests
import os
from datetime import datetime

# ✅ CORE ENGINES
from signal_engine import generate_trade_signal, options_strategy_selector
from macro_engine import build_macro_context

app = Flask(__name__)

# =========================
# 🔐 API KEYS
# =========================
POLYGON_KEY = os.environ.get("POLYGON_KEY")
AV_KEY      = os.environ.get("AV_KEY")
FRED_KEY    = os.environ.get("FRED_KEY")
FINNHUB_KEY = os.environ.get("FINNHUB_KEY")

# =========================
# 📊 DATA LAYER
# =========================

def get_price(ticker):
    url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_KEY}"
    data = requests.get(url).json()
    return data.get("c")


def get_indicator(function, ticker):
    url = (
        f"https://www.alphavantage.co/query?"
        f"function={function}&symbol={ticker}&interval=daily"
        f"&time_period=14&apikey={AV_KEY}"
    )
    return requests.get(url).json()


# =========================
# 🧠 FEATURE ENGINEERING
# =========================

def compute_rsi(data):
    try:
        values = list(data["Technical Analysis: RSI"].values())
        return float(values[0]["RSI"])
    except:
        return None


def compute_atr(data):
    try:
        values = list(data["Technical Analysis: ATR"].values())
        return float(values[0]["ATR"])
    except:
        return None


# =========================
# 🚀 MASTER PIPELINE
# =========================

def run_pipeline(ticker):
    # ----------------------------------
    # 1. DATA INGESTION
    # ----------------------------------
    price = get_price(ticker)
    rsi_data = get_indicator("RSI", ticker)
    atr_data = get_indicator("ATR", ticker)

    # ----------------------------------
    # 2. VALIDATION
    # ----------------------------------
    if not price:
        return {"error": "No price data"}

    rsi = compute_rsi(rsi_data)
    atr = compute_atr(atr_data)

    if rsi is None or atr is None:
        return {"error": "Indicator data missing"}

    # ----------------------------------
    # 3. MACRO + REGIME
    # ----------------------------------
    macro = build_macro_context(AV_KEY, FRED_KEY)
    carry_score = macro["carry"]["score"]

    vix = macro["carry"]["details"].get("vix", 20)

    # ----------------------------------
    # 4. DECISION ENGINE
    # ----------------------------------
    signal = generate_trade_signal(
        ticker=ticker,
        price=price,
        atr=atr,
        rsi=rsi,
        carry_score=carry_score,
        vix=vix
    )

    # ----------------------------------
    # 5. OPTIONS LAYER
    # ----------------------------------
    options = options_strategy_selector(ticker, price, None)

    return {
        "timestamp": datetime.now().isoformat(),
        "ticker": ticker,
        "price": price,
        "features": {
            "rsi": rsi,
            "atr": atr,
        },
        "macro": macro,
        "signal": signal,
        "options": options
    }


# =========================
# 🌐 API ENDPOINTS
# =========================

@app.route("/trade", methods=["POST"])
def trade():
    data = request.get_json()
    ticker = data.get("ticker")

    result = run_pipeline(ticker)

    return jsonify(result)


@app.route("/")
def home():
    return jsonify({
        "status": "running",
        "system": "deterministic_trading_engine_v2"
    })


# =========================
# 🚀 RUN
# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)