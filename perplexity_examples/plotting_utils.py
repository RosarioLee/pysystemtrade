# plotting_utils.py - Real plotting implementations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from typing import Dict, Any, Optional


def plot_portfolio_performance_real(ax, system):
    """Plot actual portfolio performance curve"""
    try:
        portfolio = system.accounts.portfolio()
        if portfolio is not None:
            curve = portfolio.curve()
            if len(curve) > 0:
                # Convert to cumulative returns
                if curve.iloc[0] != 0:
                    normalized_curve = (curve / curve.iloc[0] - 1) * 100
                else:
                    normalized_curve = curve.diff().cumsum()

                # Plot the curve
                ax.plot(normalized_curve.index, normalized_curve.values,
                        color='blue', linewidth=2, label='Portfolio')

                ax.set_title("Portfolio Performance", fontsize=14, fontweight='bold')
                ax.set_ylabel("Cumulative Return (%)")
                ax.grid(True, alpha=0.3)
                ax.legend()

                # Add statistics
                total_return = normalized_curve.iloc[-1]
                ax.text(0.02, 0.98, f'Total Return: {total_return:.1f}%',
                        transform=ax.transAxes, verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
            else:
                ax.text(0.5, 0.5, 'No portfolio data available',
                        ha='center', va='center', transform=ax.transAxes)
        else:
            ax.text(0.5, 0.5, 'Portfolio not available',
                    ha='center', va='center', transform=ax.transAxes)
    except Exception as e:
        ax.text(0.5, 0.5, f'Error: {str(e)[:50]}',
                ha='center', va='center', transform=ax.transAxes, color='red')


def plot_rolling_sharpe_real(ax, system):
    """Plot rolling Sharpe ratio"""
    try:
        portfolio = system.accounts.portfolio()
        if portfolio is not None:
            curve = portfolio.curve()
            returns = curve.pct_change().dropna()

            if len(returns) > 60:
                # Calculate rolling Sharpe
                rolling_sharpe = returns.rolling(60).apply(
                    lambda x: (x.mean() / x.std()) * np.sqrt(252) if x.std() > 0 else 0
                )

                ax.plot(rolling_sharpe.index, rolling_sharpe.values,
                        color='green', linewidth=2)
                ax.set_title("Rolling Sharpe Ratio (60-day)", fontsize=12, fontweight='bold')
                ax.set_ylabel("Sharpe Ratio")
                ax.axhline(y=0, color='black', linestyle='--', alpha=0.5)
                ax.grid(True, alpha=0.3)

                # Add current value
                current_sharpe = rolling_sharpe.iloc[-1]
                ax.text(0.02, 0.98, f'Current: {current_sharpe:.2f}',
                        transform=ax.transAxes, verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
            else:
                ax.text(0.5, 0.5, 'Insufficient data for rolling Sharpe',
                        ha='center', va='center', transform=ax.transAxes)
    except Exception as e:
        ax.text(0.5, 0.5, f'Error: {str(e)[:30]}',
                ha='center', va='center', transform=ax.transAxes, color='red')


def plot_drawdown_analysis_real(ax, system):
    """Plot drawdown analysis"""
    try:
        portfolio = system.accounts.portfolio()
        if portfolio is not None:
            curve = portfolio.curve()
            returns = curve.pct_change().dropna()

            if len(returns) > 0:
                # Calculate drawdown
                cumulative = (1 + returns).cumprod()
                rolling_max = cumulative.expanding().max()
                drawdown = (cumulative - rolling_max) / rolling_max * 100

                ax.fill_between(drawdown.index, drawdown.values, 0,
                                color='red', alpha=0.3, label='Drawdown')
                ax.plot(drawdown.index, drawdown.values, color='red', linewidth=1)

                ax.set_title("Drawdown Analysis", fontsize=12, fontweight='bold')
                ax.set_ylabel("Drawdown (%)")
                ax.grid(True, alpha=0.3)

                # Add max drawdown
                max_dd = drawdown.min()
                ax.text(0.02, 0.02, f'Max DD: {max_dd:.1f}%',
                        transform=ax.transAxes, verticalalignment='bottom',
                        bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.8))
            else:
                ax.text(0.5, 0.5, 'No return data available',
                        ha='center', va='center', transform=ax.transAxes)
    except Exception as e:
        ax.text(0.5, 0.5, f'Error: {str(e)[:30]}',
                ha='center', va='center', transform=ax.transAxes, color='red')


def plot_return_distribution_real(ax, system):
    """Plot return distribution"""
    try:
        portfolio = system.accounts.portfolio()
        if portfolio is not None:
            curve = portfolio.curve()
            returns = curve.pct_change().dropna() * 100  # Convert to percentage

            if len(returns) > 10:
                # Create histogram
                ax.hist(returns, bins=30, density=True, alpha=0.7,
                        color='skyblue', edgecolor='black')

                # Add normal distribution overlay
                mu, sigma = returns.mean(), returns.std()
                x = np.linspace(returns.min(), returns.max(), 100)
                normal_dist = (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
                ax.plot(x, normal_dist, 'r-', linewidth=2, label='Normal Distribution')

                ax.set_title("Return Distribution", fontsize=12, fontweight='bold')
                ax.set_xlabel("Daily Returns (%)")
                ax.set_ylabel("Density")
                ax.legend()
                ax.grid(True, alpha=0.3)

                # Add statistics
                ax.text(0.02, 0.98, f'Mean: {mu:.2f}%\nStd: {sigma:.2f}%',
                        transform=ax.transAxes, verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
            else:
                ax.text(0.5, 0.5, 'Insufficient data for distribution',
                        ha='center', va='center', transform=ax.transAxes)
    except Exception as e:
        ax.text(0.5, 0.5, f'Error: {str(e)[:30]}',
                ha='center', va='center', transform=ax.transAxes, color='red')
