"""
⚙️ EXECUTION MODEL
Simulates slippage, fees, realistic fills
"""

def apply_slippage(price, slippage_pct=0.001):
    return price * (1 + slippage_pct)


def apply_fees(value, fee_pct=0.001):
    return value * fee_pct


def execute_market_order(price, size):
    fill_price = apply_slippage(price)
    cost = fill_price * size
    fees = apply_fees(cost)

    return {
        "fill_price": fill_price,
        "fees": fees
    }
