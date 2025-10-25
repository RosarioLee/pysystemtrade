#!/usr/bin/env python3
"""
Dynamic Optimization Backtesting Script for Robert Carver's Latest System
=========================================================================

This script implements backtesting for Rob's dynamic optimization system with:
- Full dynamic position optimization
- Real-time correlation-aware risk management
- Integer contract constraints
- Cost-aware position selection

Based on research from:
- systems/provided/rob_system/run_system.py
- systems/provided/dynamic_small_system_optimise/
- Robert's blog posts on dynamic optimization

Author: Systematic Trading Implementation
Date: October 2025
"""

import os
import sys
import warnings
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Add project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_dir)

# Core pysystemtrade imports
from systems.provided.rob_system.run_system import futures_system
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
from sysdata.config.configdata import Config

# Additional imports for analysis
from syscore.constants import arg_not_supplied

# FIXED: Move static system imports to module level
from systems.accounts.accounts_stage import Account
from systems.portfolio import Portfolios  # CORRECTED: was PortfoliosEstimated
from systems.positionsizing import PositionSizing
from systems.rawdata import RawData
from systems.forecast_combine import ForecastCombine  # CORRECTED: was ForecastCombineFixed
from systems.forecast_scale_cap import ForecastScaleCap  # CORRECTED: was ForecastScaleCapFixed
from systems.forecasting import Rules
from systems.basesystem import System


