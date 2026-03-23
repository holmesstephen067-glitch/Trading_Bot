"""
📉 TRADE LIFECYCLE STATE MACHINE
"""

class Trade:
    def __init__(self, ticker, entry_price, size, stop, target):
        self.ticker = ticker
        self.entry_price = entry_price
        self.size = size
        self.stop = stop
        self.target = target

        self.status = "OPEN"
        self.exit_price = None
        self.pnl = 0

    def update(self, price):
        if self.status != "OPEN":
            return

        # STOP LOSS
        if price <= self.stop:
            self.exit(price, "STOP")

        # TAKE PROFIT
        elif price >= self.target:
            self.exit(price, "TARGET")

    def exit(self, price, reason):
        self.status = "CLOSED"
        self.exit_price = price
        self.pnl = (price - self.entry_price) * self.size
        self.reason = reason
