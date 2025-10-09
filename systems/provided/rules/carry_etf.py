def etf_carry_forecast(price, dividend_yield, funding_rate=0.0):
    """
    ETF carry forecast - proper Carver methodology
    Capping happens AFTER scalar application by the system
    """
    # Calculate risk-adjusted raw carry (annualized)
    returns = price.pct_change()
    daily_vol = returns.ewm(span=35, min_periods=10).std()
    annual_vol = daily_vol * (252 ** 0.5)

    # Raw carry = yield differential / volatility (risk-adjusted)
    raw_carry_forecast = (dividend_yield - funding_rate) / annual_vol

    # Return raw forecast - NO capping here
    # System will:
    # 1. Apply estimated scalar (via median_absolute method)
    # 2. Then cap the scaled result at ±20
    return raw_carry_forecast
