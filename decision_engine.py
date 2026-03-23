"""
🧠 MASTER DECISION ENGINE — DETERMINISTIC ONLY
Combines:
- Trend
- Momentum
- Volatility
- Carry risk
"""

from config import (
    PORTFOLIO,
    PORTFOLIO_VALUE,
    RISK_PER_TRADE_PCT,
    MAX_POSITION_PCT,
    ATR_STOP_MULTIPLIER
)

# ============================================================
# 📊 POSITION SIZING
# ============================================================

def position_size(price, atr):
    risk_dollars = PORTFOLIO_VALUE * RISK_PER_TRADE_PCT
    stop_distance = ATR_STOP_MULTIPLIER * atr

    if stop_distance == 0:
        return 0

    shares = risk_dollars / stop_distance
    max_shares = (PORTFOLIO_VALUE * MAX_POSITION_PCT) / price

    return round(min(shares, max_shares), 2)


def stop_loss(entry, atr):
    return round(entry - (ATR_STOP_MULTIPLIER * atr), 2)


def take_profit(entry, atr):
    return round(entry + (3 * ATR_STOP_MULTIPLIER * atr), 2)


# ============================================================
# 📈 SCORING SYSTEM (DETERMINISTIC)
# ============================================================

def score_trend(price, ema20, ema50, ema200):
    score = 0

    if price > ema20: score += 1
    if price > ema50: score += 1
    if price > ema200: score += 2

    if ema20 > ema50 > ema200:
        score += 2

    return score  # max 6


def score_momentum(rsi, macd):
    score = 0

    if rsi < 40: score += 2
    elif rsi < 50: score += 1

    if macd > 0: score += 2

    return score  # max 4


def score_volatility(atr, price):
    vol_pct = atr / price

    if vol_pct < 0.02:
        return 2
    elif vol_pct < 0.04:
        return 1
    return 0


# ============================================================
# 🚨 CARRY OVERRIDE
# ============================================================

def carry_override(score):
    if score <= 3:
        return "green"
    elif score <= 7:
        return "yellow"
    elif score <= 12:
        return "orange"
    else:
        return "red"


# ============================================================
# 🚀 MASTER SIGNAL
# ============================================================

def generate_trade_signal(
    ticker,
    price,
    atr,
    rsi,
    macd,
    ema20,
    ema50,
    ema200,
    carry_score,
    vix
):

    # ----------------------------------
    # 1. SCORE COMPONENTS
    # ----------------------------------
    trend_score = score_trend(price, ema20, ema50, ema200)
    momentum_score = score_momentum(rsi, macd)
    vol_score = score_volatility(atr, price)

    total_score = trend_score + momentum_score + vol_score

    # ----------------------------------
    # 2. BASE ACTION
    # ----------------------------------
    if total_score >= 8:
        action = "BUY"
    elif total_score <= 3:
        action = "SELL"
    else:
        action = "HOLD"

    # ----------------------------------
    # 3. RISK STRUCTURE
    # ----------------------------------
    signal = {
        "ticker": ticker,
        "action": action,
        "score": total_score,
        "price": price,
        "position_size": position_size(price, atr),
        "stop_loss": stop_loss(price, atr),
        "take_profit": take_profit(price, atr),
        "rsi": rsi,
        "macd": macd,
        "trend_score": trend_score,
        "momentum_score": momentum_score,
        "vol_score": vol_score,
        "vix": vix
    }

    # ----------------------------------
    # 4. CARRY OVERRIDE
    # ----------------------------------
    carry_level = carry_override(carry_score)

    if carry_level == "yellow":
        signal["position_size"] *= 0.75
        signal["note"] = "Carry: reduced size"

    elif carry_level == "orange":
        if signal["action"] == "BUY":
            signal["action"] = "HOLD"
        signal["note"] = "Carry: longs blocked"

    elif carry_level == "red":
        signal["action"] = "REDUCE"
        signal["position_size"] *= 0.5
        signal["note"] = "Carry: defensive mode"

    signal["carry_level"] = carry_level

    return signal


# ============================================================
# 💰 OPTIONS ENGINE
# ============================================================

def options_strategy_selector(ticker, price, portfolio):
    data = PORTFOLIO.get(ticker)

    if not data:
        return None

    if data["contracts"] > 0:
        strike_low = round(price * 1.05, 2)
        strike_high = round(price * 1.10, 2)

        return {
            "type": "COVERED_CALL",
            "strike_range": f"{strike_low}-{strike_high}",
            "above_cost": strike_low > data["avg_cost"]
        }

    return None
