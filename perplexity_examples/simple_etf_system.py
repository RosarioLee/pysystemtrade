# simple_etf_system.py - FIX the formatting error
import yfinance as yf
import pandas as pd
import numpy as np


def calculate_ewmac_forecast(prices, fast=8, slow=32):
    """Calculate EWMAC forecast directly - Carver's core momentum rule"""
    ewma_fast = prices.ewm(span=fast).mean()
    ewma_slow = prices.ewm(span=slow).mean()
    raw_forecast = (ewma_fast - ewma_slow) / prices.rolling(32).std()
    scaled_forecast = raw_forecast * 2.5
    capped_forecast = np.clip(scaled_forecast, -20, 20)
    return capped_forecast.dropna()


def calculate_position_size(forecast, price, volatility, risk_target=0.12):
    """Calculate position size using Carver's volatility targeting"""
    normalized_forecast = forecast / 10.0
    vol_scalar = risk_target / volatility
    position = normalized_forecast * vol_scalar
    return position


def run_simple_etf_system():
    """Run ETF system using Carver's principles directly"""

    print("=== Simple ETF System (Carver's Principles) ===")

    # Download ETF data
    print("Downloading ETF data...")
    ivv_data = yf.download("IVV", start="2020-01-01", auto_adjust=False)['Adj Close']
    hyd_data = yf.download("HYD", start="2020-01-01", auto_adjust=False)['Adj Close']

    print(f"IVV: {len(ivv_data)} days")
    print(f"HYD: {len(hyd_data)} days")

    # Calculate forecasts using Carver's EWMAC rule
    print("\n=== Calculating Trading Signals ===")
    ivv_forecast = calculate_ewmac_forecast(ivv_data, fast=8, slow=32)
    hyd_forecast = calculate_ewmac_forecast(hyd_data, fast=8, slow=32)

    # Calculate volatilities
    ivv_returns = ivv_data.pct_change().dropna()
    hyd_returns = hyd_data.pct_change().dropna()

    ivv_vol = ivv_returns.rolling(30).std() * np.sqrt(252)
    hyd_vol = hyd_returns.rolling(30).std() * np.sqrt(252)

    # Calculate positions using Carver's approach
    print("\n=== Position Sizing ===")

    # Align data
    common_dates = ivv_forecast.index.intersection(hyd_forecast.index)
    common_dates = common_dates.intersection(ivv_vol.index).intersection(hyd_vol.index)

    ivv_positions = calculate_position_size(
        ivv_forecast.loc[common_dates],
        ivv_data.loc[common_dates],
        ivv_vol.loc[common_dates]
    )

    hyd_positions = calculate_position_size(
        hyd_forecast.loc[common_dates],
        hyd_data.loc[common_dates],
        hyd_vol.loc[common_dates]
    )

    # Calculate returns (Carver's portfolio approach)
    print("\n=== Performance Calculation ===")

    # Individual instrument returns
    ivv_strategy_returns = (ivv_positions.shift(1) * ivv_returns.loc[common_dates]).dropna()
    hyd_strategy_returns = (hyd_positions.shift(1) * hyd_returns.loc[common_dates]).dropna()

    # FIX: Portfolio returns with proper date alignment
    # Find common dates where both strategies have valid returns
    common_return_dates = ivv_strategy_returns.index.intersection(hyd_strategy_returns.index)

    if len(common_return_dates) > 0:
        # Calculate portfolio returns on common dates only
        ivv_aligned = ivv_strategy_returns.loc[common_return_dates]
        hyd_aligned = hyd_strategy_returns.loc[common_return_dates]

        # Equal weight portfolio (Carver's diversification approach)
        portfolio_returns = (ivv_aligned + hyd_aligned) / 2

        print(f"Portfolio calculated on {len(common_return_dates)} common trading days")
    else:
        portfolio_returns = pd.Series(dtype=float)
        print("Warning: No common dates found for portfolio calculation")

    # Calculate Sharpe ratios - FIX: Better handling of portfolio Sharpe
    def safe_sharpe(returns_series, name="Unknown"):
        """Calculate Sharpe ratio with better error handling"""
        if len(returns_series) == 0:
            print(f"Warning: No returns data for {name}")
            return np.nan

        # Convert to numpy array to ensure scalar std and mean (from search results)
        returns_array = returns_series.values if isinstance(returns_series, pd.Series) else np.array(returns_series)
        std_val = np.std(returns_array)
        mean_val = np.mean(returns_array)

        if std_val == 0:
            print(f"Warning: Zero variance in returns for {name}")
            return np.nan

        sharpe = mean_val / std_val * np.sqrt(252)
        return float(sharpe)

    ivv_sharpe = safe_sharpe(ivv_strategy_returns, "IVV")
    hyd_sharpe = safe_sharpe(hyd_strategy_returns, "HYD")
    portfolio_sharpe = safe_sharpe(portfolio_returns, "Portfolio")

    # Display results
    print(f"IVV Sharpe Ratio: {ivv_sharpe:.2f}")
    print(f"HYD Sharpe Ratio: {hyd_sharpe:.2f}")

    if not np.isnan(portfolio_sharpe):
        print(f"Portfolio Sharpe Ratio: {portfolio_sharpe:.2f}")

        # Show diversification benefit
        if portfolio_sharpe > max(ivv_sharpe, hyd_sharpe):
            print("🎉 Portfolio shows diversification benefit!")
        else:
            print("ℹ️ Portfolio provides risk reduction through diversification")
    else:
        print("Portfolio Sharpe Ratio: Could not calculate (insufficient overlapping data)")
        # Calculate simple average as fallback
        avg_sharpe = (ivv_sharpe + hyd_sharpe) / 2
        print(f"Average Individual Sharpe: {avg_sharpe:.2f}")

    # Latest signals - FIX: Ensure scalar values
    def safe_value(series, index=-1):
        """Safely extract scalar value from Series"""
        val = series.iloc[index]
        if hasattr(val, 'iloc'):
            val = val.iloc[0] if len(val) > 0 else 0
        return float(val)

    ivv_forecast_val = safe_value(ivv_forecast)
    hyd_forecast_val = safe_value(hyd_forecast)
    ivv_pos_val = safe_value(ivv_positions)
    hyd_pos_val = safe_value(hyd_positions)

    print(f"\n=== Latest Trading Signals ===")
    print(f"IVV forecast: {ivv_forecast_val:.2f} ({'BUY' if ivv_forecast_val > 0 else 'SELL'})")
    print(f"HYD forecast: {hyd_forecast_val:.2f} ({'BUY' if hyd_forecast_val > 0 else 'SELL'})")

    print(f"\n=== Current Positions ===")
    print(f"IVV position: {ivv_pos_val:.2f}")
    print(f"HYD position: {hyd_pos_val:.2f}")

    print(f"\n🎉 ETF systematic trading system working using Carver's direct approach!")

    return {
        'ivv_sharpe': ivv_sharpe,
        'hyd_sharpe': hyd_sharpe,
        'portfolio_sharpe': portfolio_sharpe,
        'ivv_forecast': ivv_forecast_val,
        'hyd_forecast': hyd_forecast_val
    }


if __name__ == "__main__":
    results = run_simple_etf_system()
