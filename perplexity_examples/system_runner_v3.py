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

        print("=== DETAILED VOLATILITY DIAGNOSTIC ===")
        instruments = system.get_instrument_list()[:5]

        for instrument in instruments:
            print(f"\n--- {instrument} Detailed Analysis ---")

            # 1. Check raw price volatility
            try:
                prices = system.rawdata.get_daily_prices(instrument)
                if prices is not None:
                    returns = prices.pct_change().dropna()
                    manual_daily_vol = returns.std()
                    manual_annual_vol = manual_daily_vol * (252 ** 0.5)
                    print(f"Manual calculation: {manual_annual_vol:.2%} annual vol")
                else:
                    print("No price data available")
            except Exception as e:
                print(f"Manual calculation failed: {e}")

            # 2. Check system volatility calculation
            try:
                vol_data = system.rawdata.get_daily_returns_volatility(instrument)
                if vol_data is not None:
                    system_daily_vol = vol_data.iloc[-1]
                    system_annual_vol = system_daily_vol * (252 ** 0.5)
                    print(f"System calculation: {system_annual_vol:.2%} annual vol")
                else:
                    print("System volatility calculation returned None")
            except Exception as e:
                print(f"System calculation failed: {e}")

            # 3. Check volatility scalar
            try:
                vol_scalar = system.positionSize.get_volatility_scalar(instrument)
                if vol_scalar is not None:
                    latest_scalar = vol_scalar.iloc[-1]
                    print(f"Volatility scalar: {latest_scalar:.4f}")

                    # Calculate what the annual vol should be
                    if latest_scalar > 0:
                        implied_annual_vol = 0.12 / latest_scalar  # 12% target / scalar
                        print(f"Implied annual vol: {implied_annual_vol:.2%}")
                else:
                    print("Volatility scalar is None")
            except Exception as e:
                print(f"Volatility scalar failed: {e}")

            # 4. Check risk vs cash weights
            try:
                config_risk_weight = system.config.instrument_weights.get(instrument, 0)

                instrument_weights = system.portfolio.get_instrument_weights()
                if instrument_weights is not None and instrument in instrument_weights.columns:
                    actual_cash_weight = instrument_weights[instrument].iloc[-1]

                    print(f"Risk weight: {config_risk_weight:.4f}")
                    print(f"Cash weight: {actual_cash_weight:.4f}")
                    print(f"Ratio (should not be 1.0): {actual_cash_weight / config_risk_weight:.4f}")
                else:
                    print("No cash weights available")
            except Exception as e:
                print(f"Weight comparison failed: {e}")

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

        # Step 11: Generate Weights and Multipliers Analysis
        print("Exporting weights and multipliers analysis...")
        weights_file = dashboard.export_weights_and_multipliers_excel("system_weights_multipliers.xlsx")

        if weights_file:
            print(f"📊 Weights and multipliers analysis saved to: {weights_file}")

        # Step 12: Verify Instrument Weight Estimation
        print("Verifying instrument weight estimation...")
        verification_results = dashboard.verify_instrument_weight_estimation(system)

        # Step 13: Generate Instrument Volatility Analysis
        print("Exporting instrument volatility analysis...")
        volatility_file = dashboard.export_instrument_volatility_analysis_excel("instrument_volatility_analysis.xlsx")

        if volatility_file:
            print(f"📊 Volatility analysis saved to: {volatility_file}")

        # Add to your system_runner_v3.py after the existing analysis
        print("Verifying risk-to-cash weight conversion...")
        conversion_results = dashboard.verify_risk_to_cash_conversion(system)

        print("Verifying position sizing pipeline...")
        dashboard.verify_position_sizing_pipeline(system)

        print("Checking weight evolution...")
        dashboard.check_weight_evolution(system)

        # NEW: Add comprehensive weight conversion diagnosis
        print("Running comprehensive weight conversion diagnosis...")
        diagnosis_results = etf_system.diagnose_and_fix_weight_conversion(system)

        # Enhanced verification with detailed output
        print("Verifying risk-to-cash weight conversion...")
        conversion_results = dashboard.verify_risk_to_cash_conversion(system)

        # Safe system verification first
        print("Running FIXED weight conversion diagnosis...")
        dashboard = SimpleETFDashboard(system)

        # Run the fixed diagnostics
        print("1. Testing volatility calculations...")
        vol_issues = dashboard.debug_volatility_calculation(system)

        print("2. Testing weight conversion...")
        conversion_results = dashboard.verify_risk_to_cash_conversion(system)

        if vol_issues:
            print(f"\n⚠️ Volatility issues found: {len(vol_issues)}")
            for issue in vol_issues[:5]:  # Show first 5
                print(f"  • {issue}")
        else:
            print("✅ No volatility calculation issues found")

        if conversion_results:
            print("✅ Weight conversion verification completed - see results above")
        else:
            print("❌ Weight conversion verification failed")

        print("Exporting position sizing pipeline debug...")
        pipeline_debug_file = dashboard.export_complete_position_sizing_factors_excel(
            "position_sizing_pipeline_debug.xlsx")

        if pipeline_debug_file:
            print(f"📊 Position sizing pipeline debug saved to: {pipeline_debug_file}")

        # ADD THIS NEW SECTION HERE:
        print("Verifying position sizing formula...")
        formula_result = dashboard.verify_position_sizing_formula(system)
        print(f"📊 Position sizing formula result: {formula_result}")

        return results

    except Exception as e:
        print(f"ERROR in main execution: {e}")
        import traceback
        traceback.print_exc()
        return None

    force_complete_system_processing(system)




def force_complete_system_processing(system):
    """Force complete system processing before analysis"""

    print("Forcing complete system processing...")

    instruments = system.get_instrument_list()

    # Force all volatility scalars to be calculated
    for instrument in instruments:
        try:
            _ = system.positionSize.get_volatility_scalar(instrument)
            _ = system.positionSize.get_subsystem_position(instrument)
        except:
            continue

    # Force IDM calculation
    try:
        _ = system.portfolio.get_instrument_diversification_multiplier()
    except:
        pass

    # Force instrument weights calculation (this should trigger volatility scaling)
    try:
        weights = system.portfolio.get_instrument_weights()
        print(f"Forced calculation complete. Weights shape: {weights.shape}")
    except Exception as e:
        print(f"Failed to force complete processing: {e}")


if __name__ == "__main__":
    # Run the main function
    results = main()

    if results:
        print("\nResults stored in 'system_results' variable")
        print("Trading system stored in 'trading_system' variable")
    else:
        print("Analysis failed")