class DynamicSystemBacktester:
    """
    Comprehensive backtesting framework for Robert Carver's dynamic optimization system
    """

    def __init__(self, config_file='project_dynamic/dynamic_backtest_config.yaml'):
        """Initialize the backtester with configuration"""
        self.config_file = config_file
        self.system = None
        self.results = {}
        self.start_time = datetime.now()

    def setup_data_source(self, data_type='csv'):
        """Setup data source for backtesting"""
        print("Setting up data source...")

        if data_type == 'csv':
            # Use built-in CSV sample data
            self.data_source = csvFuturesSimData()
            print(f"✓ CSV data source initialized")

            # Check available instruments
            available_instruments = self.data_source.get_instrument_list()
            print(f"✓ Available instruments: {len(available_instruments)}")
            print(f"  Sample: {available_instruments[:10]}")

        elif data_type == 'database':
            # Use database connection (requires MongoDB setup)
            from sysdata.sim.db_futures_sim_data import dbFuturesSimData
            self.data_source = dbFuturesSimData()
            print(f"✓ Database data source initialized")

        return self.data_source

    def create_system(self, custom_config=None):
        """Create the dynamic optimization system"""
        print("\nCreating dynamic optimization system...")

        try:
            if custom_config:
                # Use custom configuration
                self.system = futures_system(
                    sim_data=self.data_source,
                    config_filename=None  # We'll set config manually
                )
                self.system.config = custom_config
                print(f"✓ System created with custom configuration")
            else:
                # Use the configuration file
                self.system = futures_system(
                    sim_data=self.data_source,
                    config_filename=self.config_file
                )
                print(f"✓ System created with config file: {self.config_file}")

            # Verify dynamic optimization components are loaded
            if hasattr(self.system, 'optimisedPositions'):
                print(f"✓ Dynamic optimization stage loaded successfully")
            else:
                print(f"⚠ Warning: Dynamic optimization stage not found")

            return self.system

        except Exception as e:
            print(f"❌ Error creating system: {str(e)}")
            raise

    def run_backtest(self, start_date=None, end_date=None):
        """Execute the full dynamic optimization backtest"""
        print(f"\n{'=' * 60}")
        print(f"RUNNING DYNAMIC OPTIMIZATION BACKTEST")
        print(f"{'=' * 60}")

        backtest_start = datetime.now()

        try:
            # Get optimized positions (this triggers the full optimization)
            print("Computing optimized positions (this may take several minutes)...")
            optimized_positions_df = self.system.optimisedPositions.get_optimised_position_df()
            print(f"✓ Optimized positions computed: {optimized_positions_df.shape}")

            # Get optimized weights
            print("Computing optimized portfolio weights...")
            optimized_weights_df = self.system.optimisedPositions.get_optimised_weights_df()
            print(f"✓ Optimized weights computed: {optimized_weights_df.shape}")

            # Calculate portfolio performance
            print("Calculating portfolio performance...")
            portfolio_returns = self.system.accounts.portfolio()
            print(f"✓ Portfolio performance calculated")

            # Store results
            self.results = {
                'optimized_positions': optimized_positions_df,
                'optimized_weights': optimized_weights_df,
                'portfolio_returns': portfolio_returns,
                'backtest_duration': datetime.now() - backtest_start
            }

            return self.results

        except Exception as e:
            print(f"❌ Backtest failed: {str(e)}")
            print(f"   This is common with dynamic optimization - check data availability")
            raise

    def analyze_results(self):
        """Analyze and display backtest results"""
        portfolio_returns = self.system.accounts.portfolio().percent

        try:
            stats_list = portfolio_returns.stats()
            print(f"\n📊 DETAILED STATISTICS")

            # Fix: Convert to float before formatting
            mean_val = float(stats_list[0])
            std_val = float(stats_list[1])

            print(f"Mean: {mean_val:.3f}%")
            print(f"Std: {std_val:.3f}%")

            # Safe access to additional stats
            if len(stats_list) > 2:
                skew_val = float(stats_list[2])
                print(f"Skew: {skew_val:.3f}")

            if len(stats_list) > 3:
                kurtosis_val = float(stats_list[3])
                print(f"Kurtosis: {kurtosis_val:.3f}")

        except (IndexError, TypeError, ValueError) as e:
            print(f"Using alternative statistics calculation: {e}")
            # Fallback to individual methods
            print(f"Mean: {float(portfolio_returns.mean()):.3f}%")
            print(f"Std: {float(portfolio_returns.std()):.3f}%")
            print(f"Skew: {float(portfolio_returns.skew()):.3f}")
            print(f"Kurtosis: {float(portfolio_returns.kurtosis()):.3f}")

    def save_results(self, output_dir='project_dynamic/results'):
        """Save backtest results to files"""
        if not self.results:
            print("❌ No results to save")
            return

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        try:
            # Save positions
            positions_file = f"{output_dir}/optimized_positions_{timestamp}.csv"
            self.results['optimized_positions'].to_csv(positions_file)
            print(f"✓ Positions saved: {positions_file}")

            # Save weights
            weights_file = f"{output_dir}/optimized_weights_{timestamp}.csv"
            self.results['optimized_weights'].to_csv(weights_file)
            print(f"✓ Weights saved: {weights_file}")

            # Save performance summary
            portfolio_returns = self.results['portfolio_returns']
            summary_file = f"{output_dir}/performance_summary_{timestamp}.txt"

            with open(summary_file, 'w') as f:
                f.write(f"Dynamic Optimization Backtest Results\n")
                f.write(f"Generated: {datetime.now()}\n")
                f.write(f"{'=' * 50}\n\n")
                f.write(f"Sharpe Ratio: {portfolio_returns.sharpe():.3f}\n")
                f.write(f"Annual Return: {portfolio_returns.percent.mean() * 256:.1f}%\n")
                f.write(f"Annual Volatility: {portfolio_returns.percent.std() * (256 ** 0.5):.1f}%\n")
                f.write(f"Max Drawdown: {portfolio_returns.percent.drawdown().min():.1f}%\n")
                f.write(f"Calmar Ratio: {portfolio_returns.calmar():.3f}\n")

            print(f"✓ Summary saved: {summary_file}")

            # Generate performance plots
            plot_files = self.create_performance_plots(output_dir)
            if plot_files[0]:
                print(f"✓ Plots generated successfully")

            # Generate advanced position and risk analysis
            advanced_plots = self.create_position_and_risk_plots(output_dir)
            if advanced_plots[0]:
                print(f"✓ Advanced position & risk analysis generated")

        except Exception as e:
            print(f"❌ Error saving results: {str(e)}")

    def create_performance_plots(self, output_dir='project_dynamic/results'):
        """
        Create equity curve and drawdown plots following Robert Carver's visualization style
        """
        if not self.results:
            print("❌ No results to plot")
            return

        print(f"\n📈 CREATING PERFORMANCE PLOTS")
        print(f"{'─' * 40}")

        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            from matplotlib.patches import Rectangle

            # Get portfolio returns data
            portfolio_returns = self.results['portfolio_returns']

            # Calculate equity curve (cumulative returns)
            equity_curve = (1 + portfolio_returns.percent / 100).cumprod()

            # Calculate drawdown series
            rolling_max = equity_curve.cummax()
            drawdown = (equity_curve / rolling_max - 1) * 100  # Convert to percentage

            # Create timestamp for file naming
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Set up the plotting style (Robert Carver prefers clean, professional charts)
            plt.style.use('default')
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
            fig.suptitle('Robert Carver Dynamic Optimization System - Performance Analysis',
                         fontsize=16, fontweight='bold', y=0.98)

            # ======== EQUITY CURVE PLOT ========
            ax1.plot(equity_curve.index, equity_curve.values,
                     linewidth=1.5, color='#2E86AB', label='Dynamic Portfolio')
            ax1.set_title('Cumulative Equity Curve', fontsize=14, fontweight='semibold', pad=20)
            ax1.set_ylabel('Portfolio Value (Base = 1.0)', fontsize=12)
            ax1.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
            ax1.legend(loc='upper left', frameon=True, fancybox=True, shadow=True)

            # Format x-axis dates
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
            ax1.xaxis.set_major_locator(mdates.YearLocator(2))

            # Add key statistics as text box
            final_value = equity_curve.iloc[-1]
            total_return = (final_value - 1) * 100
            sharpe = portfolio_returns.sharpe()

            stats_text = f'Total Return: {total_return:.1f}%\nSharpe Ratio: {sharpe:.3f}\nFinal Value: {final_value:.2f}'
            ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes,
                     verticalalignment='top', bbox=dict(boxstyle='round',
                                                        facecolor='wheat', alpha=0.8), fontsize=10)

            # ======== DRAWDOWN PLOT ========
            ax2.fill_between(drawdown.index, drawdown.values, 0,
                             color='#A23B72', alpha=0.6, label='Drawdown')
            ax2.plot(drawdown.index, drawdown.values,
                     linewidth=1, color='#A23B72')
            ax2.set_title('Drawdown Analysis', fontsize=14, fontweight='semibold', pad=20)
            ax2.set_xlabel('Year', fontsize=12)
            ax2.set_ylabel('Drawdown (%)', fontsize=12)
            ax2.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
            ax2.legend(loc='lower right', frameon=True, fancybox=True, shadow=True)

            # Format x-axis dates
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
            ax2.xaxis.set_major_locator(mdates.YearLocator(2))

            # Add max drawdown annotation
            max_dd = drawdown.min()
            max_dd_date = drawdown.idxmin()
            ax2.annotate(f'Max DD: {max_dd:.1f}%',
                         xy=(max_dd_date, max_dd),
                         xytext=(max_dd_date, max_dd + 5),
                         arrowprops=dict(arrowstyle='->', color='red', lw=1.5),
                         fontsize=10, ha='center',
                         bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))

            # Adjust layout and save
            plt.tight_layout()
            plt.subplots_adjust(top=0.93)

            # Save the plot
            plot_filename = f"{output_dir}/performance_analysis_{timestamp}.png"
            plt.savefig(plot_filename, dpi=300, bbox_inches='tight',
                        facecolor='white', edgecolor='none')
            print(f"✓ Performance plots saved: {plot_filename}")

            # Also save as PDF for publication quality
            pdf_filename = f"{output_dir}/performance_analysis_{timestamp}.pdf"
            plt.savefig(pdf_filename, dpi=300, bbox_inches='tight',
                        facecolor='white', edgecolor='none')
            print(f"✓ PDF version saved: {pdf_filename}")

            # Display the plot
            plt.show()

            return plot_filename, pdf_filename

        except ImportError as e:
            print(f"❌ Matplotlib not available for plotting: {e}")
            print("   Install with: pip install matplotlib")
            return None, None

        except Exception as e:
            print(f"❌ Error creating plots: {e}")
            return None, None

    def create_position_and_risk_plots(self, output_dir='project_dynamic/results'):
        """
        Create advanced position evolution and risk metrics plots
        Following Robert Carver's systematic trading analysis methodology
        """
        if not self.results:
            print("❌ No results to plot")
            return

        print(f"\n📊 CREATING POSITION & RISK ANALYSIS PLOTS")
        print(f"{'─' * 50}")

        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            from matplotlib.colors import ListedColormap
            import numpy as np

            # Get data
            positions = self.results['optimized_positions']
            weights = self.results['optimized_weights']
            portfolio_returns = self.results['portfolio_returns']

            # Create timestamp for file naming
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Set up professional styling
            plt.style.use('default')
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle('Robert Carver Dynamic System - Position Evolution & Risk Analysis',
                         fontsize=16, fontweight='bold', y=0.98)

            # ======== 1. POSITION EVOLUTION HEATMAP ========
            # Sample positions every 30 days for visibility
            positions_sampled = positions.iloc[::30, :]

            # Create heatmap of positions over time
            im1 = ax1.imshow(positions_sampled.T, aspect='auto', cmap='RdBu_r',
                             interpolation='nearest', alpha=0.8)

            ax1.set_title('Position Evolution Over Time (Contract Sizes)',
                          fontsize=12, fontweight='semibold', pad=15)
            ax1.set_xlabel('Time (sampled every 30 days)', fontsize=10)
            ax1.set_ylabel('Instruments', fontsize=10)

            # Set y-axis labels to instrument names
            ax1.set_yticks(range(len(positions.columns)))
            ax1.set_yticklabels(positions.columns, fontsize=9)

            # Set x-axis labels to dates (every 2 years)
            date_indices = range(0, len(positions_sampled), len(positions_sampled) // 8)
            ax1.set_xticks(date_indices)
            ax1.set_xticklabels([positions_sampled.index[i].strftime('%Y')
                                 for i in date_indices], rotation=45, fontsize=9)

            # Add colorbar
            cbar1 = plt.colorbar(im1, ax=ax1, shrink=0.8)
            cbar1.set_label('Position Size (Contracts)', fontsize=9)

            # ======== 2. PORTFOLIO CONCENTRATION OVER TIME ========
            # Calculate concentration metrics
            abs_weights = weights.abs()
            concentration = (abs_weights ** 2).sum(axis=1)  # Herfindahl concentration index
            num_positions = (abs_weights > 0.01).sum(axis=1)  # Number of significant positions

            # Plot concentration over time
            ax2.plot(concentration.index, concentration.values,
                     linewidth=1.5, color='#E74C3C', label='Concentration Index')
            ax2_twin = ax2.twinx()
            ax2_twin.plot(num_positions.index, num_positions.values,
                          linewidth=1.5, color='#3498DB', label='Active Positions', linestyle='--')

            ax2.set_title('Portfolio Concentration Evolution', fontsize=12, fontweight='semibold', pad=15)
            ax2.set_xlabel('Year', fontsize=10)
            ax2.set_ylabel('Concentration Index', color='#E74C3C', fontsize=10)
            ax2_twin.set_ylabel('Number of Active Positions', color='#3498DB', fontsize=10)

            ax2.grid(True, alpha=0.3)
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
            ax2.xaxis.set_major_locator(mdates.YearLocator(3))

            # Combined legend
            lines1, labels1 = ax2.get_legend_handles_labels()
            lines2, labels2 = ax2_twin.get_legend_handles_labels()
            ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper right')

            # ======== 3. ROLLING VOLATILITY & RISK METRICS ========
            # Calculate rolling metrics (quarterly windows)
            rolling_vol = portfolio_returns.percent.rolling(window=63).std() * np.sqrt(256)  # 63 = ~3 months
            rolling_sharpe = portfolio_returns.percent.rolling(window=252).mean() * 256 / (
                    portfolio_returns.percent.rolling(window=252).std() * np.sqrt(256))

            # Plot volatility over time
            ax3.plot(rolling_vol.index, rolling_vol.values,
                     linewidth=1.5, color='#9B59B6', label='Rolling Volatility (3M)')

            # Add target volatility line
            target_vol = 20.0  # From your config
            ax3.axhline(y=target_vol, color='#F39C12', linestyle='--', linewidth=2,
                        label=f'Target Vol ({target_vol}%)', alpha=0.8)

            ax3.set_title('Rolling Risk Metrics', fontsize=12, fontweight='semibold', pad=15)
            ax3.set_xlabel('Year', fontsize=10)
            ax3.set_ylabel('Annualized Volatility (%)', fontsize=10)
            ax3.grid(True, alpha=0.3)
            ax3.legend(loc='upper right')
            ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
            ax3.xaxis.set_major_locator(mdates.YearLocator(3))

            # ======== 4. ASSET CLASS ALLOCATION OVER TIME ========
            # Group instruments by asset class for allocation analysis
            asset_classes = {
                'Interest_Rates': ['US10', 'US2', 'SOFR'],
                'Equities': ['SP500_micro', 'NASDAQ', 'EUROSTX'],
                'Commodities': ['CORN', 'CRUDE_W', 'GOLD'],
                'FX': ['EUR', 'GBP', 'JPY']
            }

            # Calculate asset class weights over time
            asset_class_weights = {}
            for asset_class, instruments in asset_classes.items():
                available_instruments = [inst for inst in instruments if inst in weights.columns]
                if available_instruments:
                    asset_class_weights[asset_class] = weights[available_instruments].abs().sum(axis=1)

            # Create stacked area plot
            asset_df = pd.DataFrame(asset_class_weights)
            asset_df = asset_df.fillna(0)

            # Sample every 60 days for cleaner visualization
            asset_df_sampled = asset_df.iloc[::60, :]

            colors = ['#3498DB', '#E74C3C', '#F39C12', '#27AE60']
            ax4.stackplot(asset_df_sampled.index,
                          asset_df_sampled['Interest_Rates'],
                          asset_df_sampled['Equities'],
                          asset_df_sampled['Commodities'],
                          asset_df_sampled['FX'],
                          labels=['Interest Rates', 'Equities', 'Commodities', 'FX'],
                          colors=colors, alpha=0.8)

            ax4.set_title('Dynamic Asset Class Allocation', fontsize=12, fontweight='semibold', pad=15)
            ax4.set_xlabel('Year', fontsize=10)
            ax4.set_ylabel('Total Weight by Asset Class', fontsize=10)
            ax4.legend(loc='upper right', frameon=True, fancybox=True, shadow=True)
            ax4.grid(True, alpha=0.3)
            ax4.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
            ax4.xaxis.set_major_locator(mdates.YearLocator(3))

            # Adjust layout
            plt.tight_layout()
            plt.subplots_adjust(top=0.94, hspace=0.3, wspace=0.3)

            # Save the comprehensive analysis
            analysis_filename = f"{output_dir}/position_risk_analysis_{timestamp}.png"
            plt.savefig(analysis_filename, dpi=300, bbox_inches='tight',
                        facecolor='white', edgecolor='none')
            print(f"✓ Position & Risk analysis saved: {analysis_filename}")

            # Also save as PDF
            analysis_pdf = f"{output_dir}/position_risk_analysis_{timestamp}.pdf"
            plt.savefig(analysis_pdf, dpi=300, bbox_inches='tight',
                        facecolor='white', edgecolor='none')
            print(f"✓ PDF version saved: {analysis_pdf}")

            # Display the plot
            plt.show()

            return analysis_filename, analysis_pdf

        except ImportError as e:
            print(f"❌ Required libraries not available: {e}")
            print("   Install with: pip install matplotlib numpy")
            return None, None

        except Exception as e:
            print(f"❌ Error creating position/risk plots: {e}")
            return None, None

    def print_advanced_risk_analysis(self):
        """
        Print detailed risk analysis following Robert Carver's risk-first approach
        """
        if not self.results:
            return

        print(f"\n🔍 ADVANCED RISK ANALYSIS")
        print(f"{'─' * 50}")

        try:
            positions = self.results['optimized_positions']
            weights = self.results['optimized_weights']
            portfolio_returns = self.results['portfolio_returns'].percent

            # Position concentration analysis
            daily_total_positions = positions.abs().sum(axis=1)
            avg_daily_exposure = daily_total_positions.mean()
            max_daily_exposure = daily_total_positions.max()

            print(f"📍 POSITION METRICS")
            print(f"   Average daily positions: {avg_daily_exposure:.1f} contracts")
            print(f"   Maximum daily positions: {max_daily_exposure:.0f} contracts")
            print(f"   Position concentration:  {(positions != 0).sum(axis=1).mean():.1f} instruments/day")

            # Volatility analysis
            rolling_vol_quarterly = portfolio_returns.rolling(63).std() * np.sqrt(256)
            vol_of_vol = rolling_vol_quarterly.std()

            print(f"\n⚡ VOLATILITY ANALYSIS")
            print(f"   Target volatility:       20.0%")
            print(f"   Achieved volatility:     {portfolio_returns.std() * np.sqrt(256):.1f}%")
            print(f"   Volatility consistency:  {vol_of_vol:.1f}% (vol of vol)")
            print(f"   Vol control efficiency:  {20.0 / (portfolio_returns.std() * np.sqrt(256)):.2f}x")

            # Dynamic rebalancing frequency
            position_changes = positions.diff().abs().sum(axis=1)
            rebalance_days = (position_changes > 0).sum()
            rebalance_frequency = rebalance_days / len(positions) * 100

            print(f"\n🔄 DYNAMIC REBALANCING")
            print(f"   Rebalancing frequency:   {rebalance_frequency:.1f}% of trading days")
            print(f"   Total rebalance days:    {rebalance_days} out of {len(positions)}")
            print(f"   Avg changes per rebal:   {position_changes[position_changes > 0].mean():.1f} contracts")

        except Exception as e:
            print(f"⚠ Risk analysis calculation error: {e}")

    def compare_with_static_system(self):
        """Compare dynamic optimization with traditional static system"""
        print(f"\n🔍 DYNAMIC vs STATIC COMPARISON")
        print(f"{'─' * 40}")

        try:
            # FIXED: Use explicit imports instead of import *
            # Create static system for comparison using individual classes
            static_system = System([
                Account(),
                Portfolios(),  # CORRECTED: was PortfoliosEstimated
                PositionSizing(),
                RawData(),
                ForecastCombine(),  # CORRECTED: was ForecastCombineFixed
                ForecastScaleCap(),  # CORRECTED: was ForecastScaleCapFixed
                Rules()
            ], self.data_source, self.system.config)

            # Get static system performance
            static_returns = static_system.accounts.portfolio()
            dynamic_returns = self.results['portfolio_returns']

            print(f"Dynamic Sharpe:         {dynamic_returns.sharpe():.3f}")
            print(f"Static Sharpe:          {static_returns.sharpe():.3f}")
            print(f"Improvement:            {dynamic_returns.sharpe() - static_returns.sharpe():.3f}")

            print(f"Dynamic Vol:            {dynamic_returns.percent.std() * (256 ** 0.5):.1f}%")
            print(f"Static Vol:             {static_returns.percent.std() * (256 ** 0.5):.1f}%")

        except Exception as e:
            print(f"⚠ Static comparison unavailable: {str(e)}")
            print(f"   Note: Static comparison requires additional dependencies")


def main():
    """Main execution function"""
    print(f"🚀 ROBERT CARVER'S DYNAMIC OPTIMIZATION BACKTEST")
    print(f"Starting at: {datetime.now()}")
    print(f"Project directory: project_dynamic/")

    # Initialize backtester
    backtester = DynamicSystemBacktester()

    # Setup data source
    data_source = backtester.setup_data_source(data_type='csv')

    # Create system with config file
    system = backtester.create_system()

    # Run the backtest
    results = backtester.run_backtest()

    # Analyze results
    backtester.analyze_results()

    # Print advanced risk metrics
    backtester.print_advanced_risk_analysis()

    # Save results (includes plotting now)
    backtester.save_results()

    # Compare with static system (optional)
    try:
        backtester.compare_with_static_system()
    except Exception as e:
        print(f"⚠ Static system comparison skipped: {str(e)}")

    print(f"\n✅ BACKTEST COMPLETED SUCCESSFULLY")
    print(f"📊 Charts saved to: project_dynamic/results/")
    print(f"🔍 Check CSV files and performance plots for detailed analysis")


if __name__ == "__main__":
    main()