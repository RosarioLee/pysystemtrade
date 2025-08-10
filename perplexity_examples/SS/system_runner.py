# system_runner.py - Main execution script for Enhanced ETF System v1.1

import os
import sys
import warnings

warnings.filterwarnings('ignore')

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from perplexity_examples.enhanced_etf_system import EnhancedETFSystem


def main(development_mode=True, test_mode=False, max_instruments=10):
    """
    Progressive implementation - start with 10 instruments
    """
    print("🚀 Enhanced ETF System v1.1 – PROGRESSIVE DEPLOYMENT")
    print("=" * 60)

    # Progressive scaling approach
    if not test_mode and max_instruments > 15:
        print("⚠️ RECOMMENDATION: Start with 10-15 instruments for stability")
        max_instruments = 15

    try:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "private", "etf_system", "config_v1.1.yaml"
        )

        etf_system = EnhancedETFSystem(
            config_path=config_path,
            test_mode=False,  # Use full historical data
            max_instruments=max_instruments  # But limit instruments
        )

        # Rest of your existing code...
        if etf_system.download_etf_data() == 0:
            return None

        system = etf_system.create_carver_compliant_system()
        if system is None:
            return None

        # CRITICAL: Add compliance verification
        print("\n4️⃣ VERIFYING CARVER COMPLIANCE")
        compliance_report = etf_system.verify_carver_compliance(system)

        if compliance_report['scalar_compliance'] and compliance_report['weight_compliance']:
            print("🎉 FULL CARVER COMPLIANCE ACHIEVED")
        else:
            print("⚠️ COMPLIANCE ISSUES - Review before production")
            for issue in compliance_report['issues']:
                print(f"   • {issue}")

        # FIXED: Use standard performance calculation for smaller systems
        print(f"\n5️⃣ CALCULATING PERFORMANCE METRICS")
        if len(system.get_instrument_list()) <= 15:
            # Use standard calculation for manageable size
            perf = etf_system.calculate_performance_metrics(system)
        else:
            # Only use sampling for very large systems
            perf = etf_system.calculate_performance_metrics_optimized(system)

        return {
            "system": system,
            "compliance_report": compliance_report,
            "performance_metrics": perf
        }

    except Exception as e:
        print(f"❌ Critical error: {e}")
        import traceback
        traceback.print_exc()
        return None


def monitor_system_health(system):
    """Real-time system health monitoring"""
    print("=== SYSTEM HEALTH MONITORING ===")

    health_report = {
        'instruments': len(system.get_instrument_list()),
        'rules': len(system.rules.trading_rules()),
        'data_quality': {},
        'rule_activity': {},
        'alerts': []
    }

    # Check data quality
    for instrument in system.get_instrument_list()[:5]:  # Sample check
        try:
            prices = system.rawdata.get_daily_prices(instrument)
            health_report['data_quality'][instrument] = {
                'length': len(prices),
                'last_date': prices.index[-1],
                'null_count': prices.isnull().sum()
            }
        except Exception as e:
            health_report['alerts'].append(f"Data issue for {instrument}: {e}")

    # Check rule activity
    for rule_name in list(system.rules.trading_rules().keys())[:3]:  # Sample check
        try:
            forecast = system.forecastScaleCap.get_scaled_forecast('IVV', rule_name)
            health_report['rule_activity'][rule_name] = {
                'mean_forecast': forecast.tail(252).mean(),
                'forecast_std': forecast.tail(252).std(),
                'last_forecast': forecast.iloc[-1]
            }
        except Exception as e:
            health_report['alerts'].append(f"Rule issue for {rule_name}: {e}")

    # Display health summary
    print(f"📊 Instruments: {health_report['instruments']}")
    print(f"🎯 Trading Rules: {health_report['rules']}")
    print(f"🚨 Alerts: {len(health_report['alerts'])}")

    if health_report['alerts']:
        for alert in health_report['alerts']:
            print(f"   ⚠️ {alert}")
    else:
        print("✅ All systems healthy")

    return health_report


if __name__ == "__main__":
    """Execute main function when run directly"""
    # Run with 10 carefully selected instruments
    results = main(development_mode=True, test_mode=False, max_instruments=10)

    if results:
        print("\n💡 NEXT STEPS:")
        print("1. Review monitoring dashboards for system health")
        print("2. Analyze performance attribution by rule type")
        print("3. Monitor forecast scalar evolution over time")
        print("4. Assess cost impact of breakout rules")
        print("5. Consider additional rule diversification")
        print("\n📊 Access results through 'results' variable")

        # Make results available for interactive analysis
        globals().update(results)
    else:
        print("\n❌ Analysis failed. Please check configuration and try again.")
