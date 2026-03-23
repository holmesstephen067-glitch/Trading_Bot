"""
🚀 BACKTEST ENGINE — NO LOOKAHEAD
"""

import pandas as pd

from backtesting.trade_lifecycle import Trade
from backtesting.execution_model import execute_market_order

from core.decision_engine import generate_trade_signal


def run_backtest(df, ticker, initial_cash=10000):
    cash = initial_cash
    equity = initial_cash

    trades = []
    open_trade = None

    equity_curve = []

    for i in range(50, len(df)):  # warmup for indicators
        row = df.iloc[i]

        price = row["close"]

        # FEATURES (already precomputed in df)
        rsi = row["rsi"]
        atr = row["atr"]
        macd = row["macd"]
        ema20 = row["ema20"]
        ema50 = row["ema50"]
        ema200 = row["ema200"]

        carry_score = row.get("carry_score", 3)
        vix = row.get("vix", 20)

        # ----------------------------------
        # UPDATE EXISTING TRADE
        # ----------------------------------
        if open_trade:
            open_trade.update(price)

            if open_trade.status == "CLOSED":
                cash += open_trade.pnl
                trades.append(open_trade)
                open_trade = None

        # ----------------------------------
        # NEW SIGNAL (ONLY IF NO TRADE)
        # ----------------------------------
        if not open_trade:
            signal = generate_trade_signal(
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
            )

            if signal["action"] == "BUY":
                size = signal["position_size"]

                if size > 0 and cash > price * size:
                    exec_data = execute_market_order(price, size)

                    open_trade = Trade(
                        ticker,
                        exec_data["fill_price"],
                        size,
                        signal["stop_loss"],
                        signal["take_profit"]
                    )

                    cash -= exec_data["fill_price"] * size

        # ----------------------------------
        # EQUITY TRACKING
        # ----------------------------------
        current_value = cash

        if open_trade:
            current_value += open_trade.size * price

        equity_curve.append(current_value)

    return analyze_results(trades, equity_curve)

import numpy as np

def analyze_results(trades, equity_curve):
    if not trades:
        return {"error": "No trades"}

    pnl = [t.pnl for t in trades]

    total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0]

    wins = [p for p in pnl if p > 0]
    losses = [p for p in pnl if p <= 0]

    win_rate = len(wins) / len(pnl)

    avg_win = np.mean(wins) if wins else 0
    avg_loss = np.mean(losses) if losses else 0

    returns = np.diff(equity_curve) / equity_curve[:-1]

    sharpe = np.mean(returns) / (np.std(returns) + 1e-9) * np.sqrt(252)

    max_dd = max_drawdown(equity_curve)

    return {
        "total_return": round(total_return * 100, 2),
        "win_rate": round(win_rate * 100, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "sharpe": round(sharpe, 2),
        "max_drawdown": round(max_dd * 100, 2),
        "total_trades": len(trades)
    }


def max_drawdown(equity):
    peak = equity[0]
    max_dd = 0

    for x in equity:
        if x > peak:
            peak = x
        dd = (peak - x) / peak
        max_dd = max(max_dd, dd)

    return max_dd
