# system_runner_v2.py - Enhanced ETF System Runner v1.2

import os
import sys
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_etf_system import EnhancedETFSystem
from performance_calculator import EnhancedPerformanceCalculator
from production_monitor import ProductionMonitor


def main_v2(development_mode=True, test_mode=False, max_instruments=32):
    """Enhanced ETF System v1.2 - Production Ready"""

    print("🚀 Enhanced ETF System v1.2")
    print("=" * 40)

    try:
        # Step 1: Initialize system
        print("Initializing system...")
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "private", "etf_system", "config_v1.1.yaml"
        )

        etf_system = EnhancedETFSystem(
            config_path=config_path,
            test_mode=test_mode,
            max_instruments=max_instruments
        )

        # Step 2: Data acquisition and system creation
        print("Acquiring data and creating system...")
        download_count = etf_system.download_etf_data()
        if download_count == 0:
            print("❌ No data downloaded - aborting")
            return None

        system = etf_system.create_carver_compliant_system()
        if system is None:
            print("❌ System creation failed")
            return None

        # Step 3: Analysis
        print("Running analysis...")
        compliance_report = etf_system.verify_carver_compliance(system)

        calculator = EnhancedPerformanceCalculator(target_vol=0.12)
        performance_metrics = calculator.calculate_portfolio_performance(system)

        monitor = ProductionMonitor(system, etf_system.monitoring_config)
        health_report = monitor.run_full_health_check()

        # Step 4: Dashboard
        print("Creating dashboard...")
        dashboard = monitor.create_monitoring_dashboard()

        # Step 5: Generate final report
        deployment_status = generate_deployment_report(
            system, compliance_report, performance_metrics, health_report
        )

        results = {
            'system': system,
            'compliance_report': compliance_report,
            'performance_metrics': performance_metrics,
            'health_report': health_report,
            'deployment_status': deployment_status,
            'monitor': monitor,
            'calculator': calculator
        }

        print_summary(results)
        return results

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_deployment_report(system, compliance, performance, health):
    """Generate production deployment readiness report"""
    deployment_score = 0
    max_score = 100
    issues = []

    # Carver compliance (25 points)
    if compliance['scalar_compliance'] and compliance['weight_compliance']:
        deployment_score += 25
    else:
        issues.append("Carver methodology compliance issues")

    # Performance metrics (25 points)
    if performance and performance['sharpe_ratio'] > 0.3:
        deployment_score += 15
    if performance and performance['max_drawdown'] > -0.2:
        deployment_score += 10
    else:
        issues.append("Performance metrics below threshold")

    # System health (25 points)
    if health['overall_status'] == 'HEALTHY':
        deployment_score += 25
    else:
        issues.append("System health warnings detected")

    # Data quality (25 points)
    if health['data_quality']['status'] == 'PASS':
        deployment_score += 25
    else:
        issues.append("Data quality issues detected")

    # Determine deployment status
    if deployment_score >= 80:
        status = "READY FOR PRODUCTION"
        recommendation = "System meets production readiness criteria"
    elif deployment_score >= 60:
        status = "READY FOR PAPER TRADING"
        recommendation = "Address minor issues before live deployment"
    else:
        status = "REQUIRES DEVELOPMENT"
        recommendation = "Significant issues must be resolved"

    return {
        'status': status,
        'score': deployment_score,
        'max_score': max_score,
        'issues': issues,
        'recommendation': recommendation
    }


def print_summary(results):
    """Print concise summary"""
    print(f"\n✅ Analysis Complete - {len(results['system'].get_instrument_list())} instruments")

    if results['performance_metrics']:
        perf = results['performance_metrics']
        print(
            f"📈 Sharpe: {perf['sharpe_ratio']:.3f} | Return: {perf['annual_return']:.1%} | DD: {perf['max_drawdown']:.1%}")

    deployment = results['deployment_status']
    print(f"🚀 Status: {deployment['status']} ({deployment['score']}/100)")

    if deployment['issues']:
        print("⚠️ Issues:", ", ".join(deployment['issues']))


if __name__ == "__main__":
    results = main_v2(development_mode=True, test_mode=False, max_instruments=32)
    if results:
        globals().update({'final_results': results})
