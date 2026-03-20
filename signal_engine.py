# ============================================================
# PORTFOLIO CONFIG — update after every trade
# ============================================================

PORTFOLIO = {
    "TSLA": {"shares": 700,  "avg_cost": 204.68, "contracts": 7},
    "AMD":  {"shares": 400,  "avg_cost": 129.86, "contracts": 4},
    "NVDA": {"shares": 200,  "avg_cost": 125.94, "contracts": 2},
    "SOFI": {"shares": 2000, "avg_cost": 21.09,  "contracts": 20},
    "AMZU": {"shares": 200,  "avg_cost": 40.44,  "contracts": 2},
    "ROBN": {"shares": 100,  "avg_cost": 45.00,  "contracts": 1},
}

OPEN_OPTIONS = [
    {"ticker": "PLTR", "type": "BUY_CALL", "contracts": 1, "expiry": "2028-01-21"},
]

CRYPTO = {
    "BTC": {"amount": 0.0120392, "avg_cost": 92551},
    "ETH": {"amount": 0.40,      "avg_cost": 2829},
}

PORTFOLIO_VALUE = 117125
BUYING_POWER    = 24514   # ← Update this after every trade

# ============================================================
# RISK CONFIG — do not change unless strategy changes
# ============================================================

MAX_POSITION_PCT     = 0.05    # 5% max per position
MAX_PORTFOLIO_RISK   = 0.20    # 20% total portfolio risk
RISK_PER_TRADE_PCT   = 0.015   # 1.5% max risk per trade
ATR_STOP_MULTIPLIER  = 1.5     # Stop = entry - (1.5 × ATR)
MIN_EDGE_TO_TRADE    = 10      # TPS edge % minimum
LOW_CAPITAL_THRESHOLD = 10000  # Triggers options-only mode

# ============================================================
# CARRY UNWIND CONFIG
# ============================================================

CARRY_SCORE_THRESHOLDS = {
    "green":  (0, 3),    # Trade normally
    "yellow": (4, 7),    # Reduce new sizes 25%
    "orange": (8, 12),   # No new longs, covered calls only
    "red":    (13, 21),  # Defensive mode
}

USDJPY_RISK_LEVEL = 160.0      # The key carry unwind trigger level
