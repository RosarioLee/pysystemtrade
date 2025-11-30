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
import logging
# logging.basicConfig(level=logging.DEBUG)
import os
import sys
import warnings
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Add project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_dir)


# Additional imports for analysis
from syscore.constants import arg_not_supplied

# Modern pysystemtrade imports - Robert's latest approach
from systems.provided.rob_system.run_system import futures_system
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
from sysdata.config.configdata import Config
from turnover_analysis import RobertCarverTurnoverAnalyzer, quick_turnover_check

# Keep analysis imports
from syscore.constants import arg_not_supplied
import pandas as pd
import numpy as np


def debug_cost_calculation(data, instruments, date):
    """Debug: Print what optimizer sees"""
    print("\n" + "=" * 70)
    print("DEBUG: Cost Calculation at", date)
    print("=" * 70)

    for inst in instruments[:5]:  # First 5
        try:
            cost_obj = data.get_raw_cost_data(inst)
            price = data.daily_prices(inst).loc[date]

            slip = cost_obj.price_slippage
            block = cost_obj.value_of_block_commission
            pct = (slip + block) / price

            print(f"{inst:12s} ${slip + block:.4f} = {pct * 100:.4f}%")

            # CHECK: What does percentage_cost show?
            if hasattr(cost_obj, 'percentage_cost'):
                print(f"             percentage_cost attribute: {cost_obj.percentage_cost}")
                if cost_obj.percentage_cost == 0 and pct > 0:
                    print(f"             ⚠️  BUG: percentage_cost=0 but SR cost={pct:.6f}")
        except:
            pass
    print("=" * 70 + "\n")


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

    def setup_data_source(self):
        """Initialize CSV data source with date filtering"""
        print("\nSetting up data source...")

        try:
            from sysdata.sim.csv_futures_sim_data import csvFuturesSimData

            # Create data source
            data = csvFuturesSimData()

            # **ADD DATE FILTERING HERE**
            # Load config to get date range
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, "dynamic_backtest_config.yaml")

            if os.path.exists(config_path):
                import yaml
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)

                start_date = config.get('startdate', '2000-01-19')  # Match config
                end_date = config.get('enddate', None)

                print(f"✓ Filtering data: {start_date} to {end_date}")

                # Store for later use
                self.start_date = pd.Timestamp(start_date)
                self.end_date = pd.Timestamp(end_date)
            else:
                # Default to full range if no config
                self.start_date = None
                self.end_date = None

            self.data_source = data
            print("✓ CSV data source initialized")

            return data

        except Exception as e:
            print(f"❌ Error setting up data source: {str(e)}")
            raise

    def setup_file_logging(self, log_dir='backtest_logs'):
        """
        Setup REAL-TIME file logging for complete backtest monitoring.
        Unbuffered writes ensure you see progress as it happens.
        """
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f"{log_dir}/backtest_{timestamp}.log"

        # Create file handler with unbuffered mode
        file_handler = logging.FileHandler(
            log_filename,
            mode='a',  # Append mode
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)

        # Detailed format
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)

        # Add to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        root_logger.setLevel(logging.INFO)

        # Also add console handler so you see progress
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)  # Only warnings/errors to console
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        print(f"✅ Real-time logging to: {log_filename}")
        print(f"📊 Watch file grow: tail -f {log_filename}")
        return log_filename

    def monitor_backtest_progress(self):
        """
        Monitor and log backtest progress with key metrics.
        Call this AFTER system is created to track execution.

        Provides:
        - Date range being processed
        - Active position counts
        - Instrument participation
        - Performance indicators
        """
        logger = logging.getLogger('BacktestMonitor')
        logger.setLevel(logging.INFO)

        try:
            logger.info("=" * 60)
            logger.info("BACKTEST PROGRESS MONITORING")
            logger.info("=" * 60)

            # 1. Get optimized positions
            logger.info("Fetching optimized positions...")
            positions = self.system.optimisedPositions.get_optimised_position_df()

            # 2. Date range analysis
            total_dates = len(positions.index)
            start_date = positions.index[0]
            end_date = positions.index[-1]

            logger.info(f"📅 Processing {total_dates} dates")
            logger.info(f"📅 From: {start_date.strftime('%Y-%m-%d')}")
            logger.info(f"📅 To:   {end_date.strftime('%Y-%m-%d')}")
            logger.info(f"📅 Years: {(end_date - start_date).days / 365.25:.1f}")

            # 3. Position activity analysis
            non_zero_positions = (positions != 0).sum(axis=1)
            avg_positions = non_zero_positions.mean()
            max_positions = non_zero_positions.max()
            min_positions = non_zero_positions.min()

            logger.info(f"📊 Average positions per day: {avg_positions:.1f}")
            logger.info(f"📊 Maximum positions: {max_positions}")
            logger.info(f"📊 Minimum positions: {min_positions}")

            # 4. Instrument participation
            total_instruments = len(positions.columns)
            ever_traded = (positions != 0).any(axis=0).sum()
            participation_pct = (ever_traded / total_instruments) * 100

            logger.info(f"🎯 Instruments in universe: {total_instruments}")
            logger.info(f"🎯 Instruments ever traded: {ever_traded}")
            logger.info(f"🎯 Participation rate: {participation_pct:.1f}%")

            # 5. Most active instruments
            trade_frequency = (positions != 0).sum(axis=0)
            most_active = trade_frequency.nlargest(10)

            logger.info("🔥 Top 10 most active instruments:")
            for instrument, days in most_active.items():
                pct = (days / total_dates) * 100
                logger.info(f"   {instrument:15s}: {days:5d} days ({pct:5.1f}%)")

            # 6. Position distribution
            position_sizes = positions[positions != 0].abs()

            logger.info(f"📏 Position size statistics (contracts):")
            logger.info(f"   Mean:   {position_sizes.mean().mean():.2f}")
            logger.info(f"   Median: {position_sizes.median().median():.2f}")
            logger.info(f"   Max:    {position_sizes.max().max():.0f}")

            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ Progress monitoring failed: {e}")
            logger.error(f"   This is OK - backtest will continue")

    def log_optimization_milestones(self, positions_df):
        """
        Log key optimization milestones as backtest progresses.
        Call this periodically during backtest to track progress.

        Args:
            positions_df: Current positions dataframe
        """
        logger = logging.getLogger('OptimizationMilestones')

        try:
            total_dates = len(positions_df.index)

            # Log every 250 days (roughly once per trading year)
            for milestone in [250, 500, 1000, 2000, 3000, 4000, 5000]:
                if total_dates >= milestone and total_dates < milestone + 50:
                    current_date = positions_df.index[milestone - 1]
                    current_positions = positions_df.iloc[milestone - 1]
                    active_count = (current_positions != 0).sum()

                    logger.info(f"🎯 Milestone: {milestone} dates processed")
                    logger.info(f"   Current date: {current_date.strftime('%Y-%m-%d')}")
                    logger.info(f"   Active positions: {active_count}")
                    logger.info(f"   Progress: {(milestone / total_dates) * 100:.1f}%")

        except Exception as e:
            logger.debug(f"Milestone logging skipped: {e}")

    def enable_detailed_optimization_logging(self):
        """
        Enable DEBUG-level logging for optimization components.
        This shows EVERY optimization decision in detail.

        Warning: Creates large log files (100MB+) but invaluable for debugging.
        """
        print("🔍 Enabling detailed optimization logging...")

        # Set DEBUG level for key optimization modules
        optimization_modules = [
            'objectiveFunctionForGreedy',  # Core optimization logic
            'optimisedPositions',  # Position calculator
            'greedy_algo',  # Greedy algorithm
            'buffering',  # Speed control
            'portfolio',  # Portfolio construction
            'accounts',  # Account/cost calculations
        ]

        for module_name in optimization_modules:
            logger = logging.getLogger(module_name)
            logger.setLevel(logging.DEBUG)
            print(f"  ✓ {module_name}: DEBUG")

        print("✅ Detailed optimization logging enabled")
        print("⚠️  Warning: Log files will be much larger (50-200MB)")

    def setup_complete_logging(self, log_dir='backtest_logs'):
        """
        Capture EVERYTHING: both logging output AND console print statements.
        This mirrors exactly what you see in PyCharm's Run window.
        """
        import sys

        # Create log directory
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # ===== FILE 1: Complete output (print + logging) =====
        complete_log = f"{log_dir}/complete_output_{timestamp}.log"

        # ===== FILE 2: Just logging output =====
        logging_log = f"{log_dir}/logging_only_{timestamp}.log"

        # ===== Setup console output capture =====
        class TeeOutput:
            """Write to both file and console simultaneously"""

            def __init__(self, file_path, original_stream):
                self.file = open(file_path, 'a', encoding='utf-8')
                self.original = original_stream

            def write(self, data):
                self.file.write(data)
                self.file.flush()  # Immediate write
                self.original.write(data)

            def flush(self):
                self.file.flush()
                self.original.flush()

        # Redirect stdout (print statements)
        sys.stdout = TeeOutput(complete_log, sys.stdout)

        # Redirect stderr (error messages)
        sys.stderr = TeeOutput(complete_log, sys.stderr)

        # ===== Setup logging module capture =====
        # Configure logging to go to BOTH files
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Handler for complete log
        complete_handler = logging.FileHandler(complete_log, mode='a', encoding='utf-8')
        complete_handler.setLevel(logging.DEBUG)
        complete_handler.setFormatter(formatter)

        # Handler for logging-only log
        logging_handler = logging.FileHandler(logging_log, mode='a', encoding='utf-8')
        logging_handler.setLevel(logging.INFO)
        logging_handler.setFormatter(formatter)

        # Add to root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(complete_handler)
        root_logger.addHandler(logging_handler)

        print("=" * 70)
        print("📝 COMPLETE OUTPUT LOGGING ENABLED")
        print("=" * 70)
        print(f"✅ Complete output (print + logging): {complete_log}")
        print(f"✅ Logging only:                      {logging_log}")
        print(f"✅ All console output will be saved")
        print("=" * 70)

        return complete_log, logging_log

    def create_system(self, custom_config=None):
        """Create system using Robert's futures_system() with correct parameters"""
        print("Creating dynamic optimization system...")

        try:
            from systems.provided.rob_system.run_system import futures_system

            # Get config path
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, "dynamic_backtest_config.yaml")

            # Verify config exists
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"Config not found: {config_path}")

            print(f"✓ Config found: {config_path}")

            # CORRECT: futures_system() uses 'sim_data' and 'config_filename'
            # (Different versions of pysystemtrade use different parameter names)
            self.system = futures_system(
                sim_data=self.data_source,  # Use sim_data, not data
                config_filename=config_path  # Use config_filename, not config
            )

            print("✅ System created with Robert's futures_system()")
            print(f"✅ Using config: {config_path}")
            print(f"✅ Instruments: {len(self.system.get_instrument_list())}")

            # Verify cost system is working
            # self.verify_system_costs()

            return self.system

        except Exception as e:
            print(f"❌ Error creating system: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    def verify_config_loading(self):
        """Verify config loaded correctly"""
        print("\n📋 Config Verification:")
        print("-" * 50)

        config = self.system.config

        # Check key settings
        print(f"use_SR_costs: {getattr(config, 'use_SR_costs', 'NOT SET')}")
        print(f"use_instrument_weight_estimates: {getattr(config, 'use_instrument_weight_estimates', 'NOT SET')}")
        print(f"percentage_vol_target: {getattr(config, 'percentage_vol_target', 'NOT SET')}")

        # Check ignored instruments
        if hasattr(config, 'ignore_instruments'):
            ignored = config.ignore_instruments
            print(f"ignore_instruments: {ignored}")
        else:
            ignored = []
            print("ignore_instruments: NOT SET")

        # Check actual instrument list
        actual_instruments = self.system.get_instrument_list()
        config_instruments = config.instruments if hasattr(config, 'instruments') else []

        print(f"\nInstruments in config: {len(config_instruments)}")
        print(f"Instruments in system: {len(actual_instruments)}")
        print(f"Excluded:              {len(config_instruments) - len(actual_instruments)}")

        print("-" * 50 + "\n")

    def run_backtest(self, start_date=None, end_date=None):
        """Execute the backtest using modern approach"""
        print(f"\n{'=' * 60}")
        print(f"RUNNING DYNAMIC OPTIMIZATION BACKTEST")
        print(f"{'=' * 60}")
        backtest_start = datetime.now()

        try:
            # Simple validation instead of complex Part 1, 2, 3 validation
            self.simple_system_validation()

            # Get portfolio performance - futures_system() handles optimization automatically
            print("Calculating portfolio performance...")
            portfolio_returns = self.system.accounts.portfolio()

            # Check if dynamic optimization results are available
            try:
                optimised_returns = self.system.accounts.optimised_portfolio()
                print("✓ Using dynamic optimization results")
                portfolio_returns = optimised_returns
            except (AttributeError, Exception):
                print("✓ Using standard portfolio results")

            # Store results
            self.results = {
                'portfolio_returns': portfolio_returns,
                'backtest_start_time': backtest_start,
                'backtest_end_time': datetime.now()
            }

            # Add position and weight data if available
            try:
                if hasattr(self.system, 'optimisedPositions'):
                    self.results['optimized_positions'] = self.system.optimisedPositions.get_optimised_position_df()
                    self.results['optimized_weights'] = self.system.optimisedPositions.get_optimised_weights_df()
                    print("✓ Dynamic optimization data retrieved")
            except:
                print("⚠ Dynamic optimization data not available - using standard results")

            # Performance summary
            duration = datetime.now() - backtest_start
            print(f"\n✅ BACKTEST COMPLETED")
            print(f"⏱ Duration: {duration}")
            print(f"📊 Sharpe Ratio: {portfolio_returns.sharpe():.3f}")
            print(f"📈 Annual Return: {portfolio_returns.percent.mean() * 256:.1f}%")
            print(f"📉 Annual Volatility: {portfolio_returns.percent.std() * (256 ** 0.5):.1f}%")

            return self.results

        except Exception as e:
            print(f"❌ Backtest failed: {str(e)}")
            raise

    def validate_buffer_configuration(self):
        """Validate and display position buffering configuration"""
        try:
            config = self.system.config

            # Check buffering method
            if hasattr(config, 'buffer_method'):
                buffer_method = config.buffer_method
                buffer_size = getattr(config, 'buffer_size', 0.0)
                buffer_trade_to_edge = getattr(config, 'buffer_trade_to_edge', False)

                print(f"✓ Position buffering configured:")
                print(f"  Method: {buffer_method}")
                print(f"  Buffer size: {buffer_size * 100:.1f}%")
                print(f"  Trade to edge: {buffer_trade_to_edge}")

                if buffer_method == "position" and buffer_size >= 0.05:
                    print(f"✓ Proper position buffering for small system")
                else:
                    print(f"⚠ Warning: Buffer configuration may cause excessive turnover")

            else:
                print(f"⚠ Warning: No buffering configured - may cause overtrading")

        except Exception as e:
            print(f"❌ Buffer validation failed: {e}")

    def simple_system_validation(self):
        """Simple validation without complex correlation calculations"""
        print("\n🔧 SYSTEM VALIDATION")
        print("─" * 30)

        # Check system has required stages
        required_attributes = ['accounts', 'portfolio', 'config']
        for attr in required_attributes:
            if hasattr(self.system, attr):
                print(f"✓ {attr} available")
            else:
                print(f"❌ Missing {attr}")

        # Check if dynamic optimization is configured
        if hasattr(self.system.config, 'use_instrument_weight_estimates'):
            if self.system.config.use_instrument_weight_estimates:
                print("✓ Dynamic portfolio optimization enabled")
            else:
                print("⚠ Using static portfolio weights")

        print("✓ System validation completed")

    def analyze_small_system_performance(self):
        """Analyze performance specific to small system constraints"""
        if not self.results:
            return

        print(f"\n🔬 SMALL SYSTEM ANALYSIS")
        print(f"{'─' * 40}")

        try:
            positions = self.results['optimized_positions']
            weights = self.results['optimized_weights']

            # Integer constraint analysis
            non_integer_positions = positions[positions != positions.round()].count().sum()
            total_position_observations = (positions != 0).sum().sum()

            print(f"📊 INTEGER CONSTRAINT COMPLIANCE")
            print(f"   Non-integer positions: {non_integer_positions}")
            print(f"   Total position observations: {total_position_observations}")
            print(
                f"   Integer compliance: {(1 - non_integer_positions / max(total_position_observations, 1)) * 100:.1f}%")

            # Sparse portfolio analysis
            avg_positions_per_day = (positions != 0).sum(axis=1).mean()
            max_positions_per_day = (positions != 0).sum(axis=1).max()

            print(f"📈 PORTFOLIO SPARSITY")
            print(f"   Average active positions: {avg_positions_per_day:.1f} instruments")
            print(f"   Maximum active positions: {max_positions_per_day} instruments")
            print(f"   Sparsity ratio: {avg_positions_per_day / len(positions.columns) * 100:.1f}%")

            # Turnover analysis (key for small system)
            position_changes = positions.diff().abs().sum(axis=1)
            avg_daily_turnover = position_changes.mean()

            print(f"🔄 TURNOVER METRICS")
            print(f"   Average daily turnover: {avg_daily_turnover:.1f} contracts")
            print(f"   Turnover efficiency: {(avg_daily_turnover > 0).sum() / len(positions) * 100:.1f}% active days")

        except Exception as e:
            print(f"⚠ Small system analysis error: {e}")

    def analyze_results(self):
        """Analyze and display backtest results"""
        # Use dynamic optimization results if available
        try:
            portfolio_returns = self.system.accounts.optimised_portfolio().percent
            print(f"✓ Analyzing dynamic optimization results")
        except AttributeError:
            portfolio_returns = self.system.accounts.portfolio().percent
            print(f"⚠ Analyzing standard (non-optimized) results")

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

    def analyze_turnover_comprehensive(self):
        """
        Comprehensive turnover analysis following Robert Carver's methodology
        """
        if not self.system:
            print("❌ No system available for turnover analysis")
            return

        print(f"\n🔄 COMPREHENSIVE TURNOVER ANALYSIS")
        print(f"{'═' * 60}")

        # Initialize Robert's turnover analyzer
        analyzer = RobertCarverTurnoverAnalyzer(self.system)

        # Extract all turnover metrics
        turnover_results = analyzer.extract_all_turnover_metrics()

        # Generate comprehensive report
        report_file = analyzer.generate_turnover_report('project_dynamic/results')

        # Create visualization plots
        plot_file = analyzer.plot_turnover_analysis('project_dynamic/results')

        # Store results for later use
        self.results['turnover_analysis'] = turnover_results

        return turnover_results

    def verify_cost_loading(self):
        # Test that costs are being loaded from spreadcosts.csv
        print("🔍 COST SYSTEM VERIFICATION")
        print("─" * 40)

        test_instruments = ['US10', 'BUND', 'SP500_micro', 'CORN', 'EUR_micro']

        for instrument in test_instruments:
            try:
                if instrument in self.data_source.get_instrument_list():
                    cost_data = self.data_source.get_raw_cost_data(instrument)
                    spread_cost = cost_data.price_slippage  # ✅ CORRECT API
                    commission = cost_data.value_of_block_commission  # ✅ ADDITIONAL INFO
                    print(f"✓ {instrument}: spread={spread_cost}, commission={commission}")

                    if spread_cost == 0.0:
                        print(f"  ❌ {instrument} has zero cost!")
                        return False
                    else:
                        print(f"  ✅ {instrument} has valid cost")
            except Exception as e:
                print(f"❌ {instrument}: Error getting cost - {e}")
                return False

        print("✓ Cost system working properly")
        return True


def main():
    """Main execution with full analysis pipeline"""
    print(f"\n🚀 ROBERT CARVER'S DYNAMIC OPTIMIZATION BACKTEST")
    print(f"Starting at: {datetime.now()}")
    print(f"Project directory: project_dynamic/")
    print("=" * 70)

    # Initialize
    backtester = DynamicSystemBacktester()

    # Setup logging (optional - comment out if too verbose)
    backtester.setup_file_logging()

    # Setup data
    backtester.setup_data_source()

    # Create system
    print("\n🔧 Creating system...")
    system = backtester.create_system()
    print("✅ System created successfully\n")

    # Verify configuration
    backtester.verify_config_loading()

    # ============================================================
    # RUN BACKTEST
    # ============================================================
    print("\n" + "=" * 70)
    print("📈 RUNNING BACKTEST")
    print("=" * 70)

    results = backtester.run_backtest()

    # ============================================================
    # COMPREHENSIVE ANALYSIS SUITE
    # ============================================================

    print("\n" + "=" * 70)
    print("📊 GENERATING COMPREHENSIVE ANALYSIS")
    print("=" * 70)

    # 1. Basic statistics
    print("\n1️⃣ Analyzing Results...")
    backtester.analyze_results()

    # 2. Small system specific metrics
    print("\n2️⃣ Small System Performance Analysis...")
    backtester.analyze_small_system_performance()

    # 3. Advanced risk analysis
    print("\n3️⃣ Advanced Risk Analysis...")
    backtester.print_advanced_risk_analysis()

    # 4. Save results to CSV files
    print("\n4️⃣ Saving Results...")
    backtester.save_results(output_dir='project_dynamic/results')

    # 5. Create performance plots (equity curve + drawdown)
    print("\n5️⃣ Creating Performance Plots...")
    performance_plots = backtester.create_performance_plots(
        output_dir='project_dynamic/results'
    )

    # 6. Create position and risk analysis plots
    print("\n6️⃣ Creating Position & Risk Analysis Plots...")
    position_plots = backtester.create_position_and_risk_plots(
        output_dir='project_dynamic/results'
    )

    # 7. Turnover analysis (if turnover_analysis module is available)
    print("\n7️⃣ Turnover Analysis...")
    try:
        turnover_results = backtester.analyze_turnover_comprehensive()
        print("✓ Turnover analysis completed")
    except (ImportError, AttributeError) as e:
        print(f"⚠ Turnover analysis not available: {e}")
        print("  (This is optional - basic turnover metrics already shown)")

    # ============================================================
    # FINAL SUMMARY
    # ============================================================

    print("\n" + "=" * 70)
    print("✅ BACKTEST COMPLETED SUCCESSFULLY")
    print("=" * 70)

    duration = datetime.now() - backtester.start_time
    print(f"\n⏱  Total Duration: {duration}")
    print(f"📁 Results saved to: project_dynamic/results/")

    # Print key metrics summary
    portfolio_returns = results['portfolio_returns']
    print(f"\n📊 KEY PERFORMANCE METRICS:")
    print(f"   Sharpe Ratio: {portfolio_returns.sharpe():.3f}")
    print(f"   Annual Return: {portfolio_returns.percent.mean() * 256:.1f}%")
    print(f"   Annual Vol: {portfolio_returns.percent.std() * (256 ** 0.5):.1f}%")
    print(f"   Max Drawdown: {portfolio_returns.percent.drawdown().min():.1f}%")
    try:
        print(f"   Calmar Ratio: {portfolio_returns.calmar():.3f}")
    except:
        print(f"   Calmar Ratio: N/A")

    # Print file locations
    print(f"\n📁 OUTPUT FILES:")
    print(f"   • Positions CSV")
    print(f"   • Weights CSV")
    print(f"   • Performance plots (PNG + PDF)")
    print(f"   • Position/Risk analysis (PNG + PDF)")
    print(f"   • Performance summary (TXT)")

    print(f"\n✅ All analysis complete! Check 'project_dynamic/results/' directory")
    print(f"Finished at: {datetime.now()}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
