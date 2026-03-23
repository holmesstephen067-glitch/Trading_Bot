from flask import Flask, request, jsonify
import requests
import os

from core.decision_engine import generate_trade_signal, options_strategy_selector
from core.feature_engine import compute_rsi, compute_atr, compute_ema, compute_macd
from core.macro_engine import build_macro_context

app = Flask(__name__)

AV_KEY = os.environ.get("AV_KEY")
FINNHUB_KEY = os.environ.get("FINNHUB_KEY")

# =========================
# DATA
# =========================

def get_price(ticker):
    url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_KEY}"
    return requests.get(url).json().get("c")


def av_indicator(function, ticker, period=14):
    url = f"https://www.alphavantage.co/query?function={function}&symbol={ticker}&interval=daily&time_period={period}&apikey={AV_KEY}"
    return requests.get(url).json()


# =========================
# PIPELINE
# =========================

def run_pipeline(ticker):
    # 1. DATA
    price = get_price(ticker)

    rsi_data = av_indicator("RSI", ticker)
    atr_data = av_indicator("ATR", ticker)
    macd_data = av_indicator("MACD", ticker)

    ema20 = av_indicator("EMA", ticker, 20)
    ema50 = av_indicator("EMA", ticker, 50)
    ema200 = av_indicator("EMA", ticker, 200)

    # 2. FEATURES
    rsi = compute_rsi(rsi_data)
    atr = compute_atr(atr_data)
    macd = compute_macd(macd_data)

    ema20 = compute_ema(ema20)
    ema50 = compute_ema(ema50)
    ema200 = compute_ema(ema200)

    # 3. MACRO
    macro = build_macro_context(AV_KEY, os.environ.get("FRED_KEY"))
    carry_score = macro["carry"]["score"]
    vix = macro["carry"]["details"].get("vix", 20)

    # 4. DECISION
    signal = generate_trade_signal(
        ticker, price, atr, rsi, macd,
        ema20, ema50, ema200,
        carry_score, vix
    )

    # 5. OPTIONS
    options = options_strategy_selector(ticker, price, None)

    return {
        "ticker": ticker,
        "price": price,
        "features": {
            "rsi": rsi,
            "atr": atr,
            "macd": macd,
            "ema20": ema20,
            "ema50": ema50,
            "ema200": ema200
        },
        "macro": macro,
        "signal": signal,
        "options": options
    }


@app.route("/trade", methods=["POST"])
def trade():
    ticker = request.json.get("ticker")
    return jsonify(run_pipeline(ticker))


if __name__ == "__main__":
    app.run()
