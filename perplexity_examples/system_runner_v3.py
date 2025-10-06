# system_runner_v3.py - Enhanced ETF System Runner

import os
import sys
import warnings
import numpy as np  # Added for weight analysis calculations
from datetime import datetime
import traceback

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our custom modules
from dashboard_v1 import SimpleETFDashboard
from perplexity_examples.enhanced_etf_system import EnhancedETFSystem
from performance_calculator_v3 import SimplePerformanceCalculator
from production_monitor_v3 import SimpleProductionMonitor


class ETFSystemRunner:
    """
    Enhanced ETF System Runner v3.0
    Orchestrates the complete ETF trading system workflow:
    - System initialization and data download
    - Trading system creation with Carver compliance
    - Performance analysis and diagnostics
    - Comprehensive Excel reporting
    """

    def __init__(self, config_path=None, max_instruments=32, test_mode=False):
        """Initialize the system runner"""
        self.config_path = config_path or self._get_default_config_path()
        self.max_instruments = max_instruments
        self.test_mode = test_mode
        self.etf_system = None
        self.trading_system = None
        self.dashboard = None
        self.results = {}

        print(f"🚀 ETF System Runner v3.0 Initialized")
        print(f"📊 Max Instruments: {max_instruments}")
        print(f"🧪 Test Mode: {test_mode}")
        print(f"⚙️ Config: {self.config_path}")

    def _get_default_config_path(self):
        """Get default configuration path"""
        return os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "private", "etf_system", "config_v1.1.yaml"
        )

    def run_complete_analysis(self):
        """
        Run the complete ETF system analysis workflow
        Returns:
            dict: Complete analysis results
        """
        try:
            print("\n" + "=" * 80)
            print("🎯 STARTING COMPLETE ETF SYSTEM ANALYSIS")
            print("=" * 80)

            # Step 1: Initialize ETF System
            if not self._initialize_etf_system():
                return None

            # Step 2: Download and Process Data
            if not self._download_and_process_data():
                return None

            # Step 3: Create Trading System
            if not self._create_trading_system():
                return None

            # Step 4: Run System Diagnostics
            self._run_system_diagnostics()

            # Step 5: Calculate Performance
            self._calculate_system_performance()

            # Step 6: Run Health Monitoring
            self._run_health_monitoring()

            # Step 7: Generate Reports
            self._generate_comprehensive_reports()

            # Step 8: Final Summary
            self._display_final_summary()

            return self.results

        except Exception as e:
            print(f"❌ CRITICAL ERROR in complete analysis: {e}")
            traceback.print_exc()
            return None

    def _initialize_etf_system(self):
        """Initialize the Enhanced ETF System"""
        try:
            print("\n📥 Step 1: Initializing ETF System...")
            self.etf_system = EnhancedETFSystem(
                config_path=self.config_path,
                test_mode=self.test_mode,
                max_instruments=self.max_instruments
            )
            print("✅ ETF System initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize ETF system: {e}")
            return False

    def _download_and_process_data(self):
        """Download and process ETF data"""
        try:
            print("\n📊 Step 2: Downloading ETF Data...")
            download_count = self.etf_system.download_etf_data()
            if download_count == 0:
                print("❌ ERROR: No data downloaded - aborting analysis")
                return False

            print(f"✅ Successfully downloaded data for {download_count} instruments")
            self.results['downloaded_instruments'] = download_count
            return True
        except Exception as e:
            print(f"❌ Data download failed: {e}")
            return False

    def _create_trading_system(self):
        """Create the Carver-compliant trading system"""
        try:
            print("\n🔧 Step 3: Creating Carver-Compliant Trading System...")
            self.trading_system = self.etf_system.create_carver_compliant_system()
            if self.trading_system is None:
                print("❌ ERROR: Failed to create trading system")
                return False

            # Initialize dashboard
            self.dashboard = SimpleETFDashboard(self.trading_system)

            # Force complete system processing
            self._force_complete_system_processing()

            print("✅ Trading system created and processed successfully")
            return True
        except Exception as e:
            print(f"❌ Trading system creation failed: {e}")
            return False

    def _force_complete_system_processing(self):
        """Force complete system processing to ensure all components are calculated"""
        try:
            print("⏳ Ensuring complete system processing...")
            instruments = self.trading_system.get_instrument_list()

            # Force calculation of key components
            for instrument in instruments[:5]:  # Test with first 5
                try:
                    _ = self.trading_system.positionSize.get_volatility_scalar(instrument)
                    _ = self.trading_system.positionSize.get_subsystem_position(instrument)
                except:
                    continue

            # Force portfolio calculation
            try:
                portfolio = self.trading_system.accounts.portfolio()
                _ = portfolio.curve()

                # Force instrument weights calculation
                weights = self.trading_system.portfolio.get_instrument_weights()
                print(f"✅ System processing complete. Weights shape: {weights.shape}")
            except Exception as e:
                print(f"⚠️ Warning: System processing issue: {e}")

        except Exception as e:
            print(f"❌ Failed to force complete processing: {e}")

    def _run_system_diagnostics(self):
        """Run comprehensive system diagnostics"""
        try:
            print("\n🔍 Step 4: Running System Diagnostics...")

            # NEW: Add value_of_block_price_move debugging FIRST
            print("\n🔧 Value of Block Price Move Debug:")
            block_moves = self.debug_value_of_block_price_move()

            # NEW: Deep volatility chain analysis
            print("\n🔗 Deep Volatility Chain Analysis:")
            self.debug_volatility_calculation_chain(['BBAX', 'HYD', 'IVV', 'VGK'])

            # NEW: Add the 3 new debug functions
            print("\n🏢 Corporate Actions Analysis:")
            self.debug_corporate_actions(['HYD', 'IVV', 'BBAX'])

            print("\n📅 Data Period Analysis:")
            self.debug_data_periods(['HYD', 'IVV', 'BBAX'])

            print("\n📊 Yahoo Data Quality Analysis:")
            self.debug_yahoo_data_quality(['HYD', 'IVV', 'BBAX'])

            # Volatility diagnostics
            print("\n📈 Volatility Diagnostic Analysis:")
            vol_issues = self._run_volatility_diagnostics()

            # Weight conversion verification
            print("\n⚖️ Weight Conversion Verification:")
            conversion_results = self.dashboard.verify_risk_to_cash_conversion(self.trading_system)

            # NEW: Add actual vs config weights comparison
            print("\n📊 Risk vs Cash Weights Analysis:")
            weight_comparison = self.dashboard.compare_risk_vs_cash_weights(self.trading_system)

            # Position sizing formula verification
            print("\n🧮 Position Sizing Formula Verification:")
            formula_result = self.dashboard.verify_position_sizing_formula(self.trading_system)

            # NEW: Forecast scalar consistency check
            print("🔍 Forecast Scalar Consistency Verification...")
            forecast_consistency = self.dashboard.verify_forecast_scalar_consistency(self.trading_system)

            # NEW: Export comprehensive diagnostic analysis
            print("📋 Exporting comprehensive diagnostic analysis...")
            diagnostic_file = self.dashboard.export_diagnostic_analysis_excel("comprehensive_diagnostic_analysis.xlsx")
            if diagnostic_file:
                print(f"✅ Diagnostic analysis exported: {diagnostic_file}")

            # Store results
            self.results['diagnostics'] = {
                'volatility_issues': vol_issues,
                'weight_conversion': conversion_results,
                'weight_comparison': weight_comparison,
                'formula_verification': formula_result,
                'forecast_consistency': forecast_consistency,  # NEW
                'diagnostic_file': diagnostic_file  # NEW
            }

            print("✅ System diagnostics completed")

        except Exception as e:
            print(f"❌ System diagnostics failed: {e}")

    def _run_volatility_diagnostics(self):
        """Run detailed volatility diagnostics with enhanced cash weight analysis"""
        vol_issues = []
        instruments = self.trading_system.get_instrument_list()[:5]

        for instrument in instruments:
            print(f"\n--- {instrument} Volatility Analysis ---")
            try:
                # Check raw price volatility
                prices = self.trading_system.rawdata.get_daily_prices(instrument)
                if prices is not None:
                    returns = prices.pct_change().dropna()
                    manual_daily_vol = returns.std()
                    manual_annual_vol = manual_daily_vol * (252 ** 0.5)
                    print(f"📊 Manual calculation: {manual_annual_vol:.2%} annual vol")
                else:
                    print("❌ No price data available")
                    vol_issues.append(f"{instrument}: No price data")

                # Check system volatility calculation
                try:
                    vol_scalar = self.trading_system.positionSize.get_volatility_scalar(instrument)
                    if vol_scalar is not None:
                        latest_scalar = vol_scalar.iloc[-1]
                        if latest_scalar > 0:
                            implied_annual_vol = 0.12 / latest_scalar
                            print(f"🔧 System calculation: {implied_annual_vol:.2%} annual vol")
                            print(f"📏 Volatility scalar: {latest_scalar:.4f}")
                        else:
                            print("❌ Invalid volatility scalar")
                            vol_issues.append(f"{instrument}: Invalid volatility scalar")
                    else:
                        print("❌ System volatility calculation returned None")
                        vol_issues.append(f"{instrument}: No system volatility")
                except Exception as e:
                    print(f"❌ System calculation failed: {e}")
                    vol_issues.append(f"{instrument}: System calculation failed")

                # Enhanced: Check risk vs cash weights using actual cash weights
                try:
                    config_risk_weight = self.trading_system.config.instrument_weights.get(instrument, 0)

                    # NEW: Use actual cash weights instead of system method
                    cash_data = self.dashboard.get_actual_cash_weights(self.trading_system)
                    if cash_data and instrument in cash_data['cash_weights']:
                        actual_cash_weight = cash_data['cash_weights'][instrument]
                        cash_source = "ACTUAL"
                    else:
                        # Fallback to system method
                        instrument_weights = self.trading_system.portfolio.get_instrument_weights()
                        if instrument_weights is not None and instrument in instrument_weights.columns:
                            actual_cash_weight = instrument_weights[instrument].iloc[-1]
                            cash_source = "SYSTEM"
                        else:
                            actual_cash_weight = 0
                            cash_source = "NONE"

                    ratio = actual_cash_weight / config_risk_weight if config_risk_weight > 0 else 0

                    print(f"⚖️ Risk weight: {config_risk_weight:.4f}")
                    print(f"💰 Cash weight: {actual_cash_weight:.4f} ({cash_source})")
                    print(f"📊 Scaling ratio: {ratio:.2f}x")

                    if abs(ratio - 1.0) < 0.1:
                        vol_issues.append(f"{instrument}: Weights not properly scaled (ratio: {ratio:.2f})")

                except Exception as e:
                    print(f"❌ Weight comparison failed: {e}")
                    vol_issues.append(f"{instrument}: Weight comparison failed")

            except Exception as e:
                print(f"❌ {instrument}: Analysis failed: {e}")
                vol_issues.append(f"{instrument}: Analysis failed")

        return vol_issues

    def debug_value_of_block_price_move(self):
        """Debug function to check value_of_block_price_move for all instruments"""
        try:
            print("\n" + "=" * 80)
            print("🔍 DEBUG: Value of Block Price Move Analysis")
            print("=" * 80)

            instruments = self.trading_system.get_instrument_list()
            print(f"Analyzing {len(instruments)} instruments for value_of_block_price_move...\n")

            block_moves = {}
            anomalies = []

            for instrument in instruments:
                try:
                    # Get value_of_block_price_move from the system
                    block_move = self.trading_system.rawdata.get_value_of_block_price_move(instrument)

                    # Handle Series objects
                    if hasattr(block_move, 'iloc'):
                        block_value = float(block_move.iloc[-1])  # Latest value
                    else:
                        block_value = float(block_move) if block_move is not None else 1.0

                    block_moves[instrument] = block_value

                    # Check for non-standard values (not 1.0)
                    if abs(block_value - 1.0) > 0.001:  # Allow for small floating point differences
                        anomalies.append((instrument, block_value))
                        print(f"⚠️  {instrument}: {block_value:.6f} (NON-STANDARD)")
                    else:
                        print(f"✅ {instrument}: {block_value:.6f}")

                except Exception as e:
                    print(f"❌ {instrument}: ERROR - {e}")
                    block_moves[instrument] = f"ERROR: {e}"

            print(f"\n📊 SUMMARY:")
            print(f"Total instruments: {len(instruments)}")
            print(f"Non-standard block moves: {len(anomalies)}")

            if anomalies:
                print(f"\n🎯 FOCUS ON THESE ANOMALIES:")
                for instrument, value in anomalies:
                    print(f"  {instrument}: {value:.6f}")

                    # Special focus on HYD and IVV
                    if instrument in ['HYD', 'IVV']:
                        print(f"    >>> THIS MATCHES YOUR MISSING FACTOR ISSUE! <<<")

                        # Calculate expected missing factor
                        expected_factor = value  # This should match your Missing Factor
                        print(f"    Expected Missing Factor: {expected_factor:.3f}")

            # Store results for further analysis
            self.results['block_move_debug'] = {
                'block_moves': block_moves,
                'anomalies': anomalies,
                'standard_instruments': [k for k, v in block_moves.items()
                                         if isinstance(v, (int, float)) and abs(v - 1.0) <= 0.001]
            }

            return block_moves

        except Exception as e:
            print(f"❌ DEBUG function failed: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def debug_volatility_calculation_chain(self, focus_instruments=None):
        """Deep debug of the complete volatility scalar calculation chain"""
        try:
            print("\n" + "=" * 80)
            print("🔍 DEBUG: Complete Volatility Calculation Chain")
            print("=" * 80)

            if focus_instruments is None:
                focus_instruments = ['BBAX', 'HYD', 'IVV']  # Include working example + problem cases

            for instrument in focus_instruments:
                if instrument not in self.trading_system.get_instrument_list():
                    print(f"⚠️ {instrument} not in instrument list, skipping...")
                    continue

                print(f"\n🎯 ANALYZING {instrument} - COMPLETE CHAIN:")
                print("-" * 60)

                try:
                    # Step 1: Raw Price Data
                    prices = self.trading_system.rawdata.get_daily_prices(instrument)
                    latest_price = prices.iloc[-1] if prices is not None else None
                    print(f"1️⃣ Latest Price: ${latest_price:.4f}" if latest_price else "1️⃣ Price: MISSING")

                    # Step 2: Value of Block Price Move (already confirmed = 1.0)
                    block_move = self.trading_system.rawdata.get_value_of_block_price_move(instrument)
                    block_value = float(block_move.iloc[-1]) if hasattr(block_move, 'iloc') else float(block_move)
                    print(f"2️⃣ Block Price Move: {block_value:.6f}")

                    # Step 3: FX Rate (key suspect!)
                    try:
                        fx_rate = self.trading_system.rawdata.get_fx_for_instrument(instrument, "USD")
                        if hasattr(fx_rate, 'iloc'):
                            fx_value = float(fx_rate.iloc[-1])
                        else:
                            fx_value = float(fx_rate) if fx_rate is not None else 1.0
                        print(f"3️⃣ FX Rate (to USD): {fx_value:.6f}")

                        if abs(fx_value - 1.0) > 0.001:
                            print(f"    ⚠️ NON-USD CURRENCY DETECTED!")

                    except Exception as fx_error:
                        print(f"3️⃣ FX Rate: ERROR - {fx_error}")
                        fx_value = 1.0

                    # Step 4: Block Value Calculation
                    block_dollar_value = latest_price * block_value * 0.01 * fx_value
                    print(f"4️⃣ Block Value ($): ${block_dollar_value:.4f}")

                    # Step 5: Daily Returns Volatility
                    try:
                        daily_vol = self.trading_system.rawdata.daily_returns_volatility(instrument)
                        if daily_vol is not None:
                            latest_daily_vol = float(daily_vol.iloc[-1])
                            print(f"5️⃣ Daily Returns Vol: {latest_daily_vol:.6f} ({latest_daily_vol * 100:.4f}%)")

                            # Manual verification
                            returns = prices.pct_change().dropna()
                            manual_daily_vol = returns.std()
                            print(f"    Manual verification: {manual_daily_vol:.6f} ({manual_daily_vol * 100:.4f}%)")

                            vol_diff = abs(latest_daily_vol - manual_daily_vol)
                            if vol_diff > 0.0001:
                                print(f"    ⚠️ VOLATILITY DISCREPANCY: {vol_diff:.6f}")
                        else:
                            print(f"5️⃣ Daily Vol: MISSING")
                            latest_daily_vol = 0

                    except Exception as vol_error:
                        print(f"5️⃣ Daily Vol: ERROR - {vol_error}")
                        latest_daily_vol = 0

                    # Step 6: Instrument Value Volatility (Key Calculation!)
                    try:
                        instrument_value_vol = self.trading_system.positionSize.get_instrument_value_volatility(
                            instrument)
                        if instrument_value_vol is not None:
                            latest_instr_vol = float(instrument_value_vol.iloc[-1])
                            print(f"6️⃣ Instrument Value Vol: ${latest_instr_vol:.4f}")

                            # Manual calculation check
                            manual_instr_vol = block_dollar_value * latest_daily_vol
                            print(f"    Manual calculation: ${manual_instr_vol:.4f}")

                            instr_vol_diff = abs(latest_instr_vol - manual_instr_vol)
                            if instr_vol_diff > 0.01:
                                print(f"    ⚠️ INSTRUMENT VOL DISCREPANCY: ${instr_vol_diff:.4f}")
                                print(f"    🔍 This could be the source of the missing factor!")
                        else:
                            print(f"6️⃣ Instrument Value Vol: MISSING")
                            latest_instr_vol = 0

                    except Exception as instr_error:
                        print(f"6️⃣ Instrument Value Vol: ERROR - {instr_error}")
                        latest_instr_vol = 0

                    # Step 7: Daily Cash Vol Target
                    daily_cash_vol_target = 1000000 * 0.12 / 16  # Your confirmed formula
                    print(f"7️⃣ Daily Cash Vol Target: ${daily_cash_vol_target:.2f}")

                    # Step 8: Final Volatility Scalar
                    if latest_instr_vol > 0:
                        calculated_vol_scalar = daily_cash_vol_target / latest_instr_vol
                        print(f"8️⃣ Calculated Vol Scalar: {calculated_vol_scalar:.6f}")

                        # Compare with system value
                        system_vol_scalar = self.trading_system.positionSize.get_volatility_scalar(instrument)
                        if system_vol_scalar is not None:
                            system_scalar_value = float(system_vol_scalar.iloc[-1])
                            print(f"    System Vol Scalar: {system_scalar_value:.6f}")

                            scalar_diff = abs(calculated_vol_scalar - system_scalar_value)
                            if scalar_diff > 0.001:
                                print(f"    ⚠️ SCALAR DISCREPANCY: {scalar_diff:.6f}")

                            # Calculate the missing factor based on your Excel data
                            if instrument == 'HYD':
                                expected_missing = 0.873
                                actual_missing = system_scalar_value / calculated_vol_scalar
                                print(f"    🎯 Expected Missing Factor: {expected_missing:.3f}")
                                print(f"    🎯 Actual Missing Factor: {actual_missing:.3f}")

                            elif instrument == 'IVV':
                                expected_missing = 0.715
                                actual_missing = system_scalar_value / calculated_vol_scalar
                                print(f"    🎯 Expected Missing Factor: {expected_missing:.3f}")
                                print(f"    🎯 Actual Missing Factor: {actual_missing:.3f}")

                    print("-" * 60)

                except Exception as chain_error:
                    print(f"❌ {instrument} chain analysis failed: {chain_error}")

            print(f"\n📊 VOLATILITY CHAIN ANALYSIS COMPLETED")

        except Exception as e:
            print(f"❌ Volatility chain debug failed: {e}")
            import traceback
            traceback.print_exc()

    def _calculate_system_performance(self):
        """Calculate comprehensive system performance"""
        try:
            print("\n📈 Step 5: Calculating System Performance...")

            # Calculate performance using SimplePerformanceCalculator
            calculator = SimplePerformanceCalculator(target_vol=0.12)
            performance = calculator.calculate_performance(self.trading_system)

            if performance:
                print(f"✅ Performance calculated successfully:")
                print(f" 📊 Sharpe Ratio: {performance['sharpe_ratio']:.3f}")
                print(f" 💰 Annual Return: {performance['annual_return']:.1%}")
                print(f" 📉 Max Drawdown: {performance['max_drawdown']:.1%}")
                print(f" 🎯 Win Rate: {performance['win_rate']:.1%}")
                print(f" 📅 Years Analyzed: {performance['years_analyzed']:.1f}")
                self.results['performance'] = performance
            else:
                print("❌ Performance calculation failed")
                self.results['performance'] = None

            # Show portfolio summary
            self._show_portfolio_summary()

        except Exception as e:
            print(f"❌ Performance calculation failed: {e}")
            self.results['performance'] = None

    def _show_portfolio_summary(self):
        """Display comprehensive portfolio summary"""
        try:
            print("\n" + "=" * 60)
            print("💼 PORTFOLIO SUMMARY")
            print("=" * 60)

            portfolio = self.trading_system.accounts.portfolio()
            curve = portfolio.curve()

            if curve is not None and len(curve) > 0:
                start_value = curve.iloc[0]
                end_value = curve.iloc[-1]

                # Handle case where start_value might be 0
                if start_value != 0:
                    total_return = ((end_value / start_value) - 1) * 100
                else:
                    # Use capital base for return calculation
                    starting_capital = 1000000  # Default capital
                    total_return = (end_value / starting_capital) * 100

                print(f"💰 Starting P&L: ${start_value:,.2f}")
                print(f"💰 Ending P&L: ${end_value:,.2f}")
                print(f"📊 Total Return: {total_return:.2f}%")
                print(f"📅 Period: {curve.index[0].strftime('%Y-%m-%d')} to {curve.index[-1].strftime('%Y-%m-%d')}")
                print(f"📊 Data Points: {len(curve):,} days")

                # Additional portfolio metrics
                instruments = self.trading_system.get_instrument_list()
                print(f"🎯 Active Instruments: {len(instruments)}")
            else:
                print("❌ No portfolio curve available")

        except Exception as e:
            print(f"❌ Error showing portfolio summary: {e}")

    def _run_health_monitoring(self):
        """Run comprehensive system health monitoring"""
        try:
            print("\n🏥 Step 6: Running Health Monitoring...")
            monitor = SimpleProductionMonitor(self.trading_system)
            health = monitor.run_health_check()
            monitor.display_summary(health)
            self.results['health'] = health
            print("✅ Health monitoring completed")
        except Exception as e:
            print(f"❌ Health monitoring failed: {e}")
            self.results['health'] = None

    def _generate_comprehensive_reports(self):
        """Generate all comprehensive Excel reports"""
        try:
            print("\n📊 Step 7: Generating Comprehensive Reports...")
            reports_generated = {}

            # Report 1: Instrument Performance Analysis
            print("📈 Exporting instrument performance analysis...")
            instrument_file = self.dashboard.export_instrument_performance_excel(
                "etf_instrument_analysis.xlsx"
            )
            if instrument_file:
                reports_generated['instrument_analysis'] = instrument_file
                print(f"✅ Instrument analysis: {instrument_file}")

            # Report 2: Portfolio Summary
            print("💼 Exporting portfolio summary...")
            portfolio_file = self.dashboard.export_portfolio_summary_excel(
                "portfolio_summary.xlsx"
            )
            if portfolio_file:
                reports_generated['portfolio_summary'] = portfolio_file
                print(f"✅ Portfolio summary: {portfolio_file}")

            # Report 3: Cash Weights Time Series
            print("⏰ Exporting cash weights time series...")
            time_series_file = self.dashboard.export_cash_weights_time_series_excel(
                "cash_weights_time_series.xlsx"
            )
            if time_series_file:
                reports_generated['cash_weights_time_series'] = time_series_file
                print(f"✅ Cash weights time series: {time_series_file}")

            # Report 4: Final Day Backtest Report with MULTIPLE timeseries
            print("📋 Exporting final day backtest report with multiple timeseries...")
            final_day_file = self.dashboard.export_final_day_backtest_report(
                "final_day_backtest_report.xlsx",
                timeseries_instruments=['BBAX', 'IVV', 'HYD']  # SPECIFY MULTIPLE INSTRUMENTS
            )
            if final_day_file:
                reports_generated['final_day_report'] = final_day_file
                print(f"✅ Final day backtest report: {final_day_file}")

            # Report 5: Volatility Analysis
            print("📊 Exporting volatility analysis...")
            vol_file = self.dashboard.export_volatility_analysis_excel("enhanced_vol_analysis.xlsx")
            if vol_file:
                reports_generated['volatility_analysis'] = vol_file
                print(f"✅ Volatility analysis: {vol_file}")

            # Create equity curve plot (visual output)
            print("📊 Creating equity curve plot...")
            try:
                self.dashboard.create_equity_curve_plot()
            except Exception as plot_error:
                print(f"⚠️ Plot creation failed: {plot_error}")

            print("Creating strategy comparison plot...")
            try:
                self.dashboard.create_strategy_comparison_plot()
            except Exception as plot_error:
                print(f"Strategy comparison plot failed: {plot_error}")

            '''print("Creating comprehensive capital multiplier analysis...")
            try:
                self.dashboard.createcomprehensiveequitycurveplot()
            except Exception as comp_error:
                print(f"Comprehensive plot creation failed: {comp_error}")'''

            self.results['reports'] = reports_generated
            print(f"✅ Generated {len(reports_generated)} comprehensive reports")

        except Exception as e:
            print(f"❌ Report generation failed: {e}")
            import traceback
            traceback.print_exc()
            self.results['reports'] = {}

    def _display_final_summary(self):
        """Display comprehensive final summary"""
        try:
            print("\n" + "=" * 80)
            print("🎉 ANALYSIS COMPLETE - FINAL SUMMARY")
            print("=" * 80)

            # System Overview
            print("\n📊 SYSTEM OVERVIEW:")
            if self.results.get('downloaded_instruments'):
                print(f" 📈 Instruments Processed: {self.results['downloaded_instruments']}")

            if self.trading_system:
                instruments = self.trading_system.get_instrument_list()
                rules = self.trading_system.rules.trading_rules()
                print(f" 🎯 Active Instruments: {len(instruments)}")
                print(f" 📏 Trading Rules: {len(rules)}")

            # Performance Summary
            performance = self.results.get('performance')
            if performance:
                print(f"\n💰 PERFORMANCE SUMMARY:")
                print(f" 📊 Sharpe Ratio: {performance['sharpe_ratio']:.3f}")
                print(f" 💰 Annual Return: {performance['annual_return']:.1%}")
                print(f" 📉 Annual Volatility: {performance['annual_volatility']:.1%}")
                print(f" 📉 Maximum Drawdown: {performance['max_drawdown']:.1%}")
                print(f" 🎯 Win Rate: {performance['win_rate']:.1%}")
                print(f" 📅 Analysis Period: {performance['years_analyzed']:.1f} years")

            # Health Status
            health = self.results.get('health')
            if health:
                print(f"\n🏥 SYSTEM HEALTH: {health['overall_status']}")

            # Weight Analysis Summary (NEW)
            diagnostics = self.results.get('diagnostics', {})
            weight_comparison = diagnostics.get('weight_comparison')
            if weight_comparison:
                print(f"\n⚖️ WEIGHT ANALYSIS SUMMARY:")

                # Calculate summary statistics
                scaling_factors = [d['scaling_factor'] for d in weight_comparison.values() if d['scaling_factor'] > 0]
                if scaling_factors:
                    avg_scaling = np.mean(scaling_factors)
                    min_scaling = np.min(scaling_factors)
                    max_scaling = np.max(scaling_factors)

                    print(f" 📊 Average Scaling Factor: {avg_scaling:.2f}x")
                    print(f" 📊 Scaling Range: {min_scaling:.2f}x - {max_scaling:.2f}x")

                    # Identify extreme cases
                    extreme_instruments = []
                    for instrument, data in weight_comparison.items():
                        if data['scaling_factor'] > 2.0:
                            extreme_instruments.append(f"{instrument} (HIGH: {data['scaling_factor']:.1f}x)")
                        elif data['scaling_factor'] < 0.5:
                            extreme_instruments.append(f"{instrument} (LOW: {data['scaling_factor']:.1f}x)")

                    if extreme_instruments:
                        print(f" ⚠️ Extreme Scaling Cases: {', '.join(extreme_instruments[:3])}")
                        if len(extreme_instruments) > 3:
                            print(f"   ... and {len(extreme_instruments) - 3} more")

            # Reports Generated
            reports = self.results.get('reports', {})
            if reports:
                print(f"\n📊 REPORTS GENERATED ({len(reports)}):")
                for report_type, filename in reports.items():
                    print(f" 📁 {report_type}: {filename}")

            # Diagnostic Issues
            vol_issues = diagnostics.get('volatility_issues', [])
            if vol_issues:
                print(f"\n⚠️ DIAGNOSTIC ISSUES FOUND ({len(vol_issues)}):")
                for issue in vol_issues[:5]:  # Show first 5
                    print(f" • {issue}")
                if len(vol_issues) > 5:
                    print(f" ... and {len(vol_issues) - 5} more issues")
            else:
                print(f"\n✅ NO MAJOR DIAGNOSTIC ISSUES FOUND")

            print("\n" + "=" * 80)
            print("🚀 ETF SYSTEM ANALYSIS COMPLETED SUCCESSFULLY")
            print("=" * 80)

        except Exception as e:
            print(f"❌ Error displaying final summary: {e}")

    def debug_corporate_actions(self, focus_instruments=['HYD', 'IVV', 'BBAX']):
        """Check for corporate actions affecting price/volatility calculations"""
        import pandas as pd
        try:
            print(f"\n🔍 CORPORATE ACTIONS DEBUG")
            print("=" * 60)

            for instrument in focus_instruments:
                print(f"\n📊 {instrument} - Price History Analysis:")

                # Get raw price data
                prices = self.trading_system.rawdata.get_daily_prices(instrument)
                returns = prices.pct_change().dropna()

                # Check for unusual price jumps (splits/dividends)
                large_moves = returns[abs(returns) > 0.05]  # >5% moves
                very_large_moves = returns[abs(returns) > 0.10]  # >10% moves

                print(f"   📈 Total observations: {len(prices)}")
                print(f"   📈 Large moves (>5%): {len(large_moves)}")
                print(f"   📈 Very large moves (>10%): {len(very_large_moves)}")

                if len(very_large_moves) > 0:
                    print(f"   ⚠️ SUSPICIOUS LARGE MOVES DETECTED:")
                    for date, move in very_large_moves.tail(5).items():
                        print(f"      {date.strftime('%Y-%m-%d')}: {move:.4f} ({move * 100:.2f}%)")

                # Check price level consistency
                price_start = prices.iloc[0]
                price_end = prices.iloc[-1]
                total_return = (price_end / price_start) - 1

                print(f"   💰 Start price: ${price_start:.4f}")
                print(f"   💰 End price: ${price_end:.4f}")
                print(f"   📈 Total return: {total_return:.4f} ({total_return * 100:.2f}%)")

                # Check for price discontinuities
                price_ratios = prices / prices.shift(1)
                unusual_ratios = price_ratios[(price_ratios < 0.8) | (price_ratios > 1.2)]

                if len(unusual_ratios) > 0:
                    print(f"   ⚠️ PRICE DISCONTINUITIES DETECTED:")
                    for date, ratio in unusual_ratios.tail(3).items():
                        prev_price = prices.shift(1).loc[date]
                        curr_price = prices.loc[date]
                        print(
                            f"      {date.strftime('%Y-%m-%d')}: ${prev_price:.4f} → ${curr_price:.4f} (ratio: {ratio:.4f})")

        except Exception as e:
            print(f"❌ Corporate actions debug failed: {e}")

    def debug_data_periods(self, focus_instruments=['HYD', 'IVV', 'BBAX']):
        """Check data period consistency across instruments"""
        import pandas as pd
        try:
            print(f"\n🔍 DATA PERIOD ANALYSIS")
            print("=" * 60)

            for instrument in focus_instruments:
                prices = self.trading_system.rawdata.get_daily_prices(instrument)
                returns = prices.pct_change().dropna()

                print(f"\n📅 {instrument}:")
                print(f"   Start: {prices.index[0].strftime('%Y-%m-%d')}")
                print(f"   End: {prices.index[-1].strftime('%Y-%m-%d')}")
                print(f"   Total days: {len(prices)}")
                print(f"   Valid returns: {len(returns)}")
                print(f"   Missing data: {prices.isnull().sum()}")

                # Check for gaps in data
                price_dates = pd.DataFrame(index=prices.index)
                price_dates['trading_day'] = 1
                full_range = pd.date_range(start=prices.index[0], end=prices.index[-1], freq='D')
                missing_dates = []

                for date in full_range:
                    if date.weekday() < 5:  # Weekdays only
                        if date not in prices.index:
                            missing_dates.append(date)

                if len(missing_dates) > 5:  # Only show if significant gaps
                    print(f"   ⚠️ Missing trading days: {len(missing_dates)}")
                    print(f"      Recent gaps: {[d.strftime('%Y-%m-%d') for d in missing_dates[-3:]]}")

        except Exception as e:
            print(f"❌ Data periods debug failed: {e}")

    def debug_yahoo_data_quality(self, focus_instruments=['HYD', 'IVV', 'BBAX']):
        """Check Yahoo Finance data quality for specific instruments"""
        try:
            print(f"\n🔍 YAHOO FINANCE DATA QUALITY CHECK")
            print("=" * 60)

            for instrument in focus_instruments:
                print(f"\n📊 {instrument} - Data Quality Analysis:")

                # Get price data and check basic stats
                prices = self.trading_system.rawdata.get_daily_prices(instrument)
                returns = prices.pct_change().dropna()

                # Basic statistics
                vol_simple = returns.std()
                vol_pst = self.trading_system.rawdata.daily_returns_volatility(instrument).iloc[-1]

                print(f"   📈 Simple volatility: {vol_simple:.6f}")
                print(f"   📈 PST volatility: {vol_pst:.6f}")
                print(f"   📈 Ratio (PST/Simple): {vol_pst / vol_simple:.6f}")

                # Check for zero returns (data issues)
                zero_returns = (returns == 0).sum()
                print(f"   📊 Zero return days: {zero_returns}")

                # Check return distribution
                print(f"   📊 Return stats:")
                print(f"      Mean: {returns.mean():.6f}")
                print(f"      Std: {returns.std():.6f}")
                print(f"      Min: {returns.min():.6f}")
                print(f"      Max: {returns.max():.6f}")
                print(f"      Skew: {returns.skew():.6f}")

                # Check recent price behavior
                recent_prices = prices.tail(20)
                recent_returns = returns.tail(20)
                print(f"   📊 Recent 20-day volatility: {recent_returns.std():.6f}")

        except Exception as e:
            print(f"❌ Yahoo data quality debug failed: {e}")

    def get_trading_system(self):
        """Get the trading system for external access"""
        return self.trading_system

    def get_results(self):
        """Get complete analysis results"""
        return self.results


def main():
    """Main execution function with improved error handling"""
    try:
        # Initialize the system runner
        runner = ETFSystemRunner(
            max_instruments=32,  # Adjust as needed
            test_mode=False  # Set to True for faster testing
        )

        # Run complete analysis
        results = runner.run_complete_analysis()

        if results:
            # Store results globally for interactive access
            globals()['system_results'] = results
            globals()['trading_system'] = runner.get_trading_system()
            globals()['system_runner'] = runner

            print(f"\n✅ Analysis completed successfully!")
            print(f"📊 Results stored in 'system_results' variable")
            print(f"🔧 Trading system stored in 'trading_system' variable")
            print(f"🏃 System runner stored in 'system_runner' variable")
            return results
        else:
            print(f"\n❌ Analysis failed - check error messages above")
            return None

    except KeyboardInterrupt:
        print(f"\n⏹️ Analysis interrupted by user")
        return None
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR in main execution: {e}")
        traceback.print_exc()
        return None


# Utility functions for enhanced functionality
def run_quick_analysis(max_instruments=10):
    """Run quick analysis with limited instruments for testing"""
    runner = ETFSystemRunner(max_instruments=max_instruments, test_mode=True)
    return runner.run_complete_analysis()


def run_full_analysis():
    """Run full analysis with all available instruments"""
    runner = ETFSystemRunner(max_instruments=50, test_mode=False)
    return runner.run_complete_analysis()


def create_dashboard_only(system):
    """Create dashboard from existing system for additional analysis"""
    if system is None:
        print("❌ No trading system provided")
        return None

    dashboard = SimpleETFDashboard(system)
    print("✅ Dashboard created for additional analysis")
    return dashboard


def debug_block_moves_only():
    """Standalone function to quickly debug block moves"""
    try:
        print("🚀 Quick Block Move Debug - ETF System")

        # Quick system setup
        runner = ETFSystemRunner(max_instruments=10, test_mode=True)

        if not runner._initialize_etf_system():
            return None

        if not runner._download_and_process_data():
            return None

        if not runner._create_trading_system():
            return None

        # Run our debug
        return runner.debug_value_of_block_price_move()

    except Exception as e:
        print(f"❌ Quick debug failed: {e}")
        return None


def debug_volatility_chain_only():
    """Standalone function to debug volatility chain"""
    try:
        print("🚀 Quick Volatility Chain Debug")

        runner = ETFSystemRunner(max_instruments=20, test_mode=True)

        if not runner._initialize_etf_system():
            return None
        if not runner._download_and_process_data():
            return None
        if not runner._create_trading_system():
            return None

        # Run the chain debug on problem instruments
        runner.debug_volatility_calculation_chain(['HYD', 'IVV', 'BBAX'])

    except Exception as e:
        print(f"❌ Chain debug failed: {e}")


# To run just this debug:
# debug_volatility_chain_only()


if __name__ == "__main__":
    # Run the complete analysis
     main()
    #debug_results = debug_volatility_chain_only()

