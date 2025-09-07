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

    def _get_volatility_scalar_safe(self, system, instrument):
        """
        FIXED: Safely get volatility scalar using multiple PySystemTrade methods
        """
        vol_scalar = 0

        # Method 1: Try the standard PySystemTrade way
        try:
            vol_scalar_series = system.positionSize.get_vol_scalar(instrument)
            if vol_scalar_series is not None and len(vol_scalar_series) > 0:
                vol_scalar = vol_scalar_series.iloc[-1]
                if vol_scalar > 0:
                    return vol_scalar
        except (AttributeError, Exception):
            pass

        # Method 2: Try alternative method name
        try:
            vol_scalar_series = system.positionSize.get_volatility_scalar(instrument)
            if vol_scalar_series is not None and len(vol_scalar_series) > 0:
                vol_scalar = vol_scalar_series.iloc[-1]
                if vol_scalar > 0:
                    return vol_scalar
        except (AttributeError, Exception):
            pass

        # Method 3: Calculate manually from volatility and vol target
        try:
            # Get daily volatility from system
            vol_series = system.rawdata.get_daily_percentage_volatility(instrument)
            if vol_series is not None and len(vol_series) > 0:
                current_vol = vol_series.iloc[-1]
                if current_vol > 0:
                    vol_target = getattr(system.config, 'percentage_vol_target', 12.0) / 100
                    vol_scalar = vol_target / current_vol
                    return vol_scalar
        except (AttributeError, Exception):
            pass

        # Method 4: Try to get from forecast scalars (different approach)
        try:
            # Sometimes volatility scalar is buried in position sizing calculations
            subsystem_pos = system.positionSize.get_subsystem_position(instrument)
            if subsystem_pos is not None and len(subsystem_pos) > 0:
                # Try to reverse-engineer the volatility scalar
                # This is more complex but sometimes necessary
                pass
        except (AttributeError, Exception):
            pass

        # Method 5: Manual calculation from price data
        try:
            prices = system.rawdata.get_daily_prices(instrument)
            if prices is not None and len(prices) > 35:
                returns = prices.pct_change().dropna()
                if len(returns) > 35:
                    # Calculate 35-day rolling volatility (matching your config)
                    daily_vol = returns.rolling(window=35, min_periods=10).std().iloc[-1]
                    if daily_vol > 0:
                        annual_vol = daily_vol * (252 ** 0.5)  # Annualize
                        vol_target = getattr(system.config, 'percentage_vol_target', 12.0) / 100
                        vol_scalar = vol_target / annual_vol
                        return vol_scalar
        except Exception:
            pass

        print(f"⚠️ Could not get volatility scalar for {instrument} - using 0")
        return 0

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

    def create_equity_curve_dashboard(self):
        """Create simple equity curve dashboard aligned with Carver methodology"""
        # Get portfolio data
        portfolio = self.system.accounts.portfolio()
        pnl_curve = portfolio.curve()

        if pnl_curve is None or len(pnl_curve) == 0:
            print("No portfolio data available for dashboard")
            return None

        # Convert P&L to equity curve (proper capital base)
        starting_capital = 1000000  # Your configured capital
        equity_curve = starting_capital + pnl_curve

        # Calculate performance metrics
        performance = self.calculator.calculate_performance(self.system)

        # Create dashboard
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

        # Plot 1: Equity Curve
        ax1.plot(equity_curve.index, equity_curve.values, 'b-', linewidth=2)
        ax1.set_title('Portfolio Equity Curve', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Portfolio Value ($)')
        ax1.grid(True, alpha=0.3)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x / 1e6:.1f}M'))

        # Plot 2: Drawdown
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

        # Add performance text
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

        plt.show()
        return fig

    def create_instrument_performance_dashboard(self):
        """Create comprehensive instrument performance analysis following Carver methodology"""
        print("Creating instrument performance dashboard...")

        # Get system data
        instruments = self.system.get_instrument_list()
        portfolio = self.system.accounts.portfolio()

        if not instruments:
            print("No instruments found in system")
            return None

        # Collect instrument data
        instrument_data = {}
        for instrument in instruments:
            try:
                # Get instrument P&L
                pnl = self.system.accounts.pandl_for_instrument(instrument)
                if pnl is None or len(pnl) == 0:
                    continue

                # Convert P&L to returns (assuming $1M capital base)
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

                # Win rate
                win_rate = (returns > 0).mean()

                # Final P&L
                total_pnl = pnl.iloc[-1]

                instrument_data[instrument] = {
                    'pnl_curve': pnl,
                    'returns': returns,
                    'annual_return': annual_return,
                    'annual_vol': annual_vol,
                    'sharpe_ratio': sharpe_ratio,
                    'max_drawdown': max_drawdown,
                    'win_rate': win_rate,
                    'total_pnl': total_pnl,
                    'final_value': capital_curve.iloc[-1]
                }

            except Exception as e:
                print(f"Error processing {instrument}: {e}")
                continue

        if not instrument_data:
            print("No valid instrument data found")
            return None

        # Create dashboard
        fig = plt.figure(figsize=(20, 12))

        # Layout: 2x3 grid
        gs = fig.add_gridspec(3, 2, height_ratios=[1, 1, 1], hspace=0.3, wspace=0.3)

        # 1. Individual P&L Curves (Top Left)
        ax1 = fig.add_subplot(gs[0, 0])
        for instrument, data in instrument_data.items():
            ax1.plot(data['pnl_curve'].index, data['pnl_curve'].values,
                     linewidth=1, alpha=0.7, label=instrument)
        ax1.set_title('Individual Instrument P&L Curves', fontsize=12, fontweight='bold')
        ax1.set_ylabel('P&L ($)')
        ax1.grid(True, alpha=0.3)
        ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)

        # 2. Sharpe Ratio Ranking (Top Right)
        ax2 = fig.add_subplot(gs[0, 1])
        sharpe_data = [(k, v['sharpe_ratio']) for k, v in instrument_data.items()]
        sharpe_data.sort(key=lambda x: x[1], reverse=True)
        instruments_sorted, sharpes = zip(*sharpe_data)
        colors = ['green' if s > 0.5 else 'orange' if s > 0.2 else 'red' for s in sharpes]
        bars = ax2.barh(range(len(instruments_sorted)), sharpes, color=colors, alpha=0.7)
        ax2.set_yticks(range(len(instruments_sorted)))
        ax2.set_yticklabels(instruments_sorted, fontsize=8)
        ax2.set_xlabel('Sharpe Ratio')
        ax2.set_title('Instrument Sharpe Ratios (Ranked)', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='x')
        ax2.axvline(x=0.5, color='green', linestyle='--', alpha=0.5, label='Good (>0.5)')
        ax2.axvline(x=0.2, color='orange', linestyle='--', alpha=0.5, label='Acceptable (>0.2)')
        ax2.legend(fontsize=8)

        # 3. Return vs Risk Scatter (Middle Left)
        ax3 = fig.add_subplot(gs[1, 0])
        returns_list = [data['annual_return'] for data in instrument_data.values()]
        vols_list = [data['annual_vol'] for data in instrument_data.values()]
        scatter = ax3.scatter(vols_list, returns_list, alpha=0.7, s=60)
        ax3.set_xlabel('Annual Volatility')
        ax3.set_ylabel('Annual Return')
        ax3.set_title('Risk-Return Profile by Instrument', fontsize=12, fontweight='bold')
        ax3.grid(True, alpha=0.3)

        # Add instrument labels
        for i, instrument in enumerate(instrument_data.keys()):
            ax3.annotate(instrument, (vols_list[i], returns_list[i]),
                         fontsize=7, alpha=0.8, xytext=(5, 5), textcoords='offset points')

        # 4. Drawdown Comparison (Middle Right)
        ax4 = fig.add_subplot(gs[1, 1])
        drawdown_data = [(k, v['max_drawdown']) for k, v in instrument_data.items()]
        drawdown_data.sort(key=lambda x: x[1])  # Sort by drawdown (most negative first)
        instruments_dd, drawdowns = zip(*drawdown_data)
        colors_dd = ['red' if d < -0.3 else 'orange' if d < -0.15 else 'green' for d in drawdowns]
        ax4.barh(range(len(instruments_dd)), [d * 100 for d in drawdowns],
                 color=colors_dd, alpha=0.7)
        ax4.set_yticks(range(len(instruments_dd)))
        ax4.set_yticklabels(instruments_dd, fontsize=8)
        ax4.set_xlabel('Maximum Drawdown (%)')
        ax4.set_title('Maximum Drawdown by Instrument', fontsize=12, fontweight='bold')
        ax4.grid(True, alpha=0.3, axis='x')

        # 5. Performance Summary Table (Bottom - spans both columns)
        ax5 = fig.add_subplot(gs[2, :])
        ax5.axis('off')

        # Create summary table
        table_data = []
        for instrument, data in instrument_data.items():
            table_data.append([
                instrument,
                f"{data['annual_return']:.1%}",
                f"{data['annual_vol']:.1%}",
                f"{data['sharpe_ratio']:.3f}",
                f"{data['max_drawdown']:.1%}",
                f"{data['win_rate']:.1%}",
                f"${data['total_pnl']:,.0f}"
            ])

        # Sort by Sharpe ratio for table
        table_data.sort(key=lambda x: float(x[3]), reverse=True)

        headers = ['Instrument', 'Annual Return', 'Volatility', 'Sharpe', 'Max DD', 'Win Rate', 'Total P&L']

        # Create table
        table = ax5.table(cellText=table_data, colLabels=headers,
                          cellLoc='center', loc='center', bbox=[0, 0, 1, 1])
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.5)

        # Color code Sharpe ratios in table
        for i, row in enumerate(table_data):
            sharpe_val = float(row[3])
            if sharpe_val > 0.5:
                table[(i + 1, 3)].set_facecolor('#90EE90')  # Light green
            elif sharpe_val > 0.2:
                table[(i + 1, 3)].set_facecolor('#FFE4B5')  # Light orange
            else:
                table[(i + 1, 3)].set_facecolor('#FFB6C1')  # Light red

        plt.suptitle('Individual Instrument Performance Analysis', fontsize=16, fontweight='bold', y=0.95)

        # Add summary statistics
        avg_sharpe = np.mean([data['sharpe_ratio'] for data in instrument_data.values()])
        avg_return = np.mean([data['annual_return'] for data in instrument_data.values()])
        fig.text(0.02, 0.02,
                 f'Portfolio Summary: Avg Sharpe: {avg_sharpe:.3f} | Avg Return: {avg_return:.1%} | Instruments: {len(instrument_data)}',
                 fontsize=10, bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue"))

        plt.show()
        return fig

    def create_correlation_heatmap(self):
        """Create correlation heatmap of instrument returns"""
        print("Creating instrument correlation analysis...")

        instruments = self.system.get_instrument_list()
        returns_data = {}

        # Collect returns for all instruments
        for instrument in instruments:
            try:
                pnl = self.system.accounts.pandl_for_instrument(instrument)
                if pnl is not None and len(pnl) > 100:
                    # Convert to returns
                    starting_capital = 1000000 / len(instruments)
                    capital_curve = starting_capital + pnl
                    returns = capital_curve.pct_change().dropna()
                    returns_data[instrument] = returns
            except:
                continue

        if len(returns_data) < 2:
            print("Insufficient data for correlation analysis")
            return None

        # Create returns DataFrame
        returns_df = pd.DataFrame(returns_data).dropna()

        # Calculate correlation matrix
        correlation_matrix = returns_df.corr()

        # Create heatmap
        plt.figure(figsize=(12, 10))

        # Create mask for upper triangle
        mask = np.triu(np.ones_like(correlation_matrix, dtype=bool))

        # Create heatmap
        sns.heatmap(correlation_matrix, mask=mask, annot=True, cmap='RdYlBu_r',
                    center=0, square=True, linewidths=0.5, fmt='.2f',
                    cbar_kws={"shrink": .8})

        plt.title('Instrument Return Correlations\n(Lower Triangle Only)',
                  fontsize=14, fontweight='bold', pad=20)
        plt.tight_layout()

        # Add interpretation text
        avg_correlation = correlation_matrix.values[np.tril_indices_from(correlation_matrix.values, k=-1)].mean()
        plt.figtext(0.02, 0.02, f'Average Correlation: {avg_correlation:.3f} (Lower is better for diversification)',
                    fontsize=10, bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow"))

        plt.show()
        return plt.gcf()

    def export_instrument_performance_excel(self, filename="instrument_performance_analysis.xlsx"):
        """Export comprehensive instrument performance analysis to Excel"""
        print(f"Exporting instrument performance analysis to {filename}...")

        # Get system data
        instruments = self.system.get_instrument_list()
        if not instruments:
            print("No instruments found in system")
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

                # Convert P&L to returns (assuming $1M capital base)
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
                consecutive_positive = self._calculate_consecutive_periods(returns > 0)
                consecutive_negative = self._calculate_consecutive_periods(returns < 0)

                # Store summary data
                instrument_data[instrument] = {
                    'Annual_Return': annual_return,
                    'Annual_Volatility': annual_vol,
                    'Sharpe_Ratio': sharpe_ratio,
                    'Max_Drawdown': max_drawdown,
                    'Win_Rate': win_rate,
                    'Total_PnL': total_pnl,
                    'Final_Value': capital_curve.iloc[-1],
                    'Daily_Vol': volatility_of_returns,
                    'Best_Day': returns.max(),
                    'Worst_Day': returns.min(),
                    'Returns_10th_Percentile': returns_10th,
                    'Returns_90th_Percentile': returns_90th,
                    'Max_Consecutive_Wins': consecutive_positive['max'],
                    'Max_Consecutive_Losses': consecutive_negative['max'],
                    'Data_Points': len(returns),
                    'Start_Date': pnl.index[0],
                    'End_Date': pnl.index[-1]
                }

                # Store time series data
                daily_returns_data[instrument] = returns
                pnl_curves_data[instrument] = pnl

            except Exception as e:
                print(f"Error processing {instrument}: {e}")
                continue

        if not instrument_data:
            print("No valid instrument data found")
            return None

        # Create Excel file with multiple sheets
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            workbook = writer.book

            # Sheet 1: Summary Performance Metrics
            summary_df = pd.DataFrame.from_dict(instrument_data, orient='index')
            summary_df = summary_df.sort_values('Sharpe_Ratio', ascending=False)

            # Format percentages and currencies
            summary_df['Annual_Return'] = summary_df['Annual_Return'].apply(lambda x: f"{x:.2%}")
            summary_df['Annual_Volatility'] = summary_df['Annual_Volatility'].apply(lambda x: f"{x:.2%}")
            summary_df['Max_Drawdown'] = summary_df['Max_Drawdown'].apply(lambda x: f"{x:.2%}")
            summary_df['Win_Rate'] = summary_df['Win_Rate'].apply(lambda x: f"{x:.2%}")
            summary_df['Total_PnL'] = summary_df['Total_PnL'].apply(lambda x: f"${x:,.2f}")
            summary_df['Final_Value'] = summary_df['Final_Value'].apply(lambda x: f"${x:,.2f}")

            summary_df.to_excel(writer, sheet_name='Performance_Summary')

            # Sheet 2: Raw Performance Metrics (for further analysis)
            raw_summary_df = pd.DataFrame.from_dict(instrument_data, orient='index')
            raw_summary_df = raw_summary_df.sort_values('Sharpe_Ratio', ascending=False)
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
            risk_df = self._create_risk_analysis_df(instrument_data, daily_returns_data)
            risk_df.to_excel(writer, sheet_name='Risk_Analysis')

            # Sheet 6: Correlation Matrix
            if len(daily_returns_data) >= 2:
                corr_df = pd.DataFrame.from_dict(daily_returns_data, orient='columns').corr()
                corr_df.to_excel(writer, sheet_name='Correlations')

            # Add formatting
            self._format_excel_sheets(writer, workbook)

        print(f"✅ Excel file exported: {filename}")
        print(
            f"📊 Sheets created: Performance_Summary, Raw_Metrics, Daily_Returns, PnL_Curves, Risk_Analysis, Correlations")

        return filename

    def _calculate_consecutive_periods(self, boolean_series):
        """Calculate consecutive True periods in a boolean series"""
        if len(boolean_series) == 0:
            return {'max': 0, 'current': 0}

        # Convert to list for easier processing
        series_list = boolean_series.tolist()
        max_consecutive = 0
        current_consecutive = 0

        for value in series_list:
            if value:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        return {'max': max_consecutive, 'current': current_consecutive}

    def _create_risk_analysis_df(self, instrument_data, daily_returns_data):
        """Create risk analysis DataFrame"""
        risk_analysis = {}

        for instrument, data in instrument_data.items():
            if instrument in daily_returns_data:
                returns = daily_returns_data[instrument]

                # Value at Risk (VaR) calculations
                var_95 = returns.quantile(0.05)  # 95% VaR
                var_99 = returns.quantile(0.01)  # 99% VaR

                # Expected Shortfall (Conditional VaR)
                es_95 = returns[returns <= var_95].mean() if (returns <= var_95).any() else var_95
                es_99 = returns[returns <= var_99].mean() if (returns <= var_99).any() else var_99

                # Skewness and Kurtosis
                skewness = returns.skew()
                kurtosis = returns.kurtosis()

                # Downside deviation (only negative returns)
                downside_returns = returns[returns < 0]
                downside_deviation = downside_returns.std() if len(downside_returns) > 0 else 0

                # Sortino ratio
                sortino_ratio = (returns.mean() * 252) / (
                            downside_deviation * (252 ** 0.5)) if downside_deviation > 0 else 0

                risk_analysis[instrument] = {
                    'VaR_95': f"{var_95:.4f}",
                    'VaR_99': f"{var_99:.4f}",
                    'Expected_Shortfall_95': f"{es_95:.4f}",
                    'Expected_Shortfall_99': f"{es_99:.4f}",
                    'Skewness': f"{skewness:.3f}",
                    'Kurtosis': f"{kurtosis:.3f}",
                    'Downside_Deviation': f"{downside_deviation:.4f}",
                    'Sortino_Ratio': f"{sortino_ratio:.3f}",
                    'Sharpe_Ratio': f"{data['Sharpe_Ratio']:.3f}"
                }

        return pd.DataFrame.from_dict(risk_analysis, orient='index')

    def _format_excel_sheets(self, writer, workbook):
        """Add formatting to Excel sheets"""
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })

        # Format the Performance_Summary sheet
        worksheet = writer.sheets['Performance_Summary']
        worksheet.set_column('A:A', 12)  # Instrument names
        worksheet.set_column('B:P', 15)  # Data columns

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

    def _format_time_series_sheets(self, writer, workbook):
        """Format the time series sheets"""

        # Define formats
        percent_format = workbook.add_format({'num_format': '0.00%'})
        currency_format = workbook.add_format({'num_format': '$#,##0'})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})

        # Format weights sheet (percentages)
        if 'Cash_Weights_TimeSeries' in writer.sheets:
            worksheet = writer.sheets['Cash_Weights_TimeSeries']
            worksheet.set_column('A:A', 12, date_format)  # Date column
            worksheet.set_column('B:ZZ', 10, percent_format)  # Weight columns

        # Format positions sheet (currency)
        if 'Cash_Positions_TimeSeries' in writer.sheets:
            worksheet = writer.sheets['Cash_Positions_TimeSeries']
            worksheet.set_column('A:A', 12, date_format)  # Date column
            worksheet.set_column('B:ZZ', 12, currency_format)  # Position columns

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

    def export_instrument_turnover_analysis_excel(self, filename):
        """Placeholder - implement if needed"""
        print(f"⚠️ {filename} export not implemented yet")
        return None

    def export_trading_rule_analysis_excel(self, filename):
        """Placeholder - implement if needed"""
        print(f"⚠️ {filename} export not implemented yet")
        return None

    def export_weights_and_multipliers_excel(self, filename):
        """Placeholder - implement if needed"""
        print(f"⚠️ {filename} export not implemented yet")
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

    def export_complete_position_sizing_factors_excel(self, filename):
        """Placeholder - implement if needed"""
        print(f"⚠️ {filename} export not implemented yet")
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

    def export_final_day_backtest_report(self, filename="final_day_backtest_report.xlsx"):
        """
        Export comprehensive final day backtest report - FIXED VOLATILITY VERSION

        FIXES:
        1. Proper daily/annual volatility calculation following pysystemtrade methodology
        2. Correct volatility units (percentage vs decimal)
        3. Accurate volatility scalar labeling
        """
        try:
            print(f"📊 Exporting FIXED volatility final day backtest report to {filename}...")

            instruments = self.system.get_instrument_list()

            # Get final date from portfolio
            portfolio = self.system.accounts.portfolio()
            portfolio_curve = portfolio.curve()
            if portfolio_curve is None or len(portfolio_curve) == 0:
                print("❌ No portfolio curve data available")
                return None

            final_date = portfolio_curve.index[-1]

            # Portfolio value is EXTRACTED from equity curve
            starting_capital = 1000000
            final_pnl = portfolio_curve.iloc[-1]
            portfolio_value = starting_capital + final_pnl

            # Get target volatility from config
            target_vol = getattr(self.system.config, 'percentage_vol_target', 12.0) / 100  # Convert to decimal
            daily_cash_vol_target = portfolio_value * target_vol / 16

            print(f"📅 Final backtest date: {final_date.strftime('%Y-%m-%d')}")
            print(f"💰 Final portfolio value: ${portfolio_value:,.2f}")
            print(f"🎯 Target volatility: {target_vol:.1%}")
            print(f"💵 Daily cash volatility target: ${daily_cash_vol_target:,.2f}")

            # Collect FIXED data for all instruments
            final_day_data = []

            for instrument in instruments:
                try:
                    # Initialize row data with all components
                    row_data = {
                        'Instrument': instrument,
                        'Date': final_date,
                        'Close_Price': np.nan,
                        'Risk_Weight_Config': 0,
                        'Daily_Volatility_Pct': np.nan,  # FIXED: Daily vol as percentage
                        'Daily_Volatility_Decimal': np.nan,  # FIXED: Daily vol as decimal
                        'Annual_Volatility_Pct': np.nan,  # FIXED: Annual vol as percentage
                        'Annual_Volatility_Decimal': np.nan,  # FIXED: Annual vol as decimal
                        'Target_Volatility': target_vol,
                        'Daily_Cash_Vol_Target': daily_cash_vol_target,
                        'Portfolio_Value': portfolio_value,

                        # === SUBSYSTEM POSITION COMPONENTS ===
                        'Combined_Forecast': np.nan,  # [EXTRACTED]
                        'Volatility_Scalar': np.nan,  # [EXTRACTED/CALCULATED] - FIXED
                        'Volatility_Scalar_Source': 'UNKNOWN',  # NEW: Track source
                        'IDM': np.nan,  # [EXTRACTED]
                        'Instrument_Value_Volatility': np.nan,  # [CALCULATED]
                        'Basic_Formula_Result': np.nan,  # [CALCULATED: CF × VS ÷ 10]
                        'Advanced_Formula_Result': np.nan,  # [CALCULATED: CF × VS × IDM]
                        'Subsystem_Position': np.nan,  # [EXTRACTED - ACTUAL]
                        'Formula_Match': 'UNKNOWN',  # [CALCULATED - VERIFICATION]

                        # === OTHER POSITIONS ===
                        'Portfolio_Weighted_Position': np.nan,
                        'Cash_Weight': np.nan,
                        'Cash_Allocated': np.nan,
                        'Notional_Position': np.nan
                    }

                    # 1. CLOSE PRICE [EXTRACTED]
                    try:
                        prices = self.system.rawdata.get_daily_prices(instrument)
                        if prices is not None and len(prices) > 0:
                            if final_date in prices.index:
                                row_data['Close_Price'] = prices.loc[final_date]
                            else:
                                available_dates = prices.index[prices.index <= final_date]
                                if len(available_dates) > 0:
                                    row_data['Close_Price'] = prices.loc[available_dates[-1]]
                    except:
                        pass

                    # 2. RISK WEIGHT FROM CONFIG [EXTRACTED]
                    risk_weights = getattr(self.system.config, 'instrument_weights', {})
                    row_data['Risk_Weight_Config'] = risk_weights.get(instrument, 0)

                    # 3. COMBINED FORECAST [EXTRACTED]
                    try:
                        forecast_series = self.system.combForecast.get_combined_forecast(instrument)
                        if forecast_series is not None and len(forecast_series) > 0:
                            if final_date in forecast_series.index:
                                row_data['Combined_Forecast'] = forecast_series.loc[final_date]
                            else:
                                available_dates = forecast_series.index[forecast_series.index <= final_date]
                                if len(available_dates) > 0:
                                    row_data['Combined_Forecast'] = forecast_series.loc[available_dates[-1]]
                    except:
                        pass

                    # 4. VOLATILITY CALCULATIONS [FOLLOWING PYSYSTEMTRADE METHODOLOGY] - FIXED
                    try:
                        # Method 1: Try to get daily percentage volatility from system (EXTRACTED)
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
                                # FIXED: Store both percentage and decimal forms
                                row_data['Daily_Volatility_Pct'] = daily_pct_vol  # e.g., 4.51 (means 4.51%)
                                row_data['Daily_Volatility_Decimal'] = daily_pct_vol / 100  # e.g., 0.0451

                                # FIXED: Calculate annual volatility properly
                                annual_pct_vol = daily_pct_vol * (252 ** 0.5)  # Annualize percentage
                                row_data['Annual_Volatility_Pct'] = annual_pct_vol  # e.g., 71.52 (means 71.52%)
                                row_data['Annual_Volatility_Decimal'] = annual_pct_vol / 100  # e.g., 0.7152

                        # Method 2: Manual calculation from price data (CALCULATED)
                        if pd.isna(row_data['Daily_Volatility_Pct']):
                            prices = self.system.rawdata.get_daily_prices(instrument)
                            if prices is not None and len(prices) > 35:
                                returns = prices.pct_change().dropna()
                                if len(returns) > 35:
                                    # Calculate daily volatility using pysystemtrade method (35-day EWMA)
                                    daily_vol_decimal = returns.ewm(span=35, min_periods=10).std().iloc[-1]
                                    if pd.notna(daily_vol_decimal) and daily_vol_decimal > 0:
                                        # FIXED: Convert to percentage form to match pysystemtrade
                                        row_data['Daily_Volatility_Decimal'] = daily_vol_decimal
                                        row_data['Daily_Volatility_Pct'] = daily_vol_decimal * 100  # Convert to %

                                        # Calculate annual volatility
                                        annual_vol_decimal = daily_vol_decimal * (252 ** 0.5)
                                        row_data['Annual_Volatility_Decimal'] = annual_vol_decimal
                                        row_data['Annual_Volatility_Pct'] = annual_vol_decimal * 100

                    except Exception as e:
                        print(f"⚠️ Volatility calculation failed for {instrument}: {e}")
                        pass

                    # 5. VOLATILITY SCALAR [EXTRACTED/CALCULATED] - FIXED LABELING
                    vol_scalar = None
                    vol_scalar_source = 'UNKNOWN'

                    try:
                        # Method 1: Try to extract from system (EXTRACTED)
                        vol_scalar_series = self.system.positionSize.get_volatility_scalar(instrument)
                        if vol_scalar_series is not None and len(vol_scalar_series) > 0:
                            if final_date in vol_scalar_series.index:
                                vol_scalar = vol_scalar_series.loc[final_date]
                            else:
                                available_dates = vol_scalar_series.index[vol_scalar_series.index <= final_date]
                                if len(available_dates) > 0:
                                    vol_scalar = vol_scalar_series.loc[available_dates[-1]]

                            if pd.notna(vol_scalar) and vol_scalar > 0:
                                row_data['Volatility_Scalar'] = vol_scalar
                                vol_scalar_source = 'EXTRACTED'
                    except:
                        pass

                    # Method 2: Calculate from volatility if not extracted (CALCULATED)
                    if vol_scalar is None or pd.isna(vol_scalar) or vol_scalar <= 0:
                        if pd.notna(row_data['Annual_Volatility_Decimal']) and row_data[
                            'Annual_Volatility_Decimal'] > 0:
                            # FIXED: Calculate scalar using decimal form of annual volatility
                            vol_scalar = target_vol / row_data['Annual_Volatility_Decimal']
                            row_data['Volatility_Scalar'] = vol_scalar
                            vol_scalar_source = 'CALCULATED'

                    row_data['Volatility_Scalar_Source'] = vol_scalar_source

                    # 6. IDM [EXTRACTED]
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

                    # 7. INSTRUMENT VALUE VOLATILITY [CALCULATED] - FIXED
                    try:
                        if (pd.notna(row_data['Close_Price']) and pd.notna(row_data['Daily_Volatility_Decimal'])
                                and row_data['Close_Price'] > 0 and row_data['Daily_Volatility_Decimal'] > 0):
                            # FIXED: Use decimal daily volatility for dollar volatility calculation
                            daily_price_vol = row_data['Close_Price'] * row_data['Daily_Volatility_Decimal']
                            row_data['Instrument_Value_Volatility'] = daily_price_vol
                    except:
                        pass

                    # 8. SUBSYSTEM POSITION [EXTRACTED - ACTUAL]
                    try:
                        subsystem_series = self.system.positionSize.get_subsystem_position(instrument)
                        if subsystem_series is not None and len(subsystem_series) > 0:
                            if final_date in subsystem_series.index:
                                row_data['Subsystem_Position'] = subsystem_series.loc[final_date]
                            else:
                                available_dates = subsystem_series.index[subsystem_series.index <= final_date]
                                if len(available_dates) > 0:
                                    row_data['Subsystem_Position'] = subsystem_series.loc[available_dates[-1]]
                    except:
                        pass

                    # 9. CALCULATE FORMULAS [CALCULATED]
                    cf = row_data['Combined_Forecast']
                    vs = row_data['Volatility_Scalar']
                    idm = row_data['IDM']

                    if pd.notna(cf) and pd.notna(vs):
                        # Basic Carver formula: CF × VS ÷ 10
                        row_data['Basic_Formula_Result'] = cf * vs / 10

                        if pd.notna(idm):
                            # Advanced formula with IDM: CF × VS × IDM
                            row_data['Advanced_Formula_Result'] = cf * vs * idm

                        # Check which formula matches actual position
                        actual_pos = row_data['Subsystem_Position']
                        if pd.notna(actual_pos):
                            basic_diff = abs(row_data['Basic_Formula_Result'] - actual_pos)
                            advanced_diff = abs(row_data['Advanced_Formula_Result'] - actual_pos)

                            if basic_diff < 1.0:
                                row_data['Formula_Match'] = 'BASIC (CF×VS÷10)'
                            elif advanced_diff < 1.0:
                                row_data['Formula_Match'] = 'ADVANCED (CF×VS×IDM)'
                            elif basic_diff < advanced_diff:
                                row_data['Formula_Match'] = f'BASIC CLOSER (diff: {basic_diff:.1f})'
                            else:
                                row_data['Formula_Match'] = f'ADVANCED CLOSER (diff: {advanced_diff:.1f})'

                    # 10. OTHER POSITIONS [EXTRACTED]
                    try:
                        portfolio_pos_series = self.system.portfolio.get_notional_position(instrument)
                        if portfolio_pos_series is not None and len(portfolio_pos_series) > 0:
                            if final_date in portfolio_pos_series.index:
                                row_data['Portfolio_Weighted_Position'] = portfolio_pos_series.loc[final_date]
                            else:
                                available_dates = portfolio_pos_series.index[portfolio_pos_series.index <= final_date]
                                if len(available_dates) > 0:
                                    row_data['Portfolio_Weighted_Position'] = portfolio_pos_series.loc[
                                        available_dates[-1]]
                    except:
                        pass

                    # 11. CASH WEIGHT AND ALLOCATION [CALCULATED]
                    try:
                        if (pd.notna(row_data['Risk_Weight_Config']) and row_data['Risk_Weight_Config'] > 0 and
                                pd.notna(row_data['Volatility_Scalar']) and row_data['Volatility_Scalar'] > 0):
                            # Carver method: cash_weight = risk_weight × volatility_scalar
                            fundamental_cash_weight = row_data['Risk_Weight_Config'] * row_data['Volatility_Scalar']
                            row_data['Cash_Weight'] = fundamental_cash_weight
                            row_data['Cash_Allocated'] = fundamental_cash_weight * portfolio_value
                    except:
                        pass

                    # 12. NOTIONAL POSITION
                    row_data['Notional_Position'] = row_data['Portfolio_Weighted_Position']

                    final_day_data.append(row_data)

                except Exception as e:
                    print(f"⚠️ Error processing {instrument}: {e}")
                    # Still add the instrument with basic info
                    final_day_data.append({
                        'Instrument': instrument,
                        'Date': final_date,
                        'Portfolio_Value': portfolio_value,
                        'Daily_Cash_Vol_Target': daily_cash_vol_target,
                        'Formula_Match': 'ERROR',
                        'Volatility_Scalar_Source': 'ERROR',
                        **{k: np.nan for k in ['Close_Price', 'Risk_Weight_Config', 'Daily_Volatility_Pct',
                                               'Daily_Volatility_Decimal', 'Annual_Volatility_Pct',
                                               'Annual_Volatility_Decimal',
                                               'Target_Volatility', 'Volatility_Scalar', 'Combined_Forecast', 'IDM',
                                               'Subsystem_Position', 'Portfolio_Weighted_Position', 'Cash_Weight',
                                               'Cash_Allocated', 'Notional_Position', 'Instrument_Value_Volatility',
                                               'Basic_Formula_Result', 'Advanced_Formula_Result']}
                    })

            # Create DataFrame and export to Excel
            df = pd.DataFrame(final_day_data)
            df = df.sort_values('Instrument')

            # FIXED: Updated column labels with correct volatility descriptions
            excel_column_names = {
                'Instrument': 'Instrument',
                'Date': 'Date',
                'Close_Price': 'Close_Price [EXTRACTED]',
                'Risk_Weight_Config': 'Risk_Weight_Config [EXTRACTED]',
                'Daily_Volatility_Pct': 'Daily_Volatility_Pct [CALCULATED/EXTRACTED]',  # FIXED
                'Daily_Volatility_Decimal': 'Daily_Volatility_Decimal [CALCULATED/EXTRACTED]',  # FIXED
                'Annual_Volatility_Pct': 'Annual_Volatility_Pct [CALCULATED]',  # FIXED
                'Annual_Volatility_Decimal': 'Annual_Volatility_Decimal [CALCULATED]',  # FIXED
                'Target_Volatility': 'Target_Volatility [CONFIG]',
                'Daily_Cash_Vol_Target': 'Daily_Cash_Vol_Target [CALCULATED]',
                'Portfolio_Value': 'Portfolio_Value [EXTRACTED]',
                'Combined_Forecast': 'Combined_Forecast [EXTRACTED]',
                'Volatility_Scalar': 'Volatility_Scalar [EXTRACTED/CALCULATED]',  # FIXED
                'Volatility_Scalar_Source': 'Volatility_Scalar_Source [INFO]',  # NEW
                'IDM': 'IDM [EXTRACTED]',
                'Instrument_Value_Volatility': 'Instrument_Value_Volatility [CALCULATED]',
                'Basic_Formula_Result': 'Basic_Formula_Result [CALCULATED: CF×VS÷10]',
                'Advanced_Formula_Result': 'Advanced_Formula_Result [CALCULATED: CF×VS×IDM]',
                'Subsystem_Position': 'Subsystem_Position [EXTRACTED]',
                'Formula_Match': 'Formula_Match [CALCULATED]',
                'Portfolio_Weighted_Position': 'Portfolio_Weighted_Position [EXTRACTED]',
                'Cash_Weight': 'Cash_Weight [CALCULATED]',
                'Cash_Allocated': 'Cash_Allocated [CALCULATED]',
                'Notional_Position': 'Notional_Position [EXTRACTED]'
            }

            # Rename columns for Excel export
            df_excel = df.rename(columns=excel_column_names)

            # NEW: Add leverage analysis
            print("🔄 Calculating leverage and capital multiplier metrics...")
            leverage_analysis = self.add_leverage_controls_check(self.system)

            # Export to Excel with FIXED formatting
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                workbook = writer.book

                # Main sheet with all data
                df_excel.to_excel(writer, sheet_name='Final_Day_Report', index=False)

                # Format the sheet
                worksheet = writer.sheets['Final_Day_Report']

                # Define formats
                currency_format = workbook.add_format({'num_format': '$#,##0.00'})
                percent_format = workbook.add_format({'num_format': '0.00%'})
                decimal_format = workbook.add_format({'num_format': '0.0000'})
                pct_number_format = workbook.add_format({'num_format': '0.00'})  # FIXED: For percentage numbers (71.52)
                large_number_format = workbook.add_format({'num_format': '#,##0.00'})
                date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
                highlight_format = workbook.add_format({'bg_color': '#FFFF99'})

                # Apply column formatting - FIXED
                worksheet.set_column('A:A', 12)  # Instrument
                worksheet.set_column('B:B', 12, date_format)  # Date
                worksheet.set_column('C:C', 12, currency_format)  # Close Price
                worksheet.set_column('D:D', 12, percent_format)  # Risk Weight
                worksheet.set_column('E:E', 15, pct_number_format)  # Daily Vol %
                worksheet.set_column('F:F', 15, decimal_format)  # Daily Vol Decimal
                worksheet.set_column('G:G', 15, pct_number_format)  # Annual Vol %
                worksheet.set_column('H:H', 15, decimal_format)  # Annual Vol Decimal
                worksheet.set_column('I:I', 12, percent_format)  # Target Volatility
                worksheet.set_column('J:J', 15, large_number_format)  # Daily Cash Vol Target
                worksheet.set_column('K:K', 15, currency_format)  # Portfolio Value

                # SUBSYSTEM POSITION COMPONENTS - Create combined formats for highlighting
                highlight_large_number_format = workbook.add_format({
                    'num_format': '#,##0.00',
                    'bg_color': '#FFFF99'
                })

                highlight_decimal_format = workbook.add_format({
                    'num_format': '0.0000',
                    'bg_color': '#FFFF99'
                })

                highlight_currency_format = workbook.add_format({
                    'num_format': '$#,##0.00',
                    'bg_color': '#FFFF99'
                })

                # Apply highlighted formatting correctly
                worksheet.set_column('L:L', 15, highlight_large_number_format)  # Combined Forecast
                worksheet.set_column('M:M', 15, highlight_decimal_format)  # Volatility Scalar
                worksheet.set_column('N:N', 15)  # Volatility Scalar Source
                worksheet.set_column('O:O', 12, highlight_decimal_format)  # IDM
                worksheet.set_column('P:P', 15, highlight_currency_format)  # Instrument Value Vol
                worksheet.set_column('Q:Q', 15, highlight_large_number_format)  # Basic Formula
                worksheet.set_column('R:R', 15, highlight_large_number_format)  # Advanced Formula
                worksheet.set_column('S:S', 15, large_number_format)  # Actual Subsystem Pos
                worksheet.set_column('T:T', 25)  # Formula Match

                # Other columns (no highlighting needed)
                worksheet.set_column('U:U', 15, large_number_format)  # Portfolio Weighted Position
                worksheet.set_column('V:V', 12, decimal_format)  # Cash Weight
                worksheet.set_column('W:W', 15, currency_format)  # Cash Allocated
                worksheet.set_column('X:X', 15, large_number_format)  # Notional Position

                print(f"✅ FIXED volatility final day backtest report exported: {filename}")
                print(f"📊 Processed {len(final_day_data)} instruments with corrected volatility calculations")

                # Display sample volatility values for verification - FIXED
                sample_data = df.head(3)
                print(f"🔍 Sample Volatility Values (first 3 instruments):")
                for _, row in sample_data.iterrows():
                    daily_pct = row['Daily_Volatility_Pct']
                    daily_dec = row['Daily_Volatility_Decimal']
                    annual_pct = row['Annual_Volatility_Pct']
                    annual_dec = row['Annual_Volatility_Decimal']
                    vol_source = row['Volatility_Scalar_Source']
                    print(f"  {row['Instrument']}:")
                    print(f"    Daily: {daily_pct:.2f}% = {daily_dec:.6f} decimal")
                    print(f"    Annual: {annual_pct:.2f}% = {annual_dec:.6f} decimal")
                    print(f"    Vol Scalar: {row['Volatility_Scalar']:.4f} ({vol_source})")

                # Display summary of volatility scalar sources
                vol_source_counts = df['Volatility_Scalar_Source'].value_counts()
                print(f"🔍 Volatility Scalar Sources:")
                for source, count in vol_source_counts.items():
                    print(f"  {source}: {count} instruments")

                # Display summary of formula matches
                formula_matches = df['Formula_Match'].value_counts()
                print(f"🔍 Formula Analysis Summary:")
                for formula, count in formula_matches.items():
                    print(f"  {formula}: {count} instruments")

                # NEW: Always create leverage analysis sheets
                if leverage_analysis:
                    leverage_metrics = leverage_analysis['leverage_metrics']
                    controls_status = leverage_analysis['controls_status']

                    # Create leverage summary data (your existing code)
                    leverage_summary = {
                        'Metric': [
                            'Actual Trading Capital',
                            'Total Position Value',
                            'Actual Leverage Ratio',
                            'Capital Multiplier',
                            'Risk-Adjusted Leverage',
                            'Leverage Status'
                        ],
                        'Value': [
                            f"${leverage_metrics['actual_trading_capital']:,.2f}",
                            f"${leverage_metrics['total_position_value']:,.2f}",
                            f"{leverage_metrics['actual_leverage_ratio']:.2f}x",
                            f"{leverage_metrics['capital_multiplier']:.2f}x",
                            f"{leverage_metrics['risk_leverage_ratio']:.3f}x",
                            leverage_metrics['leverage_status']
                        ]
                    }

                    leverage_df = pd.DataFrame(leverage_summary)

                    # Controls status sheet
                    controls_data = []
                    for check, status in controls_status.items():
                        controls_data.append({
                            'Control_Check': check.replace('_', ' ').title(),
                            'Status': status
                        })
                    controls_df = pd.DataFrame(controls_data)

                    # Individual instrument leverage breakdown
                    instrument_leverage_data = []
                    for instrument, data in leverage_metrics['instrument_data'].items():
                        if data['position_value'] > 100:
                            instrument_leverage_data.append({
                                'Instrument': instrument,
                                'Position_Size': data['position_size'],
                                'Current_Price': data['current_price'],
                                'Position_Value': data['position_value'],
                                'Leverage_Contribution': data['leverage_contribution'],
                                'Risk_Exposure': data['risk_exposure'],
                                'Volatility_Scalar': data['volatility_scalar']
                            })

                    if instrument_leverage_data:
                        instrument_lev_df = pd.DataFrame(instrument_leverage_data)
                    else:
                        # Create empty DataFrame with headers
                        instrument_lev_df = pd.DataFrame(columns=[
                            'Instrument', 'Position_Size', 'Current_Price', 'Position_Value',
                            'Leverage_Contribution', 'Risk_Exposure', 'Volatility_Scalar'
                        ])

                else:
                    # CREATE PLACEHOLDER SHEETS WHEN NO DATA
                    print("⚠️ No leverage analysis data - creating placeholder sheets")

                    # Create placeholder leverage summary
                    leverage_df = pd.DataFrame({
                        'Metric': [
                            'Actual Trading Capital',
                            'Total Position Value',
                            'Actual Leverage Ratio',
                            'Capital Multiplier',
                            'Risk-Adjusted Leverage',
                            'Leverage Status'
                        ],
                        'Value': ['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'NO DATA']
                    })

                    # Create empty controls DataFrame
                    controls_df = pd.DataFrame(columns=['Control_Check', 'Status'])

                    # Create empty instrument leverage DataFrame
                    instrument_lev_df = pd.DataFrame(columns=[
                        'Instrument', 'Position_Size', 'Current_Price', 'Position_Value',
                        'Leverage_Contribution', 'Risk_Exposure', 'Volatility_Scalar'
                    ])

                # ALWAYS write these sheets (moved outside the if/else)
                leverage_df.to_excel(writer, sheet_name='Leverage_Analysis', index=False)
                controls_df.to_excel(writer, sheet_name='Leverage_Controls', index=False)
                instrument_lev_df.to_excel(writer, sheet_name='Instrument_Leverage', index=False)

                print(f"✅ ENHANCED final day report with leverage controls exported: {filename}")

            return filename

        except Exception as e:
            print(f"❌ Error exporting fixed volatility final day report: {e}")
            import traceback
            traceback.print_exc()
            return None

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




