import pandas as pd
import numpy as np
from datetime import datetime


class SimplePerformanceCalculator:
    def __init__(self, target_vol=0.12, warm_up_days=0):
        self.target_vol = target_vol
        self.warm_up_days = warm_up_days
        self.trading_days_per_year = 252

    def calculate_performance(self, system):
        try:
            print("=== DEBUGGING PERFORMANCE CALCULATION ===")

            portfolio = system.accounts.portfolio()
            if portfolio is None:
                print("ERROR: portfolio is None")
                return None

            print(f"Portfolio object type: {type(portfolio)}")

            # Get portfolio curve and show start/end values
            try:
                portfolio_curve = portfolio.curve()
                if portfolio_curve is not None and len(portfolio_curve) > 0:
                    print(f"Portfolio curve length: {len(portfolio_curve)}")
                    print(f"Starting portfolio value: {portfolio_curve.iloc[0]:.2f}")
                    print(f"Ending portfolio value: {portfolio_curve.iloc[-1]:.2f}")
                    print(f"Total return: {((portfolio_curve.iloc[-1] / portfolio_curve.iloc[0]) - 1) * 100:.2f}%")
                else:
                    print("Portfolio curve is None or empty")
            except Exception as e:
                print(f"Error getting portfolio curve: {e}")

            # Get daily returns with fallback methods
            daily_returns = self._get_returns(portfolio, system)  # Pass system here
            if daily_returns is None or daily_returns.empty:
                print("No daily returns extracted")
                return None

            print(f"Successfully extracted {len(daily_returns)} daily returns")
            print(f"First few returns: {daily_returns.head().values}")

            # Apply warm up period if specified
            if self.warm_up_days > 0 and len(daily_returns) > self.warm_up_days:
                daily_returns = daily_returns.iloc[self.warm_up_days:]
                print(f"Applied warm-up period, using {len(daily_returns)} returns")

            # Calculate core metrics
            return self._calculate_metrics(daily_returns)

        except Exception as e:
            print(f"Performance calculation failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _get_returns(self, portfolio, system):  # Add system parameter
        """Get portfolio returns with improved error handling"""
        try:
            print("--- Attempting to extract returns ---")

            # Method 1: Try portfolio percentage returns
            try:
                if hasattr(portfolio, 'percent'):
                    percent_curve = portfolio.percent
                    if hasattr(percent_curve, 'curve'):
                        curve = percent_curve.curve()
                        if curve is not None and len(curve) > 1:
                            returns = curve.pct_change().dropna()
                            if len(returns) > 0 and not returns.isna().all():
                                print(f"Method 1 SUCCESS: Using percent.curve() - {len(returns)} returns")
                                return returns
            except Exception as e:
                print(f"Method 1 failed: {e}")

            # Method 2: Try direct portfolio curve
            try:
                portfolio_curve = portfolio.curve()
                if portfolio_curve is not None and len(portfolio_curve) > 1:
                    clean_curve = portfolio_curve.dropna()
                    if len(clean_curve) > 10:
                        returns = clean_curve.pct_change().dropna()
                        if len(returns) > 0 and not returns.isna().all():
                            print(f"Method 2 SUCCESS: Using portfolio.curve() - {len(returns)} returns")
                            return returns
            except Exception as e:
                print(f"Method 2 failed: {e}")

            # Method 3: Try to get from system accounts directly (FIXED)
            try:
                account_curve = system.accounts.portfolio().net.daily.percent  # FIXED: use system parameter
                if account_curve is not None and len(account_curve) > 1:
                    returns = account_curve.dropna()
                    if len(returns) > 0:
                        print(f"Method 3 SUCCESS: Using system.accounts - {len(returns)} returns")
                        return returns
            except Exception as e:
                print(f"Method 3 failed: {e}")

            # Method 4: Alternative approach using gross returns
            try:
                gross_curve = system.accounts.portfolio().gross.daily.curve()
                if gross_curve is not None and len(gross_curve) > 1:
                    returns = gross_curve.pct_change().dropna()
                    if len(returns) > 0 and not returns.isna().all():
                        print(f"Method 4 SUCCESS: Using gross daily curve - {len(returns)} returns")
                        return returns
            except Exception as e:
                print(f"Method 4 failed: {e}")

            print("All portfolio return extraction methods failed")
            return None

        except Exception as e:
            print(f"Error in _get_returns: {e}")
            return None

    def _calculate_metrics(self, daily_returns):
        try:
            print("--- Calculating performance metrics ---")
            mean_daily_return = daily_returns.mean()
            daily_vol = daily_returns.std()

            print(f"Mean daily return: {mean_daily_return:.6f}")
            print(f"Daily volatility: {daily_vol:.6f}")

            if daily_vol == 0 or np.isnan(daily_vol):
                print("ERROR: Daily volatility is 0 or NaN")
                return None

            # Annual metrics
            annual_return = mean_daily_return * self.trading_days_per_year
            annual_vol = daily_vol * (self.trading_days_per_year ** 0.5)
            sharpe_ratio = annual_return / annual_vol if annual_vol != 0 else 0

            # Drawdown calculation
            cumulative = (1 + daily_returns).cumprod()
            rolling_max = cumulative.cummax()
            drawdown = (cumulative - rolling_max) / rolling_max
            max_drawdown = drawdown.min()

            # Win rate
            win_rate = (daily_returns > 0).mean()

            print(f"Calculated Sharpe ratio: {sharpe_ratio:.3f}")
            print(f"Calculated annual return: {annual_return:.1%}")

            return {
                'sharpe_ratio': float(sharpe_ratio),
                'annual_return': float(annual_return),
                'annual_volatility': float(annual_vol),
                'max_drawdown': float(max_drawdown),
                'win_rate': float(win_rate),
                'days_of_data': len(daily_returns),
                'years_analyzed': len(daily_returns) / self.trading_days_per_year
            }

        except Exception as e:
            print(f"Error calculating metrics: {e}")
            return None
