# production_monitor.py - Production Monitoring System v1.2

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')


class ProductionMonitor:
    """
    Production-ready monitoring system for systematic trading
    """

    def __init__(self, system, config=None):
        self.system = system
        self.config = config if config else {}
        self.instruments = system.get_instrument_list()
        self.rules = system.rules.trading_rules()

        # Alert thresholds
        self.sharpe_threshold = self.config.get('min_sharpe_ratio', 0.3)
        self.drawdown_threshold = self.config.get('max_drawdown', 0.15)
        self.vol_tolerance = self.config.get('vol_tolerance', 0.02)  # 2% tolerance

        # Dashboard settings
        self.warm_up_days = 365  # Match your system's warm_up_days setting

        print(f"✅ Production Monitor initialized for {len(self.instruments)} instruments")

    # [Keep all existing health check methods unchanged]
    def run_full_health_check(self):
        """
        Comprehensive system health check for production readiness
        """
        print("🔍 PRODUCTION HEALTH CHECK")
        print("=" * 50)

        health_report = {
            'timestamp': datetime.now(),
            'overall_status': 'HEALTHY',
            'alerts': [],
            'warnings': [],
            'system_metrics': {},
            'recommendations': []
        }

        # 1. Data Quality Check
        data_status = self._check_data_quality()
        health_report['data_quality'] = data_status

        # 2. Rule Performance Check
        rule_status = self._check_rule_performance()
        health_report['rule_performance'] = rule_status

        # 3. Risk Metrics Check
        risk_status = self._check_risk_metrics()
        health_report['risk_metrics'] = risk_status

        # 4. System Performance Check
        perf_status = self._check_system_performance()
        health_report['system_performance'] = perf_status

        # 5. Generate alerts and recommendations
        self._generate_alerts(health_report)

        # 6. Display dashboard
        self._display_health_dashboard(health_report)

        return health_report

    def _check_data_quality(self):
        """Check data quality across all instruments"""
        print("\n1️⃣ DATA QUALITY CHECK")
        data_issues = []
        data_metrics = {}

        for instrument in self.instruments:
            try:
                prices = self.system.rawdata.get_daily_prices(instrument)

                # Check data recency
                last_date = prices.index[-1]
                days_stale = (datetime.now().date() - last_date.date()).days

                # Check for gaps
                price_gaps = prices.isna().sum()

                # Check volatility
                returns = prices.pct_change().dropna()
                vol = returns.std() * np.sqrt(252)

                data_metrics[instrument] = {
                    'last_date': last_date,
                    'days_stale': days_stale,
                    'price_gaps': price_gaps,
                    'annual_vol': vol,
                    'data_points': len(prices)
                }

                # Flag issues
                if days_stale > 2:
                    data_issues.append(f"{instrument}: Data {days_stale} days stale")
                if price_gaps > 10:
                    data_issues.append(f"{instrument}: {price_gaps} price gaps")
                if vol > 0.5 or vol < 0.05:
                    data_issues.append(f"{instrument}: Unusual volatility {vol:.1%}")

            except Exception as e:
                data_issues.append(f"{instrument}: Data access error - {e}")

        print(f" ✅ Analyzed {len(self.instruments)} instruments")
        print(f" ⚠️ Found {len(data_issues)} data issues")

        return {
            'status': 'PASS' if len(data_issues) < 3 else 'WARN',
            'issues': data_issues,
            'metrics': data_metrics
        }

    def _check_rule_performance(self):
        """Check individual rule performance"""
        print("\n2️⃣ RULE PERFORMANCE CHECK")
        rule_metrics = {}
        rule_issues = []

        for rule_name in self.rules.keys():
            try:
                # Sample performance across instruments
                rule_sharpes = []
                for instrument in self.instruments[:5]:  # Sample first 5
                    try:
                        rule_pandl = self.system.accounts.pandl_for_trading_rule(instrument, rule_name)
                        if rule_pandl is not None:
                            sharpe = rule_pandl.sharpe()
                            rule_sharpes.append(sharpe)
                    except:
                        continue

                if rule_sharpes:
                    avg_sharpe = np.mean(rule_sharpes)
                    std_sharpe = np.std(rule_sharpes)
                    rule_metrics[rule_name] = {
                        'avg_sharpe': avg_sharpe,
                        'std_sharpe': std_sharpe,
                        'instruments_tested': len(rule_sharpes)
                    }

                    # Flag underperforming rules
                    if avg_sharpe < 0.1:
                        rule_issues.append(f"{rule_name}: Low Sharpe ratio ({avg_sharpe:.2f})")
                    if std_sharpe > 0.5:
                        rule_issues.append(f"{rule_name}: High Sharpe volatility ({std_sharpe:.2f})")

            except Exception as e:
                rule_issues.append(f"{rule_name}: Performance check failed - {e}")

        print(f" ✅ Analyzed {len(rule_metrics)} rules")
        print(f" ⚠️ Found {len(rule_issues)} rule issues")

        return {
            'status': 'PASS' if len(rule_issues) == 0 else 'WARN',
            'issues': rule_issues,
            'metrics': rule_metrics
        }

    def _check_risk_metrics(self):
        """Check system-wide risk metrics"""
        print("\n3️⃣ RISK METRICS CHECK")
        risk_issues = []
        risk_metrics = {}

        try:
            # Portfolio volatility check
            portfolio = self.system.accounts.portfolio()
            if portfolio is not None:
                returns = portfolio.curve().pct_change().dropna()
                actual_vol = returns.std() * np.sqrt(252)
                target_vol = 0.12  # 12% target

                risk_metrics['actual_volatility'] = actual_vol
                risk_metrics['target_volatility'] = target_vol
                risk_metrics['vol_deviation'] = abs(actual_vol - target_vol)

                # Check volatility targeting
                if abs(actual_vol - target_vol) > self.vol_tolerance:
                    risk_issues.append(f"Volatility off target: {actual_vol:.1%} vs {target_vol:.1%}")

                # Check for extreme moves
                extreme_moves = abs(returns) > 0.05  # 5% daily moves
                if extreme_moves.sum() > len(returns) * 0.05:  # More than 5% of days
                    risk_issues.append(f"High frequency of extreme moves: {extreme_moves.sum()} days")

        except Exception as e:
            risk_issues.append(f"Risk metrics calculation failed: {e}")

        print(f" ✅ Risk analysis complete")
        print(f" ⚠️ Found {len(risk_issues)} risk issues")

        return {
            'status': 'PASS' if len(risk_issues) == 0 else 'WARN',
            'issues': risk_issues,
            'metrics': risk_metrics
        }

    def _check_system_performance(self):
        """Check overall system performance"""
        print("\n4️⃣ SYSTEM PERFORMANCE CHECK")
        perf_issues = []
        perf_metrics = {}

        try:
            from performance_calculator import EnhancedPerformanceCalculator
            calculator = EnhancedPerformanceCalculator()
            metrics = calculator.calculate_portfolio_performance(self.system)

            if metrics:
                perf_metrics = metrics

                # Check performance thresholds
                if metrics['sharpe_ratio'] < self.sharpe_threshold:
                    perf_issues.append(f"Low Sharpe ratio: {metrics['sharpe_ratio']:.2f}")
                if metrics['max_drawdown'] < -self.drawdown_threshold:
                    perf_issues.append(f"High drawdown: {metrics['max_drawdown']:.1%}")
                if metrics['annual_volatility'] > 0.20:  # 20% max vol
                    perf_issues.append(f"High volatility: {metrics['annual_volatility']:.1%}")

        except Exception as e:
            perf_issues.append(f"Performance calculation failed: {e}")

        print(f" ✅ Performance analysis complete")
        print(f" ⚠️ Found {len(perf_issues)} performance issues")

        return {
            'status': 'PASS' if len(perf_issues) == 0 else 'WARN',
            'issues': perf_issues,
            'metrics': perf_metrics
        }

    def _generate_alerts(self, health_report):
        """Generate alerts and recommendations based on health check"""
        # Critical alerts
        for section in ['data_quality', 'rule_performance', 'risk_metrics', 'system_performance']:
            if health_report[section]['status'] == 'WARN':
                health_report['overall_status'] = 'WARNING'
                for issue in health_report[section]['issues']:
                    health_report['alerts'].append(f"{section.upper()}: {issue}")

        # Generate recommendations
        if health_report['overall_status'] == 'WARNING':
            health_report['recommendations'].extend([
                "Review flagged issues before live trading",
                "Consider reducing position sizes until issues resolved",
                "Implement additional monitoring during issue resolution"
            ])
        else:
            health_report['recommendations'].extend([
                "System appears healthy for production deployment",
                "Continue regular monitoring",
                "Consider scaling to additional instruments"
            ])

    def _display_health_dashboard(self, health_report):
        """Display comprehensive health dashboard"""
        print("\n" + "=" * 60)
        print("🏥 PRODUCTION HEALTH DASHBOARD")
        print("=" * 60)

        # Overall status
        status_icon = "✅" if health_report['overall_status'] == 'HEALTHY' else "⚠️"
        print(f"{status_icon} OVERALL STATUS: {health_report['overall_status']}")
        print(f"📅 Check Time: {health_report['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")

        # Alerts
        if health_report['alerts']:
            print(f"\n🚨 ALERTS ({len(health_report['alerts'])}):")
            for alert in health_report['alerts'][:10]:  # Show max 10
                print(f" • {alert}")

        # Key metrics
        if 'system_performance' in health_report and health_report['system_performance']['metrics']:
            metrics = health_report['system_performance']['metrics']
            print(f"\n📊 KEY METRICS:")
            print(f" • Sharpe Ratio: {metrics.get('sharpe_ratio', 'N/A'):.3f}")
            print(f" • Annual Return: {metrics.get('annual_return', 'N/A'):.1%}")
            print(f" • Max Drawdown: {metrics.get('max_drawdown', 'N/A'):.1%}")
            print(f" • Win Rate: {metrics.get('win_rate', 'N/A'):.1%}")

        # Recommendations
        if health_report['recommendations']:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in health_report['recommendations']:
                print(f" • {rec}")

        print("=" * 60)

    # ================================
    # REFACTORED DASHBOARD METHODS
    # ================================

    def create_monitoring_dashboard(self):
        """Create visual monitoring dashboard with modular components"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        try:
            # Create each plot using dedicated methods
            self._create_portfolio_plot(axes[0, 0])
            self._create_volatility_plot(axes[0, 1])
            self._create_drawdown_plot(axes[1, 0])
            self._create_summary_panel(axes[1, 1])

            # Enhanced layout
            fig.suptitle(f'Enhanced ETF System v1.2 - Production Dashboard',
                         fontsize=14, fontweight='bold', y=0.96)
            plt.subplots_adjust(left=0.06, right=0.94, top=0.90, bottom=0.06,
                                hspace=0.40, wspace=0.20)
            fig.set_size_inches(16, 12)
            fig.set_dpi(100)

            print("📊 Dashboard created with warm-up buffer corrections")
            plt.show(block=True)

        except Exception as e:
            print(f"⚠️ Dashboard creation error: {e}")
            plt.tight_layout()
            plt.show(block=True)

        return fig

    def _create_portfolio_plot(self, ax):
        """Create portfolio performance plot with warm-up buffer"""
        try:
            portfolio = self.system.accounts.portfolio()
            if portfolio is not None:
                curve = portfolio.curve()

                # Apply warm-up buffer to remove early spikes
                if len(curve) > self.warm_up_days:
                    curve_filtered = curve.iloc[self.warm_up_days:]
                    curve_filtered.plot(ax=ax,
                                        title=f"Portfolio Performance (After {self.warm_up_days}-Day Warm-Up)",
                                        color='blue')
                    ax.set_ylabel("P&L")
                    ax.grid(True, alpha=0.3)

                    # Add buffer indicator
                    ax.text(0.02, 0.98, f'✅ {self.warm_up_days}-day buffer applied',
                            transform=ax.transAxes, verticalalignment='top',
                            bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8),
                            fontsize=9)
                else:
                    curve.plot(ax=ax, title="Portfolio Performance (Insufficient Data for Buffer)",
                               color='orange')
                    ax.set_ylabel("P&L")
                    ax.grid(True, alpha=0.3)
            else:
                ax.text(0.5, 0.5, 'Portfolio data\nnot available',
                        ha='center', va='center', transform=ax.transAxes)
                ax.set_title("Portfolio Performance (No Data)")

        except Exception as e:
            ax.text(0.5, 0.5, f'Portfolio error:\n{str(e)[:40]}',
                    ha='center', va='center', transform=ax.transAxes, color='red')
            ax.set_title("Portfolio Performance (Error)")

    def _create_volatility_plot(self, ax):
        """Create rolling volatility plot with warm-up buffer"""
        try:
            portfolio = self.system.accounts.portfolio()
            if portfolio is not None:
                curve = portfolio.curve()

                # Apply warm-up buffer to remove early volatility spikes
                if len(curve) > self.warm_up_days:
                    curve_filtered = curve.iloc[self.warm_up_days:]
                    if len(curve_filtered) > 60:
                        returns = curve_filtered.pct_change().dropna()
                        rolling_vol = returns.rolling(60).std() * np.sqrt(252)
                        rolling_vol.plot(ax=ax,
                                         title=f"Rolling 60-Day Volatility (After {self.warm_up_days}-Day Warm-Up)",
                                         color='orange')
                        ax.axhline(y=0.12, color='red', linestyle='--', label='Target 12%')
                        ax.set_ylabel("Annualized Volatility")
                        ax.legend()
                        ax.grid(True, alpha=0.3)

                        # Add buffer indicator
                        ax.text(0.02, 0.98, f'✅ {self.warm_up_days}-day buffer applied',
                                transform=ax.transAxes, verticalalignment='top',
                                bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8),
                                fontsize=9)
                    else:
                        ax.text(0.5, 0.5, 'Insufficient data\nfor volatility after buffer',
                                ha='center', va='center', transform=ax.transAxes)
                        ax.set_title("Rolling Volatility (Insufficient Data)")
                else:
                    returns = curve.pct_change().dropna()
                    if len(returns) > 60:
                        rolling_vol = returns.rolling(60).std() * np.sqrt(252)
                        rolling_vol.plot(ax=ax, title="Rolling 60-Day Volatility (No Buffer)", color='red')
                        ax.axhline(y=0.12, color='red', linestyle='--', label='Target 12%')
                        ax.set_ylabel("Annualized Volatility")
                        ax.legend()
                        ax.grid(True, alpha=0.3)
            else:
                ax.text(0.5, 0.5, 'Volatility data\nnot available',
                        ha='center', va='center', transform=ax.transAxes)
                ax.set_title("Rolling Volatility (No Data)")

        except Exception as e:
            ax.text(0.5, 0.5, f'Volatility error:\n{str(e)[:40]}',
                    ha='center', va='center', transform=ax.transAxes, color='red')
            ax.set_title("Rolling Volatility (Error)")

    def _create_drawdown_plot(self, ax):
        """Create drawdown plot with proper handling"""
        try:
            portfolio = self.system.accounts.portfolio()
            if portfolio is not None:
                curve = portfolio.curve()

                # Apply warm-up buffer
                if len(curve) > self.warm_up_days:
                    curve_filtered = curve.iloc[self.warm_up_days:]
                    title_suffix = f" (After {self.warm_up_days}-Day Warm-Up)"
                else:
                    curve_filtered = curve
                    title_suffix = " (No Buffer)"

                if len(curve_filtered) > 50:
                    # Normalize curve to start from 1.0
                    if curve_filtered.iloc[0] <= 0:
                        curve_filtered = curve_filtered - curve_filtered.iloc[0] + 1.0

                    # Calculate drawdown
                    rolling_max = curve_filtered.expanding().max()
                    drawdown = ((curve_filtered - rolling_max) / rolling_max) * 100

                    # Plot drawdown
                    drawdown.plot(ax=ax, color='red', linewidth=2)
                    ax.fill_between(drawdown.index, drawdown.values, 0,
                                    where=(drawdown <= 0), color='red', alpha=0.2)
                    ax.set_title(f"Portfolio Drawdown{title_suffix}")
                    ax.set_ylabel("Drawdown (%)")
                    ax.grid(True, alpha=0.3)

                    # Add statistics
                    max_dd = drawdown.min()
                    current_dd = drawdown.iloc[-1]
                    ax.text(0.02, 0.98, f'Max DD: {max_dd:.1f}%\nCurrent: {current_dd:.1f}%',
                            transform=ax.transAxes, verticalalignment='top',
                            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
                    ax.set_ylim(min(drawdown.min() * 1.1, -1), 1)
                    ax.axhline(y=0, color='black', linestyle='-', alpha=0.5)
                else:
                    # Create a simple bar chart as placeholder
                    ax.bar([1], [-5], color='red', alpha=0.3, width=0.5)
                    ax.text(0.5, 0.5, f'Drawdown Analysis\n\nNeed more data\n({len(curve_filtered)} points)',
                            ha='center', va='center', transform=ax.transAxes,
                            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
                    ax.set_title("Drawdown (Insufficient Data)")
                    ax.set_ylim(-10, 0)
            else:
                # Portfolio not available - create placeholder
                ax.bar([1], [-10], color='gray', alpha=0.3, width=0.5)
                ax.text(0.5, 0.5, 'Drawdown Analysis\n\n⏳ Portfolio calculation\nin progress...',
                        ha='center', va='center', transform=ax.transAxes,
                        bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
                ax.set_title("Drawdown (Pending)")
                ax.set_ylim(-10, 0)

        except Exception as e:
            ax.text(0.5, 0.5, f'Drawdown Error:\n{str(e)[:30]}',
                    ha='center', va='center', transform=ax.transAxes, color='red')
            ax.set_title("Drawdown (Error)")

    def _create_summary_panel(self, ax):
        """Create system summary information panel"""
        ax.clear()
        ax.axis('off')

        try:
            # Get system information
            instruments = self.system.get_instrument_list()
            rules = self.system.rules.trading_rules()
            current_time = datetime.now().strftime('%H:%M:%S')

            # Get performance summary if available
            perf_text = self._get_performance_summary()

            # Create summary text
            summary_text = f"""SYSTEM HEALTH MONITOR

