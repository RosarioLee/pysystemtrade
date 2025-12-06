import pandas as pd
import numpy as np
from datetime import datetime
import sys


class SimplePerformanceCalculator:
    def __init__(self, target_vol=0.12, warm_up_days=0):
        self.target_vol = target_vol
        self.warm_up_days = warm_up_days
        self.trading_days_per_year = 252

    def debug_print(self, message):
        """Force debug output that bypasses logging systems"""
        print(f"*** DEBUG *** {message}", flush=True)
        sys.stdout.flush()

        # Also write to file as backup
        try:
            with open("force_debug.log", "a") as f:
                f.write(f"{datetime.now()}: {message}\n")
                f.flush()
        except:
            pass

    def calculate_performance(self, system):
        try:
            self.debug_print("=== DEBUGGING PERFORMANCE CALCULATION ===")

            # Run all debug methods including the corrected capital analysis
            self.debug_portfolio_access(system)
            self.test_portfolio_methods(system)
            self.test_manual_returns(system)
            capital_debug = self.debug_capital_and_returns(system)  # ADD THIS

            portfolio = system.accounts.portfolio()
            if portfolio is None:
                self.debug_print("ERROR: portfolio is None")
                return None

            # Use the proper returns from capital analysis if available
            if capital_debug and "proper_returns" in capital_debug:
                daily_returns = capital_debug["proper_returns"]
                self.debug_print(
                    f"Using capital-adjusted returns: {len(daily_returns)} returns"
                )
            else:
                # Fallback to your existing method
                daily_returns = self._get_returns(portfolio, system)

            if daily_returns is None or daily_returns.empty:
                self.debug_print("No daily returns extracted")
                return None

            # Apply warm up period if specified
            if self.warm_up_days > 0 and len(daily_returns) > self.warm_up_days:
                daily_returns = daily_returns.iloc[self.warm_up_days :]

            # Calculate performance metrics
            performance_result = self._calculate_metrics(daily_returns)

            # Add capital information if available
            if capital_debug and performance_result:
                performance_result.update(
                    {
                        "starting_capital": capital_debug["starting_capital"],
                        "total_pnl": capital_debug["total_pnl"],
                        "final_portfolio_value": capital_debug["final_portfolio_value"],
                    }
                )

            return performance_result

        except Exception as e:
            self.debug_print(f"Performance calculation failed: {e}")
            import traceback

            self.debug_print(f"Traceback: {traceback.format_exc()}")
            return None

    def _get_returns(self, portfolio, system):
        """Get portfolio returns with zero starting value handling"""
        try:
            self.debug_print("--- Attempting to extract returns ---")

            # Method 1: Try portfolio percentage returns
            try:
                if hasattr(portfolio, "percent"):
                    percent_curve = portfolio.percent
                    if hasattr(percent_curve, "curve"):
                        curve = percent_curve.curve()
                        if curve is not None and len(curve) > 1:
                            # FIXED: Handle zero starting values
                            returns = self._safe_pct_change(curve)
                            if returns is not None and len(returns) > 0:
                                self.debug_print(
                                    f"Method 1 SUCCESS: Using percent.curve() - {len(returns)} returns"
                                )
                                return returns
            except Exception as e:
                self.debug_print(f"Method 1 failed: {e}")

            # Method 2: Try direct portfolio curve
            try:
                portfolio_curve = portfolio.curve()
                if portfolio_curve is not None and len(portfolio_curve) > 1:
                    # FIXED: Handle zero starting values
                    returns = self._safe_pct_change(portfolio_curve)
                    if returns is not None and len(returns) > 0:
                        self.debug_print(
                            f"Method 2 SUCCESS: Using portfolio.curve() - {len(returns)} returns"
                        )
                        return returns
            except Exception as e:
                self.debug_print(f"Method 2 failed: {e}")

            # Continue with other methods...
            self.debug_print("All portfolio return extraction methods failed")
            return None

        except Exception as e:
            self.debug_print(f"Error in _get_returns: {e}")
            return None

    def _safe_pct_change(self, pnl_curve, starting_capital=1000000):
        """Calculate percentage returns from P&L curve with proper capital base"""
        try:
            self.debug_print("--- Calculating returns from P&L curve ---")

            # Convert P&L to actual portfolio values
            portfolio_values = starting_capital + pnl_curve

            # Calculate percentage returns
            returns = portfolio_values.pct_change().dropna()

            # Remove any infinite values
            returns = returns.replace([np.inf, -np.inf], np.nan).dropna()

            self.debug_print(
                f"Converted P&L to portfolio values starting from ${starting_capital:,.2f}"
            )
            self.debug_print(f"Returns length: {len(returns)}")
            self.debug_print(f"First few returns: {returns.head().values}")

            return returns if len(returns) > 0 else None

        except Exception as e:
            self.debug_print(f"Error in _safe_pct_change: {e}")
            return None

    def _calculate_metrics(self, daily_returns):
        try:
            self.debug_print("--- Calculating performance metrics ---")
            mean_daily_return = daily_returns.mean()
            daily_vol = daily_returns.std()

            self.debug_print(f"Mean daily return: {mean_daily_return:.6f}")
            self.debug_print(f"Daily volatility: {daily_vol:.6f}")

            if daily_vol == 0 or np.isnan(daily_vol):
                self.debug_print("ERROR: Daily volatility is 0 or NaN")
                return None

            # Annual metrics
            annual_return = mean_daily_return * self.trading_days_per_year
            annual_vol = daily_vol * (self.trading_days_per_year**0.5)
            sharpe_ratio = annual_return / annual_vol if annual_vol != 0 else 0

            # Drawdown calculation
            cumulative = (1 + daily_returns).cumprod()
            rolling_max = cumulative.cummax()
            drawdown = (cumulative - rolling_max) / rolling_max
            max_drawdown = drawdown.min()

            # Win rate
            win_rate = (daily_returns > 0).mean()

            self.debug_print(f"Calculated Sharpe ratio: {sharpe_ratio:.3f}")
            self.debug_print(f"Calculated annual return: {annual_return:.1%}")

            return {
                "sharpe_ratio": float(sharpe_ratio),
                "annual_return": float(annual_return),
                "annual_volatility": float(annual_vol),
                "max_drawdown": float(max_drawdown),
                "win_rate": float(win_rate),
                "days_of_data": len(daily_returns),
                "years_analyzed": len(daily_returns) / self.trading_days_per_year,
            }

        except Exception as e:
            self.debug_print(f"Error calculating metrics: {e}")
            return None

    def debug_portfolio_access(self, system):
        self.debug_print("=== ENHANCED PORTFOLIO DEBUG ===")

        try:
            portfolio = system.accounts.portfolio()
            self.debug_print(f"Portfolio exists: {portfolio is not None}")
            self.debug_print(f"Portfolio type: {type(portfolio)}")

            # Test portfolio curve access
            try:
                curve = portfolio.curve()
                self.debug_print(f"Portfolio curve type: {type(curve)}")
                self.debug_print(
                    f"Portfolio curve length: {len(curve) if curve is not None else 'None'}"
                )
                if curve is not None and len(curve) > 0:
                    self.debug_print(f"Curve start date: {curve.index[0]}")
                    self.debug_print(f"Curve end date: {curve.index[-1]}")
                    self.debug_print(f"First 5 values: {curve.head().values}")
                    self.debug_print(f"Last 5 values: {curve.tail().values}")
                    self.debug_print(f"Contains NaN: {curve.isna().any()}")
                    self.debug_print(f"All zeros: {(curve == 0).all()}")
            except Exception as e:
                self.debug_print(f"Portfolio curve access failed: {e}")

        except Exception as e:
            self.debug_print(f"Portfolio debug failed: {e}")

    def test_portfolio_methods(self, system):
        self.debug_print("=== TESTING PORTFOLIO ACCESS METHODS ===")

        methods_to_test = [
            "portfolio().curve()",
            "portfolio().percent.curve()",
            "portfolio().net.curve()",
            "portfolio().gross.curve()",
        ]

        for method_name in methods_to_test:
            try:
                if method_name == "portfolio().curve()":
                    result = system.accounts.portfolio().curve()
                elif method_name == "portfolio().percent.curve()":
                    result = system.accounts.portfolio().percent.curve()
                elif method_name == "portfolio().net.curve()":
                    result = system.accounts.portfolio().net.curve()
                elif method_name == "portfolio().gross.curve()":
                    result = system.accounts.portfolio().gross.curve()

                self.debug_print(
                    f"{method_name}: SUCCESS - Type: {type(result)}, Length: {len(result) if result is not None else 'None'}"
                )
            except Exception as e:
                self.debug_print(f"{method_name}: FAILED - {e}")

    def test_manual_returns(self, system):
        self.debug_print("=== MANUAL RETURNS TEST ===")

        try:
            portfolio = system.accounts.portfolio()
            curve = portfolio.curve()

            if curve is not None and len(curve) > 1:
                # Calculate returns manually
                returns = curve.pct_change().dropna()
                self.debug_print(f"Manual returns calculation:")
                self.debug_print(f"  Returns length: {len(returns)}")
                self.debug_print(f"  Returns mean: {returns.mean():.6f}")
                self.debug_print(f"  Returns std: {returns.std():.6f}")
                self.debug_print(f"  Contains NaN: {returns.isna().any()}")
                self.debug_print(f"  First few returns: {returns.head().values}")

                # Test volatility calculation
                if len(returns) > 0 and not returns.isna().all():
                    daily_vol = returns.std()
                    annual_vol = daily_vol * (252**0.5)
                    self.debug_print(f"  Daily volatility: {daily_vol:.6f}")
                    self.debug_print(f"  Annual volatility: {annual_vol:.6f}")

                    if daily_vol > 0:
                        annual_return = returns.mean() * 252
                        sharpe = annual_return / annual_vol
                        self.debug_print(f"  Manual Sharpe calculation: {sharpe:.3f}")
            else:
                self.debug_print("No valid curve data for manual calculation")

        except Exception as e:
            self.debug_print(f"Manual returns test failed: {e}")

    def debug_capital_and_returns(self, system):
        """Debug actual capital and return calculations"""
        self.debug_print("=== CAPITAL AND RETURNS DEBUG ===")

        try:
            # Get starting capital from system config
            if hasattr(system, "config") and hasattr(
                system.config, "notional_trading_capital"
            ):
                starting_capital = system.config.notional_trading_capital
                self.debug_print(
                    f"Starting capital from config: ${starting_capital:,.2f}"
                )
            else:
                # Default assumption based on standard pysystemtrade config
                starting_capital = 1000000
                self.debug_print(
                    f"Using default starting capital: ${starting_capital:,.2f}"
                )

            # Get portfolio P&L curve (cumulative profits/losses)
            portfolio = system.accounts.portfolio()
            pnl_curve = portfolio.curve()

            if pnl_curve is not None and len(pnl_curve) > 0:
                total_pnl = pnl_curve.iloc[-1]
                actual_return_pct = (total_pnl / starting_capital) * 100
                final_portfolio_value = starting_capital + total_pnl

                self.debug_print(f"Total P&L generated: ${total_pnl:,.2f}")
                self.debug_print(f"Actual portfolio return: {actual_return_pct:.2f}%")
                self.debug_print(
                    f"Final portfolio value: ${final_portfolio_value:,.2f}"
                )

                # This is the KEY fix - convert P&L to percentage returns
                capital_curve = starting_capital + pnl_curve
                proper_returns = capital_curve.pct_change().dropna()

                if len(proper_returns) > 0 and not proper_returns.isna().all():
                    self.debug_print(
                        f"Proper daily returns mean: {proper_returns.mean():.6f}"
                    )
                    self.debug_print(
                        f"Proper daily returns std: {proper_returns.std():.6f}"
                    )

                    # Calculate proper Sharpe ratio
                    if proper_returns.std() > 0:
                        annual_return = proper_returns.mean() * 252
                        annual_vol = proper_returns.std() * (252**0.5)
                        sharpe_ratio = annual_return / annual_vol
                        self.debug_print(f"Proper Sharpe ratio: {sharpe_ratio:.3f}")
                        self.debug_print(f"Proper annual return: {annual_return:.1%}")

                    return {
                        "starting_capital": starting_capital,
                        "total_pnl": total_pnl,
                        "actual_return_pct": actual_return_pct,
                        "proper_returns": proper_returns,
                        "final_portfolio_value": final_portfolio_value,
                    }

        except Exception as e:
            self.debug_print(f"Capital debug failed: {e}")

        return None
