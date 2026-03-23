import math

from config import (
    PORTFOLIO,
    PORTFOLIO_VALUE,
    BUYING_POWER,
    MAX_POSITION_PCT,
    MAX_PORTFOLIO_RISK,
    RISK_PER_TRADE_PCT,
    ATR_STOP_MULTIPLIER,
    MIN_EDGE_TO_TRADE,
    LOW_CAPITAL_THRESHOLD,
    CARRY_SCORE_THRESHOLDS
)

# ============================================================
# CORE POSITION SIZING
# ============================================================

def position_size(price, atr):
    """
    Risk-based position sizing using ATR stop distance.
    """
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
# CARRY UNWIND OVERRIDE SYSTEM
# ============================================================

def carry_override(carry_score):
    """
    Returns trading restrictions based on carry score.
    """
    if carry_score <= 3:
        return "green"
    elif carry_score <= 7:
        return "yellow"
    elif carry_score <= 12:
        return "orange"
    else:
        return "red"


def apply_carry_rules(signal, carry_level):
    """
    Modify or block trades based on carry regime.
    """
    if carry_level == "green":
        return signal

    if carry_level == "yellow":
        signal["position_size"] *= 0.75
        signal["note"] = "Carry risk: size reduced 25%"

    elif carry_level == "orange":
        if signal["action"] == "BUY":
            signal["action"] = "HOLD"
        signal["note"] = "Carry risk: long positions blocked"

    elif carry_level == "red":
        signal["action"] = "REDUCE"
        signal["position_size"] *= 0.5
        signal["note"] = "Defensive mode: reduce exposure"

    return signal


# ============================================================
# TRADE DECISION ENGINE
# ============================================================

def generate_trade_signal(
    ticker,
    price,
    atr,
    rsi,
    carry_score,
    vix
):
    """
    Fully deterministic trading decision engine.
    """

    carry_level = carry_override(carry_score)

    # ----------------------------------
    # BASIC EDGE FILTER
    # ----------------------------------
    if rsi is None:
        return {"action": "NO_DATA"}

    if abs(rsi - 50) < 5:
        return {"action": "HOLD", "reason": "No edge (RSI neutral)"}

    # ----------------------------------
    # BASE ACTION
    # ----------------------------------
    if rsi < 40:
        action = "BUY"
    elif rsi > 60:
        action = "SELL"
    else:
        action = "HOLD"

    # ----------------------------------
    # OPTIONS / LOW CAPITAL MODE
    # ----------------------------------
    if BUYING_POWER < LOW_CAPITAL_THRESHOLD:
        if action == "BUY":
            action = "OPTIONS_ONLY"

    # ----------------------------------
    # EDGE FILTER
    # ----------------------------------
    if action == "BUY" and rsi > 50:
        return {"action": "HOLD", "reason": "Insufficient edge"}

    # ----------------------------------
    # BUILD SIGNAL
    # ----------------------------------
    signal = {
        "ticker": ticker,
        "action": action,
        "price": price,
        "position_size": position_size(price, atr),
        "stop_loss": stop_loss(price, atr),
        "take_profit": take_profit(price, atr),
        "carry_level": carry_level,
        "vix": vix,
        "rsi": rsi
    }

    # ----------------------------------
    # APPLY CARRY OVERRIDE
    # ----------------------------------
    signal = apply_carry_rules(signal, carry_level)

    return signal


# ============================================================
# OPTIONS STRATEGY ENGINE
# ============================================================

def covered_call_logic(price, avg_cost, contracts):
    """
    Covered call evaluation.
    """
    if contracts <= 0:
        return None

    strike_low = round(price * 1.05, 2)
    strike_high = round(price * 1.10, 2)

    return {
        "type": "COVERED_CALL",
        "recommended_strike_range": f"{strike_low} - {strike_high}",
        "above_cost": strike_low > avg_cost,
        "note": "Prefer OTM strikes above cost basis"
    }


def options_strategy_selector(ticker, price, portfolio_entry):
    """
    Deterministic options strategy selection.
    """
    data = PORTFOLIO.get(ticker)

    if not data:
        return None

    if data["contracts"] > 0:
        return covered_call_logic(price, data["avg_cost"], data["contracts"])

    # Future: cash-secured puts, spreads, etc.
    return None