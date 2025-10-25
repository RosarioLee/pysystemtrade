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

        except Exception as e:
            print(f"❌ Error saving results: {str(e)}")

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

    # Save results
    backtester.save_results()

    # Compare with static system (optional - may fail due to dependencies)
    try:
        backtester.compare_with_static_system()
    except Exception as e:
        print(f"⚠ Static system comparison skipped: {str(e)}")

    print(f"\n✅ BACKTEST COMPLETED SUCCESSFULLY")
    print(f"Check project_dynamic/results/ for output files")


if __name__ == "__main__":
    main()