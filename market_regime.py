def detect_regime(vix, ema50, ema200, price):
    """
    Deterministic regime classification
    """

    if vix > 30:
        return "high_vol"

    if price > ema50 > ema200:
        return "trend"

    if vix < 18:
        return "low_vol"

    return "mean_reversion"
