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

    def export_trading_rule_analysis_excel(self, filename="trading_rule_analysis.xlsx"):
        """Export comprehensive trading rule analysis following Robert Carver's methodology"""

        print(f"Exporting trading rule analysis to {filename}...")

        # Get system data with proper error handling
        instruments = self.system.get_instrument_list()

        # Get rules
        try:
            rules_dict = self.system.rules.trading_rules()
            rules = list(rules_dict.keys())
            print(f"Found rules: {rules}")
        except Exception as e:
            print(f"Error getting trading rules: {e}")
            return None

        if not rules:
            print("No trading rules found in system")
            return None

        print(f"Analyzing {len(rules)} trading rules across {len(instruments)} instruments...")

        # Ensure system is fully processed
        self._ensure_system_processed()

        # Collect rule performance data
        rule_data = {}
        rule_returns_data = {}

        # NEW: Collect rule turnover data
        rule_turnover_data = {}

        for rule_name in rules:
            try:
                print(f"Processing rule: {rule_name}")

                # Get rule performance
                rule_returns = self._get_rule_aggregate_returns(rule_name, instruments)

                if rule_returns is None or len(rule_returns) < 50:
                    print(f"Insufficient data for rule {rule_name}")
                    continue

                # Calculate rule performance metrics
                annual_return = rule_returns.mean() * 252
                annual_vol = rule_returns.std() * (252 ** 0.5)
                sharpe_ratio = annual_return / annual_vol if annual_vol > 0 else 0

                # Drawdown calculation
                cumulative = (1 + rule_returns).cumprod()
                rolling_max = cumulative.cummax()
                drawdown = (cumulative - rolling_max) / rolling_max
                max_drawdown = drawdown.min()

                # Additional metrics
                win_rate = (rule_returns > 0).mean()
                skewness = rule_returns.skew()
                kurtosis = rule_returns.kurtosis()

                # Store rule performance data
                rule_data[rule_name] = {
                    'Annual_Return': annual_return,
                    'Annual_Volatility': annual_vol,
                    'Sharpe_Ratio': sharpe_ratio,
                    'Max_Drawdown': max_drawdown,
                    'Win_Rate': win_rate,
                    'Skewness': skewness,
                    'Kurtosis': kurtosis,
                    'Data_Points': len(rule_returns),
                    'Start_Date': rule_returns.index[0],
                    'End_Date': rule_returns.index[-1]
                }

                rule_returns_data[rule_name] = rule_returns

                # NEW: Calculate rule turnover
                rule_turnover_metrics = self._calculate_rule_turnover(rule_name, instruments)
                if rule_turnover_metrics:
                    rule_turnover_data[rule_name] = rule_turnover_metrics

                print(f"✅ Successfully processed rule {rule_name} (Sharpe: {sharpe_ratio:.3f})")

            except Exception as e:
                print(f"Error processing rule {rule_name}: {e}")
                continue

        if not rule_data:
            print("ERROR: No valid rule data could be extracted")
            return None

        # Create Enhanced Excel file with turnover analysis
        self._create_enhanced_rule_excel_output(filename, rule_data, rule_returns_data, rule_turnover_data)

        print(f"✅ Trading rule analysis exported: {filename}")
        print(f"📊 Rules analyzed: {len(rule_data)}")

        return filename

    def _calculate_rule_turnover(self, rule_name, instruments):
        """Calculate turnover metrics for a specific trading rule"""

        try:
            print(f"Calculating turnover for rule: {rule_name}")

            rule_forecast_changes = []
            total_instruments = 0
            successful_instruments = 0

            for instrument in instruments[:15]:  # Limit to first 15 for performance
                try:
                    # Get raw forecasts for this rule and instrument
                    forecast = self.system.rules.get_raw_forecast(instrument, rule_name)

                    if forecast is None or len(forecast) < 100:
                        continue

                    # Calculate forecast changes (this represents trading activity)
                    forecast_changes = forecast.diff().fillna(0)

                    # Calculate average absolute forecast (for normalization)
                    avg_abs_forecast = abs(forecast).mean()

                    if avg_abs_forecast > 0:
                        # Calculate rule-specific turnover metrics
                        total_abs_changes = abs(forecast_changes).sum()
                        trading_days = len(forecast)

                        # Normalize by average forecast size and calculate annual turnover
                        normalized_changes = total_abs_changes / avg_abs_forecast
                        annual_turnover = (normalized_changes / trading_days) * 252

                        rule_forecast_changes.append({
                            'instrument': instrument,
                            'annual_turnover': annual_turnover,
                            'avg_abs_forecast': avg_abs_forecast,
                            'total_changes': total_abs_changes,
                            'trading_days': trading_days
                        })

                        successful_instruments += 1

                    total_instruments += 1

                except Exception as e:
                    continue

            if not rule_forecast_changes:
                return None

            # Aggregate turnover across instruments
            avg_annual_turnover = np.mean([item['annual_turnover'] for item in rule_forecast_changes])
            max_annual_turnover = np.max([item['annual_turnover'] for item in rule_forecast_changes])
            min_annual_turnover = np.min([item['annual_turnover'] for item in rule_forecast_changes])

            # Calculate average holding period
            if avg_annual_turnover > 0:
                avg_holding_period_days = 252 / avg_annual_turnover
                avg_holding_period_weeks = avg_holding_period_days / 7
            else:
                avg_holding_period_days = 999
                avg_holding_period_weeks = 999

            # Estimate costs based on Robert's framework
            estimated_cost_per_change = self._estimate_rule_cost(rule_name)
            annual_cost_sr_units = avg_annual_turnover * estimated_cost_per_change

            return {
                'Avg_Annual_Turnover': avg_annual_turnover,
                'Max_Annual_Turnover': max_annual_turnover,
                'Min_Annual_Turnover': min_annual_turnover,
                'Avg_Holding_Period_Days': avg_holding_period_days,
                'Avg_Holding_Period_Weeks': avg_holding_period_weeks,
                'Successful_Instruments': successful_instruments,
                'Total_Instruments_Tested': total_instruments,
                'Estimated_Annual_Cost_SR': annual_cost_sr_units,
                'Speed_Assessment': self._assess_rule_speed(avg_annual_turnover),
                'Cost_Category': self._categorize_rule_cost(annual_cost_sr_units)
            }

        except Exception as e:
            print(f"Error calculating turnover for rule {rule_name}: {e}")
            return None

    def _estimate_rule_cost(self, rule_name):
        """Estimate cost per forecast change based on rule type"""
        # Based on Robert Carver's cost analysis in his books

        if 'ewmac' in rule_name.lower():
            # EWMAC rules tend to be smoother, lower cost per change
            if '2_8' in rule_name or '4_16' in rule_name:
                return 0.005  # Very fast EWMAC
            elif '8_32' in rule_name or '16_64' in rule_name:
                return 0.003  # Medium EWMAC
            else:
                return 0.002  # Slow EWMAC

        elif 'breakout' in rule_name.lower():
            # Breakout rules tend to be more binary, higher cost per change
            return 0.008

        elif 'carry' in rule_name.lower():
            # Carry rules are typically slow
            return 0.001

        else:
            # Default assumption
            return 0.004

    def _assess_rule_speed(self, annual_turnover):
        """Assess rule speed against Robert's guidelines"""
        if annual_turnover > 100:
            return "EXCESSIVE - Way too fast"
        elif annual_turnover > 50:
            return "TOO_FAST - Exceeds speed limit"
        elif annual_turnover > 20:
            return "FAST - Monitor costs carefully"
        elif annual_turnover > 5:
            return "MODERATE - Good systematic pace"
        elif annual_turnover > 1:
            return "SLOW - Long-term approach"
        else:
            return "VERY_SLOW - Almost static"

    def _categorize_rule_cost(self, cost_sr):
        """Categorize rule costs against Robert's speed limits"""
        if cost_sr > 0.15:
            return "EXCESSIVE - Unprofitable"
        elif cost_sr > 0.10:
            return "HIGH - Near speed limit"
        elif cost_sr > 0.05:
            return "MODERATE - Acceptable"
        else:
            return "LOW - Very efficient"

    def _create_enhanced_rule_excel_output(self, filename, rule_data, rule_returns_data, rule_turnover_data):
        """Create enhanced Excel output with rule analysis including turnover"""

        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            workbook = writer.book

            # Sheet 1: Rule Performance Summary
            rule_summary_df = pd.DataFrame.from_dict(rule_data, orient='index')
            rule_summary_df = rule_summary_df.sort_values('Sharpe_Ratio', ascending=False)
            rule_summary_df.to_excel(writer, sheet_name='Rule_Performance')

            # Sheet 2: NEW - Rule Turnover Analysis
            if rule_turnover_data:
                turnover_df = pd.DataFrame.from_dict(rule_turnover_data, orient='index')
                turnover_df = turnover_df.sort_values('Avg_Annual_Turnover', ascending=False)
                turnover_df.to_excel(writer, sheet_name='Rule_Turnover')

            # Sheet 3: Combined Performance + Turnover Analysis
            if rule_turnover_data:
                combined_data = {}
                for rule_name in rule_data.keys():
                    if rule_name in rule_turnover_data:
                        combined_data[rule_name] = {
                            **rule_data[rule_name],
                            **rule_turnover_data[rule_name]
                        }

                if combined_data:
                    combined_df = pd.DataFrame.from_dict(combined_data, orient='index')
                    combined_df = combined_df.sort_values('Sharpe_Ratio', ascending=False)
                    combined_df.to_excel(writer, sheet_name='Combined_Analysis')

            # Sheet 4: Rule Speed vs Performance Analysis
            if rule_turnover_data:
                speed_analysis = self._create_speed_performance_analysis(rule_data, rule_turnover_data)
                if speed_analysis is not None:
                    speed_analysis.to_excel(writer, sheet_name='Speed_vs_Performance')

            # Sheet 5: Rule Returns Time Series
            if rule_returns_data:
                rule_ts_df = pd.DataFrame.from_dict(rule_returns_data, orient='columns')
                rule_ts_df.to_excel(writer, sheet_name='Rule_Returns')

            # Sheet 6: Rule Correlations
            if len(rule_returns_data) >= 2:
                rule_corr_df = pd.DataFrame.from_dict(rule_returns_data, orient='columns').corr()
                rule_corr_df.to_excel(writer, sheet_name='Rule_Correlations')

    def _create_speed_performance_analysis(self, rule_data, rule_turnover_data):
        """Create analysis showing relationship between rule speed and performance"""

        try:
            analysis_data = {}

            for rule_name in rule_data.keys():
                if rule_name in rule_turnover_data:
                    analysis_data[rule_name] = {
                        'Sharpe_Ratio': rule_data[rule_name]['Sharpe_Ratio'],
                        'Annual_Return': rule_data[rule_name]['Annual_Return'],
                        'Annual_Turnover': rule_turnover_data[rule_name]['Avg_Annual_Turnover'],
                        'Holding_Period_Days': rule_turnover_data[rule_name]['Avg_Holding_Period_Days'],
                        'Estimated_Cost': rule_turnover_data[rule_name]['Estimated_Annual_Cost_SR'],
                        'Net_Sharpe': rule_data[rule_name]['Sharpe_Ratio'] - rule_turnover_data[rule_name][
                            'Estimated_Annual_Cost_SR'],
                        'Efficiency_Ratio': rule_data[rule_name]['Sharpe_Ratio'] / rule_turnover_data[rule_name][
                            'Avg_Annual_Turnover'] if rule_turnover_data[rule_name]['Avg_Annual_Turnover'] > 0 else 0,
                        'Rule_Category': rule_name.split('_')[0] if '_' in rule_name else rule_name
                    }

            return pd.DataFrame.from_dict(analysis_data, orient='index')

        except:
            return None

    def _ensure_system_processed(self):
        """Ensure system has completed all processing before rule extraction"""
        try:
            print("Ensuring system components are fully processed...")

            # Force calculation of key system components
            instruments = self.system.get_instrument_list()[:3]  # Test with first 3
            rules = list(self.system.rules.trading_rules().keys())[:2]  # First 2 rules

            for instrument in instruments:
                for rule_name in rules:
                    try:
                        # Try to access forecast scalars
                        _ = self.system.forecastScaleCap.get_forecast_scalar(instrument, rule_name)
                        # Try to access forecasts
                        _ = self.system.rules.get_raw_forecast(instrument, rule_name)
                    except:
                        continue

            print("✅ System processing verification complete")

        except Exception as e:
            print(f"Warning: System processing check failed: {e}")

    def _get_rule_aggregate_returns(self, rule_name, instruments):
        """Alternative method to get rule performance across instruments"""

        rule_returns_by_instrument = []
        successful_instruments = 0

        # Try multiple approaches to get rule data
        for instrument in instruments[:10]:  # Limit to first 10 instruments

            # Method 1: Try pandl_for_trading_rule
            try:
                rule_pnl = self.system.accounts.pandl_for_trading_rule(instrument, rule_name)
                if rule_pnl is not None and len(rule_pnl) > 50:
                    # Convert to returns
                    starting_capital = 100000  # Use fixed capital base
                    capital_curve = starting_capital + rule_pnl
                    returns = capital_curve.pct_change().dropna()

                    if len(returns) > 0 and not returns.isna().all():
                        rule_returns_by_instrument.append(returns)
                        successful_instruments += 1
                        continue
            except:
                pass

            # Method 2: Try using forecasts and instrument returns
            try:
                forecast = self.system.rules.get_raw_forecast(instrument, rule_name)
                instrument_returns = self._get_instrument_returns(instrument)

                if forecast is not None and instrument_returns is not None:
                    if len(forecast) > 50 and len(instrument_returns) > 50:
                        # Align data
                        aligned_data = pd.DataFrame({
                            'forecast': forecast,
                            'returns': instrument_returns
                        }).dropna()

                        if len(aligned_data) > 50:
                            # Calculate rule returns as forecast * instrument_returns
                            rule_returns = (aligned_data['forecast'] / 10.0) * aligned_data['returns']
                            rule_returns_by_instrument.append(rule_returns)
                            successful_instruments += 1
            except:
                pass

        print(f"Rule {rule_name}: Successfully processed {successful_instruments} instruments")

        if not rule_returns_by_instrument:
            return None

        # Combine returns across instruments (equal weight)
        combined_df = pd.concat(rule_returns_by_instrument, axis=1).fillna(0)
        aggregate_returns = combined_df.mean(axis=1)

        return aggregate_returns

    def _get_instrument_returns(self, instrument):
        """Get basic instrument returns"""
        try:
            prices = self.system.rawdata.get_daily_prices(instrument)
            if prices is not None and len(prices) > 1:
                returns = prices.pct_change().dropna()
                return returns
        except:
            pass
        return None

    def _create_rule_excel_output(self, filename, rule_data, rule_returns_data):
        """Create Excel output with rule analysis"""

        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            # Rule Summary Sheet
            rule_summary_df = pd.DataFrame.from_dict(rule_data, orient='index')
            rule_summary_df = rule_summary_df.sort_values('Sharpe_Ratio', ascending=False)
            rule_summary_df.to_excel(writer, sheet_name='Rule_Summary')

            # Rule Returns Time Series
            if rule_returns_data:
                rule_ts_df = pd.DataFrame.from_dict(rule_returns_data, orient='columns')
                rule_ts_df.to_excel(writer, sheet_name='Rule_Returns')

            # Rule Correlations
            if len(rule_returns_data) >= 2:
                rule_corr_df = pd.DataFrame.from_dict(rule_returns_data, orient='columns').corr()
                rule_corr_df.to_excel(writer, sheet_name='Rule_Correlations')

    def _grade_rule_performance(self, sharpe_ratio):
        """Grade rule performance based on Robert Carver's criteria"""
        if sharpe_ratio > 0.5:
            return "EXCELLENT - Strong standalone performance"
        elif sharpe_ratio > 0.3:
            return "GOOD - Solid contribution"
        elif sharpe_ratio > 0.1:
            return "ACCEPTABLE - Diversification value"
        elif sharpe_ratio > 0:
            return "WEAK - Consider removal"
        else:
            return "POOR - Remove from system"

    def _assess_diversification_value(self, sharpe_ratio, consistency):
        """Assess rule's diversification value following Robert's framework"""
        if sharpe_ratio > 0.3 and consistency > 0.5:
            return "HIGH - Good performance and stable"
        elif sharpe_ratio > 0.1 and consistency > 0.3:
            return "MEDIUM - Decent diversification benefit"
        elif sharpe_ratio > 0:
            return "LOW - Minimal benefit"
        else:
            return "NEGATIVE - Hurts portfolio"

    def _create_rule_instrument_matrix(self, rule_instrument_performance, rules, instruments):
        """Create matrix showing rule performance by instrument"""
        try:
            matrix_data = {}

            for rule_name in rules:
                if rule_name in rule_instrument_performance:
                    rule_sharpes = {}

                    for instrument in instruments:
                        if instrument in rule_instrument_performance[rule_name]:
                            returns = rule_instrument_performance[rule_name][instrument]
                            if len(returns) > 50:
                                annual_return = returns.mean() * 252
                                annual_vol = returns.std() * (252 ** 0.5)
                                sharpe = annual_return / annual_vol if annual_vol > 0 else 0
                                rule_sharpes[instrument] = sharpe
                            else:
                                rule_sharpes[instrument] = np.nan
                        else:
                            rule_sharpes[instrument] = np.nan

                    matrix_data[rule_name] = rule_sharpes

            return pd.DataFrame.from_dict(matrix_data, orient='index')
        except:
            return None

    def _analyze_rule_stability(self, rule_returns_data):
        """Analyze rule stability over time"""
        try:
            stability_data = {}

            for rule_name, returns in rule_returns_data.items():
                if len(returns) < 500:  # Need sufficient data
                    continue

                # Calculate rolling metrics
                window = 252  # 1 year
                rolling_sharpe = returns.rolling(window).apply(
                    lambda x: (x.mean() / x.std()) * (252 ** 0.5) if x.std() > 0 else 0
                ).dropna()

                rolling_vol = returns.rolling(window).std() * (252 ** 0.5)

                # Stability metrics
                stability_data[rule_name] = {
                    'Sharpe_Mean': rolling_sharpe.mean(),
                    'Sharpe_Std': rolling_sharpe.std(),
                    'Sharpe_Min': rolling_sharpe.min(),
                    'Sharpe_Max': rolling_sharpe.max(),
                    'Vol_Mean': rolling_vol.mean(),
                    'Vol_Std': rolling_vol.std(),
                    'Stability_Score': 1 / rolling_sharpe.std() if rolling_sharpe.std() > 0 else 0,
                    'Periods_Positive_Sharpe': (rolling_sharpe > 0).sum(),
                    'Total_Periods': len(rolling_sharpe)
                }

            return pd.DataFrame.from_dict(stability_data, orient='index')
        except:
            return None

    def _calculate_rule_attribution(self, rule_data, rule_returns_data):
        """Calculate rule attribution to portfolio performance"""
        try:
            attribution_data = {}

            # Calculate total portfolio return as benchmark
            if len(rule_returns_data) > 1:
                combined_df = pd.DataFrame.from_dict(rule_returns_data, orient='columns')
                portfolio_returns = combined_df.mean(axis=1)  # Equal weight
                portfolio_sharpe = (portfolio_returns.mean() / portfolio_returns.std()) * (252 ** 0.5)

                for rule_name, rule_metrics in rule_data.items():
                    if rule_name in rule_returns_data:
                        rule_sharpe = rule_metrics['Sharpe_Ratio']

                        # Calculate marginal contribution
                        marginal_contribution = rule_sharpe - portfolio_sharpe

                        # Calculate percentage contribution to total return
                        rule_annual_return = rule_metrics['Annual_Return']
                        total_return = sum([metrics['Annual_Return'] for metrics in rule_data.values()])
                        return_contribution = (rule_annual_return / total_return) * 100 if total_return != 0 else 0

                        attribution_data[rule_name] = {
                            'Rule_Sharpe': rule_sharpe,
                            'Portfolio_Sharpe': portfolio_sharpe,
                            'Marginal_Contribution': marginal_contribution,
                            'Return_Contribution_Pct': return_contribution,
                            'Recommendation': self._get_rule_recommendation(marginal_contribution, rule_sharpe)
                        }

            return pd.DataFrame.from_dict(attribution_data, orient='index')
        except:
            return None

    def _get_rule_recommendation(self, marginal_contribution, rule_sharpe):
        """Get recommendation for rule based on Robert's framework"""
        if marginal_contribution > 0.1 and rule_sharpe > 0.3:
            return "INCREASE WEIGHT - Strong contributor"
        elif marginal_contribution > 0 and rule_sharpe > 0.1:
            return "MAINTAIN - Good diversifier"
        elif marginal_contribution > -0.1 and rule_sharpe > 0:
            return "MONITOR - Marginal value"
        else:
            return "CONSIDER REMOVAL - Negative impact"

    def _format_rule_analysis_sheets(self, writer, workbook):
        """Format the rule analysis sheets"""
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })

        excellent_format = workbook.add_format({'bg_color': '#90EE90'})  # Light green
        good_format = workbook.add_format({'bg_color': '#FFE4B5'})  # Light orange
        poor_format = workbook.add_format({'bg_color': '#FFB6C1'})  # Light red

        # Format Rule_Summary sheet
        if 'Rule_Summary' in writer.sheets:
            worksheet = writer.sheets['Rule_Summary']
            worksheet.set_column('A:A', 15)  # Rule names
            worksheet.set_column('B:Z', 12)  # Data columns

    def export_weights_and_multipliers_excel(self, filename="system_weights_multipliers_analysis.xlsx"):
        """Export instrument weights, forecast weights, and diversification multipliers over time"""

        print(f"Exporting weights and multipliers analysis to {filename}...")

        try:
            # Get system data
            instruments = self.system.get_instrument_list()
            rules = list(self.system.rules.trading_rules().keys())

            print(f"Extracting data for {len(instruments)} instruments and {len(rules)} trading rules...")

            # Extract time series data
            weights_data = {}

            print("1. Extracting instrument weights...")
            instrument_weights_ts = self._extract_instrument_weights(instruments)
            if instrument_weights_ts is not None:
                weights_data['instrument_weights'] = instrument_weights_ts

            print("2. Extracting forecast weights...")
            forecast_weights_ts = self._extract_forecast_weights(instruments, rules)
            if forecast_weights_ts is not None:
                weights_data['forecast_weights'] = forecast_weights_ts

            print("3. Extracting instrument diversification multiplier...")
            idm_ts = self._extract_instrument_diversification_multiplier()
            if idm_ts is not None:
                weights_data['idm'] = idm_ts

            print("4. Extracting forecast diversification multipliers...")
            fdm_ts = self._extract_forecast_diversification_multipliers(instruments)
            if fdm_ts is not None:
                weights_data['fdm'] = fdm_ts

            if not weights_data:
                print("No weights/multipliers data could be extracted")
                return None

            # Create Excel file with multiple sheets
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                workbook = writer.book

                # Sheet 1: Instrument Weights Over Time
                if 'instrument_weights' in weights_data:
                    weights_data['instrument_weights'].to_excel(writer, sheet_name='Instrument_Weights')
                    self._format_weights_sheet(writer, workbook, 'Instrument_Weights',
                                               'Instrument Weights Over Time')

                # Sheet 2: Forecast Weights Over Time (by instrument)
                if 'forecast_weights' in weights_data:
                    # Create separate sheets for each instrument's forecast weights
                    for instrument in instruments[:10]:  # Limit to first 10 for readability
                        if instrument in weights_data['forecast_weights']:
                            fw_data = weights_data['forecast_weights'][instrument]
                            if fw_data is not None and len(fw_data) > 0:
                                sheet_name = f'FW_{instrument}'[:31]  # Excel sheet name limit
                                fw_data.to_excel(writer, sheet_name=sheet_name)
                                self._format_weights_sheet(writer, workbook, sheet_name,
                                                           f'Forecast Weights - {instrument}')

                    # Summary sheet with latest forecast weights for all instruments
                    fw_summary = self._create_forecast_weights_summary(weights_data['forecast_weights'])
                    if fw_summary is not None:
                        fw_summary.to_excel(writer, sheet_name='Forecast_Weights_Latest')
                        self._format_weights_sheet(writer, workbook, 'Forecast_Weights_Latest',
                                                   'Latest Forecast Weights by Instrument')

                # Sheet 3: Instrument Diversification Multiplier
                if 'idm' in weights_data:
                    idm_df = pd.DataFrame({'IDM': weights_data['idm']})
                    idm_df.to_excel(writer, sheet_name='IDM_Over_Time')
                    self._format_weights_sheet(writer, workbook, 'IDM_Over_Time',
                                               'Instrument Diversification Multiplier')

                # Sheet 4: Forecast Diversification Multipliers
                if 'fdm' in weights_data:
                    for instrument in list(weights_data['fdm'].keys())[:10]:  # First 10 instruments
                        fdm_data = weights_data['fdm'][instrument]
                        if fdm_data is not None and len(fdm_data) > 0:
                            sheet_name = f'FDM_{instrument}'[:31]
                            fdm_df = pd.DataFrame({f'FDM_{instrument}': fdm_data})
                            fdm_df.to_excel(writer, sheet_name=sheet_name)
                            self._format_weights_sheet(writer, workbook, sheet_name,
                                                       f'Forecast Diversification Multiplier - {instrument}')

                # Sheet 5: Summary Statistics
                summary_stats = self._create_weights_summary_stats(weights_data)
                if summary_stats is not None:
                    summary_stats.to_excel(writer, sheet_name='Summary_Statistics')
                    self._format_weights_sheet(writer, workbook, 'Summary_Statistics',
                                               'Weights and Multipliers Summary')

                # Sheet 6: Parameter Evolution Analysis
                evolution_analysis = self._analyze_parameter_evolution(weights_data)
                if evolution_analysis is not None:
                    evolution_analysis.to_excel(writer, sheet_name='Parameter_Evolution')
                    self._format_weights_sheet(writer, workbook, 'Parameter_Evolution',
                                               'Parameter Evolution Analysis')

            print(f"✅ Weights and multipliers analysis exported: {filename}")
            return filename

        except Exception as e:
            print(f"Error exporting weights and multipliers: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _extract_instrument_weights(self, instruments):
        """Extract instrument weights time series"""
        try:
            # Try to get instrument weights over time
            instrument_weights = self.system.portfolio.get_instrument_weights()

            if instrument_weights is not None:
                print(f"   Found instrument weights with {len(instrument_weights)} time points")
                return instrument_weights
            else:
                print("   No instrument weights time series found")
                return None

        except Exception as e:
            print(f"   Error extracting instrument weights: {e}")
            return None

    def _extract_forecast_weights(self, instruments, rules):
        """Extract forecast weights time series for each instrument"""
        try:
            forecast_weights_data = {}

            for instrument in instruments:
                try:
                    # Get forecast weights for this instrument
                    fw = self.system.combForecast.get_forecast_weights(instrument)

                    if fw is not None and len(fw) > 0:
                        forecast_weights_data[instrument] = fw
                        print(f"   Found forecast weights for {instrument}: {len(fw)} time points")
                    else:
                        print(f"   No forecast weights found for {instrument}")

                except Exception as e:
                    print(f"   Error getting forecast weights for {instrument}: {e}")
                    continue

            return forecast_weights_data if forecast_weights_data else None

        except Exception as e:
            print(f"   Error extracting forecast weights: {e}")
            return None

    def _extract_instrument_diversification_multiplier(self):
        """Extract instrument diversification multiplier over time"""
        try:
            # Get IDM time series
            idm = self.system.portfolio.get_instrument_diversification_multiplier()

            if idm is not None:
                print(f"   Found IDM with {len(idm)} time points")
                return idm
            else:
                print("   No IDM time series found")
                return None

        except Exception as e:
            print(f"   Error extracting IDM: {e}")
            return None

    def _extract_forecast_diversification_multipliers(self, instruments):
        """Extract forecast diversification multipliers for each instrument"""
        try:
            fdm_data = {}

            for instrument in instruments:
                try:
                    # Get FDM for this instrument
                    fdm = self.system.combForecast.get_forecast_diversification_multiplier(instrument)

                    if fdm is not None and len(fdm) > 0:
                        fdm_data[instrument] = fdm
                        print(f"   Found FDM for {instrument}: {len(fdm)} time points")
                    else:
                        print(f"   No FDM found for {instrument}")

                except Exception as e:
                    print(f"   Error getting FDM for {instrument}: {e}")
                    continue

            return fdm_data if fdm_data else None

        except Exception as e:
            print(f"   Error extracting FDMs: {e}")
            return None

    def _create_forecast_weights_summary(self, forecast_weights_data):
        """Create summary of latest forecast weights for all instruments"""
        try:
            summary_data = {}

            for instrument, fw_ts in forecast_weights_data.items():
                if fw_ts is not None and len(fw_ts) > 0:
                    # Get latest weights
                    latest_weights = fw_ts.iloc[-1]
                    summary_data[instrument] = latest_weights

            if summary_data:
                return pd.DataFrame.from_dict(summary_data, orient='index')
            return None

        except Exception as e:
            print(f"Error creating forecast weights summary: {e}")
            return None

    def _create_weights_summary_stats(self, weights_data):
        """Create summary statistics for weights and multipliers"""
        try:
            stats_data = {}

            # Instrument weights stats
            if 'instrument_weights' in weights_data:
                iw = weights_data['instrument_weights']
                for col in iw.columns:
                    stats_data[f'IW_{col}_Mean'] = iw[col].mean()
                    stats_data[f'IW_{col}_Std'] = iw[col].std()
                    stats_data[f'IW_{col}_Min'] = iw[col].min()
                    stats_data[f'IW_{col}_Max'] = iw[col].max()

            # IDM stats
            if 'idm' in weights_data:
                idm = weights_data['idm']
                stats_data['IDM_Mean'] = idm.mean()
                stats_data['IDM_Std'] = idm.std()
                stats_data['IDM_Min'] = idm.min()
                stats_data['IDM_Max'] = idm.max()

            # FDM stats (aggregate across instruments)
            if 'fdm' in weights_data:
                all_fdm = []
                for instrument, fdm_ts in weights_data['fdm'].items():
                    if fdm_ts is not None:
                        all_fdm.extend(fdm_ts.values)

                if all_fdm:
                    stats_data['FDM_Mean'] = np.mean(all_fdm)
                    stats_data['FDM_Std'] = np.std(all_fdm)
                    stats_data['FDM_Min'] = np.min(all_fdm)
                    stats_data['FDM_Max'] = np.max(all_fdm)

            if stats_data:
                return pd.DataFrame.from_dict({'Value': stats_data}, orient='columns')
            return None

        except Exception as e:
            print(f"Error creating summary stats: {e}")
            return None

    def _analyze_parameter_evolution(self, weights_data):
        """Analyze how parameters evolve over time"""
        try:
            evolution_data = {}

            # Analyze instrument weight changes
            if 'instrument_weights' in weights_data:
                iw = weights_data['instrument_weights']

                # Calculate rolling standard deviation to measure stability
                for col in iw.columns:
                    rolling_std = iw[col].rolling(window=252).std()  # 1-year window
                    evolution_data[f'IW_{col}_Rolling_Volatility'] = rolling_std.iloc[-1] if len(
                        rolling_std) > 0 else np.nan

                # Weight concentration (how concentrated the weights are)
                latest_weights = iw.iloc[-1]
                concentration = (latest_weights ** 2).sum()  # Herfindahl index
                evolution_data['Weight_Concentration_Index'] = concentration

            # Analyze IDM evolution
            if 'idm' in weights_data:
                idm = weights_data['idm']

                # Trend analysis
                if len(idm) > 252:
                    recent_idm = idm.iloc[-252:].mean()  # Last year average
                    older_idm = idm.iloc[-504:-252].mean() if len(idm) > 504 else idm.iloc[:-252].mean()
                    evolution_data['IDM_Trend'] = (recent_idm - older_idm) / older_idm if older_idm != 0 else 0

                evolution_data['IDM_Current'] = idm.iloc[-1]

            if evolution_data:
                return pd.DataFrame.from_dict({'Value': evolution_data}, orient='columns')
            return None

        except Exception as e:
            print(f"Error analyzing parameter evolution: {e}")
            return None

    def _format_weights_sheet(self, writer, workbook, sheet_name, title):
        """Format weights and multipliers sheets"""
        try:
            if sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]

                # Define formats
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'fg_color': '#D7E4BC',
                    'border': 1
                })

                # Add title
                worksheet.write('A1', title, header_format)

                # Set column widths
                worksheet.set_column('A:A', 15)  # Date column
                worksheet.set_column('B:Z', 12)  # Data columns

        except Exception as e:
            print(f"Error formatting sheet {sheet_name}: {e}")

    def verify_instrument_weight_estimation(self, system, save_to_file=True):
        """Verify whether instrument weight estimation is actually working"""

        print("=== VERIFYING INSTRUMENT WEIGHT ESTIMATION ===")

        verification_results = {
            'config_settings': {},
            'actual_behavior': {},
            'weight_analysis': {},
            'conclusion': None
        }

        try:
            # Check configuration settings
            config = system.config
            verification_results['config_settings'] = {
                'use_instrument_weight_estimates': getattr(config, 'use_instrument_weight_estimates', 'NOT SET'),
                'has_instrument_weights_config': hasattr(config, 'instrument_weights'),
                'has_instruments_list': hasattr(config, 'instruments'),
                'instrument_count': len(system.get_instrument_list())
            }

            print(
                f"Config use_instrument_weight_estimates: {verification_results['config_settings']['use_instrument_weight_estimates']}")
            print(
                f"Has instrument_weights in config: {verification_results['config_settings']['has_instrument_weights_config']}")
            print(f"Has instruments list in config: {verification_results['config_settings']['has_instruments_list']}")

            # Get actual weights over time
            try:
                actual_weights_ts = system.portfolio.get_instrument_weights()
                if actual_weights_ts is not None and len(actual_weights_ts) > 0:
                    print(f"✅ Successfully extracted instrument weights time series: {len(actual_weights_ts)} periods")

                    # Analyze weight behavior
                    latest_weights = actual_weights_ts.iloc[-1]
                    earliest_weights = actual_weights_ts.iloc[0]

                    # Check if weights are changing over time (estimation indicator)
                    weight_changes = abs(latest_weights - earliest_weights)
                    max_change = weight_changes.max()
                    instruments_changed = (weight_changes > 0.01).sum()  # 1% threshold

                    verification_results['weight_analysis'] = {
                        'max_weight_change': max_change,
                        'instruments_with_changes': instruments_changed,
                        'total_instruments': len(latest_weights),
                        'latest_weights': latest_weights.to_dict(),
                        'earliest_weights': earliest_weights.to_dict(),
                        'weight_sum_latest': latest_weights.sum(),
                        'weight_sum_earliest': earliest_weights.sum()
                    }

                    print(f"Weight analysis:")
                    print(f"  Max weight change over time: {max_change:.4f}")
                    print(f"  Instruments with >1% change: {instruments_changed}/{len(latest_weights)}")
                    print(f"  Weight sum (latest): {latest_weights.sum():.4f}")

                    # Check if weights match your config weights
                    if hasattr(config, 'instrument_weights'):
                        config_weights = config.instrument_weights
                        instruments_in_both = set(latest_weights.index) & set(config_weights.keys())

                        if instruments_in_both:
                            config_vals = [config_weights[inst] for inst in instruments_in_both]
                            actual_vals = [latest_weights[inst] for inst in instruments_in_both]

                            # Normalize config weights to sum to 1 for comparison
                            config_sum = sum(config_vals)
                            normalized_config = [w / config_sum for w in config_vals]

                            differences = [abs(a - c) for a, c in zip(actual_vals, normalized_config)]
                            max_diff = max(differences) if differences else 0

                            verification_results['weight_analysis']['config_vs_actual_max_diff'] = max_diff
                            print(f"  Max difference vs config weights: {max_diff:.4f}")

                            if max_diff < 0.001:
                                verification_results['conclusion'] = "USING_CONFIG_WEIGHTS"
                                print("❌ CONCLUSION: System is using config weights, not estimates")
                            else:
                                verification_results['conclusion'] = "USING_ESTIMATES"
                                print("✅ CONCLUSION: System appears to be using weight estimates")
                        else:
                            verification_results['conclusion'] = "UNCLEAR_NO_OVERLAP"
                            print("⚠️ CONCLUSION: Cannot compare - no instrument overlap")
                    else:
                        verification_results['conclusion'] = "NO_CONFIG_WEIGHTS"
                        print("ℹ️ No config weights to compare against")

                else:
                    print("❌ Failed to extract instrument weights time series")
                    verification_results['actual_behavior']['weights_extraction'] = "FAILED"

            except Exception as e:
                print(f"❌ Error extracting weights: {e}")
                verification_results['actual_behavior']['weights_error'] = str(e)

            # Save results to file
            if save_to_file:
                import json
                with open("instrument_weight_verification.json", "w") as f:
                    # Convert numpy types to regular Python types for JSON serialization
                    def convert_numpy(obj):
                        if hasattr(obj, 'item'):
                            return obj.item()
                        elif hasattr(obj, 'tolist'):
                            return obj.tolist()
                        return obj

                    json_results = {}
                    for key, value in verification_results.items():
                        if isinstance(value, dict):
                            json_results[key] = {k: convert_numpy(v) for k, v in value.items()}
                        else:
                            json_results[key] = convert_numpy(value)

                    json.dump(json_results, f, indent=2, default=str)
                print("📁 Verification results saved to: instrument_weight_verification.json")

            return verification_results

        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return None

    def export_instrument_volatility_analysis_excel(self, filename="instrument_volatility_analysis.xlsx"):
        """Export detailed instrument volatility analysis used for position sizing"""

        print(f"Exporting instrument volatility analysis to {filename}...")

        # Get system data
        instruments = self.system.get_instrument_list()

        if not instruments:
            print("No instruments found in system")
            return None

        # Collect volatility data
        volatility_data = {}
        raw_volatility_series = {}

        for instrument in instruments:
            try:
                print(f"Analyzing volatility for {instrument}...")

                # FIXED METHOD 1: Try multiple approaches to get system volatility
                actual_instrument_vol = None
                vol_scalar_ts = None

                # Approach 1: Try volatility scalar (original method)
                try:
                    vol_scalar = self.system.positionSize.get_volatility_scalar(instrument)
                    if vol_scalar is not None and len(vol_scalar) > 0:
                        latest_vol_scalar = vol_scalar.iloc[-1]
                        if latest_vol_scalar != 0:
                            actual_instrument_vol = 1 / latest_vol_scalar
                            vol_scalar_ts = vol_scalar
                            print(f"   Method 1 SUCCESS: volatility scalar = {actual_instrument_vol:.4f}")
                except Exception as e:
                    print(f"   Method 1 failed: {e}")

                # Approach 2: Try instrument value volatility directly
                if actual_instrument_vol is None:
                    try:
                        instrument_vol = self.system.positionSize.get_instrument_value_vol(instrument)
                        if instrument_vol is not None and len(instrument_vol) > 0:
                            # This gives daily vol in price units, convert to percentage
                            prices = self.system.rawdata.get_daily_prices(instrument)
                            if prices is not None and len(prices) > 0:
                                # Convert to annual percentage volatility
                                daily_price_vol = instrument_vol.iloc[-1]
                                latest_price = prices.iloc[-1]
                                daily_pct_vol = daily_price_vol / latest_price
                                actual_instrument_vol = daily_pct_vol * (252 ** 0.5)
                                print(f"   Method 2 SUCCESS: instrument value vol = {actual_instrument_vol:.4f}")
                    except Exception as e:
                        print(f"   Method 2 failed: {e}")

                # Approach 3: Calculate from raw price data (fallback)
                if actual_instrument_vol is None:
                    try:
                        prices = self.system.rawdata.get_daily_prices(instrument)
                        if prices is not None and len(prices) > 252:  # Need sufficient data
                            returns = prices.pct_change().dropna()
                            # Use recent volatility (last 252 days)
                            recent_returns = returns.iloc[-252:]
                            daily_vol = recent_returns.std()
                            actual_instrument_vol = daily_vol * (252 ** 0.5)
                            print(f"   Method 3 SUCCESS: calculated from prices = {actual_instrument_vol:.4f}")
                    except Exception as e:
                        print(f"   Method 3 failed: {e}")

                # If all methods failed, skip this instrument
                if actual_instrument_vol is None or actual_instrument_vol == 0:
                    print(f"   ❌ Could not extract volatility for {instrument}")
                    continue

                # Method 2: Calculate volatility manually for verification (keep existing code)
                try:
                    prices = self.system.rawdata.get_daily_prices(instrument)
                    if prices is not None and len(prices) > 50:
                        returns = prices.pct_change().dropna()

                        # Calculate different volatility measures
                        daily_vol = returns.std()
                        annual_vol_manual = daily_vol * (252 ** 0.5)

                        # Rolling volatilities
                        rolling_vol_30d = returns.rolling(30).std() * (252 ** 0.5)
                        rolling_vol_252d = returns.rolling(252).std() * (252 ** 0.5)

                        # Latest values
                        current_30d_vol = rolling_vol_30d.iloc[-1] if len(rolling_vol_30d) > 0 else 0
                        current_252d_vol = rolling_vol_252d.iloc[-1] if len(rolling_vol_252d) > 0 else 0

                    else:
                        annual_vol_manual = 0
                        current_30d_vol = 0
                        current_252d_vol = 0
                        daily_vol = 0
                except Exception as e:
                    print(f"   Error calculating manual volatility for {instrument}: {e}")
                    annual_vol_manual = 0
                    current_30d_vol = 0
                    current_252d_vol = 0
                    daily_vol = 0

                # Get instrument weights for context
                try:
                    instrument_weights = self.system.portfolio.get_instrument_weights()
                    if instrument_weights is not None and instrument in instrument_weights.columns:
                        latest_cash_weight = instrument_weights[instrument].iloc[-1]
                    else:
                        latest_cash_weight = 0
                except:
                    latest_cash_weight = 0

                # Get risk weight from config (if available)
                try:
                    config_weight = getattr(self.system.config, 'instrument_weights', {}).get(instrument, 0)
                except:
                    config_weight = 0

                # Calculate scaling factor
                target_vol = 0.12  # 12% target
                scaling_factor = target_vol / actual_instrument_vol if actual_instrument_vol > 0 else 0

                # Store comprehensive volatility data
                volatility_data[instrument] = {
                    'System_Used_Vol_Annual': actual_instrument_vol,
                    'Manual_Calc_Vol_Annual': annual_vol_manual,
                    'Rolling_30d_Vol': current_30d_vol,
                    'Rolling_252d_Vol': current_252d_vol,
                    'Daily_Vol_Raw': daily_vol,
                    'Target_Vol': target_vol,
                    'Vol_Scaling_Factor': scaling_factor,
                    'Config_Risk_Weight': config_weight,
                    'Actual_Cash_Weight': latest_cash_weight,
                    'Weight_Ratio': latest_cash_weight / config_weight if config_weight > 0 else 0,
                    'Vol_Calculation_Method': 'System_Volatility_Scalar' if vol_scalar_ts is not None else 'Manual_Calculation',
                    'Data_Points_Used': len(vol_scalar_ts) if vol_scalar_ts is not None else len(
                        prices) if 'prices' in locals() else 0
                }

                print(f"   ✅ {instrument}: System Vol = {actual_instrument_vol:.1%}, Scaling = {scaling_factor:.2f}x")

            except Exception as e:
                print(f"   ❌ Error processing {instrument}: {e}")
                continue

        if not volatility_data:
            print("No valid volatility data found")
            return None

        # Create Excel file with multiple sheets
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            workbook = writer.book

            # Sheet 1: Volatility Summary
            vol_summary_df = pd.DataFrame.from_dict(volatility_data, orient='index')
            vol_summary_df = vol_summary_df.sort_values('Vol_Scaling_Factor', ascending=False)

            # Format percentages
            percentage_cols = ['System_Used_Vol_Annual', 'Manual_Calc_Vol_Annual', 'Rolling_30d_Vol',
                               'Rolling_252d_Vol', 'Daily_Vol_Raw', 'Target_Vol']
            for col in percentage_cols:
                if col in vol_summary_df.columns:
                    vol_summary_df[f'{col}_Formatted'] = vol_summary_df[col].apply(lambda x: f"{x:.2%}")

            vol_summary_df.to_excel(writer, sheet_name='Volatility_Summary')

            # Sheet 2: Volatility Time Series
            if raw_volatility_series:
                vol_ts_df = pd.DataFrame.from_dict(raw_volatility_series, orient='columns')
                vol_ts_df.to_excel(writer, sheet_name='Volatility_TimeSeries')

            # Sheet 3: Weight Explanation Analysis
            explanation_data = {}
            for instrument, data in volatility_data.items():
                if data['Config_Risk_Weight'] > 0 and data['System_Used_Vol_Annual'] > 0:
                    expected_cash_weight = data['Config_Risk_Weight'] * data['Vol_Scaling_Factor']
                    explanation_data[instrument] = {
                        'Risk_Weight_Config': data['Config_Risk_Weight'],
                        'System_Volatility': data['System_Used_Vol_Annual'],
                        'Target_Volatility': data['Target_Vol'],
                        'Volatility_Scaling': data['Vol_Scaling_Factor'],
                        'Expected_Cash_Weight': expected_cash_weight,
                        'Actual_Cash_Weight': data['Actual_Cash_Weight'],
                        'Weight_Difference': abs(expected_cash_weight - data['Actual_Cash_Weight']),
                        'Explanation': self._explain_weight_conversion(
                            data['Config_Risk_Weight'],
                            data['System_Used_Vol_Annual'],
                            data['Target_Vol'],
                            data['Actual_Cash_Weight']
                        )
                    }

            if explanation_data:
                explanation_df = pd.DataFrame.from_dict(explanation_data, orient='index')
                explanation_df.to_excel(writer, sheet_name='Weight_Conversion_Analysis')

            # Sheet 4: Volatility Statistics
            vol_stats = self._calculate_volatility_statistics(volatility_data)
            if vol_stats is not None:
                vol_stats.to_excel(writer, sheet_name='Volatility_Statistics')

            # Add formatting
            self._format_volatility_sheets(writer, workbook)

        print(f"✅ Instrument volatility analysis exported: {filename}")
        print(f"📊 Key insights: Volatility periods, scaling factors, weight conversions")

        return filename

    def _explain_weight_conversion(self, risk_weight, instrument_vol, target_vol, actual_cash_weight):
        """Provide human-readable explanation of weight conversion"""

        scaling_factor = target_vol / instrument_vol if instrument_vol > 0 else 0
        expected_weight = risk_weight * scaling_factor

        if instrument_vol < target_vol * 0.5:  # Very low volatility
            return f"LOW_VOL: {instrument_vol:.1%} vol needs {scaling_factor:.1f}x more capital to reach {target_vol:.0%} target"
        elif instrument_vol > target_vol * 1.5:  # High volatility
            return f"HIGH_VOL: {instrument_vol:.1%} vol needs {scaling_factor:.2f}x less capital to reach {target_vol:.0%} target"
        else:
            return f"NORMAL_VOL: {instrument_vol:.1%} vol close to {target_vol:.0%} target, scaling {scaling_factor:.2f}x"

    def _calculate_volatility_statistics(self, volatility_data):
        """Calculate portfolio-wide volatility statistics"""

        try:
            vol_values = [data['System_Used_Vol_Annual'] for data in volatility_data.values() if
                          data['System_Used_Vol_Annual'] > 0]

            if not vol_values:
                return None

            stats = {
                'Portfolio_Avg_Volatility': np.mean(vol_values),
                'Portfolio_Median_Volatility': np.median(vol_values),
                'Portfolio_Min_Volatility': np.min(vol_values),
                'Portfolio_Max_Volatility': np.max(vol_values),
                'Portfolio_Vol_Std': np.std(vol_values),
                'Low_Vol_Instruments': sum(1 for v in vol_values if v < 0.08),
                'High_Vol_Instruments': sum(1 for v in vol_values if v > 0.18),
                'Target_Vol': 0.12,
                'Instruments_Below_Target': sum(1 for v in vol_values if v < 0.12),
                'Instruments_Above_Target': sum(1 for v in vol_values if v > 0.12)
            }

            return pd.DataFrame.from_dict({'Value': stats}, orient='columns')

        except Exception as e:
            print(f"Error calculating volatility statistics: {e}")
            return None

    def _format_volatility_sheets(self, writer, workbook):
        """Format volatility analysis sheets"""

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })

        percentage_format = workbook.add_format({'num_format': '0.00%'})

        # Format sheets
        for sheet_name in ['Volatility_Summary', 'Weight_Conversion_Analysis', 'Volatility_Statistics']:
            if sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                worksheet.set_column('A:A', 12)  # Instrument names
                worksheet.set_column('B:Z', 15)  # Data columns

    def verify_risk_to_cash_conversion(self, system):
        """Verify risk-to-cash weight conversion - FIXED VERSION"""
        print("=== VERIFYING RISK-TO-CASH WEIGHT CONVERSION ===")

        try:
            # Get actual instrument weights from system
            actual_weights = None

            # Try multiple methods to get weights
            try:
                actual_weights = system.portfolio.get_instrument_weights()
            except AttributeError:
                try:
                    actual_weights = system.portfolio.get_raw_instrument_weights()
                except AttributeError:
                    print("❌ Cannot access instrument weights from system")
                    return None

            if actual_weights is None or len(actual_weights) == 0:
                print("❌ No instrument weights available")
                return None

            latest_weights = actual_weights.iloc[-1]

            # Get config risk weights
            config_weights = getattr(system.config, 'instrument_weights', {})
            if not config_weights:
                print("❌ No config weights found")
                return None

            # Get volatility data and perform verification
            verification_results = {}
            total_discrepancy = 0

            print("\n📊 RISK WEIGHT → CASH WEIGHT CONVERSION CHECK:")
            print("=" * 80)
            print(
                f"{'Instrument':<8} {'Risk%':<8} {'Vol':<8} {'Scaling':<8} {'Expected%':<10} {'Actual%':<10} {'Match?':<8}")
            print("=" * 80)

            for instrument in system.get_instrument_list()[:10]:
                if instrument in config_weights and instrument in latest_weights.index:

                    # Get instrument volatility using multiple methods
                    instrument_vol = None

                    # Method 1: Try to get volatility through price data
                    try:
                        prices = system.rawdata.get_daily_prices(instrument)
                        if prices is not None and len(prices) > 100:
                            returns = prices.pct_change().dropna()
                            daily_vol = returns.std()
                            instrument_vol = daily_vol * (252 ** 0.5)  # Annualize
                    except Exception:
                        pass

                    # Method 2: Try system volatility methods
                    if instrument_vol is None:
                        try:
                            vol_data = system.rawdata.get_daily_returns_volatility(instrument)
                            if vol_data is not None and len(vol_data) > 0:
                                instrument_vol = vol_data.iloc[-1] * (252 ** 0.5)
                        except Exception:
                            pass

                    if instrument_vol is None or instrument_vol <= 0:
                        continue

                    # Calculate expected cash weight
                    risk_weight = config_weights[instrument]
                    target_vol = 0.12  # 12% annual target
                    vol_scaling = target_vol / instrument_vol

                    # Normalize risk weights to sum to 1
                    total_risk_weight = sum(config_weights.values())
                    normalized_risk_weight = risk_weight / total_risk_weight

                    # Expected cash weight (before IDM adjustment)
                    expected_cash_weight = normalized_risk_weight * vol_scaling

                    # Actual cash weight from system
                    actual_cash_weight = latest_weights[instrument]

                    # Check if they match (allowing for IDM adjustments)
                    discrepancy = abs(expected_cash_weight - actual_cash_weight)
                    total_discrepancy += discrepancy

                    # Determine match status
                    match_status = "✅ YES" if discrepancy < 0.05 else "❌ NO"
                    if 0.02 < discrepancy < 0.05:
                        match_status = "⚠️ CLOSE"

                    verification_results[instrument] = {
                        'risk_weight': risk_weight,
                        'instrument_vol': instrument_vol,
                        'vol_scaling': vol_scaling,
                        'expected_cash_weight': expected_cash_weight,
                        'actual_cash_weight': actual_cash_weight,
                        'discrepancy': discrepancy,
                        'match': match_status
                    }

                    print(
                        f"{instrument:<8} {risk_weight:<8.3f} {instrument_vol:<8.1%} {vol_scaling:<8.2f} {expected_cash_weight:<10.3f} {actual_cash_weight:<10.3f} {match_status:<8}")

            print("=" * 80)
            print(f"Total discrepancy across instruments: {total_discrepancy:.4f}")

            # Overall assessment
            if total_discrepancy < 0.1:
                print("✅ CONVERSION WORKING CORRECTLY - Small discrepancies likely due to IDM adjustments")
            elif total_discrepancy < 0.2:
                print("⚠️ CONVERSION MOSTLY WORKING - Some discrepancies may need investigation")
            else:
                print("❌ CONVERSION NOT WORKING - Major discrepancies detected")

            return verification_results

        except Exception as e:
            print(f"❌ Verification failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def verify_position_sizing_pipeline(self, system):
        """Verify the complete position sizing pipeline"""

        print("=== VERIFYING POSITION SIZING PIPELINE ===")

        sample_instruments = system.get_instrument_list()[:5]

        for instrument in sample_instruments:
            print(f"\n--- {instrument} Position Sizing Pipeline ---")

            try:
                # Step 1: Get combined forecast
                forecast = system.combForecast.get_combined_forecast(instrument)
                latest_forecast = forecast.iloc[-1] if len(forecast) > 0 else 0
                print(f"1. Combined Forecast: {latest_forecast:.2f}")

                # Step 2: Get volatility scalar
                vol_scalar = system.positionSize.get_volatility_scalar(instrument)
                latest_vol_scalar = vol_scalar.iloc[-1] if len(vol_scalar) > 0 else 0
                print(f"2. Volatility Scalar: {latest_vol_scalar:.4f}")

                # Step 3: Get instrument weight
                instr_weights = system.portfolio.get_instrument_weights()
                latest_weight = instr_weights[instrument].iloc[-1] if instrument in instr_weights.columns else 0
                print(f"3. Instrument Weight: {latest_weight:.4f}")

                # Step 4: Get IDM
                idm = system.portfolio.get_instrument_diversification_multiplier()
                latest_idm = idm.iloc[-1] if len(idm) > 0 else 1.0
                print(f"4. IDM: {latest_idm:.4f}")

                # Step 5: Get final position
                position = system.portfolio.get_notional_position(instrument)
                latest_position = position.iloc[-1] if len(position) > 0 else 0
                print(f"5. Final Position: {latest_position:.2f}")

                # Calculate expected position manually
                expected_position = latest_forecast * latest_vol_scalar * latest_weight * latest_idm
                print(f"6. Expected Position: {expected_position:.2f}")

                # Check if they match
                position_match = abs(latest_position - expected_position) < 1.0
                print(f"7. Position Match: {'✅ YES' if position_match else '❌ NO'}")

            except Exception as e:
                print(f"❌ Error checking {instrument}: {e}")

    def check_weight_evolution(self, system):
        """Check if weights evolve as expected over time"""

        print("=== CHECKING WEIGHT EVOLUTION ===")

        try:
            # Get instrument weights time series
            weights_ts = system.portfolio.get_instrument_weights()
            if weights_ts is None or len(weights_ts) < 100:
                print("❌ Insufficient weight history")
                return None

            # Check if weights are static (bad) or dynamic (good)
            sample_instruments = list(weights_ts.columns)[:5]

            for instrument in sample_instruments:
                weight_series = weights_ts[instrument]

                # Calculate weight volatility
                weight_std = weight_series.std()
                weight_range = weight_series.max() - weight_series.min()

                print(f"{instrument}:")
                print(f"  Weight Std: {weight_std:.4f}")
                print(f"  Weight Range: {weight_range:.4f}")

                # Weights should change over time due to volatility targeting
                if weight_std > 0.001:
                    print(f"  Status: ✅ DYNAMIC (volatility targeting working)")
                else:
                    print(f"  Status: ❌ STATIC (volatility targeting may not be working)")

        except Exception as e:
            print(f"❌ Weight evolution check failed: {e}")

    def diagnose_volatility_targeting_failure(self, system):
        """Diagnose why volatility targeting is not working"""

        print("=== VOLATILITY TARGETING FAILURE DIAGNOSIS ===")

        # Test each component of the position sizing pipeline
        test_instrument = system.get_instrument_list()[0]

        try:
            # 1. Check volatility scalar
            vol_scalar = system.positionSize.get_volatility_scalar(test_instrument)
            if vol_scalar is None or len(vol_scalar) == 0:
                print("❌ ISSUE: Volatility scalars not calculated")
                return "VOLATILITY_SCALAR_FAILURE"
            else:
                print(f"✅ Volatility scalar working: {vol_scalar.iloc[-1]:.4f}")

            # 2. Check IDM
            idm = system.portfolio.get_instrument_diversification_multiplier()
            if idm is None or len(idm) == 0:
                print("❌ ISSUE: IDM not calculated")
                return "IDM_FAILURE"
            else:
                print(f"✅ IDM working: {idm.iloc[-1]:.4f}")

            # 3. Check if system is using estimated weights
            config = system.config
            if hasattr(config, 'use_instrument_weight_estimates'):
                if config.use_instrument_weight_estimates:
                    print("⚠️ WARNING: Using estimated weights - should be False")
                else:
                    print("✅ Using fixed risk weights (correct)")

            # 4. Check volatility target
            vol_target = getattr(config, 'percentage_vol_target', None)
            print(f"Volatility target: {vol_target}%")

            # 5. Test complete position sizing chain
            forecast = system.combForecast.get_combined_forecast(test_instrument)
            position = system.portfolio.get_notional_position(test_instrument)

            if forecast is not None and position is not None:
                print("✅ Complete position sizing chain working")
                return "PIPELINE_WORKING_BUT_WEIGHTS_WRONG"
            else:
                print("❌ ISSUE: Position sizing pipeline broken")
                return "PIPELINE_FAILURE"

        except Exception as e:
            print(f"❌ DIAGNOSIS FAILED: {e}")
            return "DIAGNOSIS_ERROR"



    def debug_volatility_calculation(self, system):
        """Debug volatility calculation issues"""
        print("=== DEBUGGING VOLATILITY CALCULATIONS ===")

        instruments = system.get_instrument_list()
        issues_found = []

        for instrument in instruments[:10]:  # Test first 10
            try:
                # Test volatility scalar calculation
                vol_scalar = self._get_instrument_volatility_scalar_fixed(system, instrument)

                if vol_scalar is None or len(vol_scalar) == 0:
                    print(f"❌ {instrument}: No volatility scalar")
                    issues_found.append(f"{instrument}: No volatility scalar")
                elif vol_scalar.iloc[-1] <= 0:
                    print(f"❌ {instrument}: Invalid volatility scalar: {vol_scalar.iloc[-1]}")
                    issues_found.append(f"{instrument}: Invalid volatility scalar")
                elif vol_scalar.iloc[-1] > 100:  # Unreasonably high
                    print(f"⚠️ {instrument}: Very high volatility scalar: {vol_scalar.iloc[-1]}")
                    issues_found.append(f"{instrument}: Extreme volatility scalar")
                else:
                    print(f"✅ {instrument}: Valid volatility scalar: {vol_scalar.iloc[-1]:.4f}")

            except Exception as e:
                print(f"❌ {instrument}: Volatility calculation failed: {e}")
                issues_found.append(f"{instrument}: Calculation failed - {e}")

        return issues_found

    def debug_idm_calculation(self, system):
        """Debug IDM calculation issues"""
        print("=== DEBUGGING IDM CALCULATIONS ===")

        try:
            # Test IDM calculation
            idm = system.portfolio.get_instrument_diversification_multiplier()

            if idm is None or len(idm) == 0:
                print("❌ IDM calculation failed completely")
                return ["IDM calculation failed"]

            latest_idm = idm.iloc[-1]
            print(f"✅ IDM calculation successful: {latest_idm:.4f}")

            # Check correlation matrix
            try:
                corr_matrix = system.portfolio.get_instrument_correlation_matrix()
                print(f"✅ Correlation matrix shape: {corr_matrix.shape}")

                # Check if matrix is invertible
                import numpy as np
                det = np.linalg.det(corr_matrix.values)
                print(f"✅ Correlation matrix determinant: {det:.6f}")

                if abs(det) < 1e-10:
                    print("⚠️ WARNING: Correlation matrix near-singular")
                    return ["Correlation matrix near-singular"]

            except Exception as e:
                print(f"❌ Correlation matrix issue: {e}")
                return [f"Correlation matrix error: {e}"]

            return []  # No issues

        except Exception as e:
            print(f"❌ IDM calculation failed: {e}")
            return [f"IDM calculation error: {e}"]

    def verify_conversion_prerequisites(self, system):
        """Check all prerequisites for risk-to-cash conversion"""
        print("=== CHECKING CONVERSION PREREQUISITES ===")

        instruments = system.get_instrument_list()
        issues = []

        for instrument in instruments[:10]:
            # Check price data
            try:
                prices = system.rawdata.get_daily_prices(instrument)
                if prices is None or len(prices) < 100:
                    issues.append(
                        f"{instrument}: Insufficient price data ({len(prices) if prices is not None else 0} days)")
                    print(f"❌ {instrument}: Insufficient price data")
                    continue
            except:
                issues.append(f"{instrument}: Cannot access price data")
                continue

            # Check returns data
            try:
                returns = prices.pct_change().dropna()
                if len(returns) == 0 or returns.std() == 0:
                    issues.append(f"{instrument}: Invalid returns data")
                    print(f"❌ {instrument}: Invalid returns data")
                    continue
            except:
                issues.append(f"{instrument}: Cannot calculate returns")
                continue

            print(f"✅ {instrument}: Data quality OK")

        # Check overall system health
        try:
            portfolio = system.accounts.portfolio()
            if portfolio is None:
                issues.append("Portfolio calculation failed")
                print("❌ Portfolio calculation failed")
        except:
            issues.append("Portfolio access failed")
            print("❌ Portfolio access failed")

        return issues

    def force_system_recalculation(self, system):
        """Force recalculation of all system components"""
        print("=== FORCING SYSTEM RECALCULATION ===")

        try:
            instruments = system.get_instrument_list()

            # ✅ SAFE CACHE HANDLING - Replace the broken section with this:
            try:
                # Try to clear cache safely if it exists and has the right methods
                if hasattr(system, 'cache') and hasattr(system.cache, 'delete_all_items'):
                    system.cache.delete_all_items()
                    print("✅ Cleared system cache safely")
                else:
                    print("ℹ️ Cache not accessible or doesn't support clearing")
            except Exception as cache_error:
                print(f"⚠️ Cache clearing failed (non-critical): {cache_error}")

            # Force volatility recalculation
            print("Forcing volatility calculations...")
            for instrument in instruments[:10]:
                try:
                    _ = system.rawdata.daily_returns_volatility(instrument)
                    _ = system.positionSize.get_volatility_scalar(instrument)
                except:
                    continue

            # Force portfolio recalculation
            print("Forcing portfolio calculations...")
            try:
                _ = system.portfolio.get_instrument_correlation_matrix()
                _ = system.portfolio.get_instrument_diversification_multiplier()
                _ = system.portfolio.get_instrument_weights()
                print("✅ System recalculation completed")
                return True
            except Exception as e:
                print(f"❌ Portfolio recalculation failed: {e}")
                return False

        except Exception as e:
            print(f"❌ System recalculation failed: {e}")
            return False

    def comprehensive_weight_diagnosis(self, system):
        """Run comprehensive diagnosis of weight conversion issues"""
        print("=== COMPREHENSIVE WEIGHT CONVERSION DIAGNOSIS ===")

        diagnosis_results = {
            'volatility_issues': [],
            'idm_issues': [],
            'prerequisite_issues': [],
            'root_cause': None,
            'recommended_fix': None
        }

        # Step 1: Check prerequisites
        print("\n1. Checking data prerequisites...")
        prereq_issues = self.verify_conversion_prerequisites(system)
        diagnosis_results['prerequisite_issues'] = prereq_issues

        # Step 2: Check volatility calculations
        print("\n2. Checking volatility calculations...")
        vol_issues = self.debug_volatility_calculation(system)
        diagnosis_results['volatility_issues'] = vol_issues

        # Step 3: Check IDM calculations
        print("\n3. Checking IDM calculations...")
        idm_issues = self.debug_idm_calculation(system)
        diagnosis_results['idm_issues'] = idm_issues

        # Step 4: Determine root cause
        print("\n4. Analyzing root cause...")

        if prereq_issues:
            diagnosis_results['root_cause'] = "DATA_QUALITY_ISSUES"
            diagnosis_results['recommended_fix'] = "Fix data quality issues first"
        elif vol_issues:
            diagnosis_results['root_cause'] = "VOLATILITY_CALCULATION_FAILURE"
            diagnosis_results['recommended_fix'] = "Force system recalculation or check volatility settings"
        elif idm_issues:
            diagnosis_results['root_cause'] = "IDM_CALCULATION_FAILURE"
            diagnosis_results['recommended_fix'] = "Check correlation matrix or disable IDM temporarily"
        else:
            diagnosis_results['root_cause'] = "UNKNOWN_SYSTEM_ISSUE"
            diagnosis_results['recommended_fix'] = "Manual intervention required"

        # Step 5: Display results
        print(f"\n=== DIAGNOSIS COMPLETE ===")
        print(f"Root Cause: {diagnosis_results['root_cause']}")
        print(f"Recommended Fix: {diagnosis_results['recommended_fix']}")

        return diagnosis_results

    # Add this method to SimpleETFDashboard class in dashboard_v1.py

    def export_diagnostic_report_excel(self, filename, diagnosis_results, conversion_results):
        """Export comprehensive diagnostic report to Excel"""
        print(f"Exporting diagnostic report to {filename}...")

        try:
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                workbook = writer.book

                # Sheet 1: Diagnosis Summary
                summary_data = {
                    'Component': ['Data Prerequisites', 'Volatility Calculations', 'IDM Calculations', 'Root Cause',
                                  'Recommended Fix'],
                    'Status': [
                        'ISSUES FOUND' if diagnosis_results['prerequisite_issues'] else 'OK',
                        'ISSUES FOUND' if diagnosis_results['volatility_issues'] else 'OK',
                        'ISSUES FOUND' if diagnosis_results['idm_issues'] else 'OK',
                        diagnosis_results['root_cause'],
                        diagnosis_results['recommended_fix']
                    ]
                }

                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Diagnosis_Summary', index=False)

                # Sheet 2: Detailed Issues
                if diagnosis_results['prerequisite_issues']:
                    issues_df = pd.DataFrame({'Prerequisite_Issues': diagnosis_results['prerequisite_issues']})
                    issues_df.to_excel(writer, sheet_name='Prerequisite_Issues', index=False)

                if diagnosis_results['volatility_issues']:
                    vol_issues_df = pd.DataFrame({'Volatility_Issues': diagnosis_results['volatility_issues']})
                    vol_issues_df.to_excel(writer, sheet_name='Volatility_Issues', index=False)

                if diagnosis_results['idm_issues']:
                    idm_issues_df = pd.DataFrame({'IDM_Issues': diagnosis_results['idm_issues']})
                    idm_issues_df.to_excel(writer, sheet_name='IDM_Issues', index=False)

                # Sheet 3: Weight Conversion Results
                if conversion_results:
                    conversion_df = pd.DataFrame.from_dict(conversion_results, orient='index')
                    conversion_df.to_excel(writer, sheet_name='Weight_Conversion_Check')

            print(f"✅ Diagnostic report exported: {filename}")
            return filename

        except Exception as e:
            print(f"Error exporting diagnostic report: {e}")
            return None

    def safe_system_restart(self, system):
        """Safely restart system calculations without breaking cache"""
        print("=== SAFE SYSTEM RESTART ===")

        try:
            instruments = system.get_instrument_list()[:5]  # Test with first 5

            # Method 1: Force fresh calculations by accessing end-to-end pipeline
            print("Method 1: Forcing end-to-end calculations...")
            for instrument in instruments:
                try:
                    # This forces the entire calculation chain
                    _ = system.accounts.pandl_for_instrument(instrument)
                    print(f"✅ {instrument}: Full pipeline working")
                except Exception as e:
                    print(f"⚠️ {instrument}: Pipeline issue: {e}")

            # Method 2: Verify system health
            print("Method 2: Verifying system health...")
            try:
                portfolio = system.accounts.portfolio()
                if portfolio is not None and len(portfolio.curve()) > 0:
                    print("✅ Portfolio calculations working")
                else:
                    print("❌ Portfolio calculations failed")
            except Exception as e:
                print(f"❌ Portfolio verification failed: {e}")

            return True

        except Exception as e:
            print(f"❌ Safe system restart failed: {e}")
            return False

    def debug_volatility_calculation(self, system):
        """Debug volatility calculation issues - FIXED VERSION"""
        print("=== DEBUGGING VOLATILITY CALCULATIONS ===")

        instruments = system.get_instrument_list()
        issues_found = []

        for instrument in instruments[:10]:  # Test first 10
            try:
                # ✅ CORRECTED METHOD NAMES - Try multiple approaches
                vol_scalar = None

                # Method 1: Try get_instrument_vol_scalar (most likely correct)
                try:
                    vol_scalar = system.positionSize.get_instrument_vol_scalar(instrument)
                except AttributeError:
                    pass

                # Method 2: Try get_daily_volatility_scalar
                if vol_scalar is None:
                    try:
                        vol_scalar = system.positionSize.get_daily_volatility_scalar(instrument)
                    except AttributeError:
                        pass

                # Method 3: Try accessing volatility through rawdata
                if vol_scalar is None:
                    try:
                        daily_vol = system.rawdata.get_daily_returns_volatility(instrument)
                        if daily_vol is not None and len(daily_vol) > 0:
                            latest_vol = daily_vol.iloc[-1]
                            if latest_vol > 0:
                                target_vol = 0.12 / 16  # Daily target
                                vol_scalar = target_vol / latest_vol
                    except Exception:
                        pass

                # Method 4: Calculate manually as fallback
                if vol_scalar is None:
                    try:
                        prices = system.rawdata.get_daily_prices(instrument)
                        returns = prices.pct_change().dropna()
                        if len(returns) > 100:
                            daily_vol = returns.std()
                            target_vol = 0.12 / 16  # 12% annual target / sqrt(252)
                            vol_scalar = target_vol / daily_vol
                    except Exception:
                        pass

                # Check the results
                if vol_scalar is None:
                    print(f"❌ {instrument}: No volatility scalar available")
                    issues_found.append(f"{instrument}: No volatility scalar calculation possible")
                elif hasattr(vol_scalar, 'iloc'):
                    latest_val = vol_scalar.iloc[-1] if len(vol_scalar) > 0 else None
                    if latest_val is None or latest_val <= 0:
                        print(f"❌ {instrument}: Invalid volatility scalar: {latest_val}")
                        issues_found.append(f"{instrument}: Invalid volatility scalar")
                    else:
                        print(f"✅ {instrument}: Valid volatility scalar: {latest_val:.4f}")
                else:
                    if vol_scalar <= 0:
                        print(f"❌ {instrument}: Invalid volatility scalar: {vol_scalar}")
                        issues_found.append(f"{instrument}: Invalid volatility scalar")
                    else:
                        print(f"✅ {instrument}: Valid volatility scalar: {vol_scalar:.4f}")

            except Exception as e:
                print(f"❌ {instrument}: Volatility calculation failed: {e}")
                issues_found.append(f"{instrument}: Calculation failed - {e}")

        return issues_found

    def export_position_sizing_pipeline_debug(self, system, filename="position_sizing_debug.xlsx"):
        """
        Export complete position sizing pipeline components for final day debugging
        This will show every step from risk weights to final positions
        """
        print(f"Exporting position sizing pipeline debug to {filename}...")

        try:
            instruments = system.get_instrument_list()
            rules = list(system.rules.trading_rules().keys())

            # Get the final date from system
            portfolio = system.accounts.portfolio()
            final_date = portfolio.curve().index[-1]

            print(f"Extracting data for final date: {final_date}")

            # Initialize data collection
            pipeline_data = {}

            for instrument in instruments:
                try:
                    print(f"Processing {instrument}...")

                    # STEP 1: Get config risk weight
                    config_weights = getattr(system.config, 'instrument_weights', {})
                    risk_weight = config_weights.get(instrument, 0.0)

                    # STEP 2: Get individual rule forecasts (final day)
                    rule_forecasts = {}
                    for rule_name in rules:
                        try:
                            raw_forecast = system.rules.get_raw_forecast(instrument, rule_name)
                            if raw_forecast is not None and len(raw_forecast) > 0:
                                rule_forecasts[f'raw_forecast_{rule_name}'] = raw_forecast.iloc[-1]

                            # Get forecast scalar
                            forecast_scalar = system.forecastScaleCap.get_forecast_scalar(instrument, rule_name)
                            if forecast_scalar is not None and len(forecast_scalar) > 0:
                                rule_forecasts[f'forecast_scalar_{rule_name}'] = forecast_scalar.iloc[-1]

                            # Get scaled forecast
                            scaled_forecast = system.forecastScaleCap.get_scaled_forecast(instrument, rule_name)
                            if scaled_forecast is not None and len(scaled_forecast) > 0:
                                rule_forecasts[f'scaled_forecast_{rule_name}'] = scaled_forecast.iloc[-1]

                        except Exception as e:
                            rule_forecasts[f'error_{rule_name}'] = str(e)

                    # STEP 3: Get combined forecast
                    try:
                        combined_forecast = system.combForecast.get_combined_forecast(instrument)
                        final_combined_forecast = combined_forecast.iloc[-1] if len(combined_forecast) > 0 else 0
                    except Exception as e:
                        final_combined_forecast = f"Error: {e}"

                    # STEP 4: Get forecast weights
                    try:
                        forecast_weights = system.combForecast.get_forecast_weights(instrument)
                        final_forecast_weights = forecast_weights.iloc[-1].to_dict() if len(
                            forecast_weights) > 0 else {}
                    except Exception as e:
                        final_forecast_weights = f"Error: {e}"

                    # STEP 5: Get forecast diversification multiplier
                    try:
                        fdm = system.combForecast.get_forecast_diversification_multiplier(instrument)
                        final_fdm = fdm.iloc[-1] if len(fdm) > 0 else 1.0
                    except Exception as e:
                        final_fdm = f"Error: {e}"

                    # STEP 6: Get volatility scalar
                    try:
                        vol_scalar = system.positionSize.get_volatility_scalar(instrument)
                        final_vol_scalar = vol_scalar.iloc[-1] if len(vol_scalar) > 0 else 0
                    except Exception as e:
                        final_vol_scalar = f"Error: {e}"

                    # STEP 7: Get subsystem position (before cash weights)
                    try:
                        subsystem_position = system.positionSize.get_subsystem_position(instrument)
                        final_subsystem_position = subsystem_position.iloc[-1] if len(subsystem_position) > 0 else 0
                    except Exception as e:
                        final_subsystem_position = f"Error: {e}"

                    # STEP 8: Get instrument cash weight
                    try:
                        instrument_weights = system.portfolio.get_instrument_weights()
                        final_cash_weight = instrument_weights[instrument].iloc[
                            -1] if instrument in instrument_weights.columns else 0
                    except Exception as e:
                        final_cash_weight = f"Error: {e}"

                    # STEP 9: Get IDM (should be same for all instruments)
                    try:
                        idm = system.portfolio.get_instrument_diversification_multiplier()
                        final_idm = idm.iloc[-1] if len(idm) > 0 else 1.0
                    except Exception as e:
                        final_idm = f"Error: {e}"

                    # STEP 10: Get final notional position
                    try:
                        final_position = system.portfolio.get_notional_position(instrument)
                        final_notional_position = final_position.iloc[-1] if len(final_position) > 0 else 0
                    except Exception as e:
                        final_notional_position = f"Error: {e}"

                    # STEP 11: Get volatility data used
                    try:
                        # Try multiple methods to get volatility
                        vol_methods = {}

                        # Method 1: Raw volatility
                        try:
                            raw_vol = system.rawdata.get_daily_returns_volatility(instrument)
                            vol_methods['raw_daily_vol'] = raw_vol.iloc[-1] if raw_vol is not None else None
                        except:
                            vol_methods['raw_daily_vol'] = "Not available"

                        # Method 2: Calculate from prices
                        try:
                            prices = system.rawdata.get_daily_prices(instrument)
                            if prices is not None and len(prices) > 100:
                                returns = prices.pct_change().dropna()
                                daily_vol = returns.std()
                                vol_methods['calculated_daily_vol'] = daily_vol
                                vol_methods['calculated_annual_vol'] = daily_vol * (252 ** 0.5)
                        except:
                            vol_methods['calculated_daily_vol'] = "Error"
                            vol_methods['calculated_annual_vol'] = "Error"

                    except Exception as e:
                        vol_methods = {'error': str(e)}

                    # STEP 12: Manual calculation verification
                    # Calculate what the cash weight SHOULD be
                    if isinstance(final_vol_scalar, (int, float)) and final_vol_scalar != 0:
                        # Cash weight should be: risk_weight / (volatility / target_volatility)
                        target_vol = 0.12  # 12% target

                        if 'calculated_annual_vol' in vol_methods and isinstance(vol_methods['calculated_annual_vol'],
                                                                                 (int, float)):
                            actual_vol = vol_methods['calculated_annual_vol']
                            expected_cash_weight = risk_weight * (target_vol / actual_vol)
                            cash_weight_check = "OK" if abs(
                                expected_cash_weight - final_cash_weight) < 0.01 else "MISMATCH"
                        else:
                            expected_cash_weight = "Cannot calculate"
                            cash_weight_check = "Unknown"
                    else:
                        expected_cash_weight = "Vol scalar error"
                        cash_weight_check = "Error"

                    # STEP 13: Position calculation verification
                    if all(isinstance(x, (int, float)) for x in
                           [final_combined_forecast, final_vol_scalar, final_cash_weight, final_idm]):
                        expected_position = final_combined_forecast * final_vol_scalar * final_cash_weight * final_idm
                        position_check = "OK" if abs(expected_position - final_notional_position) < 1.0 else "MISMATCH"
                    else:
                        expected_position = "Cannot calculate"
                        position_check = "Error"

                    # Store all data
                    pipeline_data[instrument] = {
                        # Configuration
                        'config_risk_weight': risk_weight,
                        'target_volatility': 0.12,
                        'final_date': final_date,

                        # Volatility data
                        **{f'vol_{k}': v for k, v in vol_methods.items()},

                        # Rule forecasts
                        **rule_forecasts,

                        # Combined forecasting
                        'combined_forecast': final_combined_forecast,
                        'forecast_weights': str(final_forecast_weights),
                        'forecast_div_mult': final_fdm,

                        # Position sizing
                        'volatility_scalar': final_vol_scalar,
                        'subsystem_position': final_subsystem_position,

                        # Cash weights
                        'actual_cash_weight': final_cash_weight,
                        'expected_cash_weight': expected_cash_weight,
                        'cash_weight_check': cash_weight_check,

                        # Final positioning
                        'idm': final_idm,
                        'final_notional_position': final_notional_position,
                        'expected_position': expected_position,
                        'position_check': position_check,
                    }

                except Exception as e:
                    print(f"Error processing {instrument}: {e}")
                    pipeline_data[instrument] = {'error': str(e)}

            # Export to Excel
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:

                # Sheet 1: Complete Pipeline
                pipeline_df = pd.DataFrame.from_dict(pipeline_data, orient='index')
                pipeline_df.to_excel(writer, sheet_name='Complete_Pipeline')

                # Sheet 2: Key Components Only (easier to read)
                key_components = {}
                for instrument, data in pipeline_data.items():
                    if 'error' not in data:
                        key_components[instrument] = {
                            'config_risk_weight': data.get('config_risk_weight'),
                            'calculated_annual_vol': data.get('vol_calculated_annual_vol'),
                            'volatility_scalar': data.get('volatility_scalar'),
                            'combined_forecast': data.get('combined_forecast'),
                            'subsystem_position': data.get('subsystem_position'),
                            'actual_cash_weight': data.get('actual_cash_weight'),
                            'expected_cash_weight': data.get('expected_cash_weight'),
                            'cash_weight_check': data.get('cash_weight_check'),
                            'idm': data.get('idm'),
                            'final_notional_position': data.get('final_notional_position'),
                            'expected_position': data.get('expected_position'),
                            'position_check': data.get('position_check')
                        }

                key_df = pd.DataFrame.from_dict(key_components, orient='index')
                key_df.to_excel(writer, sheet_name='Key_Components')

                # Sheet 3: Rule-by-rule breakdown
                rule_breakdown = {}
                for instrument, data in pipeline_data.items():
                    if 'error' not in data:
                        rule_data = {k: v for k, v in data.items() if 'forecast' in k.lower()}
                        rule_breakdown[instrument] = rule_data

                if rule_breakdown:
                    rule_df = pd.DataFrame.from_dict(rule_breakdown, orient='index')
                    rule_df.to_excel(writer, sheet_name='Rule_Breakdown')

                # Sheet 4: Verification Summary
                verification_summary = {
                    'total_instruments': len(pipeline_data),
                    'successful_extractions': len([d for d in pipeline_data.values() if 'error' not in d]),
                    'cash_weight_matches': len(
                        [d for d in pipeline_data.values() if d.get('cash_weight_check') == 'OK']),
                    'position_matches': len([d for d in pipeline_data.values() if d.get('position_check') == 'OK']),
                    'final_date': final_date.strftime('%Y-%m-%d')
                }

                summary_df = pd.DataFrame.from_dict({'metrics': verification_summary}, orient='index')
                summary_df.to_excel(writer, sheet_name='Verification_Summary')

            print(f"✅ Position sizing pipeline debug exported: {filename}")
            return filename

        except Exception as e:
            print(f"❌ Export failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def verify_position_sizing_formula(self, system):
        """
        Verify the exact position sizing formula being used
        """
        print("=== POSITION SIZING FORMULA VERIFICATION ===")

        sample_instrument = system.get_instrument_list()[0]
        print(f"Testing with instrument: {sample_instrument}")

        try:
            # Get all components
            combined_forecast = system.combForecast.get_combined_forecast(sample_instrument).iloc[-1]
            vol_scalar = system.positionSize.get_volatility_scalar(sample_instrument).iloc[-1]
            cash_weight = system.portfolio.get_instrument_weights()[sample_instrument].iloc[-1]
            idm = system.portfolio.get_instrument_diversification_multiplier().iloc[-1]
            final_position = system.portfolio.get_notional_position(sample_instrument).iloc[-1]

            print(f"Combined Forecast: {combined_forecast:.4f}")
            print(f"Volatility Scalar: {vol_scalar:.6f}")
            print(f"Cash Weight: {cash_weight:.6f}")
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

    def export_complete_position_sizing_factors_excel(self, filename="complete_position_sizing_factors.xlsx"):
        """Export all factors from Robert Carver's position sizing pipeline"""

        print(f"Exporting complete position sizing factors to {filename}...")

        instruments = self.system.get_instrument_list()
        if not instruments:
            return None

        # Collect all position sizing factors
        position_sizing_data = {}

        for instrument in instruments:
            try:
                print(f"Extracting all factors for {instrument}...")

                # 1. Get current price
                prices = self.system.rawdata.get_daily_prices(instrument)
                current_price = prices.iloc[-1] if prices is not None else 0

                # 2. Calculate DAILY price volatility (not annual)
                returns = prices.pct_change().dropna()
                daily_price_volatility = returns.std()  # This is the daily figure Robert uses
                annual_price_volatility = daily_price_volatility * (252 ** 0.5)

                # 3. Block value (depends on instrument type)
                # For ETFs, this is typically 1 × price per share
                # For futures, this would be contract multiplier × price
                block_value = current_price  # Simplified for ETFs

                # 4. Get exchange rate
                # This would need to be implemented based on instrument currency
                # For USD-based system with USD ETFs, exchange_rate = 1
                exchange_rate = 1.0  # Placeholder - needs proper implementation

                # 5. Calculate instrument currency volatility (daily)
                daily_instrument_currency_volatility = block_value * daily_price_volatility

                # 6. Calculate instrument value volatility (daily, in account currency)
                daily_instrument_value_volatility = daily_instrument_currency_volatility * exchange_rate

                # 7. Get daily cash volatility target
                annual_cash_target = 0.12  # 12% annual target
                daily_cash_volatility_target = annual_cash_target / (252 ** 0.5)

                # 8. Calculate volatility scalar (Robert's key factor)
                volatility_scalar = daily_cash_volatility_target / daily_instrument_value_volatility if daily_instrument_value_volatility > 0 else 0

                # 9. Get system's calculated volatility scalar for comparison
                try:
                    system_vol_scalar = self.system.positionSize.get_volatility_scalar(instrument).iloc[-1]
                except:
                    system_vol_scalar = "Error"

                # 10. Get other system components
                try:
                    combined_forecast = self.system.combForecast.get_combined_forecast(instrument).iloc[-1]
                    cash_weight = self.system.portfolio.get_instrument_weights()[instrument].iloc[-1]
                    idm = self.system.portfolio.get_instrument_diversification_multiplier().iloc[-1]
                except:
                    combined_forecast = "Error"
                    cash_weight = "Error"
                    idm = "Error"

                # 11. Calculate expected position using Robert's formula
                if all(isinstance(x, (int, float)) for x in [combined_forecast, volatility_scalar]):
                    expected_subsystem_position = (combined_forecast * volatility_scalar) / 10
                    expected_portfolio_position = expected_subsystem_position * cash_weight * idm if isinstance(
                        cash_weight, (int, float)) and isinstance(idm, (int, float)) else "Error"
                else:
                    expected_subsystem_position = "Error"
                    expected_portfolio_position = "Error"

                # Store all factors
                position_sizing_data[instrument] = {
                    # Price data
                    'Current_Price': current_price,
                    'Currency': 'USD',  # Placeholder

                    # Block and exchange rate factors
                    'Block_Value': block_value,
                    'Exchange_Rate': exchange_rate,

                    # Volatility factors (DAILY - as Robert uses)
                    'Daily_Price_Volatility': daily_price_volatility,
                    'Daily_Price_Volatility_Percent': daily_price_volatility * 100,
                    'Daily_Instrument_Currency_Volatility': daily_instrument_currency_volatility,
                    'Daily_Instrument_Value_Volatility': daily_instrument_value_volatility,

                    # Annual equivalents (for comparison)
                    'Annual_Price_Volatility': annual_price_volatility,
                    'Annual_Price_Volatility_Percent': annual_price_volatility * 100,

                    # Cash volatility targets
                    'Annual_Cash_Volatility_Target': annual_cash_target,
                    'Daily_Cash_Volatility_Target': daily_cash_volatility_target,

                    # Key scaling factors
                    'Calculated_Volatility_Scalar': volatility_scalar,
                    'System_Volatility_Scalar': system_vol_scalar,
                    'Volatility_Scalar_Match': abs(volatility_scalar - system_vol_scalar) < 0.001 if isinstance(
                        system_vol_scalar, (int, float)) else "Cannot compare",

                    # Position sizing pipeline
                    'Combined_Forecast': combined_forecast,
                    'Expected_Subsystem_Position': expected_subsystem_position,
                    'Cash_Weight': cash_weight,
                    'IDM': idm,
                    'Expected_Portfolio_Position': expected_portfolio_position,

                    # Verification
                    'Formula_Check': f"({combined_forecast:.2f} × {volatility_scalar:.6f}) ÷ 10 = {expected_subsystem_position:.2f}" if isinstance(
                        expected_subsystem_position, (int, float)) else "Error"
                }

            except Exception as e:
                position_sizing_data[instrument] = {'Error': str(e)}

        # Export to Excel with detailed breakdown
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:

            # Main factors sheet
            factors_df = pd.DataFrame.from_dict(position_sizing_data, orient='index')
            factors_df.to_excel(writer, sheet_name='All_Position_Sizing_Factors')

            # Daily vs Annual comparison
            comparison_data = {}
            for instrument, data in position_sizing_data.items():
                if 'Error' not in data:
                    comparison_data[instrument] = {
                        'Daily_Price_Vol': data.get('Daily_Price_Volatility', 0),
                        'Annual_Price_Vol': data.get('Annual_Price_Volatility', 0),
                        'Daily_Target': data.get('Daily_Cash_Volatility_Target', 0),
                        'Annual_Target': data.get('Annual_Cash_Volatility_Target', 0),
                        'Vol_Scalar_Daily_Based': data.get('Calculated_Volatility_Scalar', 0),
                        'Vol_Scalar_System': data.get('System_Volatility_Scalar', 0)
                    }

            if comparison_data:
                comp_df = pd.DataFrame.from_dict(comparison_data, orient='index')
                comp_df.to_excel(writer, sheet_name='Daily_vs_Annual_Comparison')

        print(f"✅ Complete position sizing factors exported: {filename}")
        return filename
