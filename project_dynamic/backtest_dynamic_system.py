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
warnings.filterwarnings("ignore")

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

# Import static weight extraction modules
try:
    from extract_static_weights import ForecastWeightExtractor
    from create_static_config import StaticConfigGenerator
    STATIC_WEIGHTS_AVAILABLE = True
except ImportError:
    print("⚠️  Static weight modules not found")
    STATIC_WEIGHTS_AVAILABLE = False

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
            if hasattr(cost_obj, "percentage_cost"):
                print(
                    f"             percentage_cost attribute: {cost_obj.percentage_cost}"
                )
                if cost_obj.percentage_cost == 0 and pct > 0:
                    print(
                        f"             ⚠️  BUG: percentage_cost=0 but SR cost={pct:.6f}"
                    )
        except:
            pass
    print("=" * 70 + "\n")


class DynamicSystemBacktester:
    """
    Comprehensive backtesting framework for Robert Carver's dynamic optimization system
    """

    def __init__(self, config_file="project_dynamic/dynamic_backtest_config.yaml"):
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

                with open(config_path, "r") as f:
                    config = yaml.safe_load(f)

                start_date = config.get("startdate", "2000-01-19")  # Match config
                end_date = config.get("enddate", None)

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

    def setup_file_logging(self, log_dir="backtest_logs"):
        """
        Setup REAL-TIME file logging for complete backtest monitoring.
        Unbuffered writes ensure you see progress as it happens.
        """
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{log_dir}/backtest_{timestamp}.log"

        # Create file handler with unbuffered mode
        file_handler = logging.FileHandler(
            log_filename, mode="a", encoding="utf-8"  # Append mode
        )
        file_handler.setLevel(logging.INFO)

        # Detailed format
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
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
        logger = logging.getLogger("BacktestMonitor")
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
        logger = logging.getLogger("OptimizationMilestones")

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
            "objectiveFunctionForGreedy",  # Core optimization logic
            "optimisedPositions",  # Position calculator
            "greedy_algo",  # Greedy algorithm
            "buffering",  # Speed control
            "portfolio",  # Portfolio construction
            "accounts",  # Account/cost calculations
        ]

        for module_name in optimization_modules:
            logger = logging.getLogger(module_name)
            logger.setLevel(logging.DEBUG)
            print(f"  ✓ {module_name}: DEBUG")

        print("✅ Detailed optimization logging enabled")
        print("⚠️  Warning: Log files will be much larger (50-200MB)")

    def setup_complete_logging(self, log_dir="backtest_logs"):
        """
        Capture EVERYTHING: both logging output AND console print statements.
        This mirrors exactly what you see in PyCharm's Run window.
        """
        import sys

        # Create log directory
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # ===== FILE 1: Complete output (print + logging) =====
        complete_log = f"{log_dir}/complete_output_{timestamp}.log"

        # ===== FILE 2: Just logging output =====
        logging_log = f"{log_dir}/logging_only_{timestamp}.log"

        # ===== Setup console output capture =====
        class TeeOutput:
            """Write to both file and console simultaneously"""

            def __init__(self, file_path, original_stream):
                self.file = open(file_path, "a", encoding="utf-8")
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
            "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Handler for complete log
        complete_handler = logging.FileHandler(complete_log, mode="a", encoding="utf-8")
        complete_handler.setLevel(logging.DEBUG)
        complete_handler.setFormatter(formatter)

        # Handler for logging-only log
        logging_handler = logging.FileHandler(logging_log, mode="a", encoding="utf-8")
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
                config_filename=config_path,  # Use config_filename, not config
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
        print(
            f"use_instrument_weight_estimates: {getattr(config, 'use_instrument_weight_estimates', 'NOT SET')}"
        )
        print(
            f"percentage_vol_target: {getattr(config, 'percentage_vol_target', 'NOT SET')}"
        )

        # Check ignored instruments
        if hasattr(config, "ignore_instruments"):
            ignored = config.ignore_instruments
            print(f"ignore_instruments: {ignored}")
        else:
            ignored = []
            print("ignore_instruments: NOT SET")

        # Check actual instrument list
        actual_instruments = self.system.get_instrument_list()
        config_instruments = (
            config.instruments if hasattr(config, "instruments") else []
        )

        print(f"\nInstruments in config: {len(config_instruments)}")
        print(f"Instruments in system: {len(actual_instruments)}")
        print(
            f"Excluded:              {len(config_instruments) - len(actual_instruments)}"
        )

        print("-" * 50 + "\n")

    def run_backtest(self, start_date=None, end_date=None, extract_static=False):
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
                "portfolio_returns": portfolio_returns,
                "backtest_start_time": backtest_start,
                "backtest_end_time": datetime.now(),
            }

            # Add position and weight data if available
            try:
                if hasattr(self.system, "optimisedPositions"):
                    self.results[
                        "optimized_positions"
                    ] = self.system.optimisedPositions.get_optimised_position_df()
                    self.results[
                        "optimized_weights"
                    ] = self.system.optimisedPositions.get_optimised_weights_df()
                    print("✓ Dynamic optimization data retrieved")
            except:
                print(
                    "⚠ Dynamic optimization data not available - using standard results"
                )

            # Performance summary
            duration = datetime.now() - backtest_start
            print(f"\n✅ BACKTEST COMPLETED")
            print(f"⏱ Duration: {duration}")
            print(f"📊 Sharpe Ratio: {portfolio_returns.sharpe():.3f}")
            print(f"📈 Annual Return: {portfolio_returns.percent.mean() * 256:.1f}%")
            print(
                f"📉 Annual Volatility: {portfolio_returns.percent.std() * (256 ** 0.5):.1f}%"
            )

            # ============================================================
            # ADD THESE LINES HERE (just before "return self.results")
            # ============================================================

            # Save system to pickle for future analysis
            pickle_path = self.save_system_to_pickle()

            # Store pickle path in results for reference
            if pickle_path:
                self.results['pickle_path'] = pickle_path

            # Auto-extract static weights if requested
            if extract_static:
                print(f"\n{'=' * 70}")
                print("AUTO-EXTRACTING STATIC WEIGHTS")
                print(f"{'=' * 70}")
                self.extract_and_generate_static_weights()

            # ============================================================
            # END OF NEW CODE
            # ============================================================

            return self.results

        except Exception as e:
            print(f"❌ Backtest failed: {str(e)}")
            raise

    def validate_buffer_configuration(self):
        """Validate and display position buffering configuration"""
        try:
            config = self.system.config

            # Check buffering method
            if hasattr(config, "buffer_method"):
                buffer_method = config.buffer_method
                buffer_size = getattr(config, "buffer_size", 0.0)
                buffer_trade_to_edge = getattr(config, "buffer_trade_to_edge", False)

                print(f"✓ Position buffering configured:")
                print(f"  Method: {buffer_method}")
                print(f"  Buffer size: {buffer_size * 100:.1f}%")
                print(f"  Trade to edge: {buffer_trade_to_edge}")

                if buffer_method == "position" and buffer_size >= 0.05:
                    print(f"✓ Proper position buffering for small system")
                else:
                    print(
                        f"⚠ Warning: Buffer configuration may cause excessive turnover"
                    )

            else:
                print(f"⚠ Warning: No buffering configured - may cause overtrading")

        except Exception as e:
            print(f"❌ Buffer validation failed: {e}")

    def simple_system_validation(self):
        """Simple validation without complex correlation calculations"""
        print("\n🔧 SYSTEM VALIDATION")
        print("─" * 30)

        # Check system has required stages
        required_attributes = ["accounts", "portfolio", "config"]
        for attr in required_attributes:
            if hasattr(self.system, attr):
                print(f"✓ {attr} available")
            else:
                print(f"❌ Missing {attr}")

        # Check if dynamic optimization is configured
        if hasattr(self.system.config, "use_instrument_weight_estimates"):
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
            positions = self.results["optimized_positions"]
            weights = self.results["optimized_weights"]

            # Integer constraint analysis
            non_integer_positions = (
                positions[positions != positions.round()].count().sum()
            )
            total_position_observations = (positions != 0).sum().sum()

            print(f"📊 INTEGER CONSTRAINT COMPLIANCE")
            print(f"   Non-integer positions: {non_integer_positions}")
            print(f"   Total position observations: {total_position_observations}")
            print(
                f"   Integer compliance: {(1 - non_integer_positions / max(total_position_observations, 1)) * 100:.1f}%"
            )

            # Sparse portfolio analysis
            avg_positions_per_day = (positions != 0).sum(axis=1).mean()
            max_positions_per_day = (positions != 0).sum(axis=1).max()

            print(f"📈 PORTFOLIO SPARSITY")
            print(
                f"   Average active positions: {avg_positions_per_day:.1f} instruments"
            )
            print(f"   Maximum active positions: {max_positions_per_day} instruments")
            print(
                f"   Sparsity ratio: {avg_positions_per_day / len(positions.columns) * 100:.1f}%"
            )

            # Turnover analysis (key for small system)
            position_changes = positions.diff().abs().sum(axis=1)
            avg_daily_turnover = position_changes.mean()

            print(f"🔄 TURNOVER METRICS")
            print(f"   Average daily turnover: {avg_daily_turnover:.1f} contracts")
            print(
                f"   Turnover efficiency: {(avg_daily_turnover > 0).sum() / len(positions) * 100:.1f}% active days"
            )

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

    def extract_and_generate_static_weights(self):
        """Auto-extract static weights after backtest completes."""

        print("\n" + "=" * 70)
        print("AUTO-EXTRACTING STATIC WEIGHTS")
        print("=" * 70)

        try:
            from extract_static_weights import ForecastWeightExtractor
            from create_static_config import StaticConfigGenerator

            # Step 1: Extract forecast weights
            print("\nStep 1: Extracting forecast weights...")
            extractor = ForecastWeightExtractor(system=self.system)

            # ✅ CORRECTED METHOD NAME
            extraction_results = extractor.extract_all_forecast_weights()

            # Step 2: Run full analysis
            print("\nStep 2: Running comprehensive analysis...")
            recommended_weights = extractor.run_full_analysis(
                cost_threshold=0.13,
                weight_method='average_last_2y',
                save_plots=True
            )

            # Step 3: Generate static config
            print("\nStep 3: Generating static configuration...")
            generator = StaticConfigGenerator(
                recommended_weights=recommended_weights,
                base_config_path=self.config_file
            )

            config_file = generator.generate_static_config(
                output_path="results/static_config.yaml"
            )

            print("\n" + "=" * 70)
            print("✓ STATIC WEIGHT EXTRACTION COMPLETE")
            print("=" * 70)
            print(f"\nGenerated files:")
            print(f"  - Forecast weights: results/forecast_weights_timeseries/")
            print(f"  - Analysis: results/static_weight_analysis/")
            print(f"  - Static config: {config_file}")
            print("\nNext: Run backtest with the new static config!")

            return {
                'extractor': extractor,
                'recommended_weights': recommended_weights,
                'config_file': config_file
            }

        except Exception as e:
            print(f"\n❌ Static weight extraction failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def save_results(self, output_dir="project_dynamic/results"):
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
            self.results["optimized_positions"].to_csv(positions_file)
            print(f"✓ Positions saved: {positions_file}")

            # Save weights
            weights_file = f"{output_dir}/optimized_weights_{timestamp}.csv"
            self.results["optimized_weights"].to_csv(weights_file)
            print(f"✓ Weights saved: {weights_file}")

            # Save performance summary
            portfolio_returns = self.results["portfolio_returns"]
            summary_file = f"{output_dir}/performance_summary_{timestamp}.txt"

            with open(summary_file, "w") as f:
                f.write(f"Dynamic Optimization Backtest Results\n")
                f.write(f"Generated: {datetime.now()}\n")
                f.write(f"{'=' * 50}\n\n")
                f.write(f"Sharpe Ratio: {portfolio_returns.sharpe():.3f}\n")
                f.write(
                    f"Annual Return: {portfolio_returns.percent.mean() * 256:.1f}%\n"
                )
                f.write(
                    f"Annual Volatility: {portfolio_returns.percent.std() * (256 ** 0.5):.1f}%\n"
                )
                f.write(
                    f"Max Drawdown: {portfolio_returns.percent.drawdown().min():.1f}%\n"
                )
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

    def create_performance_plots(self, output_dir="project_dynamic/results"):
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
            portfolio_returns = self.results["portfolio_returns"]

            # Calculate equity curve (cumulative returns)
            equity_curve = (1 + portfolio_returns.percent / 100).cumprod()

            # Calculate drawdown series
            rolling_max = equity_curve.cummax()
            drawdown = (equity_curve / rolling_max - 1) * 100  # Convert to percentage

            # Create timestamp for file naming
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Set up the plotting style (Robert Carver prefers clean, professional charts)
            plt.style.use("default")
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
            fig.suptitle(
                "Robert Carver Dynamic Optimization System - Performance Analysis",
                fontsize=16,
                fontweight="bold",
                y=0.98,
            )

            # ======== EQUITY CURVE PLOT ========
            ax1.plot(
                equity_curve.index,
                equity_curve.values,
                linewidth=1.5,
                color="#2E86AB",
                label="Dynamic Portfolio",
            )
            ax1.set_title(
                "Cumulative Equity Curve", fontsize=14, fontweight="semibold", pad=20
            )
            ax1.set_ylabel("Portfolio Value (Base = 1.0)", fontsize=12)
            ax1.grid(True, alpha=0.3, linestyle="-", linewidth=0.5)
            ax1.legend(loc="upper left", frameon=True, fancybox=True, shadow=True)

            # Format x-axis dates
            ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
            ax1.xaxis.set_major_locator(mdates.YearLocator(2))

            # Add key statistics as text box
            final_value = equity_curve.iloc[-1]
            total_return = (final_value - 1) * 100
            sharpe = portfolio_returns.sharpe()

            stats_text = f"Total Return: {total_return:.1f}%\nSharpe Ratio: {sharpe:.3f}\nFinal Value: {final_value:.2f}"
            ax1.text(
                0.02,
                0.98,
                stats_text,
                transform=ax1.transAxes,
                verticalalignment="top",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
                fontsize=10,
            )

            # ======== DRAWDOWN PLOT ========
            ax2.fill_between(
                drawdown.index,
                drawdown.values,
                0,
                color="#A23B72",
                alpha=0.6,
                label="Drawdown",
            )
            ax2.plot(drawdown.index, drawdown.values, linewidth=1, color="#A23B72")
            ax2.set_title(
                "Drawdown Analysis", fontsize=14, fontweight="semibold", pad=20
            )
            ax2.set_xlabel("Year", fontsize=12)
            ax2.set_ylabel("Drawdown (%)", fontsize=12)
            ax2.grid(True, alpha=0.3, linestyle="-", linewidth=0.5)
            ax2.legend(loc="lower right", frameon=True, fancybox=True, shadow=True)

            # Format x-axis dates
            ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
            ax2.xaxis.set_major_locator(mdates.YearLocator(2))

            # Add max drawdown annotation
            max_dd = drawdown.min()
            max_dd_date = drawdown.idxmin()
            ax2.annotate(
                f"Max DD: {max_dd:.1f}%",
                xy=(max_dd_date, max_dd),
                xytext=(max_dd_date, max_dd + 5),
                arrowprops=dict(arrowstyle="->", color="red", lw=1.5),
                fontsize=10,
                ha="center",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7),
            )

            # Adjust layout and save
            plt.tight_layout()
            plt.subplots_adjust(top=0.93)

            # Save the plot
            plot_filename = f"{output_dir}/performance_analysis_{timestamp}.png"
            plt.savefig(
                plot_filename,
                dpi=300,
                bbox_inches="tight",
                facecolor="white",
                edgecolor="none",
            )
            print(f"✓ Performance plots saved: {plot_filename}")

            # Also save as PDF for publication quality
            pdf_filename = f"{output_dir}/performance_analysis_{timestamp}.pdf"
            plt.savefig(
                pdf_filename,
                dpi=300,
                bbox_inches="tight",
                facecolor="white",
                edgecolor="none",
            )
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

    def create_position_and_risk_plots(self, output_dir="project_dynamic/results"):
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
            positions = self.results["optimized_positions"]
            weights = self.results["optimized_weights"]
            portfolio_returns = self.results["portfolio_returns"]

            # Create timestamp for file naming
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Set up professional styling
            plt.style.use("default")
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle(
                "Robert Carver Dynamic System - Position Evolution & Risk Analysis",
                fontsize=16,
                fontweight="bold",
                y=0.98,
            )

            # ======== 1. POSITION EVOLUTION HEATMAP ========
            # Sample positions every 30 days for visibility
            positions_sampled = positions.iloc[::30, :]

            # Create heatmap of positions over time
            im1 = ax1.imshow(
                positions_sampled.T,
                aspect="auto",
                cmap="RdBu_r",
                interpolation="nearest",
                alpha=0.8,
            )

            ax1.set_title(
                "Position Evolution Over Time (Contract Sizes)",
                fontsize=12,
                fontweight="semibold",
                pad=15,
            )
            ax1.set_xlabel("Time (sampled every 30 days)", fontsize=10)
            ax1.set_ylabel("Instruments", fontsize=10)

            # Set y-axis labels to instrument names
            ax1.set_yticks(range(len(positions.columns)))
            ax1.set_yticklabels(positions.columns, fontsize=9)

            # Set x-axis labels to dates (every 2 years)
            date_indices = range(0, len(positions_sampled), len(positions_sampled) // 8)
            ax1.set_xticks(date_indices)
            ax1.set_xticklabels(
                [positions_sampled.index[i].strftime("%Y") for i in date_indices],
                rotation=45,
                fontsize=9,
            )

            # Add colorbar
            cbar1 = plt.colorbar(im1, ax=ax1, shrink=0.8)
            cbar1.set_label("Position Size (Contracts)", fontsize=9)

            # ======== 2. PORTFOLIO CONCENTRATION OVER TIME ========
            # Calculate concentration metrics
            abs_weights = weights.abs()
            concentration = (abs_weights**2).sum(
                axis=1
            )  # Herfindahl concentration index
            num_positions = (abs_weights > 0.01).sum(
                axis=1
            )  # Number of significant positions

            # Plot concentration over time
            ax2.plot(
                concentration.index,
                concentration.values,
                linewidth=1.5,
                color="#E74C3C",
                label="Concentration Index",
            )
            ax2_twin = ax2.twinx()
            ax2_twin.plot(
                num_positions.index,
                num_positions.values,
                linewidth=1.5,
                color="#3498DB",
                label="Active Positions",
                linestyle="--",
            )

            ax2.set_title(
                "Portfolio Concentration Evolution",
                fontsize=12,
                fontweight="semibold",
                pad=15,
            )
            ax2.set_xlabel("Year", fontsize=10)
            ax2.set_ylabel("Concentration Index", color="#E74C3C", fontsize=10)
            ax2_twin.set_ylabel(
                "Number of Active Positions", color="#3498DB", fontsize=10
            )

            ax2.grid(True, alpha=0.3)
            ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
            ax2.xaxis.set_major_locator(mdates.YearLocator(3))

            # Combined legend
            lines1, labels1 = ax2.get_legend_handles_labels()
            lines2, labels2 = ax2_twin.get_legend_handles_labels()
            ax2.legend(lines1 + lines2, labels1 + labels2, loc="upper right")

            # ======== 3. ROLLING VOLATILITY & RISK METRICS ========
            # Calculate rolling metrics (quarterly windows)
            rolling_vol = portfolio_returns.percent.rolling(window=63).std() * np.sqrt(
                256
            )  # 63 = ~3 months
            rolling_sharpe = (
                portfolio_returns.percent.rolling(window=252).mean()
                * 256
                / (portfolio_returns.percent.rolling(window=252).std() * np.sqrt(256))
            )

            # Plot volatility over time
            ax3.plot(
                rolling_vol.index,
                rolling_vol.values,
                linewidth=1.5,
                color="#9B59B6",
                label="Rolling Volatility (3M)",
            )

            # Add target volatility line
            target_vol = 20.0  # From your config
            ax3.axhline(
                y=target_vol,
                color="#F39C12",
                linestyle="--",
                linewidth=2,
                label=f"Target Vol ({target_vol}%)",
                alpha=0.8,
            )

            ax3.set_title(
                "Rolling Risk Metrics", fontsize=12, fontweight="semibold", pad=15
            )
            ax3.set_xlabel("Year", fontsize=10)
            ax3.set_ylabel("Annualized Volatility (%)", fontsize=10)
            ax3.grid(True, alpha=0.3)
            ax3.legend(loc="upper right")
            ax3.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
            ax3.xaxis.set_major_locator(mdates.YearLocator(3))

            # ======== 4. ASSET CLASS ALLOCATION OVER TIME ========
            # Group instruments by asset class for allocation analysis
            asset_classes = {
                "Interest_Rates": ["US10", "US2", "SOFR"],
                "Equities": ["SP500_micro", "NASDAQ", "EUROSTX"],
                "Commodities": ["CORN", "CRUDE_W", "GOLD"],
                "FX": ["EUR", "GBP", "JPY"],
            }

            # Calculate asset class weights over time
            asset_class_weights = {}
            for asset_class, instruments in asset_classes.items():
                available_instruments = [
                    inst for inst in instruments if inst in weights.columns
                ]
                if available_instruments:
                    asset_class_weights[asset_class] = (
                        weights[available_instruments].abs().sum(axis=1)
                    )

            # Create stacked area plot
            asset_df = pd.DataFrame(asset_class_weights)
            asset_df = asset_df.fillna(0)

            # Sample every 60 days for cleaner visualization
            asset_df_sampled = asset_df.iloc[::60, :]

            colors = ["#3498DB", "#E74C3C", "#F39C12", "#27AE60"]
            ax4.stackplot(
                asset_df_sampled.index,
                asset_df_sampled["Interest_Rates"],
                asset_df_sampled["Equities"],
                asset_df_sampled["Commodities"],
                asset_df_sampled["FX"],
                labels=["Interest Rates", "Equities", "Commodities", "FX"],
                colors=colors,
                alpha=0.8,
            )

            ax4.set_title(
                "Dynamic Asset Class Allocation",
                fontsize=12,
                fontweight="semibold",
                pad=15,
            )
            ax4.set_xlabel("Year", fontsize=10)
            ax4.set_ylabel("Total Weight by Asset Class", fontsize=10)
            ax4.legend(loc="upper right", frameon=True, fancybox=True, shadow=True)
            ax4.grid(True, alpha=0.3)
            ax4.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
            ax4.xaxis.set_major_locator(mdates.YearLocator(3))

            # Adjust layout
            plt.tight_layout()
            plt.subplots_adjust(top=0.94, hspace=0.3, wspace=0.3)

            # Save the comprehensive analysis
            analysis_filename = f"{output_dir}/position_risk_analysis_{timestamp}.png"
            plt.savefig(
                analysis_filename,
                dpi=300,
                bbox_inches="tight",
                facecolor="white",
                edgecolor="none",
            )
            print(f"✓ Position & Risk analysis saved: {analysis_filename}")

            # Also save as PDF
            analysis_pdf = f"{output_dir}/position_risk_analysis_{timestamp}.pdf"
            plt.savefig(
                analysis_pdf,
                dpi=300,
                bbox_inches="tight",
                facecolor="white",
                edgecolor="none",
            )
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

    def plot_instrument_with_signals(self, instrument_code, rule_name=None,
                                     start_date=None, end_date=None):
        """
        Plot instrument price with ACTUAL trading signals from optimized positions.

        This plots:
        - Price chart with actual buy/sell trades (from optimized integer positions)
        - Combined forecast (the signal strength)
        - Actual optimized positions (whole numbers after dynamic optimization)

        Args:
            instrument_code: The instrument to plot (e.g., 'GOLD', 'SP500micro')
            rule_name: Specific rule to plot (e.g., 'momentum16'), or None for combined
            start_date: Start date for plot (default: last 2 years)
            end_date: End date for plot (default: latest)
        """
        import matplotlib.pyplot as plt
        import pandas as pd
        from matplotlib.dates import DateFormatter

        if not self.system:
            print("No system available. Run backtest first!")
            return

        print(f"\n{'=' * 60}")
        print(f"Plotting {instrument_code} - ACTUAL OPTIMIZED POSITIONS")
        print(f"{'=' * 60}")

        try:
            # 1. Get price data
            price = self.system.rawdata.get_daily_prices(instrument_code)

            # 2. Get combined forecast (trading signal - BEFORE optimization)
            combined_forecast = self.system.combForecast.get_combined_forecast(instrument_code)

            # 3. Get ACTUAL OPTIMIZED positions (integer, after dynamic optimization)
            # This is the KEY FIX - use optimised positions, not portfolio positions
            try:
                optimized_positions_df = self.system.optimisedPositions.get_optimised_position_df()
                if instrument_code in optimized_positions_df.columns:
                    actual_positions = optimized_positions_df[instrument_code]
                    print(f"✓ Using optimized integer positions for {instrument_code}")
                else:
                    print(f"✗ {instrument_code} not in optimized positions - not traded in this backtest")
                    return
            except AttributeError:
                print("✗ Dynamic optimization not available - using standard positions")
                actual_positions = self.system.portfolio.get_notional_position(instrument_code)

            # 4. Filter by date range
            if start_date is None:
                start_date = price.index[-504]  # ~2 years of daily data
            if end_date is None:
                end_date = price.index[-1]

            price = price[start_date:end_date]
            combined_forecast = combined_forecast[start_date:end_date]
            actual_positions = actual_positions[start_date:end_date]

            # 5. Identify ACTUAL buy/sell trades (from optimized positions)
            # Only mark as trade if position actually changed (not just signal change)
            position_changes = actual_positions.diff()

            # Buy = position increased (includes both new longs and covering shorts)
            buys = position_changes[position_changes > 0]
            # Sell = position decreased (includes both new shorts and selling longs)
            sells = position_changes[position_changes < 0]

            # 6. Verify these are integer positions
            non_integer = actual_positions[actual_positions != actual_positions.round()]
            if len(non_integer) > 0:
                print(f"⚠ WARNING: Found {len(non_integer)} fractional positions!")
                print(f"  This suggests positions are NOT from optimized output")
                print(f"  First few fractional values: {non_integer.head()}")
            else:
                print(f"✓ All positions are integers (as expected)")

            # 7. Create the plot
            fig, axes = plt.subplots(3, 1, figsize=(15, 10), sharex=True)

            # Plot 1: Price with ACTUAL buy/sell markers
            ax1 = axes[0]
            ax1.plot(price.index, price.values, 'k-', linewidth=1.5, label='Price')

            # Mark actual trades with larger, more visible markers
            if len(buys) > 0:
                ax1.scatter(buys.index, price.loc[buys.index],
                            color='green', marker='^', s=150, label='Buy/Cover',
                            zorder=5, edgecolors='darkgreen', linewidths=2)
            if len(sells) > 0:
                ax1.scatter(sells.index, price.loc[sells.index],
                            color='red', marker='v', s=150, label='Sell/Short',
                            zorder=5, edgecolors='darkred', linewidths=2)

            ax1.set_ylabel('Price', fontsize=12)
            ax1.set_title(f'{instrument_code} - Price with ACTUAL TRADES (Optimized Positions)',
                          fontsize=14, fontweight='bold')
            ax1.legend(loc='upper left')
            ax1.grid(True, alpha=0.3)

            # Plot 2: Combined forecast (signal strength BEFORE optimization)
            ax2 = axes[1]
            ax2.plot(combined_forecast.index, combined_forecast.values,
                     'b-', linewidth=1.5, label='Combined Forecast (Pre-Optimization)')
            ax2.axhline(y=0, color='black', linestyle='--', alpha=0.5)
            ax2.fill_between(combined_forecast.index, 0, combined_forecast.values,
                             where=(combined_forecast.values > 0), alpha=0.3,
                             color='green', label='Long Signal')
            ax2.fill_between(combined_forecast.index, 0, combined_forecast.values,
                             where=(combined_forecast.values < 0), alpha=0.3,
                             color='red', label='Short Signal')
            ax2.set_ylabel('Forecast', fontsize=12)
            ax2.set_title('Signal Strength (Before Dynamic Optimization)', fontsize=12)
            ax2.legend(loc='upper left')
            ax2.grid(True, alpha=0.3)

            # Plot 3: ACTUAL OPTIMIZED positions (integers)
            ax3 = axes[2]
            # Use step plot to emphasize integer nature
            ax3.step(actual_positions.index, actual_positions.values, 'purple',
                     linewidth=2.5, label='Optimized Position (Integers)', where='post')
            ax3.axhline(y=0, color='black', linestyle='--', alpha=0.5)
            ax3.fill_between(actual_positions.index, 0, actual_positions.values,
                             where=(actual_positions.values > 0), alpha=0.3,
                             color='green', step='post')
            ax3.fill_between(actual_positions.index, 0, actual_positions.values,
                             where=(actual_positions.values < 0), alpha=0.3,
                             color='red', step='post')
            ax3.set_ylabel('Position (contracts)', fontsize=12)
            ax3.set_xlabel('Date', fontsize=12)
            ax3.set_title('Actual Portfolio Position (After Dynamic Optimization)', fontsize=12)
            ax3.legend(loc='upper left')
            ax3.grid(True, alpha=0.3)

            # Format x-axis
            date_fmt = DateFormatter('%Y-%m-%d')
            ax3.xaxis.set_major_formatter(date_fmt)
            plt.xticks(rotation=45)

            plt.tight_layout()
            plt.show()

            # Print detailed statistics
            print(f"\n{'=' * 60}")
            print(f"ACTUAL TRADING STATISTICS for {instrument_code}")
            print(f"{'=' * 60}")
            print(f"Position Statistics:")
            print(f"  Average position: {actual_positions.mean():.2f} contracts")
            print(f"  Max long position: {actual_positions.max():.0f} contracts")
            print(f"  Max short position: {actual_positions.min():.0f} contracts")
            print(f"  Position std dev: {actual_positions.std():.2f}")

            print(f"\nTrading Activity:")
            print(f"  Number of buy trades: {len(buys)}")
            print(f"  Number of sell trades: {len(sells)}")
            print(f"  Total trades: {len(buys) + len(sells)}")
            print(f"  Average trade size: {position_changes.abs().mean():.2f} contracts")
            print(f"  Largest trade: {position_changes.abs().max():.0f} contracts")

            print(f"\nHolding Statistics:")
            days_in_market = (actual_positions != 0).sum()
            days_long = (actual_positions > 0).sum()
            days_short = (actual_positions < 0).sum()
            days_flat = (actual_positions == 0).sum()
            total_days = len(actual_positions)

            print(f"  Days in market: {days_in_market}/{total_days} ({days_in_market / total_days * 100:.1f}%)")
            print(f"  Days long: {days_long} ({days_long / total_days * 100:.1f}%)")
            print(f"  Days short: {days_short} ({days_short / total_days * 100:.1f}%)")
            print(f"  Days flat: {days_flat} ({days_flat / total_days * 100:.1f}%)")

            print(f"\nSignal vs Position Comparison:")
            forecast_avg = combined_forecast.mean()
            position_avg = actual_positions.mean()
            print(f"  Avg forecast: {forecast_avg:.2f}")
            print(f"  Avg position: {position_avg:.2f}")

            # How often does optimizer reject signals?
            strong_signals = combined_forecast.abs() > 10
            no_position = actual_positions == 0
            rejected_signals = (strong_signals & no_position).sum()
            print(
                f"  Strong signals rejected: {rejected_signals}/{strong_signals.sum()} ({rejected_signals / max(strong_signals.sum(), 1) * 100:.1f}%)")
            print(f"    (Shows shadow cost/optimization filtering)")

        except Exception as e:
            print(f"Error plotting {instrument_code}: {e}")
            import traceback
            traceback.print_exc()

    def plot_top_traded_instruments(self, n=5, years=2):
        """
        Plot the top N most actively traded instruments using OPTIMIZED positions.
        """
        if not self.system:
            print("No system available. Run backtest first!")
            return

        print(f"\nFinding top {n} most traded instruments from OPTIMIZED positions...")

        try:
            # Get optimized positions dataframe
            optimized_positions_df = self.system.optimisedPositions.get_optimised_position_df()

            # Calculate trade counts for each instrument
            trade_counts = {}
            for instrument in optimized_positions_df.columns:
                positions = optimized_positions_df[instrument]
                # Count actual position changes (trades)
                trades = (positions.diff() != 0).sum()
                # Only include if actually traded
                if trades > 0:
                    trade_counts[instrument] = trades

            # Sort by trade count
            top_instruments = sorted(trade_counts.items(),
                                     key=lambda x: x[1], reverse=True)[:n]

            print(f"\nTop {n} most traded instruments (from optimized positions):")
            for i, (inst, count) in enumerate(top_instruments, 1):
                print(f"  {i}. {inst}: {count} trades")

            # Plot each one
            for instrument, count in top_instruments:
                self.plot_instrument_with_signals(instrument)
                input("Press Enter for next instrument...")

        except AttributeError:
            print("✗ Optimized positions not available!")
            print("  System may not have dynamic optimization enabled")

    def plot_individual_rule_signals(self, instrument_code, start_date=None, end_date=None):
        """
        Plot each trading rule's forecast separately for an instrument.
        Shows how different strategies contribute to final signal.
        """
        import matplotlib.pyplot as plt

        if not self.system:
            print("No system available. Run backtest first!")
            return

        # Get price
        price = self.system.rawdata.get_daily_prices(instrument_code)

        # Get all rule forecasts
        rules = self.system.rules.trading_rules().keys()

        # Set up subplots: 1 for price + 1 per rule + 1 for combined
        n_plots = len(rules) + 2
        fig, axes = plt.subplots(n_plots, 1, figsize=(15, 3 * n_plots), sharex=True)

        # Date filtering
        if start_date is None:
            start_date = price.index[-504]
        if end_date is None:
            end_date = price.index[-1]

        price = price[start_date:end_date]

        # Plot 1: Price
        axes[0].plot(price.index, price.values, 'k-', linewidth=1.5)
        axes[0].set_title(f'{instrument_code} - Price', fontweight='bold')
        axes[0].set_ylabel('Price')
        axes[0].grid(True, alpha=0.3)

        # Plot each rule
        for i, rule_name in enumerate(rules, 1):
            try:
                forecast = self.system.rules.get_raw_forecast(instrument_code, rule_name)
                forecast = forecast[start_date:end_date]

                axes[i].plot(forecast.index, forecast.values, linewidth=1.5)
                axes[i].axhline(y=0, color='black', linestyle='--', alpha=0.5)
                axes[i].set_title(f'Rule: {rule_name}')
                axes[i].set_ylabel('Forecast')
                axes[i].grid(True, alpha=0.3)
            except:
                axes[i].text(0.5, 0.5, f'{rule_name}: No data',
                             ha='center', va='center', transform=axes[i].transAxes)

        # Plot combined forecast
        combined = self.system.combForecast.get_combined_forecast(instrument_code)
        combined = combined[start_date:end_date]
        axes[-1].plot(combined.index, combined.values, 'purple', linewidth=2)
        axes[-1].axhline(y=0, color='black', linestyle='--', alpha=0.5)
        axes[-1].set_title('Combined Forecast', fontweight='bold')
        axes[-1].set_ylabel('Forecast')
        axes[-1].set_xlabel('Date')
        axes[-1].grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()

    def print_advanced_risk_analysis(self):
        """
        Print detailed risk analysis following Robert Carver's risk-first approach
        """
        if not self.results:
            return

        print(f"\n🔍 ADVANCED RISK ANALYSIS")
        print(f"{'─' * 50}")

        try:
            positions = self.results["optimized_positions"]
            weights = self.results["optimized_weights"]
            portfolio_returns = self.results["portfolio_returns"].percent

            # Position concentration analysis
            daily_total_positions = positions.abs().sum(axis=1)
            avg_daily_exposure = daily_total_positions.mean()
            max_daily_exposure = daily_total_positions.max()

            print(f"📍 POSITION METRICS")
            print(f"   Average daily positions: {avg_daily_exposure:.1f} contracts")
            print(f"   Maximum daily positions: {max_daily_exposure:.0f} contracts")
            print(
                f"   Position concentration:  {(positions != 0).sum(axis=1).mean():.1f} instruments/day"
            )

            # Volatility analysis
            rolling_vol_quarterly = portfolio_returns.rolling(63).std() * np.sqrt(256)
            vol_of_vol = rolling_vol_quarterly.std()

            print(f"\n⚡ VOLATILITY ANALYSIS")
            print(f"   Target volatility:       20.0%")
            print(
                f"   Achieved volatility:     {portfolio_returns.std() * np.sqrt(256):.1f}%"
            )
            print(f"   Volatility consistency:  {vol_of_vol:.1f}% (vol of vol)")
            print(
                f"   Vol control efficiency:  {20.0 / (portfolio_returns.std() * np.sqrt(256)):.2f}x"
            )

            # Dynamic rebalancing frequency
            position_changes = positions.diff().abs().sum(axis=1)
            rebalance_days = (position_changes > 0).sum()
            rebalance_frequency = rebalance_days / len(positions) * 100

            print(f"\n🔄 DYNAMIC REBALANCING")
            print(
                f"   Rebalancing frequency:   {rebalance_frequency:.1f}% of trading days"
            )
            print(
                f"   Total rebalance days:    {rebalance_days} out of {len(positions)}"
            )
            print(
                f"   Avg changes per rebal:   {position_changes[position_changes > 0].mean():.1f} contracts"
            )

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
        report_file = analyzer.generate_turnover_report("project_dynamic/results")

        # Create visualization plots
        plot_file = analyzer.plot_turnover_analysis("project_dynamic/results")

        # Store results for later use
        self.results["turnover_analysis"] = turnover_results

        return turnover_results

    def run_turnover_diagnostics(self):
        """
        Run comprehensive turnover diagnostics
        Call this AFTER backtest completes
        """
        print(f"\n" + "=" * 70)
        print(f"🔬 RUNNING TURNOVER DIAGNOSTICS")
        print(f"=" * 70)

        if not self.system:
            print("❌ No system available - run backtest first!")
            return

        # Initialize analyzer
        analyzer = RobertCarverTurnoverAnalyzer(self.system)

        # Run all three diagnostics
        print(f"\n" + "🔍" * 35)
        activity = analyzer.diagnostic_position_activity()

        print(f"\n" + "🔍" * 35)
        positions = analyzer.verify_average_position_calculation()

        # Pick most active instrument for detailed check
        if activity:
            most_active = max(activity.items(), key=lambda x: x[1]["total_changes"])
            instrument = most_active[0]
            print(f"\n" + "🔍" * 35)
            crosscheck = analyzer.cross_check_turnover_calculation(instrument)

        return {
            "activity": activity,
            "positions": positions,
            "crosscheck": crosscheck if activity else {},
        }

    def save_system_to_pickle(self, output_path=None):
        """
        Save the complete system object to pickle file.
        This allows future analysis without re-running the backtest.

        Args:
            output_path: Where to save (default: auto-generated in results/)

        Returns:
            str: Path to saved pickle file
        """
        import pickle

        # Generate filename with timestamp if not provided
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"results/pickles/system_{timestamp}.pkl"

        # Create directory
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        print(f"\n{'=' * 70}")
        print("💾 SAVING SYSTEM TO PICKLE")
        print(f"{'=' * 70}")
        print(f"📁 Output: {output_path}")
        print(f"⏳ Saving (this takes ~30 seconds)...")

        try:
            with open(output_path, 'wb') as f:
                pickle.dump(self.system, f, protocol=pickle.HIGHEST_PROTOCOL)

            # Check file size
            file_size_mb = os.path.getsize(output_path) / (1024 * 1024)

            print(f"✅ System saved successfully!")
            print(f"📦 File size: {file_size_mb:.1f} MB")
            print(f"📝 To use this pickle:")
            print(f"   python extract_static_weights.py --pickle {output_path}")
            print(f"{'=' * 70}\n")

            return output_path

        except Exception as e:
            print(f"❌ Error saving pickle: {e}")
            import traceback
            traceback.print_exc()
            return None

    def debug_forecast_weight_calculation(self):
        """
        Diagnose which instruments have empty rule P&L data.
        Call this BEFORE run_backtest() to identify problem instruments.
        """
        print(f"\n{'=' * 80}")
        print("DIAGNOSTIC: FORECAST WEIGHT CALCULATION DATA AVAILABILITY")
        print(f"{'=' * 80}\n")

        instrument_list = self.system.get_instrument_list()
        trading_rules = list(self.system.rules.trading_rules().keys())

        print(f"Total instruments: {len(instrument_list)}")
        print(f"Trading rules: {trading_rules}\n")
        print(f"{'=' * 80}")

        problem_instruments = []

        for instrument in instrument_list:
            print(f"\n{instrument}:")
            print(f"{'-' * 40}")

            valid_rules = []
            empty_rules = []
            error_rules = []

            for rule_name in trading_rules:
                try:
                    # Try to get forecast for this rule
                    forecast = self.system.rules.get_raw_forecast(instrument, rule_name)

                    # Try to get price data
                    price = self.system.rawdata.get_daily_prices(instrument)

                    # Check if we have overlapping data
                    if len(forecast) == 0:
                        empty_rules.append(rule_name)
                        print(f"  ❌ {rule_name:15s}: EMPTY forecast")
                    elif forecast.isna().all():
                        empty_rules.append(rule_name)
                        print(f"  ❌ {rule_name:15s}: ALL NaN values")
                    else:
                        # Count valid observations
                        valid_obs = (~forecast.isna()).sum()
                        total_obs = len(forecast)
                        pct_valid = (valid_obs / total_obs) * 100

                        if pct_valid < 10:
                            empty_rules.append(rule_name)
                            print(f"  ⚠️  {rule_name:15s}: Only {pct_valid:.1f}% valid data")
                        else:
                            valid_rules.append(rule_name)
                            print(f"  ✓  {rule_name:15s}: {valid_obs} valid obs ({pct_valid:.1f}%)")

                except Exception as e:
                    error_rules.append(rule_name)
                    print(f"  💥 {rule_name:15s}: ERROR - {str(e)[:50]}")

            # Summary for this instrument
            print(f"\n  Summary:")
            print(f"    Valid rules:  {len(valid_rules)} / {len(trading_rules)}")
            print(f"    Empty rules:  {len(empty_rules)}")
            print(f"    Error rules:  {len(error_rules)}")

            # Check if this instrument will cause problems
            if len(valid_rules) == 0:
                print(f"  🚨 PROBLEM: NO VALID RULES - will cause 'No objects to concatenate' error!")
                problem_instruments.append(instrument)
            elif len(valid_rules) < 2:
                print(f"  ⚠️  WARNING: Only {len(valid_rules)} valid rule(s) - may cause optimization issues")

        # Final summary
        print(f"\n{'=' * 80}")
        print(f"DIAGNOSTIC SUMMARY")
        print(f"{'=' * 80}")
        print(f"Total instruments analyzed: {len(instrument_list)}")
        print(f"Problem instruments (zero valid rules): {len(problem_instruments)}")

        if problem_instruments:
            print(f"\n🚨 INSTRUMENTS THAT WILL CAUSE ERRORS:")
            for inst in problem_instruments:
                print(f"   - {inst}")

            print(f"\n💡 RECOMMENDED FIX:")
            print(f"   Add to your config:")
            print(f"   ignore_instruments:")
            for inst in problem_instruments:
                print(f"     - {inst}")
        else:
            print(f"\n✅ All instruments have at least one valid trading rule")

        print(f"{'=' * 80}\n")

        return problem_instruments


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

    results = backtester.run_backtest(extract_static=True)

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
    backtester.save_results(output_dir="project_dynamic/results")

    # 7. Turnover analysis (if turnover_analysis module is available)
    print("\n7️⃣ Turnover Analysis...")
    try:
        turnover_results = backtester.analyze_turnover_comprehensive()
        print("✓ Turnover analysis completed")
    except (ImportError, AttributeError) as e:
        print(f"⚠ Turnover analysis not available: {e}")
        print("  (This is optional - basic turnover metrics already shown)")

    # PLOTTING ANALYSIS
    print("\n" + "=" * 60)
    print("SIGNAL ANALYSIS")
    print("=" * 60)

    # Automatically plot top traded instruments
    # backtester.plot_top_traded_instruments(n=10, years=2)

    # print("=" * 70)
    # print("3️⃣ Running Turnover Diagnostics...")
    # diagnostic_results = backtester.run_turnover_diagnostics()
    # backtester.results["diagnostic_results"] = diagnostic_results

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
    portfolio_returns = results["portfolio_returns"]
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
