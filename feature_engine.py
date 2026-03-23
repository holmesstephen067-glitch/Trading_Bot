"""
📊 FEATURE ENGINE — ALL INDICATORS
"""

def compute_rsi(data):
    try:
        return float(list(data["Technical Analysis: RSI"].values())[0]["RSI"])
    except:
        return None


def compute_atr(data):
    try:
        return float(list(data["Technical Analysis: ATR"].values())[0]["ATR"])
    except:
        return None


def compute_ema(data):
    try:
        return float(list(data["Technical Analysis: EMA"].values())[0]["EMA"])
    except:
        return None


def compute_macd(data):
    try:
        return float(list(data["Technical Analysis: MACD"].values())[0]["MACD"])
    except:
        return 0
