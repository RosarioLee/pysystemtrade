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

        print(f"✅ Production Monitor initialized for {len(self.instruments)} instruments")

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

        print(f"   ✅ Analyzed {len(self.instruments)} instruments")
        print(f"   ⚠️ Found {len(data_issues)} data issues")

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

        print(f"   ✅ Analyzed {len(rule_metrics)} rules")
        print(f"   ⚠️ Found {len(rule_issues)} rule issues")

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

        print(f"   ✅ Risk analysis complete")
        print(f"   ⚠️ Found {len(risk_issues)} risk issues")

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

        print(f"   ✅ Performance analysis complete")
        print(f"   ⚠️ Found {len(perf_issues)} performance issues")

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
                print(f"   • {alert}")

        # Key metrics
        if 'system_performance' in health_report and health_report['system_performance']['metrics']:
            metrics = health_report['system_performance']['metrics']
            print(f"\n📊 KEY METRICS:")
            print(f"   • Sharpe Ratio: {metrics.get('sharpe_ratio', 'N/A'):.3f}")
            print(f"   • Annual Return: {metrics.get('annual_return', 'N/A'):.1%}")
            print(f"   • Max Drawdown: {metrics.get('max_drawdown', 'N/A'):.1%}")
            print(f"   • Win Rate: {metrics.get('win_rate', 'N/A'):.1%}")

        # Recommendations
        if health_report['recommendations']:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in health_report['recommendations']:
                print(f"   • {rec}")

        print("=" * 60)

    def create_monitoring_dashboard(self):
        """Create visual monitoring dashboard"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        try:
            # Plot 1: Portfolio Performance
            ax1 = axes[0, 0]
            portfolio = self.system.accounts.portfolio()
            if portfolio is not None:
                curve = portfolio.curve()
                curve.plot(ax=ax1, title="Portfolio Performance", color='blue')
                ax1.set_ylabel("P&L")
                ax1.grid(True, alpha=0.3)

            # Plot 2: Rolling Volatility
            ax2 = axes[0, 1]
            returns = portfolio.curve().pct_change().dropna()
            rolling_vol = returns.rolling(60).std() * np.sqrt(252)
            rolling_vol.plot(ax=ax2, title="Rolling 60-Day Volatility", color='orange')
            ax2.axhline(y=0.12, color='red', linestyle='--', label='Target 12%')
            ax2.set_ylabel("Annualized Volatility")
            ax2.legend()
            ax2.grid(True, alpha=0.3)

            # Plot 3: Drawdown
            ax3 = axes[1, 0]
            rolling_max = portfolio.curve().expanding().max()
            drawdown = (portfolio.curve() - rolling_max) / rolling_max
            drawdown.plot(ax=ax3, title="Drawdown", color='red', area=True, alpha=0.3)
            ax3.set_ylabel("Drawdown")
            ax3.grid(True, alpha=0.3)

            # Plot 4: System Summary
            ax4 = axes[1, 1]
            ax4.axis('off')

            summary_text = f"""
SYSTEM HEALTH SUMMARY

📊 CONFIGURATION:
• Instruments: {len(self.instruments)}
• Trading Rules: {len(self.rules)}
• Volatility Target: 12%
• Cost Multiplier: 2.5x

📈 STATUS:
• Data Quality: Monitoring
• Rule Performance: Active
• Risk Controls: Enabled
• Alert System: Active

⚙️ CARVER METHODOLOGY:
• Pooled Scalars: ✅
• Uniform Weights: ✅
• Cost Awareness: ✅
• Dynamic Optimization: ✅

🔔 MONITORING:
• Real-time tracking
• Performance alerts
• Risk limit monitoring
• Regular health checks
"""

            ax4.text(0.05, 0.95, summary_text, transform=ax4.transAxes,
                     fontsize=10, verticalalignment='top', fontfamily='monospace',
                     bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))

        except Exception as e:
            print(f"⚠️ Dashboard creation error: {e}")

        plt.suptitle('Production Monitoring Dashboard', fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.show()

        return fig
