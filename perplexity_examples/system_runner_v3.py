# system_runner_v3.py
import os
import sys
import warnings
from dashboard_v1 import SimpleETFDashboard

warnings.filterwarnings('ignore')

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from perplexity_examples.enhanced_etf_system import EnhancedETFSystem
from performance_calculator_v3 import SimplePerformanceCalculator
from production_monitor_v3 import SimpleProductionMonitor


def run_simplified_analysis(system):
    """Run simplified ETF system analysis with performance calculation and health monitoring"""
    print("Running Simplified ETF System Analysis")
    print("=" * 50)

    # Performance calculation
    calculator = SimplePerformanceCalculator(target_vol=0.12)
    performance = calculator.calculate_performance(system)

    if performance:
        print(f"Portfolio Sharpe: {performance['sharpe_ratio']:.3f}")
        print(f"Annual Return: {performance['annual_return']:.1%}")
        print(f"Max Drawdown: {performance['max_drawdown']:.1%}")
        print(f"Win Rate: {performance['win_rate']:.1%}")
        print(f"Years of Data: {performance['years_analyzed']:.1f}")
    else:
        print("Performance calculation failed")

    # Health monitoring
    monitor = SimpleProductionMonitor(system)
    health = monitor.run_health_check()
    monitor.display_summary(health)

    return {
        'performance': performance,
        'health': health
    }


def show_portfolio_summary(system):
    """Display portfolio summary with start/end values"""
    try:
        print("\n" + "=" * 50)
        print("PORTFOLIO SUMMARY")
        print("=" * 50)

        portfolio = system.accounts.portfolio()
        curve = portfolio.curve()

        if curve is not None and len(curve) > 0:
            start_value = curve.iloc[0]
            end_value = curve.iloc[-1]
            total_return = ((end_value / start_value) - 1) * 100

            print(f"Starting Value: ${start_value:,.2f}")
            print(f"Ending Value: ${end_value:,.2f}")
            print(f"Total Return: {total_return:.2f}%")
            print(f"Data Period: {curve.index[0].strftime('%Y-%m-%d')} to {curve.index[-1].strftime('%Y-%m-%d')}")
            print(f"Number of Days: {len(curve)}")
        else:
            print("No portfolio curve available")

    except Exception as e:
        print(f"Error showing portfolio summary: {e}")


def main():
    """Main execution function"""
    try:
        print("ETF System Runner v3.0")
        print("=" * 30)

        # Step 1: Configure system
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "private", "etf_system", "config_v1.1.yaml"
        )

        print(f"Using config: {config_path}")

        # Step 2: Initialize ETF system
        print("Initializing ETF system...")
        etf_system = EnhancedETFSystem(
            config_path=config_path,
            test_mode=False,
            max_instruments=32
        )

        # Step 3: Download data
        print("Downloading ETF data...")
        download_count = etf_system.download_etf_data()  # Adjust method name as needed
        if download_count == 0:
            print("ERROR: No data downloaded - aborting")
            return None
        print(f"Downloaded data for {download_count} instruments")

        # Step 4: Create trading system
        print("Creating trading system...")
        system = etf_system.create_carver_compliant_system()
        if system is None:
            print("ERROR: Failed to create trading system")
            return None

        # NEW: Wait for system to complete processing
        print("Ensuring system is fully processed...")
        try:
            # Force system to calculate all components
            instruments = system.get_instrument_list()[:5]  # Test with first 5
            for instrument in instruments:
                _ = system.positionSize.get_subsystem_position(instrument)

            # Force portfolio calculation
            portfolio = system.accounts.portfolio()
            _ = portfolio.curve()

            print("System processing complete")
        except Exception as e:
            print(f"Warning: System processing issue: {e}")

        # Step 5: Show portfolio summary
        show_portfolio_summary(system)

        # Step 6: Run simplified analysis (change step numbers accordingly)
        results = run_simplified_analysis(system)

        # Step 6: Generate summary
        print("\n" + "=" * 50)
        print("ANALYSIS COMPLETE")
        print("=" * 50)

        if results['performance']:
            perf = results['performance']
            print(f"System Performance Summary:")
            print(f"  Sharpe Ratio: {perf['sharpe_ratio']:.3f}")
            print(f"  Annual Return: {perf['annual_return']:.1%}")
            print(f"  Annual Volatility: {perf['annual_volatility']:.1%}")
            print(f"  Maximum Drawdown: {perf['max_drawdown']:.1%}")
            print(f"  Win Rate: {perf['win_rate']:.1%}")
            print(f"  Data Period: {perf['years_analyzed']:.1f} years")

        health = results['health']
        print(f"\nSystem Health: {health['overall_status']}")

        # Step 7: Store results globally for inspection
        globals()['system_results'] = results
        globals()['trading_system'] = system

        # Step 8: Generate Excel Reports instead of plots
        print("Exporting performance analysis to Excel...")
        dashboard = SimpleETFDashboard(system)

        # Export comprehensive instrument analysis to Excel
        instrument_file = dashboard.export_instrument_performance_excel("etf_instrument_analysis.xlsx")

        # Export portfolio summary to Excel
        portfolio_file = dashboard.export_portfolio_summary_excel("portfolio_summary.xlsx")

        # Still create equity curve plot (this one is readable with any number of instruments)
        print("Creating equity curve plot...")
        dashboard.create_equity_curve_dashboard()

        if instrument_file:
            print(f"📊 Instrument analysis saved to: {instrument_file}")
        if portfolio_file:
            print(f"📈 Portfolio summary saved to: {portfolio_file}")

        # Step 9: Generate Turnover Analysis
        print("Exporting turnover analysis...")
        turnover_file = dashboard.export_instrument_turnover_analysis_excel("etf_turnover_analysis.xlsx")

        if turnover_file:
            print(f"📊 Turnover analysis saved to: {turnover_file}")

        # Step 10: Generate Trading Rule Analysis
        print("Exporting trading rule analysis...")
        rule_file = dashboard.export_trading_rule_analysis_excel("etf_trading_rule_analysis.xlsx")

        if rule_file:
            print(f"📊 Trading rule analysis saved to: {rule_file}")

        return results

    except Exception as e:
        print(f"ERROR in main execution: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Run the main function
    results = main()

    if results:
        print("\nResults stored in 'system_results' variable")
        print("Trading system stored in 'trading_system' variable")
    else:
        print("Analysis failed")
