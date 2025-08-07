import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings

# Import the performance calculator
from performance_calculator_v3 import SimplePerformanceCalculator

warnings.filterwarnings('ignore')


class SimpleProductionMonitor:
    def __init__(self, system):
        self.system = system
        self.instruments = system.get_instrument_list()
        self.rules = system.rules.trading_rules() if hasattr(system, 'rules') else {}

    def run_health_check(self):
        results = {
            'timestamp': datetime.now(),
            'data_quality': self._check_data_quality(),
            'system_performance': self._check_system_performance(),
            'rule_performance': self._check_rule_performance()
        }

        # Determine overall status
        issues = sum([
            1 for check in results.values()
            if isinstance(check, dict) and check.get('status') == 'WARN'
        ])

        results['overall_status'] = 'HEALTHY' if issues == 0 else 'WARNING'
        return results

    def _check_data_quality(self):
        stale_count = 0
        total_instruments = len(self.instruments)

        try:
            for instrument in self.instruments:
                prices = self.system.rawdata.get_daily_prices(instrument)
                if prices is not None and len(prices) > 0:
                    last_date = prices.index[-1]
                    days_old = (datetime.now().date() - last_date.date()).days
                    if days_old > 5:  # Consider data stale after 5 days
                        stale_count += 1
        except Exception as e:
            return {'status': 'ERROR', 'message': str(e)}

        stale_percentage = stale_count / total_instruments if total_instruments > 0 else 0
        status = 'HEALTHY' if stale_percentage < 0.1 else 'WARN'

        return {
            'status': status,
            'stale_instruments': stale_count,
            'total_instruments': total_instruments,
            'stale_percentage': stale_percentage
        }

    def _check_system_performance(self):
        # Now this will work because we imported SimplePerformanceCalculator
        calc = SimplePerformanceCalculator()
        performance = calc.calculate_performance(self.system)

        if performance is None:
            return {'status': 'ERROR', 'message': 'Could not calculate performance'}

        # Check thresholds
        issues = []
        if performance['sharpe_ratio'] < 0.2:
            issues.append(f"Low Sharpe ratio: {performance['sharpe_ratio']:.3f}")
        if performance['max_drawdown'] < -0.25:
            issues.append(f"High drawdown: {performance['max_drawdown']:.1%}")

        status = 'HEALTHY' if len(issues) == 0 else 'WARN'

        return {
            'status': status,
            'issues': issues,
            'metrics': performance
        }

    def _check_rule_performance(self):
        rule_metrics = {}
        total_issues = 0

        sample_instruments = self.instruments[:min(3, len(self.instruments))]

        for rule_name in list(self.rules.keys())[:5]:  # Check first 5 rules
            rule_sharpes = []

            for instrument in sample_instruments:
                try:
                    rule_returns = self._get_rule_returns(instrument, rule_name)
                    if rule_returns is not None and len(rule_returns) > 50:
                        sharpe = (rule_returns.mean() / rule_returns.std()) * (252 ** 0.5)
                        if not np.isnan(sharpe):
                            rule_sharpes.append(sharpe)
                except:
                    continue

            if rule_sharpes:
                avg_sharpe = np.mean(rule_sharpes)
                rule_metrics[rule_name] = {
                    'avg_sharpe': float(avg_sharpe),
                    'instruments_tested': len(rule_sharpes)
                }

                if avg_sharpe < 0.1:
                    total_issues += 1

        status = 'HEALTHY' if total_issues <= 1 else 'WARN'

        return {
            'status': status,
            'issues_count': total_issues,
            'rule_metrics': rule_metrics
        }

    def _get_rule_returns(self, instrument, rule_name):
        try:
            pnl = self.system.accounts.pandl_for_trading_rule(instrument, rule_name)
            if pnl is not None:
                returns = pnl.pct_change().dropna()
                return returns if len(returns) > 0 else None
        except:
            pass
        return None

    def display_summary(self, health_results):
        print("=" * 50)
        print("SYSTEM HEALTH SUMMARY")
        print("=" * 50)
        print(f"Overall Status: {health_results['overall_status']}")
        print(f"Check Time: {health_results['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")

        # Data Quality
        dq = health_results['data_quality']
        print(f"\nData Quality: {dq['status']}")
        if dq['status'] != 'ERROR':
            print(f"  Stale instruments: {dq['stale_instruments']}/{dq['total_instruments']}")

        # System Performance
        sp = health_results['system_performance']
        print(f"\nSystem Performance: {sp['status']}")
        if 'metrics' in sp:
            m = sp['metrics']
            print(f"  Sharpe Ratio: {m['sharpe_ratio']:.3f}")
            print(f"  Annual Return: {m['annual_return']:.1%}")
            print(f"  Max Drawdown: {m['max_drawdown']:.1%}")
            print(f"  Win Rate: {m['win_rate']:.1%}")

        # Rule Performance
        rp = health_results['rule_performance']
        print(f"\nRule Performance: {rp['status']}")
        print(f"  Issues found: {rp['issues_count']}")

        print("=" * 50)
