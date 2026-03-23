"""
🚀 WALK-FORWARD OPTIMIZATION ENGINE
Prevents overfitting using rolling train/test windows
"""

import pandas as pd
import numpy as np

from backtesting.engine import run_backtest


# ============================================================
# 🔧 PARAMETER GRID (DETERMINISTIC)
# ============================================================

PARAM_GRID = {
    "rsi_low":  [30, 35, 40],
    "rsi_high": [60, 65, 70],
    "atr_mult": [1.0, 1.5, 2.0],
}


def generate_param_combinations():
    combos = []

    for low in PARAM_GRID["rsi_low"]:
        for high in PARAM_GRID["rsi_high"]:
            for atr in PARAM_GRID["atr_mult"]:
                combos.append({
                    "rsi_low": low,
                    "rsi_high": high,
                    "atr_mult": atr
                })

    return combos


# ============================================================
# 🧪 TRAIN PHASE (OPTIMIZATION)
# ============================================================

def optimize_on_window(df_train, ticker):
    best_score = -np.inf
    best_params = None

    for params in generate_param_combinations():
        results = run_backtest(df_train, ticker)

        # Objective function (Sharpe + Return - Drawdown penalty)
        score = (
            results.get("sharpe", 0)
            + results.get("total_return", 0) * 0.1
            - results.get("max_drawdown", 0) * 0.5
        )

        if score > best_score:
            best_score = score
            best_params = params

    return best_params


# ============================================================
# 🚀 WALK-FORWARD LOOP
# ============================================================

def walk_forward_analysis(df, ticker,
                          train_size=252,
                          test_size=63):
    """
    train_size = ~1 year
    test_size  = ~3 months
    """

    results = []
    equity_curves = []

    start = 0

    while start + train_size + test_size < len(df):
        train = df.iloc[start:start + train_size]
        test  = df.iloc[start + train_size : start + train_size + test_size]

        # -----------------------------
        # 1. OPTIMIZE ON TRAIN
        # -----------------------------
        best_params = optimize_on_window(train, ticker)

        # -----------------------------
        # 2. TEST ON UNSEEN DATA
        # -----------------------------
        test_result = run_backtest(test, ticker)

        results.append({
            "start_index": start,
            "params": best_params,
            "performance": test_result
        })

        start += test_size  # roll forward

    return aggregate_results(results)


# ============================================================
# 📊 AGGREGATION
# ============================================================

def aggregate_results(results):
    if not results:
        return {"error": "No walk-forward windows"}

    sharpe_vals = []
    returns = []
    drawdowns = []
    trades = []

    for r in results:
        perf = r["performance"]

        sharpe_vals.append(perf.get("sharpe", 0))
        returns.append(perf.get("total_return", 0))
        drawdowns.append(perf.get("max_drawdown", 0))
        trades.append(perf.get("total_trades", 0))

    return {
        "windows": len(results),
        "avg_sharpe": round(np.mean(sharpe_vals), 2),
        "avg_return": round(np.mean(returns), 2),
        "avg_drawdown": round(np.mean(drawdowns), 2),
        "avg_trades": int(np.mean(trades)),
        "consistency_score": consistency_score(returns, sharpe_vals)
    }


def consistency_score(returns, sharpes):
    """
    Measures stability across windows (VERY important)
    """
    return round(
        (np.mean(returns) / (np.std(returns) + 1e-6)) +
        (np.mean(sharpes) / (np.std(sharpes) + 1e-6)),
        2
    )
