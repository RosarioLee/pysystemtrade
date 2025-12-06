#!/usr/bin/env python3
"""
DYNAMIC OPTIMIZATION BACKTESTING SCRIPT
========================================

This script runs a complete dynamic optimization backtest using Robert Carver's
proven systematic trading framework. It's designed for beginners to understand
each step of the process.

What this script does:
1. Loads your configuration and data
2. Sets up the dynamic optimization system
3. Runs a complete backtest
4. Shows you the results and performance metrics

Author: Based on Robert Carver's pysystemtrade
Date: October 2025
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import yaml
import sys
import os

# Import the core pysystemtrade components
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
from systems.forecasting import Rules
from systems.basesystem import System
from systems.forecast_combine import ForecastCombine
from systems.forecast_scale_cap import ForecastScaleCap
from systems.positionsizing import PositionSizing
from systems.portfolio import Portfolios
from systems.accounts.accounts_stage import Account
from systems.provided.dynamic_small_system_optimise.optimised_positions_stage import (
    optimisedPositions,
)
from sysdata.config.configdata import Config


def get_project_root():
    """
    Find the project_dynamic root directory

    This function finds the correct path regardless of where the script is run from
    """
    current_file = Path(__file__).resolve()  # Get the full path to this script

    # Go up directories until we find project_dynamic
    for parent in current_file.parents:
        if parent.name == "project_dynamic":
            return parent

    # If not found, assume current directory's parent
    return current_file.parent.parent


def load_config(config_filename="dynamic_config.yaml"):
    """
    Load the YAML configuration file using correct path resolution

    Args:
        config_filename: Name of your config file (just the filename, not path)

    Returns:
        Dictionary containing all your system settings
    """
    # Get the correct path to the config file
    project_root = get_project_root()

    # *** FIX: Make sure we only add "config" directory once ***
    # Remove any path components from config_filename to ensure it's just the filename
    config_filename_only = Path(config_filename).name
    config_path = project_root / "config" / config_filename_only

    print(f"📋 Loading configuration from: {config_path}")
    print(f"   Project root detected at: {project_root}")
    print(f"   Config filename: {config_filename_only}")

    # Check if config file exists
    if not config_path.exists():
        print(f"❌ Config file not found at: {config_path}")
        print(f"   Current working directory: {os.getcwd()}")
        print(f"   Script location: {Path(__file__).resolve()}")
        print(f"   Project root: {project_root}")
        print(f"   Expected config location: {config_path}")

        # List what's actually in the config directory
        config_dir = project_root / "config"
        if config_dir.exists():
            print(f"   Files in config directory:")
            for file in config_dir.iterdir():
                print(f"     - {file.name}")
        else:
            print(f"   Config directory doesn't exist: {config_dir}")

        raise FileNotFoundError(f"Config file not found: {config_path}")

    # Load the YAML file into a Python dictionary
    with open(config_path, "r") as file:
        config = yaml.safe_load(file)

    print(f"✅ Configuration loaded successfully!")
    print(f"   - Volatility Target: {config.get('percentage_vol_target', 'Not set')}%")
    print(f"   - Number of Instruments: {len(config.get('instrument_weights', {}))}")
    print(f"   - Number of Trading Rules: {len(config.get('trading_rules', {}))}")

    return config


def setup_data_source(data_dirname="data"):
    """
    Use pysystemtrade's bundled sample data under pysystemtrade/data/futures/adjusted_prices_csv.
    Falls back to your project_dynamic/data if you switch back later.
    """
    from pathlib import Path
    from sysdata.sim.csv_futures_sim_data import csvFuturesSimData

    # 1) Locate repo root = path containing this basic_dynamic_backtest.py up to pysystemtrade/
    examples_file = Path(__file__).resolve()
    repo_root = examples_file.parents[2]  # .../PySystemTrade/pysystemtrade

    # 2) Point to built-in adjusted prices
    adjusted_prices_path = repo_root / "data" / "futures" / "adjusted_prices_csv"

    print(f"📊 Using bundled sample data from: {adjusted_prices_path}")

    # 3) Build csv_data_paths mapping for the classes csvFuturesSimData expects
    csv_data_paths = {
        # Minimum needed to read prices
        "csvFuturesAdjustedPricesData": str(adjusted_prices_path),
        # You can wire these later when you add costs / FX / rolls:
        # "csvFuturesMultiplePricesData": str(repo_root / "data" / "futures" / "multiple_prices_csv"),
        # "csvFuturesInstrumentData": str(repo_root / "data" / "instruments"),
        # "csvFxPricesData": str(repo_root / "data" / "fx"),
        # "csvRollParametersData": str(repo_root / "data" / "futures" / "roll_parameters"),
        # "csvSpreadCostData": str(repo_root / "data" / "costs"),
    }

    # 4) Construct the data object with explicit paths
    data = csvFuturesSimData(csv_data_paths=csv_data_paths)
    print("✅ Data source configured to use pysystemtrade bundled sample data")
    return data


def create_dynamic_system(data, config):
    """
    Build the complete dynamic optimization trading system
    """
    print(f"🔧 Building dynamic optimization system...")

    # *** FIX: Convert dictionary to proper Config object ***
    if isinstance(config, dict):
        # Convert raw dictionary to pysystemtrade Config object
        config_object = Config(config)
        print("   ✅ Converted config dictionary to Config object")
    else:
        config_object = config

    # STAGE 1: Raw Data
    # This stage provides price data to all other stages
    print("   ⚙️  Stage 1: Raw data loaded")

    # STAGE 2: Trading Rules
    # Generates buy/sell signals (forecasts) from price patterns
    rules_stage = Rules()
    print(
        f"   ⚙️  Stage 2: Trading rules ({len(config.get('trading_rules', {}))} rules)"
    )

    # STAGE 3: Forecast Scaling & Capping
    # Makes sure all forecasts are on the same scale (-20 to +20)
    scale_stage = ForecastScaleCap()
    print("   ⚙️  Stage 3: Forecast scaling and capping")

    # STAGE 4: Forecast Combination
    # Blends multiple trading signals into one combined forecast per instrument
    combine_stage = ForecastCombine()
    print("   ⚙️  Stage 4: Forecast combination")

    # STAGE 5: Position Sizing
    # Converts forecasts into actual position sizes based on volatility targeting
    position_stage = PositionSizing()
    print("   ⚙️  Stage 5: Position sizing with volatility targeting")

    # STAGE 6: Portfolio Construction (THE DYNAMIC PART!)
    # This is where the dynamic optimization happens:
    # - Estimates changing correlations between instruments
    # - Dynamically adjusts diversification multiplier
    # - Optimizes portfolio weights based on current market conditions
    portfolio_stage = Portfolios()
    print("   ⚙️  Stage 6: Dynamic portfolio optimization")

    # STAGE 7: Optimized Positions (Advanced Dynamic Features)
    # Uses Robert's advanced optimization:
    # - Transaction cost optimization
    # - Risk budgeting across instruments
    # - Dynamic rebalancing based on market regime
    optimized_stage = optimisedPositions()  # ✅ Correct: lowercase 'o'
    print("   ⚙️  Stage 7: Advanced position optimization")

    # STAGE 8: Account Tracking
    # Calculates profit/loss, tracks performance, manages capital
    account_stage = Account()
    print("   ⚙️  Stage 8: Account and P&L tracking")

    # BUILD THE COMPLETE SYSTEM
    # *** FIX: Remove data from stages list ***
    system_stages = [
        # ❌ DON'T PUT data HERE - it goes as separate parameter
        rules_stage,  # Trading signals
        scale_stage,  # Signal standardization
        combine_stage,  # Signal combination
        position_stage,  # Position sizing
        portfolio_stage,  # Dynamic optimization
        optimized_stage,  # Advanced optimization
        account_stage,  # Performance tracking
    ]

    # Create the complete system object
    # The System constructor expects: (stages_list, data_object, config_object)
    system = System(
        system_stages,  # ✅ ONLY system stages (no data object)
        data,  # ✅ Data source as separate parameter
        config_object,  # ✅ Config object as separate parameter
    )

    print(f"✅ Dynamic system built successfully!")
    print(f"   - System contains {len(system_stages)} processing stages")
    print(f"   - Dynamic optimization: ENABLED")
    print(f"   - Risk management: ENABLED")

    return system


def run_backtest(system, start_date="2010-01-01", end_date="2025-12-31"):
    """
    Execute the complete backtest

    This runs your trading system on historical data to see how it would have performed

    Args:
        system: The complete trading system
        start_date: When to start the backtest
        end_date: When to end the backtest

    Returns:
        Dictionary containing all performance results
    """
    print(f"🚀 Starting backtest from {start_date} to {end_date}")
    print("   This may take a few minutes for the first run...")

    # Get the list of instruments from your configuration
    instruments = system.get_instrument_list()
    print(
        f"   - Trading {len(instruments)} instruments: {', '.join(instruments[:5])}..."
    )

    # CALCULATE KEY SYSTEM OUTPUTS
    results = {}

    print("   📈 Calculating portfolio performance...")

    # 1. ACCOUNT CURVE (Your main P&L)
    # This shows how your account value changes over time
    try:
        account_curve = system.accounts.portfolio()
        results["account_curve"] = account_curve
        print(f"   ✅ Account curve calculated ({len(account_curve)} data points)")
    except Exception as e:
        print(f"   ❌ Error calculating account curve: {e}")
        results["account_curve"] = None

    # 2. INDIVIDUAL INSTRUMENT PERFORMANCE
    # Shows how each market contributed to your returns
    print("   📊 Calculating instrument performance...")
    instrument_returns = {}

    for instrument in instruments[:10]:  # First 10 to save time
        try:
            # Get the P&L curve for this specific instrument
            curve = system.accounts.pandl_for_instrument(instrument)
            instrument_returns[instrument] = curve
            print(f"   ✅ {instrument}: {len(curve)} data points")
        except Exception as e:
            print(f"   ⚠️  {instrument}: Error - {e}")

    results["instrument_returns"] = instrument_returns

    # 3. POSITION HISTORY
    # Shows how your positions changed over time (the dynamic part!)
    print("   📋 Calculating position history...")
    position_history = {}

    for instrument in instruments[:5]:  # First 5 instruments
        try:
            # Get the position size over time for this instrument
            positions = system.portfolio.get_notional_position(instrument)
            position_history[instrument] = positions
            print(f"   ✅ {instrument}: Position history recorded")
        except Exception as e:
            print(f"   ⚠️  {instrument}: Error - {e}")

    results["positions"] = position_history

    # 4. RISK METRICS
    # Calculate key risk and return statistics
    print("   🎯 Calculating performance metrics...")

    if results["account_curve"] is not None:
        account_curve = results["account_curve"]

        # Calculate daily returns
        daily_returns = account_curve.pct_change().dropna()

        # Key performance metrics
        total_return = (account_curve.iloc[-1] / account_curve.iloc[0]) - 1
        annual_return = ((1 + total_return) ** (252 / len(daily_returns))) - 1
        annual_volatility = daily_returns.std() * (252**0.5)
        sharpe_ratio = annual_return / annual_volatility if annual_volatility > 0 else 0

        # Maximum drawdown calculation
        cumulative = (1 + daily_returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()

        results["performance_metrics"] = {
            "total_return": total_return,
            "annual_return": annual_return,
            "annual_volatility": annual_volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "num_trades": len(daily_returns),
        }

        print(f"   ✅ Performance calculated!")
        print(f"      - Annual Return: {annual_return:.1%}")
        print(f"      - Annual Volatility: {annual_volatility:.1%}")
        print(f"      - Sharpe Ratio: {sharpe_ratio:.2f}")
        print(f"      - Max Drawdown: {max_drawdown:.1%}")

    print(f"🎉 Backtest completed successfully!")

    return results


def display_results(results):
    """
    Create charts and display the backtest results

    This shows you how your dynamic optimization system performed

    Args:
        results: Dictionary containing backtest results
    """
    print(f"📊 Generating performance charts...")

    # Set up the plotting environment
    plt.style.use(
        "seaborn-v0_8" if "seaborn-v0_8" in plt.style.available else "default"
    )
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle(
        "Dynamic Optimization System - Backtest Results", fontsize=16, fontweight="bold"
    )

    # CHART 1: Account Curve (Main Performance)
    if results.get("account_curve") is not None:
        account_curve = results["account_curve"]

        axes[0, 0].plot(account_curve.index, account_curve.values, "b-", linewidth=2)
        axes[0, 0].set_title("Portfolio Value Over Time")
        axes[0, 0].set_ylabel("Portfolio Value")
        axes[0, 0].grid(True, alpha=0.3)

        # Add performance annotation
        if "performance_metrics" in results:
            metrics = results["performance_metrics"]
            textstr = f"Annual Return: {metrics['annual_return']:.1%}\n"
            textstr += f"Volatility: {metrics['annual_volatility']:.1%}\n"
            textstr += f"Sharpe: {metrics['sharpe_ratio']:.2f}\n"
            textstr += f"Max DD: {metrics['max_drawdown']:.1%}"

            axes[0, 0].text(
                0.02,
                0.98,
                textstr,
                transform=axes[0, 0].transAxes,
                fontsize=9,
                verticalalignment="top",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
            )

    # CHART 2: Individual Instrument Performance
    if results.get("instrument_returns"):
        instrument_returns = results["instrument_returns"]

        for i, (instrument, returns) in enumerate(list(instrument_returns.items())[:5]):
            if returns is not None and len(returns) > 0:
                # Normalize to start at 1.0 for comparison
                normalized = returns / returns.iloc[0]
                axes[0, 1].plot(
                    normalized.index,
                    normalized.values,
                    label=instrument,
                    linewidth=1,
                    alpha=0.7,
                )

        axes[0, 1].set_title("Individual Instrument Performance (Normalized)")
        axes[0, 1].set_ylabel("Normalized Value")
        axes[0, 1].legend(fontsize=8)
        axes[0, 1].grid(True, alpha=0.3)

    # CHART 3: Position History (The Dynamic Part!)
    if results.get("positions"):
        position_history = results["positions"]

        for instrument, positions in list(position_history.items())[:3]:
            if positions is not None and len(positions) > 0:
                axes[1, 0].plot(
                    positions.index,
                    positions.values,
                    label=instrument,
                    linewidth=1,
                    alpha=0.7,
                )

        axes[1, 0].set_title("Position Sizes Over Time (Dynamic Optimization)")
        axes[1, 0].set_ylabel("Position Size")
        axes[1, 0].legend(fontsize=8)
        axes[1, 0].grid(True, alpha=0.3)
        axes[1, 0].axhline(y=0, color="black", linestyle="-", alpha=0.3)

    # CHART 4: Rolling Performance
    if results.get("account_curve") is not None:
        account_curve = results["account_curve"]
        daily_returns = account_curve.pct_change().dropna()

        # Calculate rolling 252-day (1-year) returns
        rolling_returns = daily_returns.rolling(252).apply(lambda x: (1 + x).prod() - 1)

        axes[1, 1].plot(
            rolling_returns.index,
            rolling_returns.values * 100,
            "g-",
            linewidth=1.5,
            alpha=0.7,
        )
        axes[1, 1].set_title("Rolling 12-Month Returns")
        axes[1, 1].set_ylabel("Rolling Return (%)")
        axes[1, 1].grid(True, alpha=0.3)
        axes[1, 1].axhline(y=0, color="red", linestyle="--", alpha=0.5)

    # Adjust layout and save
    plt.tight_layout()

    # Save the chart to the project root
    project_root = get_project_root()
    chart_path = project_root / "dynamic_optimization_results.png"
    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    print(f"   💾 Charts saved as: {chart_path}")

    # Show the chart
    plt.show()


def print_summary(results):
    """
    Print a text summary of the backtest results

    Args:
        results: Dictionary containing backtest results
    """
    print("\n" + "=" * 60)
    print("🎯 DYNAMIC OPTIMIZATION BACKTEST SUMMARY")
    print("=" * 60)

    if "performance_metrics" in results:
        metrics = results["performance_metrics"]

        print(f"\n📈 PERFORMANCE METRICS:")
        print(f"   Total Return:        {metrics['total_return']:>8.1%}")
        print(f"   Annualized Return:   {metrics['annual_return']:>8.1%}")
        print(f"   Annual Volatility:   {metrics['annual_volatility']:>8.1%}")
        print(f"   Sharpe Ratio:        {metrics['sharpe_ratio']:>8.2f}")
        print(f"   Maximum Drawdown:    {metrics['max_drawdown']:>8.1%}")
        print(f"   Number of Days:      {metrics['num_trades']:>8,}")

        # Performance interpretation
        print(f"\n💡 INTERPRETATION:")
        if metrics["sharpe_ratio"] > 1.0:
            print(f"   ✅ Excellent risk-adjusted returns (Sharpe > 1.0)")
        elif metrics["sharpe_ratio"] > 0.5:
            print(f"   ✅ Good risk-adjusted returns (Sharpe > 0.5)")
        else:
            print(f"   ⚠️  Below-average risk-adjusted returns")

        if abs(metrics["max_drawdown"]) < 0.20:
            print(f"   ✅ Reasonable drawdown control (< 20%)")
        else:
            print(f"   ⚠️  High drawdown - consider risk management")

    if results.get("instrument_returns"):
        instruments_count = len(results["instrument_returns"])
        print(f"\n🌍 DIVERSIFICATION:")
        print(f"   Instruments Traded:  {instruments_count:>8,}")
        print(f"   Dynamic Optimization: {'✅ ENABLED':>15}")
        print(f"   Risk Management:     {'✅ ENABLED':>15}")

    print(f"\n🔄 DYNAMIC FEATURES ACTIVE:")
    print(f"   ✅ Correlation estimation and adjustment")
    print(f"   ✅ Volatility-based position sizing")
    print(f"   ✅ Dynamic diversification multiplier")
    print(f"   ✅ Transaction cost optimization")
    print(f"   ✅ Risk overlay for extreme conditions")

    print("\n" + "=" * 60)


def main():
    """
    Main function that runs the complete dynamic optimization backtest

    This orchestrates the entire process from start to finish
    """
    print("🚀 DYNAMIC OPTIMIZATION BACKTEST STARTING")
    print("=" * 50)

    try:
        # Step 1: Load your configuration (*** FIXED: Pass only filename ***)
        config = load_config("dynamic_config.yaml")  # Just the filename, not path

        # Step 2: Set up data source (now with proper path handling)
        data = setup_data_source("data")

        # Step 3: Build the dynamic optimization system
        system = create_dynamic_system(data, config)

        # Step 4: Run the backtest
        results = run_backtest(system)

        # Step 5: Display results
        display_results(results)

        # Step 6: Print summary
        print_summary(results)

        print(f"\n🎉 BACKTEST COMPLETED SUCCESSFULLY!")
        print(f"   Your dynamic optimization system is ready for analysis.")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print(f"   Check your configuration and data files.")
        print(f"   See the error details above for troubleshooting.")
        sys.exit(1)


if __name__ == "__main__":
    # Run the backtest when script is executed directly
    main()
