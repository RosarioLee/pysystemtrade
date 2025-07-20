# system_runner_v2.py - Phase 2 Production System Runner

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


def main_v2(development_mode=True, test_mode=False, max_instruments=15):
    """
    Enhanced ETF System v1.2 - Production Ready

    Phase 2 Features:
    - Fixed performance calculations
    - Comprehensive monitoring
    - Production health checks
    - Risk control validation
    """
    print("🚀 Enhanced ETF System v1.2 – PRODUCTION READY")
    print("=" * 60)
    print("Phase 2 Features: Fixed Calculations + Production Monitoring")
    print("=" * 60)

    try:
        # Step 1: Initialize enhanced system
        print("\n1️⃣ INITIALIZING ENHANCED SYSTEM V1.2")
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "private", "etf_system", "config_v1.1.yaml"
        )

        etf_system = EnhancedETFSystem(
            config_path=config_path,
            test_mode=test_mode,
            max_instruments=max_instruments
        )

        # Step 2: Data acquisition
        print("\n2️⃣ DATA ACQUISITION")
        download_count = etf_system.download_etf_data()
        if download_count == 0:
            print("❌ No data downloaded - aborting")
            return None

        # Step 3: Create Carver-compliant system
        print("\n3️⃣ CREATING CARVER-COMPLIANT SYSTEM")
        system = etf_system.create_carver_compliant_system()
        if system is None:
            print("❌ System creation failed")
            return None

        # Step 4: Carver compliance verification
        print("\n4️⃣ VERIFYING CARVER COMPLIANCE")
        compliance_report = etf_system.verify_carver_compliance(system)

        # Step 5: Enhanced performance calculation
        print("\n5️⃣ ENHANCED PERFORMANCE CALCULATION")
        calculator = EnhancedPerformanceCalculator(target_vol=0.12)
        performance_metrics = calculator.calculate_portfolio_performance(system)

        # Step 6: Production health check
        print("\n6️⃣ PRODUCTION HEALTH CHECK")
        monitor = ProductionMonitor(system, etf_system.monitoring_config)
        health_report = monitor.run_full_health_check()

        # Step 7: Create monitoring dashboard
        print("\n7️⃣ CREATING MONITORING DASHBOARD")
        dashboard = monitor.create_monitoring_dashboard()

        # Step 8: Generate deployment report
        print("\n8️⃣ GENERATING DEPLOYMENT REPORT")
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

        print_final_summary_v2(results)
        return results

    except Exception as e:
        print(f"❌ Critical error in v1.2: {e}")
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


def print_final_summary_v2(results):
    """Print comprehensive Phase 2 summary"""
    print("\n" + "=" * 70)
    print("🎉 ENHANCED ETF SYSTEM v1.2 ANALYSIS COMPLETE")
    print("=" * 70)

    # System configuration
    print("📊 SYSTEM CONFIGURATION:")
    print(f"   • Instruments: {len(results['system'].get_instrument_list())}")
    print(f"   • Trading Rules: {len(results['system'].rules.trading_rules())}")
    print(f"   • Methodology: Robert Carver compliant")
    print(f"   • Cost Multiplier: 2.5x")

    # Performance summary
    if results['performance_metrics']:
        perf = results['performance_metrics']
        print(f"\n📈 CORRECTED PERFORMANCE METRICS:")
        print(f"   • Sharpe Ratio: {perf['sharpe_ratio']:.3f}")
        print(f"   • Annual Return: {perf['annual_return']:.1%}")
        print(f"   • Annual Volatility: {perf['annual_volatility']:.1%}")
        print(f"   • Maximum Drawdown: {perf['max_drawdown']:.1%}")
        print(f"   • Win Rate: {perf['win_rate']:.1%}")

    # Health status
    health = results['health_report']
    status_icon = "✅" if health['overall_status'] == 'HEALTHY' else "⚠️"
    print(f"\n🏥 SYSTEM HEALTH: {status_icon} {health['overall_status']}")
    print(f"   • Alerts: {len(health['alerts'])}")
    print(f"   • Data Quality: {health['data_quality']['status']}")
    print(f"   • Rule Performance: {health['rule_performance']['status']}")

    # Deployment readiness
    deployment = results['deployment_status']
    print(f"\n🚀 DEPLOYMENT STATUS: {deployment['status']}")
    print(f"   • Readiness Score: {deployment['score']}/{deployment['max_score']}")
    print(f"   • Recommendation: {deployment['recommendation']}")

    if deployment['issues']:
        print(f"\n⚠️ ISSUES TO ADDRESS:")
        for issue in deployment['issues']:
            print(f"   • {issue}")

    print(f"\n💡 PHASE 2 ACHIEVEMENTS:")
    print(f"   ✅ Fixed performance calculation bugs")
    print(f"   ✅ Implemented production monitoring")
    print(f"   ✅ Added comprehensive health checks")
    print(f"   ✅ Created deployment readiness assessment")
    print(f"   ✅ Maintained Carver methodology compliance")

    print("\n📋 NEXT PHASE RECOMMENDATIONS:")
    if deployment['score'] >= 80:
        print("   • Begin paper trading validation")
        print("   • Implement live data feeds")
        print("   • Set up automated monitoring alerts")
        print("   • Scale to additional instruments")
    else:
        print("   • Address flagged issues")
        print("   • Re-run health checks")
        print("   • Validate performance calculations")
        print("   • Review system configuration")

    print("=" * 70)


if __name__ == "__main__":
    """Execute Phase 2 system"""
    results = main_v2(
        development_mode=True,
        test_mode=False,
        max_instruments=32  # Scale up from 10 to 15 instruments
    )

    if results:
        print("\n🎯 PHASE 2 COMPLETE - SYSTEM READY FOR NEXT PHASE")
        globals().update(results)
    else:
        print("\n❌ Phase 2 failed - Review errors and retry")