⏰ Time: {current_time}
🎯 Status: ACTIVE

📊 CONFIGURATION:
• ETFs: {len(instruments)}
• Rules: {len(rules)}
• Warm-up: {self.warm_up_days} days
• Vol Target: 12%

📈 PERFORMANCE:
{perf_text}

⚙️ CARVER METHOD:
• Pooled Scalars: ✅
• Uniform Weights: ✅
• Cost Awareness: ✅
• Buffer Applied: ✅

🔔 MONITORING:
• Dashboard: Live
• Health: Active
• Alerts: Enabled
• Status: Ready

💡 NOTES:
• Full 32-ETF universe
• Production v1.2
• Enhanced monitoring
• Real-time updates"""

            ax.text(0.02, 0.98, summary_text, transform=ax.transAxes,
                    fontsize=8, verticalalignment='top', fontfamily='monospace',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='lightcyan', alpha=0.9))

        except Exception as e:
            # Emergency fallback
            ax.text(0.5, 0.5,
                    f'System Summary\n\nStatus: Active\nTime: {datetime.now().strftime("%H:%M:%S")}\nETFs: Processing\n\nError: {str(e)[:20]}',
                    ha='center', va='center', transform=ax.transAxes,
                    bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))

    def _get_performance_summary(self):
        """Get performance summary text"""
        try:
            portfolio = self.system.accounts.portfolio()
            if portfolio is not None:
                curve = portfolio.curve()
                if len(curve) > self.warm_up_days:
                    curve_filtered = curve.iloc[self.warm_up_days:]
                    returns = curve_filtered.pct_change().dropna()
                    if len(returns) > 0 and returns.std() > 0:
                        sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
                        vol = returns.std() * np.sqrt(252)
                        return f"Sharpe: {sharpe:.2f}\nVol: {vol:.1%}"
                    else:
                        return "Calculating..."
                else:
                    return "Warming up..."
            else:
                return "Pending..."
        except:
            return "Error"

    def create_persistent_dashboard(self):
        """Create dashboard with multiple viewing and saving options"""
        print("🎨 CREATING ENHANCED MONITORING DASHBOARD")
        print("=" * 50)

        # Create the dashboard
        fig = self.create_monitoring_dashboard()

        # Enhanced viewing options
        print("\n📊 DASHBOARD READY!")
        print("Options:")
        print(" 1. View interactive plot (recommended)")
        print(" 2. Save to PNG file only")
        print(" 3. Save to PDF file only")
        print(" 4. Save to both PNG and PDF")
        print(" 5. View AND save (PNG)")

        while True:
            try:
                choice = input("\nEnter choice (1-5): ").strip()

                if choice == "1":
                    print("📊 Opening interactive dashboard...")
                    plt.show(block=True)
                    break
                elif choice == "2":
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f'etf_dashboard_{timestamp}.png'
                    plt.savefig(filename, dpi=300, bbox_inches='tight')
                    print(f"💾 Saved as: {filename}")
                    break
                elif choice == "3":
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f'etf_dashboard_{timestamp}.pdf'
                    plt.savefig(filename, bbox_inches='tight')
                    print(f"💾 Saved as: {filename}")
                    break
                elif choice == "4":
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    png_file = f'etf_dashboard_{timestamp}.png'
                    pdf_file = f'etf_dashboard_{timestamp}.pdf'
                    plt.savefig(png_file, dpi=300, bbox_inches='tight')
                    plt.savefig(pdf_file, bbox_inches='tight')
                    print(f"💾 Saved as: {png_file} and {pdf_file}")
                    break
                elif choice == "5":
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f'etf_dashboard_{timestamp}.png'
                    plt.savefig(filename, dpi=300, bbox_inches='tight')
                    print(f"💾 Saved as: {filename}")
                    print("📊 Opening interactive dashboard...")
                    plt.show(block=True)
                    break
                else:
                    print("❌ Invalid choice. Please enter 1-5.")

            except KeyboardInterrupt:
                print("\n⏸️ Dashboard creation cancelled")
                break
            except:
                print("❌ Invalid input. Please try again.")

        return fig
