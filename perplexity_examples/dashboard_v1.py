# dashboard_v1.py - Simple ETF System Dashboard

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime
from performance_calculator_v3 import SimplePerformanceCalculator
import seaborn as sns


class SimpleETFDashboard:
    def __init__(self, system):
        self.system = system
        self.calculator = SimplePerformanceCalculator()

    def get_actual_cash_weights(self, system, date=None):
        """
        ENHANCED: Extract cash weights using Carver's method with detailed volatility info
        """
        try:
            instruments = system.get_instrument_list()
            if date is None:
                portfolio = system.accounts.portfolio()
                if portfolio is None or len(portfolio.curve()) == 0:
                    print("❌ No portfolio data available")
                    return None
                date = portfolio.curve().index[-1]

            # Get system's portfolio value
            starting_capital = 1000000
            portfolio_curve = system.accounts.portfolio().curve()
            portfolio_pnl = portfolio_curve.asof(date)
            if pd.isna(portfolio_pnl):
                portfolio_pnl = 0
            system_portfolio_value = starting_capital + portfolio_pnl

            print(f"📊 ENHANCED Portfolio Analysis for {date}")
            print(f"💰 Starting Capital: ${starting_capital:,.2f}")
            print(f"📈 P&L to Date: ${portfolio_pnl:,.2f}")
            print(f"💼 Current Portfolio Value: ${system_portfolio_value:,.2f}")

            # Get risk weights and volatility target from config
            risk_weights = getattr(system.config, 'instrument_weights', {})
            vol_target = getattr(system.config, 'percentage_vol_target', 12.0) / 100

            # Calculate enhanced cash weights
            enhanced_cash_weights = {}
            actual_cash_positions = {}
            volatility_details = {}

            for instrument in instruments:
                try:
                    risk_weight = risk_weights.get(instrument, 0)

                    # Get detailed volatility information
                    vol_data = self._get_detailed_volatility_info(system, instrument, vol_target)
                    volatility_details[instrument] = vol_data

                    # Calculate cash weight using Carver's formula
                    if vol_data['volatility_scalar'] and vol_data['volatility_scalar'] > 0:
                        fundamental_weight = risk_weight * vol_data['volatility_scalar']
                        enhanced_cash_weights[instrument] = fundamental_weight
                        # Calculate theoretical cash position
                        notional_position = fundamental_weight * system_portfolio_value
                        actual_cash_positions[instrument] = notional_position
                    else:
                        enhanced_cash_weights[instrument] = 0
                        actual_cash_positions[instrument] = 0

                except Exception as e:
                    print(f"⚠️ Error processing {instrument}: {e}")
                    enhanced_cash_weights[instrument] = 0
                    actual_cash_positions[instrument] = 0
                    volatility_details[instrument] = {'daily_volatility': None, 'annual_volatility': None,
                                                      'volatility_scalar': None}

            # Normalize weights to sum to 1.0
            total_weight = sum(enhanced_cash_weights.values())
            normalized_cash_weights = {}
            if total_weight > 0:
                for instrument, weight in enhanced_cash_weights.items():
                    normalized_cash_weights[instrument] = weight / total_weight
            else:
                normalized_cash_weights = {instrument: 0 for instrument in instruments}

            # Display significant positions with volatility details
            total_cash_deployed = sum(actual_cash_positions.values())
            print(f"💸 Total Cash Deployed (Theoretical): ${total_cash_deployed:,.2f}")
            print(f"📊 Deployment Ratio: {total_cash_deployed / system_portfolio_value:.2f}x")
            print(f"\n📈 Position Details:")

            for instrument, weight in normalized_cash_weights.items():
                if weight > 0.01:  # Only print significant positions
                    cash_pos = actual_cash_positions.get(instrument, 0)
                    vol_details = volatility_details.get(instrument, {})
                    vol_scalar = vol_details.get('volatility_scalar', 0)
                    annual_vol = vol_details.get('annual_volatility', 0)

                    print(f"  {instrument}: {weight:.2%} (${cash_pos:,.0f}) "
                          f"[Vol: {annual_vol * 100 if annual_vol else 0:.1f}%, Scalar: {vol_scalar:.2f}]")

            return {
                'cash_weights': normalized_cash_weights,
                'cash_positions': actual_cash_positions,
                'volatility_details': volatility_details,  # NEW: detailed volatility info
                'total_portfolio_cash': system_portfolio_value,
                'total_cash_deployed': total_cash_deployed,
                'date': date,
                'method': 'enhanced_carver_method'
            }

        except Exception as e:
            print(f"❌ Error calculating enhanced cash weights: {e}")
            import traceback
            traceback.print_exc()
            return None

    def compare_risk_vs_cash_weights(self, system):
        """
        ENHANCED: Compare config risk weights vs fundamental cash weights
        Now includes detailed volatility breakdown
        """
        print("=== ENHANCED RISK vs CASH WEIGHTS ANALYSIS ===")

        # Get config risk weights
        config_weights = getattr(system.config, 'instrument_weights', {})
        vol_target = getattr(system.config, 'percentage_vol_target', 12.0) / 100  # Convert to decimal

        print("-" * 120)
        print(
            f"{'Instrument':12} {'Risk Wt':8} {'Daily Vol':10} {'Annual Vol':11} {'Vol Target':10} {'Vol Scalar':10} {'Cash Wt':10} {'Scaling':8}")
        print("-" * 120)

        comparison_data = {}

        for instrument in system.get_instrument_list():
            try:
                # Step 1: Extract risk weight from config
                risk_weight = config_weights.get(instrument, 0)

                # Step 2: Get detailed volatility information
                vol_data = self._get_detailed_volatility_info(system, instrument, vol_target)

                # Step 3: Calculate cash weight using Carver's formula
                if vol_data['volatility_scalar'] and vol_data['volatility_scalar'] > 0:
                    cash_weight = risk_weight * vol_data['volatility_scalar']
                    scaling_factor = vol_data['volatility_scalar']
                else:
                    cash_weight = 0
                    scaling_factor = 0

                # Store enhanced data
                comparison_data[instrument] = {
                    'risk_weight': risk_weight,
                    'daily_volatility': vol_data['daily_volatility'],
                    'annual_volatility': vol_data['annual_volatility'],
                    'volatility_target': vol_target,
                    'volatility_scalar': vol_data['volatility_scalar'],
                    'cash_weight': cash_weight,
                    'scaling_factor': scaling_factor,
                    'volatility_effect': scaling_factor - 1.0 if scaling_factor else 0,
                    'weight_difference': cash_weight - risk_weight
                }

                # Display row
                print(
                    f"{instrument:12} {risk_weight:8.4f} {vol_data['daily_volatility'] or 0:10.4f} {vol_data['annual_volatility'] or 0:11.4f} "
                    f"{vol_target:10.4f} {vol_data['volatility_scalar'] or 0:10.4f} {cash_weight:10.4f} {scaling_factor:8.2f}")

            except Exception as e:
                print(f"❌ Error processing {instrument}: {e}")
                comparison_data[instrument] = {
                    'risk_weight': 0, 'daily_volatility': None, 'annual_volatility': None,
                    'volatility_target': vol_target, 'volatility_scalar': 0, 'cash_weight': 0,
                    'scaling_factor': 0, 'volatility_effect': 0, 'weight_difference': 0
                }

        print("-" * 120)
        print("💡 Key: Daily Vol = daily standard deviation, Annual Vol = daily × √252")
        print("💡 Formula: Vol Scalar = Vol Target ÷ Annual Vol, Cash Weight = Risk Weight × Vol Scalar")

        return comparison_data

    def get_volatility_scalar_safe(self, system, instrument):
        """
        ENHANCED: Safely get volatility scalar using multiple PySystemTrade methods
        Now returns both value and source information for tracking
        """
        # Method 1: Direct volatility scalar access (most reliable)
        try:
            vol_scalar_series = system.positionSize.get_volatility_scalar(instrument)
            if vol_scalar_series is not None and len(vol_scalar_series) > 0:
                vol_scalar = vol_scalar_series.iloc[-1]
                if vol_scalar > 0:
                    return vol_scalar, "PYSYSTEMTRADE_DIRECT"
        except (AttributeError, Exception):
            pass

        # Method 2: Alternative method names for different versions
        alternative_methods = ['get_vol_scalar', 'volatility_scalar', '_volatility_scalar']
        for method_name in alternative_methods:
            try:
                if hasattr(system.positionSize, method_name):
                    method = getattr(system.positionSize, method_name)
                    vol_scalar_series = method(instrument)
                    if vol_scalar_series is not None and len(vol_scalar_series) > 0:
                        vol_scalar = vol_scalar_series.iloc[-1]
                        if vol_scalar > 0:
                            return vol_scalar, f"PYSYSTEMTRADE_{method_name.upper()}"
            except (AttributeError, Exception):
                continue

        # Method 3: Reverse engineer from position calculations
        try:
            subsystem_pos = system.positionSize.get_subsystem_position(instrument)
            combined_forecast = system.combForecast.get_combined_forecast(instrument)

            if (subsystem_pos is not None and combined_forecast is not None and
                    len(subsystem_pos) > 0 and len(combined_forecast) > 0):

                # Find the most recent date with both data points
                pos_dates = set(subsystem_pos.dropna().index)
                forecast_dates = set(combined_forecast.dropna().index)
                common_dates = sorted(pos_dates.intersection(forecast_dates))

                if len(common_dates) > 0:
                    latest_date = common_dates[-1]
                    pos = subsystem_pos.loc[latest_date]
                    forecast = combined_forecast.loc[latest_date]

                    if abs(forecast) > 0.01:  # Avoid division by very small numbers
                        # Formula: subsystem_position = (vol_scalar * combined_forecast) / 10
                        vol_scalar = (pos * 10) / forecast
                        if vol_scalar > 0:
                            return abs(vol_scalar), "REVERSE_ENGINEERED"
        except (AttributeError, Exception):
            pass

        # Method 4: Manual calculation from raw volatility data
        try:
            # Get daily volatility
            vol_series = system.rawdata.get_daily_percentage_volatility(instrument)
            if vol_series is not None and len(vol_series) > 0:
                current_vol = vol_series.iloc[-1]
                if current_vol > 0:
                    # Get target volatility from config
                    vol_target = getattr(system.config, 'percentage_vol_target', 12.0) / 100
                    vol_scalar = vol_target / current_vol
                    return vol_scalar, "CALCULATED_FROM_VOLATILITY"
        except (AttributeError, Exception):
            pass

        # Method 5: Final fallback - calculate from price data
        try:
            prices = system.rawdata.get_daily_prices(instrument)
            if prices is not None and len(prices) >= 35:
                returns = prices.pct_change().dropna()
                if len(returns) >= 35:
                    # Calculate 35-day rolling volatility (matching your config)
                    daily_vol = returns.rolling(window=35, min_periods=10).std().iloc[-1]
                    if daily_vol > 0:
                        annual_vol = daily_vol * (252 ** 0.5)  # Annualize
                        vol_target = getattr(system.config, 'percentage_vol_target', 12.0) / 100
                        vol_scalar = vol_target / annual_vol
                        return vol_scalar, "CALCULATED_FROM_PRICES"
        except Exception:
            pass

        print(f"WARNING: Could not extract volatility scalar for {instrument}")
        return 0, "ERROR_ALL_METHODS_FAILED"

    def _get_actual_cash_weights_quiet(self, system, date=None):
        """
        FIXED: Quiet version using correct PySystemTrade volatility scalar access
        """
        try:
            instruments = system.get_instrument_list()
            if date is None:
                portfolio = system.accounts.portfolio()
                date = portfolio.curve().index[-1]

            # Get system's portfolio value
            starting_capital = 1000000
            portfolio_curve = system.accounts.portfolio().curve()
            portfolio_pnl = portfolio_curve.asof(date)
            if pd.isna(portfolio_pnl):
                portfolio_pnl = 0

            system_portfolio_value = starting_capital + portfolio_pnl

            # Get risk weights from config
            risk_weights = getattr(system.config, 'instrument_weights', {})

            # Calculate fundamental cash weights
            fundamental_cash_weights = {}
            actual_cash_positions = {}

            for instrument in instruments:
                try:
                    # FIXED: Use safe volatility scalar method
                    vol_scalar = self._get_volatility_scalar_safe(system, instrument)

                    if vol_scalar > 0:
                        risk_weight = risk_weights.get(instrument, 0)
                        fundamental_weight = risk_weight * vol_scalar
                        fundamental_cash_weights[instrument] = fundamental_weight

                        # Calculate theoretical cash position
                        notional_position = fundamental_weight * system_portfolio_value
                        actual_cash_positions[instrument] = notional_position
                    else:
                        fundamental_cash_weights[instrument] = 0
                        actual_cash_positions[instrument] = 0

                except Exception:
                    fundamental_cash_weights[instrument] = 0
                    actual_cash_positions[instrument] = 0

            # Normalize weights
            total_weight = sum(fundamental_cash_weights.values())
            normalized_cash_weights = {}

            if total_weight > 0:
                for instrument, weight in fundamental_cash_weights.items():
                    normalized_cash_weights[instrument] = weight / total_weight
            else:
                normalized_cash_weights = {instrument: 0 for instrument in instruments}

            total_cash_deployed = sum(actual_cash_positions.values())

            return {
                'cash_weights': normalized_cash_weights,
                'cash_positions': actual_cash_positions,
                'total_portfolio_cash': system_portfolio_value,
                'total_cash_deployed': total_cash_deployed,
                'date': date,
                'method': 'carver_fundamental_cash_weights'
            }

        except Exception as e:
            return None

    def get_cash_weights_over_time(self, system):
        """
        FIXED: Get cash weights AND volatility data over time with proper error handling
        """
        try:
            print("=== Calculating Cash Weights & Volatility Over Time ===")

            instruments = system.get_instrument_list()
            portfolio = system.accounts.portfolio()
            portfolio_curve = portfolio.curve()

            if portfolio_curve is None or len(portfolio_curve) == 0:
                print("❌ No portfolio curve data available")
                return None

            # Starting capital for calculations
            starting_capital = 1000000
            vol_target = getattr(system.config, 'percentage_vol_target', 12.0) / 100

            # Get date range (use ALL data points for complete backtest)
            dates = portfolio_curve.index

            # Initialize data containers
            cash_weights_data = {}
            cash_positions_data = {}
            volatility_scalar_data = {}
            implied_volatility_data = {}
            manual_volatility_data = {}
            portfolio_values = []

            print(f"📊 Processing {len(dates)} time periods for {len(instruments)} instruments")
            print("📈 Collecting: Cash Weights, Positions, Vol Scalars, Implied Vol, Manual Vol")

            # Pre-calculate volatility data with proper error handling
            print("🔄 Pre-calculating volatility data...")
            vol_scalars_cache = {}
            manual_vol_cache = {}

            for instrument in instruments:
                print(f"  📈 Processing volatility for {instrument}")

                try:
                    # FIXED: Use safe method for volatility scalars
                    vol_scalar = self._get_volatility_scalar_safe(system, instrument)
                    if vol_scalar > 0:
                        # Create a simple series for consistent access
                        vol_scalars_cache[instrument] = pd.Series([vol_scalar], index=[dates[-1]])
                        print(f"  ✅ Vol scalar: {vol_scalar:.4f}")
                    else:
                        print(f"  ⚠️ No vol scalar for {instrument}")
                        vol_scalars_cache[instrument] = None

                    # Calculate manual volatility time series
                    prices = system.rawdata.get_daily_prices(instrument)
                    if prices is not None and len(prices) > 50:
                        returns = prices.pct_change().dropna()
                        # Calculate rolling 30-day volatility
                        rolling_vol = returns.rolling(window=30, min_periods=10).std()
                        annualized_vol = rolling_vol * (252 ** 0.5)
                        manual_vol_cache[instrument] = annualized_vol
                        print(f"  ✅ Manual vol: {len(annualized_vol)} data points")
                    else:
                        print(f"  ⚠️ Insufficient price data for {instrument}")
                        manual_vol_cache[instrument] = None

                except Exception as e:
                    print(f"  ❌ Error processing {instrument}: {e}")
                    vol_scalars_cache[instrument] = None
                    manual_vol_cache[instrument] = None

            # Process each date with cached data
            for i, date in enumerate(dates):
                if i % 20 == 0:  # Progress indicator
                    print(f"⏳ Processing date {i + 1}/{len(dates)}: {date.strftime('%Y-%m-%d')}")

                # Calculate portfolio value for this date
                portfolio_pnl = portfolio_curve.asof(date)
                if pd.isna(portfolio_pnl):
                    continue

                portfolio_value = starting_capital + portfolio_pnl
                portfolio_values.append(portfolio_value)

                # Get cash weights for this specific date
                weights_data = self._get_actual_cash_weights_quiet(system, date=date)

                # Process each instrument for this date
                for instrument in instruments:
                    # Initialize instrument data containers if needed
                    for data_dict in [cash_weights_data, cash_positions_data,
                                      volatility_scalar_data, implied_volatility_data,
                                      manual_volatility_data]:
                        if instrument not in data_dict:
                            data_dict[instrument] = []

                    # Append cash weight and position data
                    if weights_data:
                        weight = weights_data['cash_weights'].get(instrument, 0)
                        position = weights_data['cash_positions'].get(instrument, 0)
                        cash_weights_data[instrument].append(weight)
                        cash_positions_data[instrument].append(position)
                    else:
                        cash_weights_data[instrument].append(0)
                        cash_positions_data[instrument].append(0)

                    # Collect volatility data using cached series
                    try:
                        # Get volatility scalar from cache
                        if vol_scalars_cache.get(instrument) is not None:
                            vol_scalar = self._get_volatility_scalar_safe(system, instrument)

                            if vol_scalar > 0:
                                volatility_scalar_data[instrument].append(vol_scalar)
                                # Calculate implied volatility
                                implied_vol = vol_target / vol_scalar
                                implied_volatility_data[instrument].append(implied_vol)
                            else:
                                volatility_scalar_data[instrument].append(None)
                                implied_volatility_data[instrument].append(None)
                        else:
                            volatility_scalar_data[instrument].append(None)
                            implied_volatility_data[instrument].append(None)

                        # Get manual volatility from cache
                        if manual_vol_cache.get(instrument) is not None:
                            manual_vol_series = manual_vol_cache[instrument]
                            try:
                                if date in manual_vol_series.index:
                                    manual_vol = manual_vol_series.loc[date]
                                else:
                                    # Find closest date
                                    available_dates = manual_vol_series.index[manual_vol_series.index <= date]
                                    if len(available_dates) > 0:
                                        closest_date = available_dates[-1]
                                        manual_vol = manual_vol_series.loc[closest_date]
                                    else:
                                        manual_vol = None

                                if pd.notna(manual_vol):
                                    manual_volatility_data[instrument].append(manual_vol)
                                else:
                                    manual_volatility_data[instrument].append(None)
                            except:
                                manual_volatility_data[instrument].append(None)
                        else:
                            manual_volatility_data[instrument].append(None)

                    except Exception as e:
                        # Fill with None if error
                        volatility_scalar_data[instrument].append(None)
                        implied_volatility_data[instrument].append(None)
                        manual_volatility_data[instrument].append(None)

            # Convert to DataFrames
            valid_dates = dates[:len(portfolio_values)]
            cash_weights_df = pd.DataFrame(cash_weights_data, index=valid_dates)
            cash_positions_df = pd.DataFrame(cash_positions_data, index=valid_dates)
            volatility_scalar_df = pd.DataFrame(volatility_scalar_data, index=valid_dates)
            implied_volatility_df = pd.DataFrame(implied_volatility_data, index=valid_dates)
            manual_volatility_df = pd.DataFrame(manual_volatility_data, index=valid_dates)
            portfolio_values_series = pd.Series(portfolio_values, index=valid_dates)

            print(f"✅ Successfully calculated time series data")
            print(f"📊 Shape: {cash_weights_df.shape[0]} dates x {cash_weights_df.shape[1]} instruments")
            print(f"📈 Volatility data coverage:")
            print(f"  Vol scalars: {volatility_scalar_df.notna().sum().sum()} data points")
            print(f"  Implied vol: {implied_volatility_df.notna().sum().sum()} data points")
            print(f"  Manual vol: {manual_volatility_df.notna().sum().sum()} data points")

            # Debug: Check if we have any non-zero values
            total_nonzero_weights = (cash_weights_df != 0).sum().sum()
            total_nonzero_scalars = (volatility_scalar_df.notna() & (volatility_scalar_df != 0)).sum().sum()
            print(f"🔍 DEBUG: Non-zero weights: {total_nonzero_weights}, Non-zero scalars: {total_nonzero_scalars}")

            return {
                'cash_weights_df': cash_weights_df,
                'cash_positions_df': cash_positions_df,
                'volatility_scalar_df': volatility_scalar_df,
                'implied_volatility_df': implied_volatility_df,
                'manual_volatility_df': manual_volatility_df,
                'portfolio_values_series': portfolio_values_series
            }

        except Exception as e:
            print(f"❌ Error calculating time series data: {e}")
            import traceback
            traceback.print_exc()
            return None

    def verify_risk_to_cash_conversion(self, system):
        """Enhanced version with actual cash weights"""
        print("=== ENHANCED RISK-TO-CASH WEIGHT CONVERSION ===")

        # Get both types of weights
        comparison_data = self.compare_risk_vs_cash_weights(system)

        if comparison_data:
            print("\n✅ Successfully extracted actual cash weights")
            print("💡 Key Insight: Cash weights ≠ Risk weights due to volatility scaling")

            # Identify extreme cases
            for instrument, data in comparison_data.items():
                if data['scaling_factor'] > 2.0:
                    print(f"📈 {instrument}: HIGH cash allocation (low volatility)")
                elif data['scaling_factor'] < 0.5:
                    print(f"📉 {instrument}: LOW cash allocation (high volatility)")

            return comparison_data
        else:
            print("❌ Could not extract actual cash weights")
            return None

    def export_instrument_performance_excel(self, filename="instrument_performance_analysis.xlsx"):
        """
        Export comprehensive instrument performance analysis to Excel
        UPDATED: Fixed _format_excel_sheets call to include required timeseries_instrument parameter
        """
        print(f"📊 Exporting instrument performance analysis to {filename}...")

        instruments = self.system.get_instrument_list()
        if not instruments:
            print("❌ No instruments found in system")
            return None

        # Collect instrument data
        instrument_data = {}
        daily_returns_data = {}
        pnl_curves_data = {}

        for instrument in instruments:
            try:
                # Get instrument P&L
                pnl = self.system.accounts.pandl_for_instrument(instrument)
                if pnl is None or len(pnl) == 0:
                    continue

                # Convert P&L to returns (assuming 1M capital base)
                starting_capital = 1000000 / len(instruments)  # Equal allocation
                capital_curve = starting_capital + pnl
                returns = capital_curve.pct_change().dropna()

                if len(returns) < 50:  # Need sufficient data
                    continue

                # Calculate metrics
                annual_return = returns.mean() * 252
                annual_vol = returns.std() * (252 ** 0.5)
                sharpe_ratio = annual_return / annual_vol if annual_vol > 0 else 0

                # Drawdown calculation
                cumulative = (1 + returns).cumprod()
                rolling_max = cumulative.cummax()
                drawdown = (cumulative - rolling_max) / rolling_max
                max_drawdown = drawdown.min()

                # Additional metrics
                win_rate = (returns > 0).mean()
                total_pnl = pnl.iloc[-1]
                volatility_of_returns = returns.std()

                # Percentile analysis
                returns_10th = returns.quantile(0.10)
                returns_90th = returns.quantile(0.90)

                # Consecutive wins/losses
                consecutive_positive = self.calculate_consecutive_periods(returns > 0)
                consecutive_negative = self.calculate_consecutive_periods(returns < 0)

                instrument_data[instrument] = {
                    'AnnualReturn': annual_return,
                    'AnnualVolatility': annual_vol,
                    'SharpeRatio': sharpe_ratio,
                    'MaxDrawdown': max_drawdown,
                    'WinRate': win_rate,
                    'TotalPnL': total_pnl,
                    'FinalValue': capital_curve.iloc[-1],
                    'DailyVol': volatility_of_returns,
                    'BestDay': returns.max(),
                    'WorstDay': returns.min(),
                    'Returns10thPercentile': returns_10th,
                    'Returns90thPercentile': returns_90th,
                    'MaxConsecutiveWins': consecutive_positive['max'],
                    'MaxConsecutiveLosses': consecutive_negative['max'],
                    'DataPoints': len(returns),
                    'StartDate': pnl.index[0],
                    'EndDate': pnl.index[-1]
                }

                # Store time series data
                daily_returns_data[instrument] = returns
                pnl_curves_data[instrument] = pnl

            except Exception as e:
                print(f"❌ Error processing {instrument}: {e}")
                continue

        if not instrument_data:
            print("❌ No valid instrument data found")
            return None

        # Create Excel file with multiple sheets
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            workbook = writer.book

            # Sheet 1: Summary Performance Metrics
            summary_df = pd.DataFrame.from_dict(instrument_data, orient='index')
            summary_df = summary_df.sort_values('SharpeRatio', ascending=False)

            # Format percentages and currencies
            summary_df['AnnualReturn'] = summary_df['AnnualReturn'].apply(lambda x: f"{x:.2%}")
            summary_df['AnnualVolatility'] = summary_df['AnnualVolatility'].apply(lambda x: f"{x:.2%}")
            summary_df['MaxDrawdown'] = summary_df['MaxDrawdown'].apply(lambda x: f"{x:.2%}")
            summary_df['WinRate'] = summary_df['WinRate'].apply(lambda x: f"{x:.2%}")
            summary_df['TotalPnL'] = summary_df['TotalPnL'].apply(lambda x: f"${x:,.2f}")
            summary_df['FinalValue'] = summary_df['FinalValue'].apply(lambda x: f"${x:,.2f}")

            summary_df.to_excel(writer, sheet_name='Performance_Summary')

            # Sheet 2: Raw Performance Metrics (for further analysis)
            raw_summary_df = pd.DataFrame.from_dict(instrument_data, orient='index')
            raw_summary_df = raw_summary_df.sort_values('SharpeRatio', ascending=False)
            raw_summary_df.to_excel(writer, sheet_name='Raw_Metrics')

            # Sheet 3: Daily Returns Time Series
            if daily_returns_data:
                returns_df = pd.DataFrame.from_dict(daily_returns_data, orient='columns')
                returns_df.to_excel(writer, sheet_name='Daily_Returns')

            # Sheet 4: P&L Curves Time Series
            if pnl_curves_data:
                pnl_df = pd.DataFrame.from_dict(pnl_curves_data, orient='columns')
                pnl_df.to_excel(writer, sheet_name='PnL_Curves')

            # Sheet 5: Risk Analysis
            risk_df = self.create_risk_analysis_df(instrument_data, daily_returns_data)
            risk_df.to_excel(writer, sheet_name='Risk_Analysis')

            # Sheet 6: Correlation Matrix
            if len(daily_returns_data) >= 2:
                corr_df = pd.DataFrame.from_dict(daily_returns_data, orient='columns').corr()
                corr_df.to_excel(writer, sheet_name='Correlations')

            # FIXED: Add formatting with proper parameters
            # Note: This method doesn't need timeseries_instrument, so we'll create a simpler version
            self._format_instrument_performance_sheets(writer, workbook)

        print(f"✅ Excel file exported: {filename}")
        print(
            f"📋 Sheets created: Performance_Summary, Raw_Metrics, Daily_Returns, PnL_Curves, Risk_Analysis, Correlations")
        return filename

    def _format_instrument_performance_sheets(self, writer, workbook):
        """
        Add formatting to instrument performance Excel sheets
        Separate from the main _format_excel_sheets to avoid parameter conflicts
        """
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })

        percent_format = workbook.add_format({'num_format': '0.00%'})
        currency_format = workbook.add_format({'num_format': '$#,##0.00'})
        number_format = workbook.add_format({'num_format': '#,##0.00'})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})

        # Format the Performance_Summary sheet
        if 'Performance_Summary' in writer.sheets:
            worksheet = writer.sheets['Performance_Summary']
            worksheet.set_column('A:A', 12)  # Instrument names
            worksheet.set_column('B:P', 15)  # Data columns

            # Apply header formatting to first row
            for col_num in range(16):  # Adjust based on number of columns
                worksheet.write(0, col_num, worksheet.cell(0, col_num).value, header_format)

        # Format Raw_Metrics sheet
        if 'Raw_Metrics' in writer.sheets:
            worksheet = writer.sheets['Raw_Metrics']
            worksheet.set_column('A:A', 12)  # Instrument names
            worksheet.set_column('B:B', 12, percent_format)  # Annual Return
            worksheet.set_column('C:C', 12, percent_format)  # Annual Volatility
            worksheet.set_column('D:D', 12, number_format)  # Sharpe Ratio
            worksheet.set_column('E:E', 12, percent_format)  # Max Drawdown
            worksheet.set_column('F:F', 12, percent_format)  # Win Rate
            worksheet.set_column('G:G', 15, currency_format)  # Total PnL
            worksheet.set_column('H:H', 15, currency_format)  # Final Value
            worksheet.set_column('I:P', 12, number_format)  # Other metrics

        # Format time series sheets
        for sheet_name in ['Daily_Returns', 'PnL_Curves', 'Risk_Analysis', 'Correlations']:
            if sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                worksheet.set_column('A:A', 12, date_format if sheet_name in ['Daily_Returns', 'PnL_Curves'] else None)
                worksheet.set_column('B:Z', 12, number_format)

    def export_portfolio_summary_excel(self, filename="portfolio_summary.xlsx"):
        """Export overall portfolio summary to Excel"""
        print(f"Exporting portfolio summary to {filename}...")

        try:
            # Get portfolio data
            portfolio = self.system.accounts.portfolio()
            pnl_curve = portfolio.curve()

            if pnl_curve is None or len(pnl_curve) == 0:
                print("No portfolio data available")
                return None

            # Calculate performance metrics
            performance = self.calculator.calculate_performance(self.system)

            # Create summary data
            starting_capital = 1000000
            equity_curve = starting_capital + pnl_curve

            summary_data = {
                'Metric': ['Starting Capital', 'Ending Value', 'Total P&L', 'Total Return',
                           'Annual Return', 'Annual Volatility', 'Sharpe Ratio', 'Max Drawdown',
                           'Win Rate', 'Years Analyzed', 'Data Points'],
                'Value': [
                    f"${starting_capital:,.2f}",
                    f"${equity_curve.iloc[-1]:,.2f}",
                    f"${pnl_curve.iloc[-1]:,.2f}",
                    f"{((equity_curve.iloc[-1] / starting_capital) - 1) * 100:.2f}%",
                    f"{performance['annual_return']:.2%}" if performance else "N/A",
                    f"{performance['annual_volatility']:.2%}" if performance else "N/A",
                    f"{performance['sharpe_ratio']:.3f}" if performance else "N/A",
                    f"{performance['max_drawdown']:.2%}" if performance else "N/A",
                    f"{performance['win_rate']:.2%}" if performance else "N/A",
                    f"{performance['years_analyzed']:.1f}" if performance else "N/A",
                    f"{len(pnl_curve):,}"
                ]
            }

            # Create Excel file
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                # Portfolio Summary
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Portfolio_Summary', index=False)

                # Equity Curve
                equity_df = pd.DataFrame({
                    'Date': equity_curve.index,
                    'Portfolio_Value': equity_curve.values,
                    'PnL': pnl_curve.values,
                    'Daily_Return': equity_curve.pct_change()
                })
                equity_df.to_excel(writer, sheet_name='Equity_Curve', index=False)

            print(f"✅ Portfolio summary exported: {filename}")
            return filename

        except Exception as e:
            print(f"Error exporting portfolio summary: {e}")
            return None

    # Additional methods from the original file would continue here...
    # For brevity, I'm including the key methods that demonstrate the enhanced functionality

    def verify_position_sizing_formula(self, system):
        """Verify the exact position sizing formula being used"""
        print("=== POSITION SIZING FORMULA VERIFICATION ===")
        sample_instrument = system.get_instrument_list()[0]
        print(f"Testing with instrument: {sample_instrument}")

        try:
            # Get all components
            combined_forecast = system.combForecast.get_combined_forecast(sample_instrument).iloc[-1]
            vol_scalar = system.positionSize.get_volatility_scalar(sample_instrument).iloc[-1]

            # Get ACTUAL cash weight (not config risk weight)
            cash_data = self.get_actual_cash_weights(system)
            if cash_data and sample_instrument in cash_data['cash_weights']:
                cash_weight = cash_data['cash_weights'][sample_instrument]
            else:
                # Fallback to system method (which returns risk weights when fixed)
                cash_weight = system.portfolio.get_instrument_weights()[sample_instrument].iloc[-1]

            idm = system.portfolio.get_instrument_diversification_multiplier().iloc[-1]
            final_position = system.portfolio.get_notional_position(sample_instrument).iloc[-1]

            print(f"Combined Forecast: {combined_forecast:.4f}")
            print(f"Volatility Scalar: {vol_scalar:.6f}")
            print(f"Cash Weight (ACTUAL): {cash_weight:.6f}")
            print(f"IDM: {idm:.4f}")
            print(f"Final Position: {final_position:.4f}")

            # Test different formulas
            formula1 = combined_forecast * vol_scalar * cash_weight * idm
            formula2 = combined_forecast * vol_scalar * cash_weight
            formula3 = (combined_forecast * vol_scalar) * cash_weight * idm

            print(f"\nFormula Testing:")
            print(f"Formula 1 (CF * VS * CW * IDM): {formula1:.4f} | Match: {abs(formula1 - final_position) < 1.0}")
            print(f"Formula 2 (CF * VS * CW): {formula2:.4f} | Match: {abs(formula2 - final_position) < 1.0}")
            print(f"Formula 3 ((CF * VS) * CW * IDM): {formula3:.4f} | Match: {abs(formula3 - final_position) < 1.0}")

            if abs(formula1 - final_position) < 1.0:
                print("✅ Standard formula working: Position = Combined_Forecast × Vol_Scalar × Cash_Weight × IDM")
                return "standard"
            elif abs(formula2 - final_position) < 1.0:
                print("⚠️ IDM not applied in final position calculation")
                return "no_idm"
            else:
                print("❌ Position sizing formula unclear")
                return "unknown"

        except Exception as e:
            print(f"❌ Formula verification failed: {e}")
            return "error"

    def create_equity_curve_plot(self):
        """Create equity curve plot with drawdown - complete dashboard version"""
        try:
            import matplotlib
            import matplotlib.pyplot as plt
            import os

            # Force interactive backend for plot display
            if os.name == 'nt':  # Windows
                matplotlib.use('TkAgg')
            else:  # Linux/Mac
                matplotlib.use('TkAgg')

            print("📊 Initializing plot with backend:", matplotlib.get_backend())

            # Get portfolio data
            portfolio = self.system.accounts.portfolio()
            pnl_curve = portfolio.curve()

            if pnl_curve is None or len(pnl_curve) == 0:
                print("❌ No portfolio P&L curve data available for plotting.")
                return None

            # Convert P&L to equity curve (proper capital base)
            starting_capital = 1000000  # Your configured capital
            equity_curve = starting_capital + pnl_curve

            print(f"📈 Plotting equity curve with {len(equity_curve)} data points")

            # Calculate performance metrics
            performance = self.calculator.calculate_performance(self.system)

            # Create dashboard with 2 plots (like your original)
            plt.ioff()  # Turn off interactive mode initially
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

            # Plot 1: Equity Curve
            ax1.plot(equity_curve.index, equity_curve.values, 'b-', linewidth=2)
            ax1.set_title('Portfolio Equity Curve', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Portfolio Value ($)')
            ax1.grid(True, alpha=0.3)
            ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x / 1e6:.1f}M'))

            # Plot 2: Drawdown (The missing part!)
            returns = equity_curve.pct_change().dropna()
            cumulative = (1 + returns).cumprod()
            rolling_max = cumulative.cummax()
            drawdown = (cumulative - rolling_max) / rolling_max

            ax2.fill_between(drawdown.index, drawdown.values, 0, color='red', alpha=0.3)
            ax2.plot(drawdown.index, drawdown.values, 'r-', linewidth=1)
            ax2.set_title('Drawdown', fontsize=14, fontweight='bold')
            ax2.set_ylabel('Drawdown (%)')
            ax2.set_xlabel('Date')
            ax2.grid(True, alpha=0.3)
            ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1%}'))

            plt.tight_layout()

            # Add performance text box (like your original)
            if performance:
                textstr = f"""
    Performance Summary:
    Sharpe Ratio: {performance['sharpe_ratio']:.3f}
    Annual Return: {performance['annual_return']:.1%}
    Max Drawdown: {performance['max_drawdown']:.1%}
    Win Rate: {performance['win_rate']:.1%}
    """
                plt.figtext(0.02, 0.02, textstr, fontsize=10,
                            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"))

            # Force display with blocking
            plt.ion()  # Turn on interactive mode
            plt.show(block=True)  # Block until window is closed

            print("✅ Equity curve plot with drawdown displayed successfully")
            return fig

        except Exception as e:
            print(f"❌ Error creating equity curve plot: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_actual_cash_weights(self, system, date=None):
        """
        CORRECTED: Extract cash weights using Carver's fundamental method
        cash_weight = risk_weight × volatility_scalar
        """
        try:
            instruments = system.get_instrument_list()
            if date is None:
                portfolio = system.accounts.portfolio()
                if portfolio is None or len(portfolio.curve()) == 0:
                    print("❌ No portfolio data available")
                    return None
                date = portfolio.curve().index[-1]

            # Get system's portfolio value
            starting_capital = 1000000
            portfolio_curve = system.accounts.portfolio().curve()
            portfolio_pnl = portfolio_curve.asof(date)
            if pd.isna(portfolio_pnl):
                portfolio_pnl = 0

            system_portfolio_value = starting_capital + portfolio_pnl

            print(f"📊 Portfolio Analysis for {date} (CARVER METHOD)")
            print(f"💰 Starting Capital: ${starting_capital:,.2f}")
            print(f"📈 P&L to Date: ${portfolio_pnl:,.2f}")
            print(f"💼 Current Portfolio Value: ${system_portfolio_value:,.2f}")

            # Get risk weights from config
            risk_weights = getattr(system.config, 'instrument_weights', {})

            # Calculate fundamental cash weights (risk_weight * vol_scalar)
            fundamental_cash_weights = {}
            actual_cash_positions = {}

            for instrument in instruments:
                try:
                    # Step 1: Get risk weight from config
                    risk_weight = risk_weights.get(instrument, 0)

                    # Step 2: Extract volatility scalar from system
                    vol_scalar_series = system.positionSize.get_volatility_scalar(instrument)
                    if vol_scalar_series is not None and len(vol_scalar_series) > 0:
                        # Get the volatility scalar for the specific date
                        if date in vol_scalar_series.index:
                            vol_scalar = vol_scalar_series.loc[date]
                        else:
                            # Find the closest available date
                            available_dates = vol_scalar_series.index[vol_scalar_series.index <= date]
                            if len(available_dates) > 0:
                                closest_date = available_dates[-1]
                                vol_scalar = vol_scalar_series.loc[closest_date]
                            else:
                                vol_scalar = None

                        # Step 3: Calculate cash weight using Carver's formula
                        if vol_scalar is not None and vol_scalar > 0:
                            # CARVER METHOD: cash_weight = risk_weight * volatility_scalar
                            fundamental_weight = risk_weight * vol_scalar
                            fundamental_cash_weights[instrument] = fundamental_weight

                            # Calculate notional position for reference
                            notional_position = fundamental_weight * system_portfolio_value
                            actual_cash_positions[instrument] = notional_position
                        else:
                            fundamental_cash_weights[instrument] = 0
                            actual_cash_positions[instrument] = 0
                    else:
                        print(f"⚠️ No volatility scalar available for {instrument}")
                        fundamental_cash_weights[instrument] = 0
                        actual_cash_positions[instrument] = 0

                except Exception as e:
                    print(f"⚠️ Error processing {instrument}: {e}")
                    fundamental_cash_weights[instrument] = 0
                    actual_cash_positions[instrument] = 0

            # Normalize weights to sum to 1.0
            total_weight = sum(fundamental_cash_weights.values())
            normalized_cash_weights = {}

            if total_weight > 0:
                for instrument, weight in fundamental_cash_weights.items():
                    normalized_cash_weights[instrument] = weight / total_weight
            else:
                normalized_cash_weights = {instrument: 0 for instrument in instruments}

            # Display significant positions
            total_cash_deployed = sum(actual_cash_positions.values())
            print(f"💸 Total Cash Deployed (Theoretical): ${total_cash_deployed:,.2f}")
            print(f"📊 Deployment Ratio: {total_cash_deployed / system_portfolio_value:.2f}x")

            for instrument, weight in normalized_cash_weights.items():
                if weight > 0.01:  # Only print significant positions
                    cash_pos = actual_cash_positions.get(instrument, 0)
                    vol_scalar = fundamental_cash_weights[instrument] / risk_weights.get(instrument,
                                                                                         1) if risk_weights.get(
                        instrument, 0) > 0 else 0
                    print(f"  {instrument}: {weight:.2%} (${cash_pos:,.0f}) [vol_scalar: {vol_scalar:.2f}]")

            return {
                'cash_weights': normalized_cash_weights,
                'cash_positions': actual_cash_positions,
                'total_portfolio_cash': system_portfolio_value,
                'total_cash_deployed': total_cash_deployed,
                'date': date,
                'method': 'carver_fundamental_cash_weights'
            }

        except Exception as e:
            print(f"❌ Error calculating fundamental cash weights: {e}")
            import traceback
            traceback.print_exc()
            return None

    def export_cash_weights_time_series_excel(self, filename="cash_weights_time_series.xlsx"):
        """
        ENHANCED: Export cash weights AND volatility time series to Excel
        """
        print(f"📊 Exporting comprehensive time series analysis to {filename}...")

        # Get enhanced time series data
        time_series_data = self.get_cash_weights_over_time(self.system)
        if not time_series_data:
            print("❌ No time series data available")
            return None

        # Get current snapshot for comparison
        current_comparison = self.compare_risk_vs_cash_weights(self.system)

        try:
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                workbook = writer.book

                # Sheet 1: Current Snapshot (same as before)
                if current_comparison:
                    current_df = pd.DataFrame.from_dict(current_comparison, orient='index')
                    current_df['weight_difference'] = current_df['cash_weight'] - current_df['risk_weight']
                    current_df['volatility_effect'] = current_df['scaling_factor'] - 1.0
                    current_df.to_excel(writer, sheet_name='Current_Snapshot')

                # Sheet 2: Cash Weights Time Series
                weights_df = time_series_data['cash_weights_df']
                weights_df.to_excel(writer, sheet_name='Cash_Weights_TimeSeries')

                # Sheet 3: Cash Positions Time Series ($)
                positions_df = time_series_data['cash_positions_df']
                positions_df.to_excel(writer, sheet_name='Cash_Positions_TimeSeries')

                # NEW Sheet 4: Volatility Scalars Time Series
                vol_scalar_df = time_series_data['volatility_scalar_df']
                vol_scalar_df.to_excel(writer, sheet_name='Volatility_Scalars_TimeSeries')

                # NEW Sheet 5: Implied Volatility Time Series
                implied_vol_df = time_series_data['implied_volatility_df']
                implied_vol_df.to_excel(writer, sheet_name='Implied_Volatility_TimeSeries')

                # NEW Sheet 6: Manual Volatility Time Series
                manual_vol_df = time_series_data['manual_volatility_df']
                manual_vol_df.to_excel(writer, sheet_name='Manual_Volatility_TimeSeries')

                # Sheet 7: Portfolio Total Value Over Time
                portfolio_df = pd.DataFrame({
                    'Date': time_series_data['portfolio_values_series'].index,
                    'Total_Portfolio_Value': time_series_data['portfolio_values_series'].values
                })
                portfolio_df.to_excel(writer, sheet_name='Portfolio_Value_TimeSeries', index=False)

                # Enhanced Sheet 8: Summary Statistics (including volatility)
                summary_stats = {}
                for instrument in weights_df.columns:
                    weights_series = weights_df[instrument].dropna()
                    vol_scalar_series = vol_scalar_df[instrument].dropna()
                    implied_vol_series = implied_vol_df[instrument].dropna()
                    manual_vol_series = manual_vol_df[instrument].dropna()

                    if len(weights_series) > 0:
                        summary_stats[instrument] = {
                            # Weight statistics
                            'Mean_Weight': weights_series.mean(),
                            'Std_Weight': weights_series.std(),
                            'Min_Weight': weights_series.min(),
                            'Max_Weight': weights_series.max(),
                            'Current_Weight': weights_series.iloc[-1] if len(weights_series) > 0 else 0,
                            'Days_Active': (weights_series > 0.001).sum(),
                            'Weight_Volatility': weights_series.std() / weights_series.mean() if weights_series.mean() > 0 else 0,

                            # NEW: Volatility statistics
                            'Mean_Vol_Scalar': vol_scalar_series.mean() if len(vol_scalar_series) > 0 else None,
                            'Std_Vol_Scalar': vol_scalar_series.std() if len(vol_scalar_series) > 0 else None,
                            'Current_Vol_Scalar': vol_scalar_series.iloc[-1] if len(vol_scalar_series) > 0 else None,
                            'Mean_Implied_Vol': implied_vol_series.mean() if len(implied_vol_series) > 0 else None,
                            'Current_Implied_Vol': implied_vol_series.iloc[-1] if len(implied_vol_series) > 0 else None,
                            'Mean_Manual_Vol': manual_vol_series.mean() if len(manual_vol_series) > 0 else None,
                            'Current_Manual_Vol': manual_vol_series.iloc[-1] if len(manual_vol_series) > 0 else None,
                            'Vol_Data_Coverage': len(vol_scalar_series) / len(weights_df) if len(weights_df) > 0 else 0
                        }

                if summary_stats:
                    summary_df = pd.DataFrame.from_dict(summary_stats, orient='index')
                    summary_df = summary_df.sort_values('Mean_Weight', ascending=False)
                    summary_df.to_excel(writer, sheet_name='Enhanced_Statistics')

                # Add enhanced formatting
                self._format_enhanced_time_series_sheets(writer, workbook)

                print(f"✅ Enhanced time series export completed: {filename}")
                print(
                    f"📊 Sheets: Current_Snapshot, Cash_Weights, Cash_Positions, Vol_Scalars, Implied_Vol, Manual_Vol, Portfolio_Value, Enhanced_Statistics")

                return filename

        except Exception as e:
            print(f"❌ Export failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_cash_weights_over_time(self, system):
        """
        FIXED: Get cash weights AND volatility data over time
        Returns time series for weights, positions, portfolio values, and volatility metrics
        """
        try:
            print("=== Calculating Cash Weights & Volatility Over Time ===")

            instruments = system.get_instrument_list()
            portfolio = system.accounts.portfolio()
            portfolio_curve = portfolio.curve()

            if portfolio_curve is None or len(portfolio_curve) == 0:
                print("❌ No portfolio curve data available")
                return None

            # Starting capital for calculations
            starting_capital = 1000000
            vol_target = 0.12  # 12% from your config

            # Get date range (use last 100 data points)
            dates = portfolio_curve.index[-100:]

            # Initialize data containers
            cash_weights_data = {}
            cash_positions_data = {}
            volatility_scalar_data = {}
            implied_volatility_data = {}
            manual_volatility_data = {}
            portfolio_values = []

            print(f"📊 Processing {len(dates)} time periods for {len(instruments)} instruments")
            print("📈 Collecting: Cash Weights, Positions, Vol Scalars, Implied Vol, Manual Vol")

            # Pre-calculate all volatility scalars and manual volatilities
            print("🔄 Pre-calculating volatility data...")
            vol_scalars_cache = {}
            manual_vol_cache = {}

            for instrument in instruments:
                print(f"  📈 Processing volatility for {instrument}")
                try:
                    # Get volatility scalar time series (FULL SERIES)
                    vol_scalar_series = system.positionSize.get_volatility_scalar(instrument)
                    if vol_scalar_series is not None and len(vol_scalar_series) > 0:
                        vol_scalars_cache[instrument] = vol_scalar_series
                        print(f"    ✅ Vol scalars: {len(vol_scalar_series)} data points")
                    else:
                        print(f"    ⚠️ No vol scalars for {instrument}")
                        vol_scalars_cache[instrument] = None

                    # Calculate manual volatility time series
                    prices = system.rawdata.get_daily_prices(instrument)
                    if prices is not None and len(prices) > 50:
                        returns = prices.pct_change().dropna()
                        # Calculate rolling 30-day volatility
                        rolling_vol = returns.rolling(window=30, min_periods=10).std()
                        annualized_vol = rolling_vol * (252 ** 0.5)
                        manual_vol_cache[instrument] = annualized_vol
                        print(f"    ✅ Manual vol: {len(annualized_vol)} data points")
                    else:
                        print(f"    ⚠️ Insufficient price data for {instrument}")
                        manual_vol_cache[instrument] = None

                except Exception as e:
                    print(f"    ❌ Error processing {instrument}: {e}")
                    vol_scalars_cache[instrument] = None
                    manual_vol_cache[instrument] = None

            # Now process each date with cached data
            for i, date in enumerate(dates):
                if i % 20 == 0:  # Progress indicator
                    print(f"⏳ Processing date {i + 1}/{len(dates)}: {date.strftime('%Y-%m-%d')}")

                # Calculate portfolio value for this date
                portfolio_pnl = portfolio_curve.asof(date)
                if pd.isna(portfolio_pnl):
                    continue

                portfolio_value = starting_capital + portfolio_pnl
                portfolio_values.append(portfolio_value)

                # Get cash weights for this specific date (suppress output)
                weights_data = self._get_actual_cash_weights_quiet(system, date=date)

                # FIXED: Process each instrument for this date
                for instrument in instruments:
                    # Initialize instrument data containers if needed
                    for data_dict in [cash_weights_data, cash_positions_data,
                                      volatility_scalar_data, implied_volatility_data,
                                      manual_volatility_data]:
                        if instrument not in data_dict:
                            data_dict[instrument] = []

                    # FIXED: Append cash weight and position data
                    if weights_data:
                        # Cash data (existing)
                        weight = weights_data['cash_weights'].get(instrument, 0)
                        position = weights_data['cash_positions'].get(instrument, 0)
                        cash_weights_data[instrument].append(weight)
                        cash_positions_data[instrument].append(position)
                    else:
                        # No weight data available
                        cash_weights_data[instrument].append(0)
                        cash_positions_data[instrument].append(0)

                    # FIXED: Collect volatility data using cached series
                    try:
                        # Get volatility scalar from cache
                        if vol_scalars_cache.get(instrument) is not None:
                            vol_scalar_series = vol_scalars_cache[instrument]
                            # Use .loc or direct indexing instead of .asof for better data retrieval
                            try:
                                if date in vol_scalar_series.index:
                                    vol_scalar = vol_scalar_series.loc[date]
                                else:
                                    # Find closest date
                                    available_dates = vol_scalar_series.index[vol_scalar_series.index <= date]
                                    if len(available_dates) > 0:
                                        closest_date = available_dates[-1]
                                        vol_scalar = vol_scalar_series.loc[closest_date]
                                    else:
                                        vol_scalar = None

                                if pd.notna(vol_scalar) and vol_scalar > 0:
                                    volatility_scalar_data[instrument].append(vol_scalar)
                                    # Calculate implied volatility
                                    implied_vol = vol_target / vol_scalar
                                    implied_volatility_data[instrument].append(implied_vol)
                                else:
                                    volatility_scalar_data[instrument].append(None)
                                    implied_volatility_data[instrument].append(None)
                            except:
                                volatility_scalar_data[instrument].append(None)
                                implied_volatility_data[instrument].append(None)
                        else:
                            volatility_scalar_data[instrument].append(None)
                            implied_volatility_data[instrument].append(None)

                        # Get manual volatility from cache
                        if manual_vol_cache.get(instrument) is not None:
                            manual_vol_series = manual_vol_cache[instrument]
                            try:
                                if date in manual_vol_series.index:
                                    manual_vol = manual_vol_series.loc[date]
                                else:
                                    # Find closest date
                                    available_dates = manual_vol_series.index[manual_vol_series.index <= date]
                                    if len(available_dates) > 0:
                                        closest_date = available_dates[-1]
                                        manual_vol = manual_vol_series.loc[closest_date]
                                    else:
                                        manual_vol = None

                                if pd.notna(manual_vol):
                                    manual_volatility_data[instrument].append(manual_vol)
                                else:
                                    manual_volatility_data[instrument].append(None)
                            except:
                                manual_volatility_data[instrument].append(None)
                        else:
                            manual_volatility_data[instrument].append(None)

                    except Exception as e:
                        # Fill with None if error
                        volatility_scalar_data[instrument].append(None)
                        implied_volatility_data[instrument].append(None)
                        manual_volatility_data[instrument].append(None)

            # Convert to DataFrames
            valid_dates = dates[:len(portfolio_values)]
            cash_weights_df = pd.DataFrame(cash_weights_data, index=valid_dates)
            cash_positions_df = pd.DataFrame(cash_positions_data, index=valid_dates)
            volatility_scalar_df = pd.DataFrame(volatility_scalar_data, index=valid_dates)
            implied_volatility_df = pd.DataFrame(implied_volatility_data, index=valid_dates)
            manual_volatility_df = pd.DataFrame(manual_volatility_data, index=valid_dates)
            portfolio_values_series = pd.Series(portfolio_values, index=valid_dates)

            print(f"✅ Successfully calculated time series data")
            print(f"📊 Shape: {cash_weights_df.shape[0]} dates x {cash_weights_df.shape[1]} instruments")
            print(f"📈 Volatility data coverage:")
            print(f"  Vol scalars: {volatility_scalar_df.notna().sum().sum()} data points")
            print(f"  Implied vol: {implied_volatility_df.notna().sum().sum()} data points")
            print(f"  Manual vol: {manual_volatility_df.notna().sum().sum()} data points")

            return {
                'cash_weights_df': cash_weights_df,
                'cash_positions_df': cash_positions_df,
                'volatility_scalar_df': volatility_scalar_df,
                'implied_volatility_df': implied_volatility_df,
                'manual_volatility_df': manual_volatility_df,
                'portfolio_values_series': portfolio_values_series
            }

        except Exception as e:
            print(f"❌ Error calculating time series data: {e}")
            import traceback
            traceback.print_exc()
            return None

    def export_volatility_analysis_excel(self, filename="volatility_analysis.xlsx"):
        """Export volatility analysis for all instruments"""
        print(f"Exporting volatility analysis to {filename}...")

        instruments = self.system.get_instrument_list()
        vol_data = {}

        for instrument in instruments:
            try:
                # Get manual calculation (from prices)
                prices = self.system.rawdata.get_daily_prices(instrument)
                if prices is not None:
                    returns = prices.pct_change().dropna()
                    manual_annual_vol = returns.std() * (252 ** 0.5)
                else:
                    manual_annual_vol = None

                # Get system volatility scalar
                vol_scalar = self.system.positionSize.get_volatility_scalar(instrument)
                if vol_scalar is not None:
                    latest_scalar = vol_scalar.iloc[-1]
                    # Implied volatility from system: vol_target / scalar
                    implied_annual_vol = 0.12 / latest_scalar if latest_scalar > 0 else None
                else:
                    latest_scalar = None
                    implied_annual_vol = None

                vol_data[instrument] = {
                    'Manual_Annual_Vol': manual_annual_vol,
                    'System_Implied_Vol': implied_annual_vol,
                    'Volatility_Scalar': latest_scalar,
                    'Vol_Target': 0.12  # 12% from your config
                }

            except Exception as e:
                print(f"Error processing {instrument}: {e}")
                continue

        if vol_data:
            # Export to Excel
            df = pd.DataFrame.from_dict(vol_data, orient='index')
            df.to_excel(filename, sheet_name='Volatility_Analysis')
            print(f"✅ Volatility analysis exported: {filename}")
            return filename
        else:
            print("❌ No volatility data found")
            return None

    def _format_enhanced_time_series_sheets(self, writer, workbook):
        """Enhanced formatting for time series sheets including volatility data"""

        # Define formats
        percent_format = workbook.add_format({'num_format': '0.00%'})
        currency_format = workbook.add_format({'num_format': '$#,##0'})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        number_format = workbook.add_format({'num_format': '0.0000'})
        vol_format = workbook.add_format({'num_format': '0.00%', 'bg_color': '#E6F3FF'})

        # Format existing sheets
        for sheet_name, cell_format in [
            ('Cash_Weights_TimeSeries', percent_format),
            ('Cash_Positions_TimeSeries', currency_format),
            ('Volatility_Scalars_TimeSeries', number_format),
            ('Implied_Volatility_TimeSeries', vol_format),
            ('Manual_Volatility_TimeSeries', vol_format)
        ]:
            if sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                worksheet.set_column('A:A', 12, date_format)  # Date column
                worksheet.set_column('B:ZZ', 12, cell_format)  # Data columns

    def _get_actual_cash_weights_quiet(self, system, date=None):
        """
        UPDATED: Quiet version using Carver's fundamental cash weight method
        For time series processing without verbose output
        """
        try:
            instruments = system.get_instrument_list()
            if date is None:
                portfolio = system.accounts.portfolio()
                date = portfolio.curve().index[-1]

            # Get system's portfolio value
            starting_capital = 1000000
            portfolio_curve = system.accounts.portfolio().curve()
            portfolio_pnl = portfolio_curve.asof(date)
            if pd.isna(portfolio_pnl):
                portfolio_pnl = 0
            system_portfolio_value = starting_capital + portfolio_pnl

            # Get risk weights from config
            risk_weights = getattr(system.config, 'instrument_weights', {})

            # Calculate fundamental cash weights
            fundamental_cash_weights = {}
            actual_cash_positions = {}

            for instrument in instruments:
                try:
                    # Get volatility scalar
                    vol_scalar_series = system.positionSize.get_volatility_scalar(instrument)
                    if vol_scalar_series is not None and len(vol_scalar_series) > 0:
                        if date in vol_scalar_series.index:
                            vol_scalar = vol_scalar_series.loc[date]
                        else:
                            available_dates = vol_scalar_series.index[vol_scalar_series.index <= date]
                            vol_scalar = vol_scalar_series.loc[available_dates[-1]] if len(
                                available_dates) > 0 else None

                        if vol_scalar is not None and vol_scalar > 0:
                            risk_weight = risk_weights.get(instrument, 0)
                            fundamental_weight = risk_weight * vol_scalar
                            fundamental_cash_weights[instrument] = fundamental_weight

                            # Calculate theoretical cash position
                            notional_position = fundamental_weight * system_portfolio_value
                            actual_cash_positions[instrument] = notional_position
                        else:
                            fundamental_cash_weights[instrument] = 0
                            actual_cash_positions[instrument] = 0
                    else:
                        fundamental_cash_weights[instrument] = 0
                        actual_cash_positions[instrument] = 0
                except:
                    fundamental_cash_weights[instrument] = 0
                    actual_cash_positions[instrument] = 0

            # Normalize weights
            total_weight = sum(fundamental_cash_weights.values())
            normalized_cash_weights = {}

            if total_weight > 0:
                for instrument, weight in fundamental_cash_weights.items():
                    normalized_cash_weights[instrument] = weight / total_weight
            else:
                normalized_cash_weights = {instrument: 0 for instrument in instruments}

            total_cash_deployed = sum(actual_cash_positions.values())

            return {
                'cash_weights': normalized_cash_weights,
                'cash_positions': actual_cash_positions,
                'total_portfolio_cash': system_portfolio_value,
                'total_cash_deployed': total_cash_deployed,
                'date': date,
                'method': 'carver_fundamental_cash_weights'
            }

        except Exception as e:
            return None

    def _get_detailed_volatility_info(self, system, instrument, vol_target):
        """
        Extract detailed volatility information from pysystemtrade system
        Returns daily vol, annual vol, and volatility scalar with proper error handling
        """
        vol_info = {
            'daily_volatility': None,
            'annual_volatility': None,
            'volatility_scalar': None
        }

        try:
            # Method 1: Try to get volatility scalar directly from system
            try:
                vol_scalar_series = system.positionSize.get_volatility_scalar(instrument)
                if vol_scalar_series is not None and len(vol_scalar_series) > 0:
                    latest_scalar = vol_scalar_series.dropna()
                    if len(latest_scalar) > 0:
                        vol_info['volatility_scalar'] = float(latest_scalar.iloc[-1])
            except:
                pass

            # Method 2: Get underlying volatility data to understand the calculation
            try:
                # Get daily percentage volatility (this is what pysystemtrade uses internally)
                daily_vol_series = system.rawdata.get_daily_percentage_volatility(instrument)
                if daily_vol_series is not None and len(daily_vol_series) > 0:
                    latest_daily_vol = daily_vol_series.dropna()
                    if len(latest_daily_vol) > 0:
                        daily_vol = float(latest_daily_vol.iloc[-1])
                        vol_info['daily_volatility'] = daily_vol

                        # Annualize: daily vol × √252, then convert from percentage to decimal
                        annual_vol_pct = daily_vol * (252 ** 0.5)
                        vol_info['annual_volatility'] = annual_vol_pct / 100.0  # CONVERT TO DECIMAL

                        # Calculate scalar if we don't have it from Method 1
                        if vol_info['volatility_scalar'] is None and vol_info['annual_volatility'] > 0:
                            vol_info['volatility_scalar'] = vol_target / vol_info['annual_volatility']
            except:
                pass

            # Method 3: Manual calculation from prices as fallback
            if vol_info['daily_volatility'] is None:
                try:
                    prices = system.rawdata.get_daily_prices(instrument)
                    if prices is not None and len(prices) > 35:
                        returns = prices.pct_change().dropna()
                        if len(returns) > 35:
                            # Use exponentially weighted std with 35-day span (pysystemtrade default)
                            daily_vol = returns.ewm(span=35, min_periods=10).std().iloc[-1]
                            vol_info['daily_volatility'] = float(daily_vol)
                            # Convert to annual and ensure it's in decimal form
                            vol_info['annual_volatility'] = daily_vol * (
                                        252 ** 0.5)  # Already in decimal since returns are decimal

                            if vol_info['annual_volatility'] > 0:
                                vol_info['volatility_scalar'] = vol_target / vol_info['annual_volatility']
                except:
                    pass

        except Exception as e:
            print(f"⚠️ Volatility calculation failed for {instrument}: {e}")

        return vol_info

    def export_final_day_backtest_report(self, filename="final_day_backtest_report.xlsx",
                                         timeseries_instruments=None, timeseries_days=None):

        """
        Export comprehensive final day backtest report with multiple timeseries sheets.

        Args:
            filename (str): file path for saving the Excel report
            timeseries_instruments (list): list of instrument symbols for timeseries sheets
            timeseries_days (int): number of days to include in timeseries, default 100

        Returns:
            str: path to the saved Excel file or None if failure
        """
        import numpy as np
        import pandas as pd

        try:
            print(f"📊 Exporting combined final day backtest report to {filename}...")

            instruments = self.system.get_instrument_list()
            if not instruments:
                print("❌ No instruments found in system")
                return None

            # Handle multiple timeseries instruments
            if timeseries_instruments is None:
                timeseries_instruments = [instruments[0]]  # Default to first instrument
                print(f"📈 Auto-selected {timeseries_instruments[0]} for timeseries analysis")
            elif isinstance(timeseries_instruments, str):
                timeseries_instruments = [timeseries_instruments]  # Convert string to list

            # Validate and filter timeseries instruments
            valid_timeseries_instruments = []
            for instrument in timeseries_instruments:
                if instrument in instruments:
                    valid_timeseries_instruments.append(instrument)
                else:
                    print(f"⚠️ Specified instrument {instrument} not found in system")

            if not valid_timeseries_instruments:
                valid_timeseries_instruments = [instruments[0]]
                print(f"📈 Using fallback instrument {instruments[0]} for timeseries")

            print(f"📈 Will create timeseries for: {', '.join(valid_timeseries_instruments)}")

            # Get portfolio data
            portfolio = self.system.accounts.portfolio()
            portfolio_curve = portfolio.curve()

            if portfolio_curve is None or len(portfolio_curve) == 0:
                print("❌ No portfolio curve data available")
                return None

            final_date = portfolio_curve.index[-1]
            starting_capital = 1000000
            final_pnl = portfolio_curve.iloc[-1]
            portfolio_value = starting_capital + final_pnl

            # Get target volatility from config
            target_vol = getattr(self.system.config, 'percentage_vol_target', 12.0) / 100
            daily_cash_vol_target = portfolio_value * target_vol / 16

            print(f"📅 Final backtest date: {final_date.strftime('%Y-%m-%d')}")
            print(f"💰 Final portfolio value: ${portfolio_value:,.2f}")
            print(f"📊 Target volatility: {target_vol:.1%}")
            print(f"💵 Daily cash volatility target: ${daily_cash_vol_target:,.2f}")

            # ========== PART 1: FINAL DAY REPORT DATA ==========
            print("📋 Processing final day data for all instruments...")
            final_day_data = []

            for instrument in instruments:
                try:
                    row_data = self._process_instrument_final_day(instrument, final_date, portfolio_value,
                                                                  target_vol, daily_cash_vol_target)
                    final_day_data.append(row_data)

                except Exception as e:
                    print(f"❌ Error processing {instrument}: {e}")
                    # Still add the instrument with basic info
                    final_day_data.append({
                        'Instrument': instrument,
                        'Date': final_date,
                        'PortfolioValue': portfolio_value,
                        'DailyCashVolTarget': daily_cash_vol_target,
                        **{k: np.nan for k in ['ClosePrice', 'RiskWeightConfig', 'DailyVolatilityPct',
                                               'DailyVolatilityDecimal', 'AnnualVolatilityPct',
                                               'AnnualVolatilityDecimal', 'TargetVolatility',
                                               'CombinedForecast', 'IDM', 'InstrumentValueVolatility',
                                               'SubsystemPosition', 'NotionalPosition', 'PositionValue',
                                               'LeverageContribution', 'RiskExposure',
                                               'NativeVolatilityScalarPySystemTrade', 'NativeVolatilityScalarSource',
                                               'PSTDailyReturnsVolatility']}
                    })

            # ========== PART 2: MULTIPLE TIMESERIES DATA ==========
            timeseries_dataframes = {}

            for timeseries_instrument in valid_timeseries_instruments:
                print(f"📈 Processing timeseries data for {timeseries_instrument}...")
                timeseries_data = []

                # Get timeseries dates
                available_dates = portfolio_curve.index
                if timeseries_days is None:
                    timeseries_dates = available_dates  # Use ALL dates
                elif len(available_dates) >= timeseries_days:
                    timeseries_dates = available_dates[-timeseries_days:]
                else:
                    timeseries_dates = available_dates

                print(f"📊 Generating {len(timeseries_dates)} days of timeseries data for {timeseries_instrument}...")

                for date in timeseries_dates:
                    try:
                        # Calculate portfolio value for this date
                        portfolio_pnl = portfolio_curve.asof(date)
                        if pd.isna(portfolio_pnl):
                            continue
                        date_portfolio_value = starting_capital + portfolio_pnl
                        date_daily_cash_vol_target = date_portfolio_value * target_vol / 16

                        # Use the same data structure as final day report
                        ts_row_data = self._process_instrument_timeseries_day(
                            timeseries_instrument, date, date_portfolio_value,
                            target_vol, date_daily_cash_vol_target
                        )
                        timeseries_data.append(ts_row_data)

                    except Exception as e:
                        print(f"⚠️ Error processing {timeseries_instrument} on {date}: {e}")
                        continue

                # Store the timeseries data for this instrument
                if timeseries_data:
                    timeseries_dataframes[timeseries_instrument] = pd.DataFrame(timeseries_data)
                    print(f"✅ Generated {len(timeseries_data)} rows for {timeseries_instrument}")
                else:
                    print(f"⚠️ No timeseries data generated for {timeseries_instrument}")

            # ========== PART 3: LEVERAGE ANALYSIS ==========
            print("📊 Calculating leverage and capital multiplier metrics...")
            leverage_analysis = self.add_leverage_controls_check(self.system)

            # ========== PART 4: EXCEL EXPORT ==========
            print("📝 Creating Excel file with multiple sheets...")

            # Create DataFrames
            df_final = pd.DataFrame(final_day_data).sort_values('Instrument')

            # EXACT SAME COLUMN MAPPING for all sheets
            excel_column_names = {
                'Instrument': 'Instrument',
                'Date': 'Date',
                'ClosePrice': 'Close_Price [EXTRACTED]',
                'RiskWeightConfig': 'Risk_Weight_Config [EXTRACTED]',
                'DailyVolatilityPct': 'Daily_Volatility_Pct [CALCULATED/EXTRACTED]',
                'DailyVolatilityDecimal': 'Daily_Volatility_Decimal [CALCULATED/EXTRACTED]',
                'AnnualVolatilityPct': 'Annual_Volatility_Pct [CALCULATED]',
                'AnnualVolatilityDecimal': 'Annual_Volatility_Decimal [CALCULATED]',
                'TargetVolatility': 'Target_Volatility [CONFIG]',
                'DailyCashVolTarget': 'Daily_Cash_Vol_Target [CALCULATED]',
                'PortfolioValue': 'Portfolio_Value [EXTRACTED]',
                'CombinedForecast': 'Combined_Forecast [EXTRACTED]',
                'IDM': 'IDM [EXTRACTED]',
                'InstrumentValueVolatility': 'Instrument_Value_Volatility [CALCULATED]',
                'SubsystemPosition': 'Subsystem_Position [EXTRACTED]',
                'NotionalPosition': 'Notional_Position [EXTRACTED]',
                'PositionValue': 'Position_Value [CALCULATED]',
                'LeverageContribution': 'Leverage_Contribution [CALCULATED]',
                'RiskExposure': 'Risk_Exposure [CALCULATED]',
                'NativeVolatilityScalarPySystemTrade': 'Native_Volatility_Scalar_PySystemTrade [EXTRACTED]',
                'NativeVolatilityScalarSource': 'Native_Volatility_Scalar_Source [INFO]',
                'PSTDailyReturnsVolatility': 'PST_Daily_Returns_Volatility [EXTRACTED]'
            }

            # Apply column renaming to final day DataFrame
            df_final_excel = df_final.rename(columns=excel_column_names)

            # Apply column renaming to all timeseries DataFrames
            timeseries_dataframes_excel = {}
            for instrument, df_ts in timeseries_dataframes.items():
                timeseries_dataframes_excel[instrument] = df_ts.rename(columns=excel_column_names)

            # Create leverage DataFrames (same as before)
            if leverage_analysis:
                leverage_metrics = leverage_analysis['leverage_metrics']
                controls_status = leverage_analysis['controls_status']

                leverage_summary = [
                    {'Metric': 'Actual Trading Capital',
                     'Value': f"${leverage_metrics['actual_trading_capital']:,.2f}"},
                    {'Metric': 'Total Position Value', 'Value': f"${leverage_metrics['total_position_value']:,.2f}"},
                    {'Metric': 'Actual Leverage Ratio', 'Value': f"{leverage_metrics['actual_leverage_ratio']:.2f}x"},
                    {'Metric': 'Capital Multiplier', 'Value': f"{leverage_metrics['capital_multiplier']:.2f}x"},
                    {'Metric': 'Risk-Adjusted Leverage', 'Value': f"{leverage_metrics['risk_leverage_ratio']:.3f}x"},
                    {'Metric': 'Leverage Status', 'Value': leverage_metrics['leverage_status']}
                ]

                leverage_df = pd.DataFrame(leverage_summary)

                controls_data = []
                for check, status in controls_status.items():
                    controls_data.append({
                        'Control_Check': check.replace('_', ' ').title(),
                        'Status': status
                    })
                controls_df = pd.DataFrame(controls_data)
            else:
                leverage_df = pd.DataFrame({
                    'Metric': ['Actual Trading Capital', 'Total Position Value', 'Actual Leverage Ratio',
                               'Capital Multiplier', 'Risk-Adjusted Leverage', 'Leverage Status'],
                    'Value': ['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'NO DATA']
                })
                controls_df = pd.DataFrame(columns=['Control_Check', 'Status'])

            # Export to Excel with MULTIPLE timeseries sheets
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                workbook = writer.book

                # Sheet 1: Final Day Report
                df_final_excel.to_excel(writer, sheet_name='Final_Day_Report', index=False)

                # Multiple Timeseries Sheets
                timeseries_sheet_names = []
                for instrument, df_ts_excel in timeseries_dataframes_excel.items():
                    sheet_name = f"{instrument}_Timeseries"
                    df_ts_excel.to_excel(writer, sheet_name=sheet_name, index=False)
                    timeseries_sheet_names.append(sheet_name)
                    print(f"✅ Created timeseries sheet: {sheet_name} with {len(df_ts_excel)} rows")

                # Leverage Analysis Sheets
                leverage_df.to_excel(writer, sheet_name='Leverage_Analysis', index=False)
                controls_df.to_excel(writer, sheet_name='Leverage_Controls', index=False)

                # Apply IDENTICAL formatting to all sheets
                self._format_excel_sheets_multiple(writer, workbook, timeseries_sheet_names)

            # Summary
            sheets_created = ['Final_Day_Report', 'Leverage_Analysis', 'Leverage_Controls'] + timeseries_sheet_names

            print(f"✅ Combined report exported successfully: {filename}")
            print(f"📊 Processed {len(final_day_data)} instruments")
            print(f"📈 Created {len(timeseries_sheet_names)} timeseries sheets: {', '.join(timeseries_sheet_names)}")
            print(f"📋 Total sheets created: {', '.join(sheets_created)}")

            return filename

        except Exception as e:
            print(f"❌ Error exporting combined final day report: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _format_excel_sheets_multiple(self, writer, workbook, timeseries_sheet_names):
        """Apply consistent formatting to all Excel sheets including multiple timeseries sheets"""

        # Define formats (same as before)
        currency_format = workbook.add_format({'num_format': '#,##0.00'})
        percent_format = workbook.add_format({'num_format': '0.00%'})
        decimal_format = workbook.add_format({'num_format': '0.0000'})
        pct_number_format = workbook.add_format({'num_format': '0.00'})
        large_number_format = workbook.add_format({'num_format': '#,##0.00'})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})

        # Highlighting formats for key columns
        highlight_large_number_format = workbook.add_format({'num_format': '#,##0.00', 'bg_color': '#FFFF99'})
        highlight_decimal_format = workbook.add_format({'num_format': '0.0000', 'bg_color': '#FFFF99'})
        highlight_currency_format = workbook.add_format({'num_format': '#,##0.00', 'bg_color': '#FFFF99'})

        # Format Final_Day_Report sheet
        if 'Final_Day_Report' in writer.sheets:
            self._apply_standard_formatting(writer.sheets['Final_Day_Report'],
                                            currency_format, percent_format, decimal_format,
                                            pct_number_format, large_number_format, date_format,
                                            highlight_large_number_format, highlight_decimal_format,
                                            highlight_currency_format)

        # Format ALL timeseries sheets with IDENTICAL formatting
        for sheet_name in timeseries_sheet_names:
            if sheet_name in writer.sheets:
                self._apply_standard_formatting(writer.sheets[sheet_name],
                                                currency_format, percent_format, decimal_format,
                                                pct_number_format, large_number_format, date_format,
                                                highlight_large_number_format, highlight_decimal_format,
                                                highlight_currency_format)

    def _apply_standard_formatting(self, worksheet, currency_format, percent_format, decimal_format,
                                   pct_number_format, large_number_format, date_format,
                                   highlight_large_number_format, highlight_decimal_format,
                                   highlight_currency_format):
        """Apply standard formatting to a worksheet"""

        # Apply column formatting (adjusted for removed Volatility_Scalar columns)
        worksheet.set_column('A:A', 12)  # Instrument
        worksheet.set_column('B:B', 12, date_format)  # Date
        worksheet.set_column('C:C', 12, currency_format)  # Close Price
        worksheet.set_column('D:D', 12, percent_format)  # Risk Weight
        worksheet.set_column('E:E', 15, pct_number_format)  # Daily Vol %
        worksheet.set_column('F:F', 15, decimal_format)  # Daily Vol Decimal
        worksheet.set_column('G:G', 15, pct_number_format)  # Annual Vol %
        worksheet.set_column('H:H', 15, decimal_format)  # Annual Vol Decimal
        worksheet.set_column('I:I', 12, percent_format)  # Target Volatility
        worksheet.set_column('J:J', 15, currency_format)  # Daily Cash Vol Target (FIXED)
        worksheet.set_column('K:K', 15, currency_format)  # Portfolio Value
        worksheet.set_column('L:L', 15, highlight_large_number_format)  # Combined Forecast
        worksheet.set_column('M:M', 12, highlight_decimal_format)  # IDM
        worksheet.set_column('N:N', 15, highlight_currency_format)  # Instrument Value Vol
        worksheet.set_column('O:O', 15, large_number_format)  # Subsystem Position
        worksheet.set_column('P:P', 15, large_number_format)  # Notional Position
        worksheet.set_column('Q:Q', 15, currency_format)  # Position Value
        worksheet.set_column('R:R', 15, percent_format)  # Leverage Contribution
        worksheet.set_column('S:S', 15, currency_format)  # Risk Exposure
        worksheet.set_column('T:T', 20, highlight_decimal_format)  # Native Vol Scalar
        worksheet.set_column('U:U', 20)  # Native Vol Scalar Source
        worksheet.set_column('V:V', 15, decimal_format)  # PST Daily Returns Volatility
    def _process_instrument_final_day(self, instrument, final_date, portfolio_value, target_vol, daily_cash_vol_target):
        """Helper method to process single instrument for final day report"""
        import numpy as np
        import pandas as pd

        row_data = {
            'Instrument': instrument,
            'Date': final_date,
            'ClosePrice': np.nan,
            'RiskWeightConfig': 0,
            'DailyVolatilityPct': np.nan,
            'DailyVolatilityDecimal': np.nan,
            'AnnualVolatilityPct': np.nan,
            'AnnualVolatilityDecimal': np.nan,
            'TargetVolatility': target_vol,
            'DailyCashVolTarget': daily_cash_vol_target,
            'PortfolioValue': portfolio_value,
            'CombinedForecast': np.nan,
            'IDM': np.nan,
            'InstrumentValueVolatility': np.nan,
            'SubsystemPosition': np.nan,
            'NotionalPosition': np.nan,
            'PositionValue': np.nan,
            'LeverageContribution': np.nan,
            'RiskExposure': np.nan,
            'NativeVolatilityScalarPySystemTrade': np.nan,
            'NativeVolatilityScalarSource': "UNKNOWN",
            'PSTDailyReturnsVolatility': np.nan
        }

        # 1. CLOSE PRICE [EXTRACTED]
        try:
            prices = self.system.rawdata.get_daily_prices(instrument)
            if prices is not None and len(prices) > 0:
                if final_date in prices.index:
                    row_data['ClosePrice'] = prices.loc[final_date]
                else:
                    available_dates = prices.index[prices.index <= final_date]
                    if len(available_dates) > 0:
                        row_data['ClosePrice'] = prices.loc[available_dates[-1]]
        except:
            pass

        # 2. RISK WEIGHT FROM CONFIG [EXTRACTED]
        risk_weights = getattr(self.system.config, 'instrument_weights', {})
        row_data['RiskWeightConfig'] = risk_weights.get(instrument, 0)

        # 3. COMBINED FORECAST [EXTRACTED]
        try:
            forecast_series = self.system.combForecast.get_combined_forecast(instrument)
            if forecast_series is not None and len(forecast_series) > 0:
                if final_date in forecast_series.index:
                    row_data['CombinedForecast'] = forecast_series.loc[final_date]
                else:
                    available_dates = forecast_series.index[forecast_series.index <= final_date]
                    if len(available_dates) > 0:
                        row_data['CombinedForecast'] = forecast_series.loc[available_dates[-1]]
        except:
            pass

        # 4. VOLATILITY CALCULATIONS
        try:
            daily_pct_vol_series = self.system.rawdata.get_daily_percentage_volatility(instrument)
            if daily_pct_vol_series is not None and len(daily_pct_vol_series) > 0:
                if final_date in daily_pct_vol_series.index:
                    daily_pct_vol = daily_pct_vol_series.loc[final_date]
                else:
                    available_dates = daily_pct_vol_series.index[daily_pct_vol_series.index <= final_date]
                    if len(available_dates) > 0:
                        daily_pct_vol = daily_pct_vol_series.loc[available_dates[-1]]
                    else:
                        daily_pct_vol = None

                if pd.notna(daily_pct_vol) and daily_pct_vol > 0:
                    row_data['DailyVolatilityPct'] = daily_pct_vol
                    row_data['DailyVolatilityDecimal'] = daily_pct_vol / 100

                    annual_pct_vol = daily_pct_vol * (252 ** 0.5)
                    row_data['AnnualVolatilityPct'] = annual_pct_vol
                    row_data['AnnualVolatilityDecimal'] = annual_pct_vol / 100
        except:
            pass

        # Method 2: Manual calculation from price data [CALCULATED]
        if pd.isna(row_data['DailyVolatilityPct']):
            try:
                prices = self.system.rawdata.get_daily_prices(instrument)
                if prices is not None and len(prices) > 35:
                    returns = prices.pct_change().dropna()
                    if len(returns) > 35:
                        daily_vol_decimal = returns.ewm(span=35, min_periods=10).std().iloc[-1]
                        if pd.notna(daily_vol_decimal) and daily_vol_decimal > 0:
                            row_data['DailyVolatilityDecimal'] = daily_vol_decimal
                            row_data['DailyVolatilityPct'] = daily_vol_decimal * 100

                            annual_vol_decimal = daily_vol_decimal * (252 ** 0.5)
                            row_data['AnnualVolatilityDecimal'] = annual_vol_decimal
                            row_data['AnnualVolatilityPct'] = annual_vol_decimal * 100
            except:
                pass

        # NEW: Extract pysystemtrade daily returns volatility
        try:
            pst_daily_vol_series = self.system.rawdata.daily_returns_volatility(instrument)
            if pst_daily_vol_series is not None and len(pst_daily_vol_series) > 0:
                if final_date in pst_daily_vol_series.index:
                    pst_daily_vol = pst_daily_vol_series.loc[final_date]
                else:
                    available_dates = pst_daily_vol_series.index[pst_daily_vol_series.index <= final_date]
                    if len(available_dates) > 0:
                        pst_daily_vol = pst_daily_vol_series.loc[available_dates[-1]]
                    else:
                        pst_daily_vol = None

                if pd.notna(pst_daily_vol) and pst_daily_vol > 0:
                    row_data['PSTDailyReturnsVolatility'] = pst_daily_vol
        except:
            pass

        # 5. IDM [EXTRACTED]
        try:
            idm_series = self.system.portfolio.get_instrument_diversification_multiplier()
            if idm_series is not None and len(idm_series) > 0:
                if final_date in idm_series.index:
                    row_data['IDM'] = idm_series.loc[final_date]
                else:
                    available_dates = idm_series.index[idm_series.index <= final_date]
                    if len(available_dates) > 0:
                        row_data['IDM'] = idm_series.loc[available_dates[-1]]
        except:
            pass

        # 6. SUBSYSTEM POSITION [EXTRACTED]
        try:
            subsystem_series = self.system.positionSize.get_subsystem_position(instrument)
            if subsystem_series is not None and len(subsystem_series) > 0:
                if final_date in subsystem_series.index:
                    row_data['SubsystemPosition'] = subsystem_series.loc[final_date]
                else:
                    available_dates = subsystem_series.index[subsystem_series.index <= final_date]
                    if len(available_dates) > 0:
                        row_data['SubsystemPosition'] = subsystem_series.loc[available_dates[-1]]
        except:
            pass

        # 7. NOTIONAL POSITION [EXTRACTED]
        try:
            notional_series = self.system.portfolio.get_notional_position(instrument)
            if notional_series is not None and len(notional_series) > 0:
                if final_date in notional_series.index:
                    row_data['NotionalPosition'] = notional_series.loc[final_date]
                else:
                    available_dates = notional_series.index[notional_series.index <= final_date]
                    if len(available_dates) > 0:
                        row_data['NotionalPosition'] = notional_series.loc[available_dates[-1]]
        except:
            pass

        # 8. INSTRUMENT VALUE VOLATILITY [CALCULATED] - FIX #1
        try:
            if (pd.notna(row_data['ClosePrice']) and pd.notna(row_data['DailyVolatilityDecimal'])
                    and row_data['ClosePrice'] > 0 and row_data['DailyVolatilityDecimal'] > 0):
                daily_price_vol = row_data['ClosePrice'] * row_data['DailyVolatilityDecimal']
                row_data['InstrumentValueVolatility'] = daily_price_vol
        except:
            pass

        # 9. POSITION VALUE [CALCULATED]
        try:
            if (pd.notna(row_data['NotionalPosition']) and pd.notna(row_data['ClosePrice'])
                    and row_data['ClosePrice'] > 0):
                position_value = abs(row_data['NotionalPosition']) * row_data['ClosePrice']
                row_data['PositionValue'] = position_value
        except:
            pass

        # 10. LEVERAGE CONTRIBUTION [CALCULATED]
        try:
            if pd.notna(row_data['PositionValue']) and portfolio_value > 0:
                row_data['LeverageContribution'] = row_data['PositionValue'] / portfolio_value
        except:
            pass

        # 11. RISK EXPOSURE [CALCULATED]
        try:
            if (pd.notna(row_data['PositionValue']) and pd.notna(row_data['DailyVolatilityDecimal'])
                    and row_data['DailyVolatilityDecimal'] > 0):
                risk_exposure = row_data['PositionValue'] * row_data['DailyVolatilityDecimal']
                row_data['RiskExposure'] = risk_exposure
        except:
            pass

        # 12. NATIVE VOLATILITY SCALAR - FIX #2: Use the existing safe method
        try:
            native_vol_scalar, native_vol_scalar_source = self.get_volatility_scalar_safe(self.system, instrument)
            if native_vol_scalar and native_vol_scalar > 0:
                row_data['NativeVolatilityScalarPySystemTrade'] = native_vol_scalar
                row_data['NativeVolatilityScalarSource'] = native_vol_scalar_source
            else:
                row_data['NativeVolatilityScalarPySystemTrade'] = np.nan
                row_data['NativeVolatilityScalarSource'] = "NO_DATA"
        except Exception as e:
            print(f"❌ Native volatility scalar extraction failed for {instrument}: {e}")
            row_data['NativeVolatilityScalarPySystemTrade'] = np.nan
            row_data['NativeVolatilityScalarSource'] = "ERROR"

        return row_data

    def _process_instrument_timeseries_day(self, instrument, date, portfolio_value, target_vol, daily_cash_vol_target):
        """Helper method to process single instrument for single day timeseries - EXACT same structure as final day"""
        import numpy as np
        import pandas as pd

        # Use EXACT same structure as final day processing
        row_data = {
            'Instrument': instrument,
            'Date': date,
            'ClosePrice': np.nan,
            'RiskWeightConfig': 0,
            'DailyVolatilityPct': np.nan,
            'DailyVolatilityDecimal': np.nan,
            'AnnualVolatilityPct': np.nan,
            'AnnualVolatilityDecimal': np.nan,
            'TargetVolatility': target_vol,
            'DailyCashVolTarget': daily_cash_vol_target,
            'PortfolioValue': portfolio_value,
            'CombinedForecast': np.nan,
            'IDM': np.nan,
            'InstrumentValueVolatility': np.nan,
            'SubsystemPosition': np.nan,
            'NotionalPosition': np.nan,
            'PositionValue': np.nan,
            'LeverageContribution': np.nan,
            'RiskExposure': np.nan,
            'NativeVolatilityScalarPySystemTrade': np.nan,
            'NativeVolatilityScalarSource': "UNKNOWN",
            'PSTDailyReturnsVolatility': np.nan
        }

        # 1. CLOSE PRICE [EXTRACTED] - SAME AS FINAL_DAY_REPORT
        try:
            prices = self.system.rawdata.get_daily_prices(instrument)
            if prices is not None and len(prices) > 0:
                if date in prices.index:
                    row_data['ClosePrice'] = prices.loc[date]
                else:
                    available_dates_price = prices.index[prices.index <= date]
                    if len(available_dates_price) > 0:
                        row_data['ClosePrice'] = prices.loc[available_dates_price[-1]]
        except:
            pass

        # 2. RISK WEIGHT FROM CONFIG [EXTRACTED] - SAME AS FINAL_DAY_REPORT
        risk_weights = getattr(self.system.config, 'instrument_weights', {})
        row_data['RiskWeightConfig'] = risk_weights.get(instrument, 0)

        # 3. COMBINED FORECAST [EXTRACTED] - SAME AS FINAL_DAY_REPORT
        try:
            forecast_series = self.system.combForecast.get_combined_forecast(instrument)
            if forecast_series is not None and len(forecast_series) > 0:
                if date in forecast_series.index:
                    row_data['CombinedForecast'] = forecast_series.loc[date]
                else:
                    available_dates_forecast = forecast_series.index[forecast_series.index <= date]
                    if len(available_dates_forecast) > 0:
                        row_data['CombinedForecast'] = forecast_series.loc[available_dates_forecast[-1]]
        except:
            pass

        # 4. VOLATILITY CALCULATIONS - SAME AS FINAL_DAY_REPORT
        try:
            daily_pct_vol_series = self.system.rawdata.get_daily_percentage_volatility(instrument)
            if daily_pct_vol_series is not None and len(daily_pct_vol_series) > 0:
                if date in daily_pct_vol_series.index:
                    daily_pct_vol = daily_pct_vol_series.loc[date]
                else:
                    available_dates_vol = daily_pct_vol_series.index[daily_pct_vol_series.index <= date]
                    if len(available_dates_vol) > 0:
                        daily_pct_vol = daily_pct_vol_series.loc[available_dates_vol[-1]]
                    else:
                        daily_pct_vol = None

                if pd.notna(daily_pct_vol) and daily_pct_vol > 0:
                    row_data['DailyVolatilityPct'] = daily_pct_vol
                    row_data['DailyVolatilityDecimal'] = daily_pct_vol / 100

                    annual_pct_vol = daily_pct_vol * (252 ** 0.5)
                    row_data['AnnualVolatilityPct'] = annual_pct_vol
                    row_data['AnnualVolatilityDecimal'] = annual_pct_vol / 100
        except:
            pass

        # Method 2: Manual calculation from price data [CALCULATED] - SAME AS FINAL_DAY_REPORT
        if pd.isna(row_data['DailyVolatilityPct']):
            try:
                prices = self.system.rawdata.get_daily_prices(instrument)
                if prices is not None and len(prices) > 35:
                    # Use only data up to current date for historical accuracy
                    prices_up_to_date = prices[prices.index <= date]
                    if len(prices_up_to_date) > 35:
                        returns = prices_up_to_date.pct_change().dropna()
                        if len(returns) > 35:
                            daily_vol_decimal = returns.ewm(span=35, min_periods=10).std().iloc[-1]
                            if pd.notna(daily_vol_decimal) and daily_vol_decimal > 0:
                                row_data['DailyVolatilityDecimal'] = daily_vol_decimal
                                row_data['DailyVolatilityPct'] = daily_vol_decimal * 100

                                annual_vol_decimal = daily_vol_decimal * (252 ** 0.5)
                                row_data['AnnualVolatilityDecimal'] = annual_vol_decimal
                                row_data['AnnualVolatilityPct'] = annual_vol_decimal * 100
            except:
                pass

        # 5. PST DAILY RETURNS VOLATILITY [EXTRACTED] - SAME AS FINAL_DAY_REPORT
        try:
            pst_daily_vol_series = self.system.rawdata.daily_returns_volatility(instrument)
            if pst_daily_vol_series is not None and len(pst_daily_vol_series) > 0:
                if date in pst_daily_vol_series.index:
                    pst_daily_vol = pst_daily_vol_series.loc[date]
                else:
                    available_dates_pst = pst_daily_vol_series.index[pst_daily_vol_series.index <= date]
                    if len(available_dates_pst) > 0:
                        pst_daily_vol = pst_daily_vol_series.loc[available_dates_pst[-1]]
                    else:
                        pst_daily_vol = None

                if pd.notna(pst_daily_vol) and pst_daily_vol > 0:
                    row_data['PSTDailyReturnsVolatility'] = pst_daily_vol
        except:
            pass

        # 6. IDM [EXTRACTED] - SAME AS FINAL_DAY_REPORT
        try:
            idm_series = self.system.portfolio.get_instrument_diversification_multiplier()
            if idm_series is not None and len(idm_series) > 0:
                if date in idm_series.index:
                    row_data['IDM'] = idm_series.loc[date]
                else:
                    available_dates_idm = idm_series.index[idm_series.index <= date]
                    if len(available_dates_idm) > 0:
                        row_data['IDM'] = idm_series.loc[available_dates_idm[-1]]
        except:
            pass

        # 7. SUBSYSTEM POSITION [EXTRACTED] - SAME AS FINAL_DAY_REPORT
        try:
            subsystem_series = self.system.positionSize.get_subsystem_position(instrument)
            if subsystem_series is not None and len(subsystem_series) > 0:
                if date in subsystem_series.index:
                    row_data['SubsystemPosition'] = subsystem_series.loc[date]
                else:
                    available_dates_sub = subsystem_series.index[subsystem_series.index <= date]
                    if len(available_dates_sub) > 0:
                        row_data['SubsystemPosition'] = subsystem_series.loc[available_dates_sub[-1]]
        except:
            pass

        # 8. NOTIONAL POSITION [EXTRACTED] - SAME AS FINAL_DAY_REPORT
        try:
            notional_series = self.system.portfolio.get_notional_position(instrument)
            if notional_series is not None and len(notional_series) > 0:
                if date in notional_series.index:
                    row_data['NotionalPosition'] = notional_series.loc[date]
                else:
                    available_dates_not = notional_series.index[notional_series.index <= date]
                    if len(available_dates_not) > 0:
                        row_data['NotionalPosition'] = notional_series.loc[available_dates_not[-1]]
        except:
            pass

        # 9. INSTRUMENT VALUE VOLATILITY [CALCULATED] - SAME AS FINAL_DAY_REPORT
        try:
            if (pd.notna(row_data['ClosePrice']) and pd.notna(row_data['DailyVolatilityDecimal'])
                    and row_data['ClosePrice'] > 0 and row_data['DailyVolatilityDecimal'] > 0):
                daily_price_vol = row_data['ClosePrice'] * row_data['DailyVolatilityDecimal']
                row_data['InstrumentValueVolatility'] = daily_price_vol
        except:
            pass

        # 10. POSITION VALUE [CALCULATED] - SAME AS FINAL_DAY_REPORT
        try:
            if (pd.notna(row_data['NotionalPosition']) and pd.notna(row_data['ClosePrice'])
                    and row_data['ClosePrice'] > 0):
                position_value = abs(row_data['NotionalPosition']) * row_data['ClosePrice']
                row_data['PositionValue'] = position_value
        except:
            pass

        # 11. LEVERAGE CONTRIBUTION [CALCULATED] - SAME AS FINAL_DAY_REPORT
        try:
            if pd.notna(row_data['PositionValue']) and portfolio_value > 0:
                row_data['LeverageContribution'] = row_data['PositionValue'] / portfolio_value
        except:
            pass

        # 12. RISK EXPOSURE [CALCULATED] - SAME AS FINAL_DAY_REPORT
        try:
            if (pd.notna(row_data['PositionValue']) and pd.notna(row_data['DailyVolatilityDecimal'])
                    and row_data['DailyVolatilityDecimal'] > 0):
                risk_exposure = row_data['PositionValue'] * row_data['DailyVolatilityDecimal']
                row_data['RiskExposure'] = risk_exposure
        except:
            pass

        # 13. NATIVE VOLATILITY SCALAR [EXTRACTED] - REVERSE ENGINEERED APPROACH FROM FINAL_DAY_REPORT
        try:
            # METHOD 1: Direct extraction from PySystemTrade (preferred)
            vol_scalar_extracted = None
            vol_scalar_source = "UNKNOWN"

            try:
                # Try direct volatility scalar access
                vol_scalar_series = self.system.positionSize.get_volatility_scalar(instrument)
                if vol_scalar_series is not None and len(vol_scalar_series) > 0:
                    # Get value for this specific date
                    if date in vol_scalar_series.index:
                        vol_scalar_extracted = vol_scalar_series.loc[date]
                        vol_scalar_source = "PYSYSTEMTRADE_DIRECT"
                    else:
                        available_dates_vs = vol_scalar_series.index[vol_scalar_series.index <= date]
                        if len(available_dates_vs) > 0:
                            vol_scalar_extracted = vol_scalar_series.loc[available_dates_vs[-1]]
                            vol_scalar_source = "PYSYSTEMTRADE_NEAREST_DATE"
            except (AttributeError, Exception):
                pass

            # METHOD 2: Reverse engineer from positions (SAME AS FINAL_DAY_REPORT)
            if vol_scalar_extracted is None or vol_scalar_extracted <= 0:
                try:
                    # Get subsystem position and combined forecast for this date
                    subsystem_pos = row_data.get('SubsystemPosition')
                    forecast_val = row_data.get('CombinedForecast')

                    # Reverse engineer: subsystem_position = (vol_scalar * combined_forecast) / 10
                    if (subsystem_pos is not None and forecast_val is not None and
                            not pd.isna(subsystem_pos) and not pd.isna(forecast_val) and abs(forecast_val) > 0.01):
                        vol_scalar_extracted = abs(subsystem_pos * 10 / forecast_val)
                        vol_scalar_source = "REVERSE_ENGINEERED_FROM_POSITIONS"
                except (AttributeError, Exception):
                    pass

            # METHOD 3: Calculate from volatility data (SAME AS FINAL_DAY_REPORT)
            if vol_scalar_extracted is None or vol_scalar_extracted <= 0:
                try:
                    # Use the already calculated volatility from above
                    current_vol = row_data.get('DailyVolatilityDecimal')

                    if current_vol is not None and current_vol > 0:
                        # Convert daily volatility to annual
                        annual_vol = current_vol * (252 ** 0.5)

                        # Calculate volatility scalar: vol_target / annual_volatility
                        vol_scalar_extracted = target_vol / annual_vol
                        vol_scalar_source = "CALCULATED_FROM_VOLATILITY"
                except (AttributeError, Exception):
                    pass

            # METHOD 4: Final fallback - use the working method from Final_Day_Report
            if vol_scalar_extracted is None or vol_scalar_extracted <= 0:
                try:
                    vol_scalar_extracted, fallback_source = self.get_volatility_scalar_safe(self.system, instrument)
                    if vol_scalar_extracted and vol_scalar_extracted > 0:
                        vol_scalar_source = f"FALLBACK_{fallback_source}"
                    else:
                        vol_scalar_extracted = None
                except:
                    pass

            # Set the final values
            if vol_scalar_extracted is not None and vol_scalar_extracted > 0:
                row_data['NativeVolatilityScalarPySystemTrade'] = vol_scalar_extracted
                row_data['NativeVolatilityScalarSource'] = vol_scalar_source
            else:
                row_data['NativeVolatilityScalarPySystemTrade'] = np.nan
                row_data['NativeVolatilityScalarSource'] = "NO_DATA_ALL_METHODS_FAILED"

        except Exception as e:
            print(f"⚠️ Native volatility scalar extraction failed for {instrument} on {date}: {e}")
            row_data['NativeVolatilityScalarPySystemTrade'] = np.nan
            row_data['NativeVolatilityScalarSource'] = "ERROR"

        return row_data

    def _extract_additional_fields(self, row_data, instrument, date, target_vol):
        """Helper to extract additional fields for both final day and timeseries"""
        import pandas as pd
        import numpy as np

        # PST Daily Returns Volatility
        try:
            pst_daily_vol_series = self.system.rawdata.daily_returns_volatility(instrument)
            if pst_daily_vol_series is not None and len(pst_daily_vol_series) > 0:
                if date in pst_daily_vol_series.index:
                    pst_daily_vol = pst_daily_vol_series.loc[date]
                else:
                    available_dates = pst_daily_vol_series.index[pst_daily_vol_series.index <= date]
                    if len(available_dates) > 0:
                        pst_daily_vol = pst_daily_vol_series.loc[available_dates[-1]]
                    else:
                        pst_daily_vol = None

                if pd.notna(pst_daily_vol) and pst_daily_vol > 0:
                    row_data['PSTDailyReturnsVolatility'] = pst_daily_vol
        except:
            pass

        # IDM
        try:
            idm_series = self.system.portfolio.get_instrument_diversification_multiplier()
            if idm_series is not None and len(idm_series) > 0:
                if date in idm_series.index:
                    row_data['IDM'] = idm_series.loc[date]
                else:
                    available_dates = idm_series.index[idm_series.index <= date]
                    if len(available_dates) > 0:
                        row_data['IDM'] = idm_series.loc[available_dates[-1]]
        except:
            pass

        # Continue with other fields...
        self._extract_position_fields(row_data, instrument, date)

    def _extract_position_fields(self, row_data, instrument, date):
        """Extract position-related fields"""
        import pandas as pd
        import numpy as np

        # Subsystem Position
        try:
            subsystem_series = self.system.positionSize.get_subsystem_position(instrument)
            if subsystem_series is not None and len(subsystem_series) > 0:
                if date in subsystem_series.index:
                    row_data['SubsystemPosition'] = subsystem_series.loc[date]
                else:
                    available_dates = subsystem_series.index[subsystem_series.index <= date]
                    if len(available_dates) > 0:
                        row_data['SubsystemPosition'] = subsystem_series.loc[available_dates[-1]]
        except:
            pass

        # Notional Position
        try:
            notional_series = self.system.portfolio.get_notional_position(instrument)
            if notional_series is not None and len(notional_series) > 0:
                if date in notional_series.index:
                    row_data['NotionalPosition'] = notional_series.loc[date]
                else:
                    available_dates = notional_series.index[notional_series.index <= date]
                    if len(available_dates) > 0:
                        row_data['NotionalPosition'] = notional_series.loc[available_dates[-1]]
        except:
            pass

        # Calculate derived fields
        try:
            if (not pd.isna(row_data['NotionalPosition']) and not pd.isna(row_data['ClosePrice'])):
                row_data['PositionValue'] = abs(row_data['NotionalPosition']) * row_data['ClosePrice']

                # Calculate leverage contribution
                if not pd.isna(row_data['PortfolioValue']) and row_data['PortfolioValue'] > 0:
                    row_data['LeverageContribution'] = row_data['PositionValue'] / row_data['PortfolioValue']

                # Calculate risk exposure
                if not pd.isna(row_data['DailyVolatilityDecimal']):
                    row_data['RiskExposure'] = row_data['PositionValue'] * row_data['DailyVolatilityDecimal']
        except:
            pass

    def calculate_actual_leverage_metrics(self, system, date=None):
        """
        Calculate actual leverage using actual positions instead of notional
        Returns comprehensive leverage analysis following Carver's methodology
        """
        try:
            print("=== ACTUAL LEVERAGE & CAPITAL MULTIPLIER ANALYSIS ===")

            instruments = system.get_instrument_list()
            if date is None:
                portfolio = system.accounts.portfolio()
                if portfolio is None or len(portfolio.curve()) == 0:
                    print("❌ No portfolio data available")
                    return None
                date = portfolio.curve().index[-1]

            # Get actual trading capital (not notional)
            starting_capital = 1000000  # Your configured capital base
            portfolio_curve = system.accounts.portfolio().curve()
            portfolio_pnl = portfolio_curve.asof(date)
            if pd.isna(portfolio_pnl):
                portfolio_pnl = 0
            actual_trading_capital = starting_capital + portfolio_pnl

            print(f"📊 Leverage Analysis for {date.strftime('%Y-%m-%d')}")
            print(f"💰 Starting Capital: ${starting_capital:,.2f}")
            print(f"📈 Current P&L: ${portfolio_pnl:,.2f}")
            print(f"💼 Actual Trading Capital: ${actual_trading_capital:,.2f}")

            # Calculate actual positions and leverage
            leverage_data = {}
            total_position_value = 0
            total_risk_exposure = 0

            for instrument in instruments:
                try:
                    # Get actual position size
                    portfolio_pos = system.portfolio.get_notional_position(instrument)
                    if portfolio_pos is not None and len(portfolio_pos) > 0:
                        if date in portfolio_pos.index:
                            position_size = portfolio_pos.loc[date]
                        else:
                            available_dates = portfolio_pos.index[portfolio_pos.index <= date]
                            position_size = portfolio_pos.loc[available_dates[-1]] if len(available_dates) > 0 else 0
                    else:
                        position_size = 0

                    # Get current price for position valuation
                    prices = system.rawdata.get_daily_prices(instrument)
                    if prices is not None and len(prices) > 0:
                        if date in prices.index:
                            current_price = prices.loc[date]
                        else:
                            available_dates = prices.index[prices.index <= date]
                            current_price = prices.loc[available_dates[-1]] if len(available_dates) > 0 else 0
                    else:
                        current_price = 0

                    # Calculate actual position value
                    position_value = abs(position_size * current_price) if current_price > 0 else 0

                    # Get volatility for risk calculation
                    vol_scalar = self._get_volatility_scalar_safe(system, instrument)
                    daily_vol = 0
                    if vol_scalar > 0:
                        target_vol = getattr(system.config, 'percentage_vol_target', 12.0) / 100
                        daily_vol = target_vol / vol_scalar / 16  # Convert to daily

                    # Calculate risk exposure (position * volatility)
                    risk_exposure = position_value * daily_vol if daily_vol > 0 else 0

                    leverage_data[instrument] = {
                        'position_size': position_size,
                        'current_price': current_price,
                        'position_value': position_value,
                        'volatility_scalar': vol_scalar,
                        'daily_volatility': daily_vol,
                        'risk_exposure': risk_exposure,
                        'leverage_contribution': position_value / actual_trading_capital if actual_trading_capital > 0 else 0
                    }

                    total_position_value += position_value
                    total_risk_exposure += risk_exposure

                except Exception as e:
                    print(f"⚠️ Error processing {instrument}: {e}")
                    leverage_data[instrument] = {
                        'position_size': 0, 'current_price': 0, 'position_value': 0,
                        'volatility_scalar': 0, 'daily_volatility': 0, 'risk_exposure': 0,
                        'leverage_contribution': 0
                    }

            # Calculate portfolio-level leverage metrics
            actual_leverage_ratio = total_position_value / actual_trading_capital if actual_trading_capital > 0 else 0
            capital_multiplier = actual_leverage_ratio  # Carver's capital multiplier concept
            risk_leverage_ratio = total_risk_exposure / actual_trading_capital if actual_trading_capital > 0 else 0

            # Determine leverage status
            def assess_leverage_status(leverage_ratio, risk_ratio):
                if leverage_ratio <= 1.0:
                    return "CONSERVATIVE", "✅"
                elif leverage_ratio <= 2.0:
                    return "MODERATE", "⚠️"
                elif leverage_ratio <= 3.0:
                    return "HIGH", "🔶"
                else:
                    return "EXCESSIVE", "🚨"

            leverage_status, status_icon = assess_leverage_status(actual_leverage_ratio, risk_leverage_ratio)

            print(f"\n📊 PORTFOLIO LEVERAGE METRICS:")
            print(f"💼 Total Position Value: ${total_position_value:,.2f}")
            print(f"📈 Actual Leverage Ratio: {actual_leverage_ratio:.2f}x")
            print(f"🔄 Capital Multiplier: {capital_multiplier:.2f}x")
            print(f"⚡ Risk-Adjusted Leverage: {risk_leverage_ratio:.2f}x")
            print(f"{status_icon} Leverage Status: {leverage_status}")

            # Display individual instrument contributions
            print(f"\n📈 INSTRUMENT LEVERAGE BREAKDOWN:")
            print(f"{'Instrument':<15} {'Position':<12} {'Value':<12} {'Leverage':<10} {'Risk Exp':<12}")
            print("-" * 70)

            for instrument, data in leverage_data.items():
                if data['position_value'] > 1000:  # Only show significant positions
                    print(f"{instrument:<15} {data['position_size']:<12.1f} "
                          f"${data['position_value']:<11,.0f} {data['leverage_contribution']:<10.2f} "
                          f"${data['risk_exposure']:<11,.0f}")

            return {
                'date': date,
                'actual_trading_capital': actual_trading_capital,
                'total_position_value': total_position_value,
                'total_risk_exposure': total_risk_exposure,
                'actual_leverage_ratio': actual_leverage_ratio,
                'capital_multiplier': capital_multiplier,
                'risk_leverage_ratio': risk_leverage_ratio,
                'leverage_status': leverage_status,
                'instrument_data': leverage_data
            }

        except Exception as e:
            print(f"❌ Error calculating leverage metrics: {e}")
            import traceback
            traceback.print_exc()
            return None

    def add_leverage_controls_check(self, system):
        """
        Check for leverage controls as recommended by Carver
        """
        print("=== LEVERAGE CONTROLS CHECK ===")

        leverage_metrics = self.calculate_actual_leverage_metrics(system)
        if not leverage_metrics:
            print("❌ Cannot perform leverage controls check")
            return None

        controls_status = {}

        # Check 1: Overall leverage within safe limits
        actual_leverage = leverage_metrics['actual_leverage_ratio']
        if actual_leverage <= 2.0:
            controls_status['overall_leverage'] = "✅ PASS - Within safe limits"
        elif actual_leverage <= 3.0:
            controls_status['overall_leverage'] = "⚠️ CAUTION - Moderate leverage"
        else:
            controls_status['overall_leverage'] = "🚨 FAIL - Excessive leverage"

        # Check 2: Capital multiplier monitoring
        capital_mult = leverage_metrics['capital_multiplier']
        if capital_mult <= 1.5:
            controls_status['capital_multiplier'] = "✅ PASS - Conservative multiplier"
        elif capital_mult <= 2.5:
            controls_status['capital_multiplier'] = "⚠️ CAUTION - Moderate multiplier"
        else:
            controls_status['capital_multiplier'] = "🚨 FAIL - High multiplier risk"

        # Check 3: Risk-adjusted leverage
        risk_leverage = leverage_metrics['risk_leverage_ratio']
        if risk_leverage <= 0.15:  # Carver's typical daily vol target
            controls_status['risk_leverage'] = "✅ PASS - Risk-appropriate leverage"
        elif risk_leverage <= 0.25:
            controls_status['risk_leverage'] = "⚠️ CAUTION - Elevated risk leverage"
        else:
            controls_status['risk_leverage'] = "🚨 FAIL - Excessive risk leverage"

        # Check 4: Individual position concentration
        max_position_pct = 0
        for instrument, data in leverage_metrics['instrument_data'].items():
            position_pct = data['leverage_contribution']
            if position_pct > max_position_pct:
                max_position_pct = position_pct

        if max_position_pct <= 0.3:
            controls_status['position_concentration'] = "✅ PASS - Well diversified"
        elif max_position_pct <= 0.5:
            controls_status['position_concentration'] = "⚠️ CAUTION - Some concentration"
        else:
            controls_status['position_concentration'] = "🚨 FAIL - High concentration risk"

        print("\n🛡️ LEVERAGE CONTROLS STATUS:")
        for check, status in controls_status.items():
            print(f"{check.replace('_', ' ').title()}: {status}")

        return {
            'leverage_metrics': leverage_metrics,
            'controls_status': controls_status
        }

    def export_diagnostic_analysis_excel(self, filename="diagnostic_analysis.xlsx"):
        """
        Export comprehensive diagnostic analysis comparing IVV, HYD with other instruments
        """
        import pandas as pd
        import numpy as np

        try:
            print(f"🔍 Exporting comprehensive diagnostic analysis to {filename}...")

            instruments = self.system.get_instrument_list()
            focus_instruments = ['BBAX', 'IVV', 'HYD'] if all(
                inst in instruments for inst in ['BBAX', 'IVV', 'HYD']) else instruments[:3]

            # ========== DATA COLLECTION ==========
            diagnostic_data = {}

            for instrument in focus_instruments:
                print(f"📊 Analyzing {instrument}...")

                diagnostic_info = {
                    'Instrument': instrument,
                    'DataStartDate': None,
                    'DataEndDate': None,
                    'TotalDays': 0,
                    'ValidReturns': 0,
                    'MissingDataPoints': 0,
                    'DataCompleteness': 0.0,
                    'VolatilityLookbackDays': None,
                    'EWMASpan': None,
                    'ManualDailyVol': np.nan,
                    'SystemDailyVol': np.nan,
                    'PST_DailyReturnsVol': np.nan,
                    'VolatilityMethod': 'UNKNOWN',
                    'ForecastScalar': np.nan,
                    'LatestBlockValue': np.nan,
                    'FXRate': np.nan,
                    'CorporateActions': 0,
                    'LargeMoves_5pct': 0,
                    'VeryLargeMoves_10pct': 0,
                    'VolatilityStability': np.nan
                }

                # 1. DATA LENGTH AND COMPLETENESS
                try:
                    prices = self.system.rawdata.get_daily_prices(instrument)
                    if prices is not None and len(prices) > 0:
                        diagnostic_info['DataStartDate'] = prices.index[0]
                        diagnostic_info['DataEndDate'] = prices.index[-1]
                        diagnostic_info['TotalDays'] = len(prices)

                        # Check for missing data
                        missing_count = prices.isnull().sum()
                        diagnostic_info['MissingDataPoints'] = missing_count
                        diagnostic_info['DataCompleteness'] = (len(prices) - missing_count) / len(prices)

                        # Calculate returns for further analysis
                        returns = prices.pct_change().dropna()
                        diagnostic_info['ValidReturns'] = len(returns)

                        # Manual volatility calculation
                        if len(returns) > 35:
                            manual_vol = returns.ewm(span=35, min_periods=10).std().iloc[-1]
                            diagnostic_info['ManualDailyVol'] = manual_vol

                            # Check volatility stability (volatility of volatility)
                            vol_series = returns.rolling(35).std().dropna()
                            if len(vol_series) > 10:
                                vol_stability = vol_series.std() / vol_series.mean()
                                diagnostic_info['VolatilityStability'] = vol_stability

                        # Corporate actions detection (unusual price jumps)
                        large_moves = returns[abs(returns) > 0.05]  # 5% moves
                        very_large_moves = returns[abs(returns) > 0.10]  # 10% moves
                        diagnostic_info['LargeMoves_5pct'] = len(large_moves)
                        diagnostic_info['VeryLargeMoves_10pct'] = len(very_large_moves)
                        diagnostic_info['CorporateActions'] = len(very_large_moves)  # Proxy for corporate actions
                except Exception as e:
                    print(f"⚠️ Price data analysis failed for {instrument}: {e}")

                # 2. SYSTEM VOLATILITY EXTRACTION
                try:
                    # PySystemTrade daily percentage volatility
                    system_vol_series = self.system.rawdata.get_daily_percentage_volatility(instrument)
                    if system_vol_series is not None and len(system_vol_series) > 0:
                        system_vol = system_vol_series.iloc[-1] / 100  # Convert to decimal
                        diagnostic_info['SystemDailyVol'] = system_vol
                        diagnostic_info['VolatilityMethod'] = 'PYSYSTEMTRADE_PERCENTAGE'

                    # PST daily returns volatility (the actual one used internally)
                    pst_vol_series = self.system.rawdata.daily_returns_volatility(instrument)
                    if pst_vol_series is not None and len(pst_vol_series) > 0:
                        pst_vol = pst_vol_series.iloc[-1]
                        diagnostic_info['PST_DailyReturnsVol'] = pst_vol
                except Exception as e:
                    print(f"⚠️ System volatility extraction failed for {instrument}: {e}")

                # 3. FORECAST SCALAR CHECK
                try:
                    # Check if using fixed or estimated forecast scalars
                    use_estimates = getattr(self.system.config, 'use_forecast_scale_estimates', False)
                    print(f"📊 {instrument} - Using estimated forecast scalars: {use_estimates}")

                    if use_estimates:
                        # Estimated scalars (instrument-specific)
                        scalar_series = self.system.forecastScaleCap._get_forecast_scalar_estimated(instrument,
                                                                                                    'ewmac8')
                        if scalar_series is not None and len(scalar_series) > 0:
                            diagnostic_info['ForecastScalar'] = scalar_series.iloc[-1]
                            diagnostic_info['ForecastScalarType'] = 'ESTIMATED'
                    else:
                        # Fixed scalars (should be same for all instruments)
                        try:
                            scalar = self.system.config.trading_rules['ewmac8']['forecast_scalar']
                            diagnostic_info['ForecastScalar'] = scalar
                            diagnostic_info['ForecastScalarType'] = 'FIXED_CONFIG'
                        except:
                            try:
                                scalar = self.system.config.forecast_scalars['ewmac8']
                                diagnostic_info['ForecastScalar'] = scalar
                                diagnostic_info['ForecastScalarType'] = 'FIXED_GLOBAL'
                            except:
                                scalar = self.system.config.get_element("forecast_scalar")
                                diagnostic_info['ForecastScalar'] = scalar
                                diagnostic_info['ForecastScalarType'] = 'FIXED_DEFAULT'

                except Exception as e:
                    print(f"⚠️ Forecast scalar check failed for {instrument}: {e}")

                # 4. BLOCK VALUE AND FX CHECKS
                try:
                    # Block value (should be 1.0 for ETFs)
                    block_move = self.system.rawdata.get_value_of_block_price_move(instrument)
                    if hasattr(block_move, 'iloc'):
                        diagnostic_info['LatestBlockValue'] = float(block_move.iloc[-1])
                    else:
                        diagnostic_info['LatestBlockValue'] = float(block_move) if block_move else 1.0

                    # FX Rate check
                    try:
                        fx_rate = self.system.rawdata.get_fx_for_instrument(instrument, "USD")
                        if hasattr(fx_rate, 'iloc'):
                            diagnostic_info['FXRate'] = float(fx_rate.iloc[-1])
                        else:
                            diagnostic_info['FXRate'] = float(fx_rate) if fx_rate else 1.0
                    except:
                        diagnostic_info['FXRate'] = 1.0  # Default USD

                except Exception as e:
                    print(f"⚠️ Block value/FX analysis failed for {instrument}: {e}")

                diagnostic_data[instrument] = diagnostic_info

            # ========== VOLATILITY SCALAR ANALYSIS ==========
            vol_scalar_comparison = {}

            for instrument in focus_instruments:
                try:
                    # Get system volatility scalar
                    system_scalar, scalar_source = self.get_volatility_scalar_safe(self.system, instrument)

                    # Calculate expected scalar using target volatility
                    target_vol = getattr(self.system.config, 'percentage_vol_target', 12.0) / 100
                    manual_vol = diagnostic_data[instrument]['ManualDailyVol']

                    if pd.notna(manual_vol) and manual_vol > 0:
                        annual_vol = manual_vol * (252 ** 0.5)
                        expected_scalar = target_vol / annual_vol
                        missing_factor = system_scalar / expected_scalar if expected_scalar > 0 else np.nan
                    else:
                        expected_scalar = np.nan
                        missing_factor = np.nan

                    vol_scalar_comparison[instrument] = {
                        'SystemVolatilityScalar': system_scalar,
                        'ScalarSource': scalar_source,
                        'ExpectedVolatilityScalar': expected_scalar,
                        'MissingFactor': missing_factor,
                        'ManualAnnualVol': manual_vol * (252 ** 0.5) if pd.notna(manual_vol) else np.nan,
                        'TargetVol': target_vol
                    }

                except Exception as e:
                    print(f"⚠️ Volatility scalar comparison failed for {instrument}: {e}")

            # ========== EXCEL EXPORT ==========
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                workbook = writer.book

                # Sheet 1: Data Quality Analysis
                data_quality_df = pd.DataFrame.from_dict(diagnostic_data, orient='index')
                data_quality_df.to_excel(writer, sheet_name='Data_Quality', index=False)

                # Sheet 2: Volatility Scalar Comparison
                vol_scalar_df = pd.DataFrame.from_dict(vol_scalar_comparison, orient='index')
                vol_scalar_df.to_excel(writer, sheet_name='Volatility_Scalar_Analysis', index=False)

                # Sheet 3: Time Series Comparison (first 50 days)
                portfolio = self.system.accounts.portfolio()
                portfolio_curve = portfolio.curve()
                recent_dates = portfolio_curve.index[-50:] if len(portfolio_curve) >= 50 else portfolio_curve.index

                timeseries_comparison = []
                for date in recent_dates:
                    for instrument in focus_instruments:
                        try:
                            # Get data for this date
                            prices = self.system.rawdata.get_daily_prices(instrument)
                            close_price = prices.loc[date] if date in prices.index else np.nan

                            # Get returns up to this date for volatility calculation
                            returns_up_to_date = prices.pct_change().dropna()
                            returns_up_to_date = returns_up_to_date[returns_up_to_date.index <= date]

                            if len(returns_up_to_date) > 35:
                                rolling_vol = returns_up_to_date.ewm(span=35).std().iloc[-1]
                            else:
                                rolling_vol = np.nan

                            # Get system volatility scalar for this date
                            try:
                                vol_scalar_series = self.system.positionSize.get_volatility_scalar(instrument)
                                if vol_scalar_series is not None and date in vol_scalar_series.index:
                                    system_scalar = vol_scalar_series.loc[date]
                                else:
                                    system_scalar = np.nan
                            except:
                                system_scalar = np.nan

                            timeseries_comparison.append({
                                'Date': date,
                                'Instrument': instrument,
                                'ClosePrice': close_price,
                                'RollingDailyVol': rolling_vol,
                                'SystemVolScalar': system_scalar,
                                'ExpectedVolScalar': target_vol / (rolling_vol * (252 ** 0.5)) if pd.notna(
                                    rolling_vol) and rolling_vol > 0 else np.nan
                            })

                        except:
                            continue

                timeseries_df = pd.DataFrame(timeseries_comparison)
                if len(timeseries_df) > 0:
                    # Pivot for easier comparison
                    for metric in ['ClosePrice', 'RollingDailyVol', 'SystemVolScalar', 'ExpectedVolScalar']:
                        pivot_df = timeseries_df.pivot(index='Date', columns='Instrument', values=metric)
                        pivot_df.to_excel(writer, sheet_name=f'TimeSeries_{metric}')

                # Apply formatting
                self._format_diagnostic_sheets(writer, workbook)

            print(f"✅ Diagnostic analysis exported: {filename}")
            return filename

        except Exception as e:
            print(f"❌ Error exporting diagnostic analysis: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _format_diagnostic_sheets(self, writer, workbook):
        """Format diagnostic analysis sheets"""

        # Define formats
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        number_format = workbook.add_format({'num_format': '#,##0.00'})
        percent_format = workbook.add_format({'num_format': '0.00%'})
        decimal_format = workbook.add_format({'num_format': '0.0000'})

        # Format each sheet
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]

            if 'Data_Quality' in sheet_name:
                worksheet.set_column('A:A', 12)  # Instrument
                worksheet.set_column('B:C', 12, date_format)  # Dates
                worksheet.set_column('D:G', 12, number_format)  # Counts
                worksheet.set_column('H:H', 12, percent_format)  # Completeness
                worksheet.set_column('I:P', 15, decimal_format)  # Volatilities
            elif 'TimeSeries' in sheet_name:
                worksheet.set_column('A:A', 12, date_format)  # Date
                worksheet.set_column('B:Z', 15, number_format)  # Data

    def verify_forecast_scalar_consistency(self, system):
        """
        Verify that forecast scalars are consistent across all instruments
        """
        print("🔍 FORECAST SCALAR CONSISTENCY CHECK")
        print("-" * 60)

        instruments = system.get_instrument_list()
        trading_rules = list(system.config.trading_rules.keys())

        forecast_scalar_data = {}

        for rule in trading_rules:
            print(f"📊 Checking rule: {rule}")
            rule_scalars = {}

            for instrument in instruments:
                try:
                    # Check if this rule applies to this instrument
                    instrument_rules = system.rules.get_trading_rule_list(instrument)
                    if rule in instrument_rules:
                        # Get the scalar using the same method as the system
                        if hasattr(system.config,
                                   'use_forecast_scale_estimates') and system.config.use_forecast_scale_estimates:
                            # Using estimated scalars
                            scalar_series = system.forecastScaleCap._get_forecast_scalar_estimated(instrument, rule)
                            if scalar_series is not None and len(scalar_series) > 0:
                                scalar_value = scalar_series.iloc[-1]
                                scalar_type = "ESTIMATED"
                        else:
                            # Using fixed scalars
                            scalar_value = system.forecastScaleCap._get_forecast_scalar_fixed(instrument, rule)
                            scalar_type = "FIXED"

                        rule_scalars[instrument] = {
                            'scalar': scalar_value,
                            'type': scalar_type
                        }

                        print(f"  {instrument}: {scalar_value:.4f} ({scalar_type})")

                except Exception as e:
                    print(f"  {instrument}: ERROR - {e}")
                    rule_scalars[instrument] = {'scalar': np.nan, 'type': 'ERROR'}

            forecast_scalar_data[rule] = rule_scalars

            # Check consistency within rule
            scalar_values = [data['scalar'] for data in rule_scalars.values() if not pd.isna(data['scalar'])]
            if len(scalar_values) > 1:
                scalar_std = np.std(scalar_values)
                scalar_mean = np.mean(scalar_values)
                cv = scalar_std / scalar_mean if scalar_mean > 0 else 0

                print(f"  📈 Rule {rule} consistency:")
                print(f"    Mean: {scalar_mean:.4f}, Std: {scalar_std:.4f}, CV: {cv:.4f}")

                if cv > 0.01:  # More than 1% variation
                    print(f"    ⚠️ HIGH VARIATION DETECTED! ({cv:.2%})")
                    print(f"    🔍 This could explain your Missing Factor discrepancies!")

            print()

        return forecast_scalar_data

    def createcomprehensiveequitycurveplot(self):
        """CORRECTED: True compounding analysis with proper difference detection"""
        try:
            import matplotlib.pyplot as plt
            import pandas as pd
            import numpy as np

            import matplotlib
            matplotlib.use('TkAgg')
            plt.ioff()

            print("Creating CORRECTED compounding analysis...")

            portfolio = self.system.accounts.portfolio()
            pnl_curve = portfolio.curve()

            if pnl_curve is None or len(pnl_curve) == 0:
                print("No portfolio data available.")
                return None

            starting_capital = 1000000

            # TRUTH: Get the fixed capital results (what pysystemtrade actually calculated)
            fixed_capital_pnl = self.system.accounts.portfolio().curve().copy()
            fixed_equity = starting_capital + fixed_capital_pnl

            # CORRECTED: True compounding simulation
            # NOTE: This is a SIMULATION of what would have happened with compounding
            # It's NOT what pysystemtrade actually calculated

            daily_returns = fixed_capital_pnl.pct_change().fillna(0)  # Use return percentages
            daily_returns = daily_returns.clip(-0.3, 0.3)  # Cap extreme days at ±30%

            # True compounding equity curve
            compounding_multipliers = (1 + daily_returns).cumprod()
            simulated_compounding_equity = starting_capital * compounding_multipliers

            # PRECISION: Calculate differences with high precision
            difference_precise = simulated_compounding_equity - fixed_equity

            print(f"\nCORRECTED ANALYSIS:")
            print(f"Fixed Capital Final: ${fixed_equity.iloc[-1]:,.2f}")
            print(f"Simulated Compounding Final: ${simulated_compounding_equity.iloc[-1]:,.2f}")
            print(f"Difference: ${difference_precise.iloc[-1]:,.2f}")
            print(f"Difference Range: ${difference_precise.min():,.2f} to ${difference_precise.max():,.2f}")
            print(f"Difference StdDev: ${difference_precise.std():,.2f}")

            # EXPLANATION: Why they might be nearly identical
            total_return = (fixed_equity.iloc[-1] - starting_capital) / starting_capital
            print(f"Total Strategy Return: {total_return:.2%}")
            print(f"Annualized Return: {(total_return / (len(daily_returns) / 252)):.2%}")

            # Create plots with CORRECTED formatting
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 12))

            # Plot 1: Equity Curves (CORRECTED: Show they should be nearly identical for low-vol strategies)
            ax1.plot(fixed_equity.index, fixed_equity.values, 'b-', linewidth=3,
                     label=f'Fixed Capital (Actual Backtest)', alpha=0.8)
            ax1.plot(simulated_compounding_equity.index, simulated_compounding_equity.values, 'r--', linewidth=2,
                     label=f'Simulated Compounding (What-If)', alpha=0.8)
            ax1.set_title(
                'CORRECTED: Fixed Capital vs Simulated Compounding\n(Lines may overlap for low-volatility strategies)',
                fontsize=14, fontweight='bold')
            ax1.set_ylabel('Portfolio Value ($)')
            ax1.grid(True, alpha=0.3)
            ax1.legend()
            ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x / 1e6:.1f}M'))

            # Plot 2: Compounding multipliers
            ax2.plot(compounding_multipliers.index, compounding_multipliers.values, 'g-', linewidth=2)
            ax2.axhline(y=1.0, color='black', linestyle='--', alpha=0.5, label='Initial Level')
            ax2.set_title(f'Compounding Multiplier (Final: {compounding_multipliers.iloc[-1]:.4f})',
                          fontsize=14, fontweight='bold')
            ax2.set_ylabel('Multiplier')
            ax2.grid(True, alpha=0.3)
            ax2.legend()

            # Plot 3: CORRECTED Difference with proper precision
            ax3.plot(difference_precise.index, difference_precise.values, 'purple', linewidth=2)
            ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            ax3.set_title(
                f'Difference: Compounding - Fixed (Range: ${difference_precise.min():,.0f} to ${difference_precise.max():,.0f})',
                fontsize=14, fontweight='bold')
            ax3.set_ylabel('Difference ($)')
            ax3.set_xlabel('Date')
            ax3.grid(True, alpha=0.3)

            # CORRECTED: Adaptive formatter based on difference magnitude
            max_abs_diff = max(abs(difference_precise.min()), abs(difference_precise.max()))
            if max_abs_diff < 10:
                ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:.2f}'))  # Show cents
            elif max_abs_diff < 1000:
                ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:.0f}'))  # Show dollars
            else:
                ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x / 1e3:.0f}K'))  # Show thousands

            plt.tight_layout()

            # CORRECTED Summary
            final_diff = difference_precise.iloc[-1]
            final_diff_pct = (final_diff / fixed_equity.iloc[-1]) * 100

            summary_text = f"""CORRECTED Compounding Analysis:
    Fixed Capital (Actual): ${fixed_equity.iloc[-1]:,.0f}
    Simulated Compounding: ${simulated_compounding_equity.iloc[-1]:,.0f}
    Difference: ${final_diff:,.2f} ({final_diff_pct:.3f}%)
    Strategy Total Return: {total_return:.2%}

    EXPLANATION: Small differences normal for low-volatility strategies
    This is SIMULATION - pysystemtrade cannot backtest true compounding"""

            plt.figtext(0.02, 0.02, summary_text, fontsize=9,
                        bbox=dict(boxstyle="round,pad=0.3", facecolor='lightyellow'))

            plt.show(block=True)
            input("Press Enter after viewing the corrected analysis...")

            print(f"\nCORRECTED FINAL SUMMARY:")
            print(f"Fixed Capital Final: ${fixed_equity.iloc[-1]:,.2f}")
            print(f"Simulated Compounding Final: ${simulated_compounding_equity.iloc[-1]:,.2f}")
            print(f"Final Difference: ${final_diff:,.2f} ({final_diff_pct:.3f}%)")
            print(f"Max Absolute Difference: ${max_abs_diff:,.2f}")
            print(f"\nIMPORTANT UNDERSTANDING:")
            print(f"- Pysystemtrade backtests use FIXED capital only")
            print(f"- 'Full compounding' config affects LIVE TRADING, not backtests")
            print(f"- This analysis shows SIMULATED compounding difference")
            print(f"- Small differences are normal for low-volatility strategies")

            return fig

        except Exception as e:
            print(f"Error in corrected analysis: {e}")
            import traceback
            traceback.print_exc()
            return None

    def create_strategy_comparison_plot(self):
        """PERSISTENT VERSION: Create enhanced comparison that stays visible"""
        try:
            import matplotlib.pyplot as plt
            import pandas as pd
            import numpy as np
            import time

            print("🚀 Creating Enhanced Strategy Comparison (4 strategies)...")

            # Get the original long-short system equity curve
            portfolio = self.system.accounts.portfolio()
            ls_equity_curve = portfolio.curve()

            if ls_equity_curve is None or len(ls_equity_curve) == 0:
                print("❌ No portfolio data available for comparison.")
                return None

            # Starting capital base
            starting_capital = 1000000
            ls_equity = starting_capital + ls_equity_curve

            # Create long-only version
            print("📊 Calculating long-only strategy...")
            lo_pnl_curve = self.calculate_long_only_pnl()
            lo_equity = starting_capital + lo_pnl_curve

            print("📈 Using system's existing IVV and HYD data for benchmarks...")

            try:
                # Use system's existing data
                ivv_prices = self.system.rawdata.get_daily_prices('IVV')
                hyd_prices = self.system.rawdata.get_daily_prices('HYD')

                if ivv_prices is None or hyd_prices is None:
                    raise Exception("IVV or HYD not found in system data")

                print(f"✅ Using system IVV data: {len(ivv_prices)} data points")
                print(f"✅ Using system HYD data: {len(hyd_prices)} data points")

                # Calculate buy-and-hold returns
                ivv_returns = ivv_prices.pct_change().fillna(0)
                hyd_returns = hyd_prices.pct_change().fillna(0)

                # Create buy-and-hold equity curves
                ivv_equity = starting_capital * (1 + ivv_returns).cumprod()
                hyd_equity = starting_capital * (1 + hyd_returns).cumprod()

                # Align dates
                common_dates = ls_equity.index.intersection(ivv_equity.index).intersection(hyd_equity.index)
                print(f"✅ Found {len(common_dates)} overlapping trading days")

                # Align all series
                ls_equity_aligned = ls_equity.loc[common_dates]
                lo_equity_aligned = lo_equity.loc[common_dates]
                ivv_equity_aligned = ivv_equity.loc[common_dates]
                hyd_equity_aligned = hyd_equity.loc[common_dates]

            except Exception as system_data_error:
                print(f"❌ System data access failed: {system_data_error}")
                print("📊 Showing Long-Short vs Long-Only comparison only...")
                return self.create_simple_strategy_comparison(ls_equity, lo_equity)

            print("🎨 Creating PERSISTENT enhanced comparison plot...")

            # CRITICAL FIX: Proper matplotlib setup for persistent display
            import matplotlib
            matplotlib.use('TkAgg')  # Force TkAgg backend
            plt.close('all')  # Close any existing plots
            plt.ioff()  # Turn OFF interactive mode initially

            # Create figure with proper settings for persistence
            fig = plt.figure(figsize=(16, 12))
            fig.canvas.manager.set_window_title('Enhanced Strategy Comparison - Keep Open!')
            fig.suptitle('🏆 SYSTEMATIC TRADING vs BUY & HOLD COMPARISON',
                         fontsize=20, fontweight='bold', y=0.95)

            # Plot 1: All strategies comparison
            ax1 = plt.subplot(3, 1, 1)
            ax1.plot(ls_equity_aligned.index, ls_equity_aligned.values, 'b-', linewidth=4,
                     label='🔵 Long-Short Strategy', alpha=0.9)
            ax1.plot(lo_equity_aligned.index, lo_equity_aligned.values, 'r-', linewidth=4,
                     label='🔴 Long-Only Strategy', alpha=0.9)
            ax1.plot(ivv_equity_aligned.index, ivv_equity_aligned.values, 'g-', linewidth=3,
                     label='🟢 Buy & Hold IVV (S&P 500)', alpha=0.8)
            ax1.plot(hyd_equity_aligned.index, hyd_equity_aligned.values, 'orange', linewidth=3,
                     label='🟠 Buy & Hold HYD (Muni Bonds)', alpha=0.8)

            ax1.set_title('📊 PORTFOLIO VALUE COMPARISON', fontsize=16, fontweight='bold', pad=20)
            ax1.set_ylabel('Portfolio Value ($)', fontsize=14)
            ax1.grid(True, alpha=0.4)
            ax1.legend(loc='upper left', fontsize=12)
            ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x / 1e6:.1f}M'))

            # Plot 2: Excess returns
            ax2 = plt.subplot(3, 1, 2)
            ls_vs_ivv = ls_equity_aligned - ivv_equity_aligned
            lo_vs_ivv = lo_equity_aligned - ivv_equity_aligned
            ls_vs_hyd = ls_equity_aligned - hyd_equity_aligned

            ax2.plot(ls_vs_ivv.index, ls_vs_ivv.values, 'b-', linewidth=3,
                     label='🔵 Long-Short vs IVV', alpha=0.9)
            ax2.plot(lo_vs_ivv.index, lo_vs_ivv.values, 'r-', linewidth=3,
                     label='🔴 Long-Only vs IVV', alpha=0.9)
            ax2.plot(ls_vs_hyd.index, ls_vs_hyd.values, 'purple', linewidth=3,
                     label='🟣 Long-Short vs HYD', alpha=0.9)
            ax2.axhline(y=0, color='black', linestyle='--', alpha=0.7, linewidth=2)

            ax2.set_title('📈 EXCESS RETURNS OVER BENCHMARKS', fontsize=16, fontweight='bold')
            ax2.set_ylabel('Excess Return ($)', fontsize=14)
            ax2.grid(True, alpha=0.4)
            ax2.legend(loc='upper left', fontsize=12)
            ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x / 1e3:.0f}K'))

            # Plot 3: Rolling volatility
            ax3 = plt.subplot(3, 1, 3)
            window = 60

            ls_vol = ls_equity_aligned.pct_change().rolling(window).std() * np.sqrt(252) * 100
            lo_vol = lo_equity_aligned.pct_change().rolling(window).std() * np.sqrt(252) * 100
            ivv_vol = ivv_equity_aligned.pct_change().rolling(window).std() * np.sqrt(252) * 100
            hyd_vol = hyd_equity_aligned.pct_change().rolling(window).std() * np.sqrt(252) * 100

            ax3.plot(ls_vol.index, ls_vol.values, 'b-', linewidth=3, label='🔵 Long-Short')
            ax3.plot(lo_vol.index, lo_vol.values, 'r-', linewidth=3, label='🔴 Long-Only')
            ax3.plot(ivv_vol.index, ivv_vol.values, 'g-', linewidth=3, label='🟢 IVV')
            ax3.plot(hyd_vol.index, hyd_vol.values, 'orange', linewidth=3, label='🟠 HYD')

            ax3.set_title(f'📊 {window}-DAY ROLLING VOLATILITY', fontsize=16, fontweight='bold')
            ax3.set_ylabel('Volatility (%)', fontsize=14)
            ax3.set_xlabel('Date', fontsize=14)
            ax3.grid(True, alpha=0.4)
            ax3.legend(loc='upper left', fontsize=12)

            # Calculate and display stats
            strategies = {
                'Long-Short': ls_equity_aligned,
                'Long-Only': lo_equity_aligned,
                'IVV B&H': ivv_equity_aligned,
                'HYD B&H': hyd_equity_aligned
            }

            stats_summary = []
            for name, equity in strategies.items():
                returns = equity.pct_change().dropna()
                total_return = (equity.iloc[-1] / starting_capital - 1) * 100
                annual_return = ((equity.iloc[-1] / starting_capital) ** (252 / len(equity)) - 1) * 100
                volatility = returns.std() * np.sqrt(252) * 100
                sharpe = (annual_return - 2) / volatility if volatility > 0 else 0
                max_dd = ((equity / equity.cummax()) - 1).min() * 100

                stats_summary.append({
                    'Strategy': name,
                    'Total Return': f"{total_return:.1f}%",
                    'Annual Return': f"{annual_return:.1f}%",
                    'Volatility': f"{volatility:.1f}%",
                    'Sharpe Ratio': f"{sharpe:.2f}",
                    'Max Drawdown': f"{max_dd:.1f}%"
                })

            # Add performance summary to plot
            summary_lines = []
            for stats in stats_summary:
                summary_lines.append(f"{stats['Strategy']}: Ret {stats['Total Return']}, "
                                     f"Sharpe {stats['Sharpe Ratio']}, Vol {stats['Volatility']}")

            summary_text = "📋 PERFORMANCE SUMMARY:\n" + "\n".join(summary_lines)
            plt.figtext(0.02, 0.02, summary_text, fontsize=9,
                        bbox=dict(boxstyle="round,pad=0.4", facecolor='lightblue', alpha=0.9))

            plt.tight_layout()
            plt.subplots_adjust(top=0.92, bottom=0.25)

            # CRITICAL: Persistent display method
            print("🎯 DISPLAYING PERSISTENT ENHANCED COMPARISON...")
            print("📌 IMPORTANT: Plot window will stay open - close manually when done!")

            plt.ion()  # Turn on interactive mode
            plt.show(block=True)  # BLOCK until manually closed

            # Print console results
            print("\n" + "=" * 90)
            print("🏆 STRATEGY COMPARISON RESULTS")
            print("=" * 90)
            for stats in stats_summary:
                print(f"{stats['Strategy']:15} | {stats['Total Return']:8} | {stats['Annual Return']:8} | " +
                      f"{stats['Volatility']:6} | {stats['Sharpe Ratio']:6} | {stats['Max Drawdown']:8}")

            return fig

        except Exception as e:
            print(f"❌ Error in enhanced strategy comparison: {e}")
            import traceback
            traceback.print_exc()
            return None

    def create_simple_strategy_comparison(self, ls_equity, lo_equity):
        """PERSISTENT VERSION: Simple Long-Short vs Long-Only comparison"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib

            print("📊 Creating PERSISTENT simple strategy comparison...")

            # Force proper backend
            matplotlib.use('TkAgg')
            plt.close('all')

            fig, ax = plt.subplots(figsize=(12, 8))
            fig.canvas.manager.set_window_title('Strategy Comparison - Keep Open!')

            ax.plot(ls_equity.index, ls_equity.values, 'b-', linewidth=3,
                    label='🔵 Long-Short Strategy', alpha=0.9)
            ax.plot(lo_equity.index, lo_equity.values, 'r-', linewidth=3,
                    label='🔴 Long-Only Strategy', alpha=0.9)

            ax.set_title('🏆 Strategy Comparison: Long-Short vs Long-Only',
                         fontsize=16, fontweight='bold')
            ax.set_ylabel('Portfolio Value ($)', fontsize=14)
            ax.set_xlabel('Date', fontsize=14)
            ax.grid(True, alpha=0.4)
            ax.legend(fontsize=12)
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x / 1e6:.1f}M'))

            plt.tight_layout()

            print("🎯 DISPLAYING PERSISTENT SIMPLE COMPARISON...")
            print("📌 IMPORTANT: Plot window will stay open - close manually when done!")

            plt.ion()
            plt.show(block=True)  # FORCE BLOCKING

            return fig

        except Exception as e:
            print(f"❌ Error in simple strategy comparison: {e}")
            return None

    def calculate_buy_and_hold_benchmark(self, symbol, start_date, end_date, starting_capital):
        """Calculate buy-and-hold performance for a benchmark ETF"""
        try:
            import yfinance as yf

            # Download data
            data = yf.download(symbol, start=start_date, end=end_date)['Adj Close']

            if data.empty:
                print(f"No data available for {symbol}")
                return None

            # Calculate returns and equity curve
            returns = data.pct_change().fillna(0)
            equity_curve = starting_capital * (1 + returns).cumprod()

            return equity_curve

        except Exception as e:
            print(f"Error calculating benchmark for {symbol}: {e}")
            return None

    def calculate_long_only_pnl(self):
        """Calculate P&L for long-only strategy by clipping negative positions"""
        try:
            instruments = self.system.get_instrument_list()
            daily_pnl_series = []

            print(f"Calculating long-only P&L for {len(instruments)} instruments...")

            for instrument in instruments:
                # Get original positions (long-short)
                positions = self.system.portfolio.get_notional_position(instrument)

                # Create long-only positions by clipping negatives
                long_only_positions = positions.clip(lower=0)

                # Get price changes
                prices = self.system.rawdata.get_daily_prices(instrument)
                if prices is None:
                    continue

                price_changes = prices.pct_change()

                # Calculate P&L: position * price_change * previous_price
                # Note: positions are shifted to avoid look-ahead bias
                instrument_pnl = (long_only_positions.shift(1) *
                                  price_changes * prices.shift(1)).fillna(0)

                daily_pnl_series.append(instrument_pnl)

            # Combine all instrument P&L into portfolio P&L
            if daily_pnl_series:
                portfolio_daily_pnl = pd.concat(daily_pnl_series, axis=1).sum(axis=1)
                portfolio_cumulative_pnl = portfolio_daily_pnl.cumsum()

                print(f"Long-only P&L calculation completed: {len(portfolio_cumulative_pnl)} data points")
                return portfolio_cumulative_pnl
            else:
                print("No valid instruments for long-only calculation")
                return pd.Series()

        except Exception as e:
            print(f"Error calculating long-only P&L: {e}")
            return pd.Series()
