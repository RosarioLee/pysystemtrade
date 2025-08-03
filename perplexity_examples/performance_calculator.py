# performance_calculator.py - Enhanced Performance Calculation v1.2

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')


class EnhancedPerformanceCalculator:
    """
    Production-ready performance calculator with robust error handling
    and proper volatility scaling following Carver methodology
    """

    def __init__(self, target_vol=0.12, warm_up_days=None):
        self.target_vol = target_vol
        self.warm_up_days = warm_up_days
        self.trading_days_per_year = 252

    def calculate_portfolio_performance(self, system, timeout_seconds=300):
        """
        Calculate portfolio performance with proper volatility targeting
        """
        print("=== Enhanced Performance Calculation v1.2 ===")
        start_time = datetime.now()

        try:
            # Get portfolio curve
            portfolio_curve = system.accounts.portfolio()
            if portfolio_curve is None:
                print("❌ Portfolio curve unavailable")
                return None

            # Extract P&L curve
            raw_curve = portfolio_curve.curve()
            print(f"📈 Raw portfolio data: {len(raw_curve)} points")

            # Apply warm-up buffer if specified
            if hasattr(self, 'warm_up_days') and self.warm_up_days and len(raw_curve) > self.warm_up_days:
                raw_curve = raw_curve.iloc[self.warm_up_days:]
                print(f"🔧 Applied {self.warm_up_days}-day warm-up buffer")

            # Convert P&L to percentage returns
            if raw_curve.iloc[0] == 0:
                # Handle zero-start P&L curves
                raw_curve = raw_curve + 100  # Add base capital

            # Calculate daily percentage returns
            daily_returns = raw_curve.pct_change().dropna()

            # CRITICAL FIX: Apply volatility scaling
            actual_vol = daily_returns.std() * np.sqrt(self.trading_days_per_year)
            vol_scalar = self.target_vol / actual_vol if actual_vol > 0 else 1.0

            # Scale returns to target volatility
            scaled_returns = daily_returns * vol_scalar
            scaled_vol = scaled_returns.std() * np.sqrt(self.trading_days_per_year)

            print(f"🎯 Volatility targeting: {actual_vol:.1%} → {scaled_vol:.1%}")

            # Calculate cumulative performance
            cumulative_returns = (1 + scaled_returns).cumprod()

            # Performance metrics
            metrics = self._calculate_metrics(scaled_returns, cumulative_returns)
            metrics['vol_scalar_applied'] = vol_scalar
            metrics['actual_vol_pre_scaling'] = actual_vol
            metrics['calculation_time'] = (datetime.now() - start_time).total_seconds()

            self._display_metrics(metrics)
            return metrics

        except Exception as e:
            print(f"❌ Performance calculation failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _calculate_metrics(self, returns, cumulative_returns):
        """Calculate comprehensive performance metrics"""

        # Basic metrics
        mean_return = returns.mean()
        vol = returns.std() * np.sqrt(self.trading_days_per_year)
        sharpe = mean_return / returns.std() * np.sqrt(self.trading_days_per_year) if returns.std() > 0 else 0

        # Return metrics
        total_return = cumulative_returns.iloc[-1] - 1
        years = len(returns) / self.trading_days_per_year
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

        # Risk metrics
        rolling_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        # Advanced metrics
        negative_returns = returns[returns < 0]
        positive_returns = returns[returns > 0]

        win_rate = len(positive_returns) / len(returns) if len(returns) > 0 else 0
        avg_win = positive_returns.mean() if len(positive_returns) > 0 else 0
        avg_loss = negative_returns.mean() if len(negative_returns) > 0 else 0
        profit_factor = abs(avg_win * len(positive_returns)) / abs(
            avg_loss * len(negative_returns)) if avg_loss != 0 else np.inf

        # Calmar Ratio (Annual Return / Max Drawdown)
        calmar_ratio = abs(annual_return / max_drawdown) if max_drawdown != 0 else np.inf

        # Volatility-Adjusted Return (Return per unit of volatility)
        vol_adjusted_return = annual_return / vol if vol > 0 else 0

        # Average Daily Return scaled for comparison
        avg_daily_return = returns.mean()

        # Downside Deviation (volatility of negative returns only)
        downside_returns = returns[returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(self.trading_days_per_year) if len(
            downside_returns) > 0 else 0

        # Sortino Ratio (return vs downside risk)
        sortino_ratio = annual_return / downside_deviation if downside_deviation > 0 else np.inf

        return {
            'sharpe_ratio': float(sharpe),
            'calmar_ratio': float(calmar_ratio),
            'vol_adjusted_return': float(vol_adjusted_return),
            'sortino_ratio': float(sortino_ratio),
            'downside_deviation': float(downside_deviation),
            'avg_daily_return': float(avg_daily_return),
            'annual_return': float(annual_return),
            'annual_volatility': float(vol),
            'max_drawdown': float(max_drawdown),
            'total_return': float(total_return),
            'win_rate': float(win_rate),
            'profit_factor': float(profit_factor),
            'trading_days': len(returns),
            'years_analyzed': float(years)
        }

    def _display_metrics(self, metrics):
        """Display metrics in formatted output"""
        print(f"\n📊 CORRECTED Performance Metrics:")
        print(f"   • Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
        print(f" • Calmar Ratio: {metrics['calmar_ratio']:.2f}")
        print(f" • Sortino Ratio: {metrics['sortino_ratio']:.2f}")
        print(f" • Vol-Adjusted Return: {metrics['vol_adjusted_return']:.2f}")
        print(f" • Downside Deviation: {metrics['downside_deviation']:.1%}")
        print(f"   • Annual Return: {metrics['annual_return']:.1%}")
        print(f"   • Annual Volatility: {metrics['annual_volatility']:.1%}")
        print(f"   • Maximum Drawdown: {metrics['max_drawdown']:.1%}")
        print(f"   • Total Return: {metrics['total_return']:.1%}")
        print(f"   • Win Rate: {metrics['win_rate']:.1%}")
        print(f"   • Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"   • Years Analyzed: {metrics['years_analyzed']:.1f}")
