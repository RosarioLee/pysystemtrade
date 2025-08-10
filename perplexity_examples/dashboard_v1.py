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

    def export_instrument_turnover_analysis_excel(self, filename="instrument_turnover_analysis.xlsx"):
        """Export comprehensive turnover analysis for each instrument as per Robert Carver's methodology"""

        print(f"Exporting instrument turnover analysis to {filename}...")

        # Get system data
        instruments = self.system.get_instrument_list()

        if not instruments:
            print("No instruments found in system")
            return None

        # Collect turnover and trading cost data
        turnover_data = {}
        position_data = {}

        for instrument in instruments:
            try:
                print(f"Calculating turnover for {instrument}...")

                # Get position time series for turnover calculation
                subsystem_position = self.system.portfolio.get_notional_position(instrument)
                if subsystem_position is None or len(subsystem_position) == 0:
                    continue

                # Calculate average absolute position (for turnover calculation)
                avg_abs_position = abs(subsystem_position).mean()
                if avg_abs_position == 0:
                    continue

                # Calculate position changes (daily trading activity)
                position_changes = subsystem_position.diff().fillna(0)

                # Calculate turnover: sum of absolute position changes / (2 * avg_abs_position * days_per_year)
                # Division by 2 because round trip = buy + sell
                total_abs_changes = abs(position_changes).sum()
                trading_days = len(subsystem_position)
                days_per_year = 252  # Trading days per year

                # Annual turnover in round trips
                if avg_abs_position > 0:
                    annual_turnover = (total_abs_changes / (2 * avg_abs_position)) * (days_per_year / trading_days)
                else:
                    annual_turnover = 0

                # Calculate average holding period
                if annual_turnover > 0:
                    avg_holding_period_days = days_per_year / annual_turnover
                    avg_holding_period_weeks = avg_holding_period_days / 7
                else:
                    avg_holding_period_days = float('inf')
                    avg_holding_period_weeks = float('inf')

                # Get instrument P&L for performance context
                instrument_pnl = self.system.accounts.pandl_for_instrument(instrument)
                total_pnl = instrument_pnl.iloc[-1] if instrument_pnl is not None and len(instrument_pnl) > 0 else 0

                # Estimate trading costs (simplified - would need actual cost data)
                # Using rough estimates based on Robert's cost analysis
                estimated_cost_per_round_trip = self._estimate_instrument_cost(instrument)
                annual_cost_sr_units = annual_turnover * estimated_cost_per_round_trip

                # Store results
                turnover_data[instrument] = {
                    'Annual_Turnover_Roundtrips': annual_turnover,
                    'Avg_Holding_Period_Days': avg_holding_period_days if avg_holding_period_days != float(
                        'inf') else 999,
                    'Avg_Holding_Period_Weeks': avg_holding_period_weeks if avg_holding_period_weeks != float(
                        'inf') else 999,
                    'Avg_Absolute_Position': avg_abs_position,
                    'Total_Position_Changes': total_abs_changes,
                    'Trading_Days': trading_days,
                    'Estimated_Cost_SR_Units': annual_cost_sr_units,
                    'Total_PnL': total_pnl,
                    'Cost_as_Pct_PnL': (annual_cost_sr_units / abs(total_pnl) * 100) if total_pnl != 0 else 0
                }

                # Store position data for detailed analysis
                position_data[instrument] = {
                    'positions': subsystem_position,
                    'changes': position_changes
                }

            except Exception as e:
                print(f"Error processing turnover for {instrument}: {e}")
                continue

        if not turnover_data:
            print("No valid turnover data found")
            return None

        # Create Excel file with multiple sheets
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            workbook = writer.book

            # Sheet 1: Turnover Summary (Robert's key metrics)
            turnover_df = pd.DataFrame.from_dict(turnover_data, orient='index')
            turnover_df = turnover_df.sort_values('Annual_Turnover_Roundtrips', ascending=False)

            # Add Robert's speed limit analysis
            turnover_df['Speed_Assessment'] = turnover_df['Annual_Turnover_Roundtrips'].apply(self._assess_speed)
            turnover_df['Holding_Period_Category'] = turnover_df['Avg_Holding_Period_Weeks'].apply(
                self._categorize_holding_period)

            turnover_df.to_excel(writer, sheet_name='Turnover_Summary')

            # Sheet 2: Trading Frequency Analysis
            freq_analysis = self._analyze_trading_frequency(position_data)
            if freq_analysis is not None:
                freq_analysis.to_excel(writer, sheet_name='Trading_Frequency')

            # Sheet 3: Cost Analysis per Robert's methodology
            cost_df = turnover_df[['Annual_Turnover_Roundtrips', 'Estimated_Cost_SR_Units', 'Cost_as_Pct_PnL']].copy()
            cost_df['Cost_Bucket'] = cost_df['Estimated_Cost_SR_Units'].apply(self._categorize_cost)
            cost_df.to_excel(writer, sheet_name='Cost_Analysis')

            # Sheet 4: Position Change Patterns
            change_patterns = self._analyze_position_patterns(position_data)
            if change_patterns is not None:
                change_patterns.to_excel(writer, sheet_name='Position_Patterns')

            # Add formatting
            self._format_turnover_sheets(writer, workbook)

        print(f"✅ Turnover analysis exported: {filename}")
        print(f"📊 Key metrics: Turnover, Holding Periods, Trading Costs, Speed Assessment")

        return filename

    def _estimate_instrument_cost(self, instrument):
        """Estimate cost per round trip based on instrument type (simplified)"""
        # These are rough estimates based on Robert's cost analysis in his books
        # In practice, you'd want to get actual broker costs

        if 'future' in instrument.lower() or instrument in ['ES', 'NQ', 'YM']:  # Futures
            return 0.002  # Very cheap futures
        elif any(etf in instrument for etf in ['SPY', 'IVV', 'VTI']):  # Major ETFs
            return 0.08  # ETF costs per Robert's estimates
        else:
            return 0.01  # Mid-range assumption

    def _assess_speed(self, turnover):
        """Assess trading speed against Robert's guidelines"""
        if turnover > 50:
            return "TOO_FAST - Exceeds speed limit"
        elif turnover > 20:
            return "FAST - Monitor costs carefully"
        elif turnover > 5:
            return "MODERATE - Reasonable pace"
        elif turnover > 1:
            return "SLOW - Long-term holding"
        else:
            return "VERY_SLOW - Almost buy-and-hold"

    def _categorize_holding_period(self, weeks):
        """Categorize holding periods as per Robert's framework"""
        if weeks < 2:
            return "SHORT_TERM - High frequency"
        elif weeks < 8:
            return "MEDIUM_TERM - Monthly rebalancing"
        elif weeks < 26:
            return "LONG_TERM - Quarterly changes"
        else:
            return "VERY_LONG_TERM - Annual or longer"

    def _categorize_cost(self, cost_sr):
        """Categorize costs against Robert's speed limits"""
        if cost_sr > 0.13:
            return "EXCESSIVE - Above speed limit"
        elif cost_sr > 0.08:
            return "HIGH - Near speed limit"
        elif cost_sr > 0.04:
            return "MODERATE - Acceptable"
        else:
            return "LOW - Very efficient"

    def _analyze_trading_frequency(self, position_data):
        """Analyze how often each instrument trades"""
        try:
            freq_data = {}

            for instrument, data in position_data.items():
                changes = data['changes']

                # Count trading days
                trading_days = (changes != 0).sum()
                total_days = len(changes)

                # Calculate frequency metrics
                freq_data[instrument] = {
                    'Trading_Days': trading_days,
                    'Total_Days': total_days,
                    'Trading_Frequency_Pct': (trading_days / total_days) * 100 if total_days > 0 else 0,
                    'Days_Between_Trades': total_days / trading_days if trading_days > 0 else total_days,
                    'Max_Position_Change': abs(changes).max(),
                    'Avg_Position_Change': abs(changes[changes != 0]).mean() if trading_days > 0 else 0
                }

            return pd.DataFrame.from_dict(freq_data, orient='index')
        except:
            return None

    def _analyze_position_patterns(self, position_data):
        """Analyze position change patterns"""
        try:
            pattern_data = {}

            for instrument, data in position_data.items():
                changes = data['changes']
                positions = data['positions']

                # Analyze patterns
                positive_changes = (changes > 0).sum()
                negative_changes = (changes < 0).sum()
                zero_changes = (changes == 0).sum()

                pattern_data[instrument] = {
                    'Increases': positive_changes,
                    'Decreases': negative_changes,
                    'No_Change': zero_changes,
                    'Net_Direction_Bias': (positive_changes - negative_changes) / len(changes) * 100,
                    'Position_Volatility': positions.std(),
                    'Max_Position': positions.max(),
                    'Min_Position': positions.min(),
                    'Position_Range': positions.max() - positions.min()
                }

            return pd.DataFrame.from_dict(pattern_data, orient='index')
        except:
            return None

    def _format_turnover_sheets(self, writer, workbook):
        """Format the turnover analysis sheets"""
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })

        # Format sheets
        for sheet_name in ['Turnover_Summary', 'Trading_Frequency', 'Cost_Analysis', 'Position_Patterns']:
            if sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                worksheet.set_column('A:A', 12)  # Instrument names
                worksheet.set_column('B:Z', 15)  # Data columns

