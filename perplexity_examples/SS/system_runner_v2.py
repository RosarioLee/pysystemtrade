# system_runner_v2.py - Enhanced ETF System Runner v1.3 - FIXED

import os
import sys
import warnings

warnings.filterwarnings('ignore')

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from perplexity_examples.enhanced_etf_system import EnhancedETFSystem
from perplexity_examples.SS.performance_calculator import EnhancedPerformanceCalculator
from production_monitor import ProductionMonitor


def main_v2(development_mode=True, test_mode=False, max_instruments=32):
    """Enhanced ETF System v1.3 - Production Ready - FIXED"""
    print("ðŸš€ Enhanced ETF System v1.3 - FIXED")
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
            print("âŒ No data downloaded - aborting")
            return None

        system = etf_system.create_carver_compliant_system()
        if system is None:
            print("âŒ System creation failed")
            return None

        # Step 3: Enhanced Analysis (FIXED ERROR HANDLING)
        print("Running enhanced analysis...")
        compliance_report = etf_system.verify_carver_compliance(system)

        # Use the NEW comprehensive performance calculator with FIXED error handling
        try:
            calculator = EnhancedPerformanceCalculator(target_vol=0.12)
            comprehensive_performance = calculator.calculate_comprehensive_performance(system)

            if comprehensive_performance is None:
                print("âš ï¸ Using fallback performance calculation")
                # Fallback to basic performance calculation
                basic_performance = calculator.calculate_portfolio_performance(system)
                if basic_performance:
                    # Convert basic performance to comprehensive format
                    comprehensive_performance = {
                        'portfolio_metrics': basic_performance,
                        'rule_performance': {},
                        'instrument_performance': {},
                        'cost_analysis': {},
                        'etf_statistics': {}
                    }
                else:
                    comprehensive_performance = None

        except Exception as e:
            print(f"âŒ Performance calculation error: {e}")
            comprehensive_performance = None

        monitor = ProductionMonitor(system, etf_system.monitoring_config)
        health_report = monitor.run_full_health_check()

        # NEW: Run enhanced performance analysis with FIXED error handling
        enhanced_analysis = None
        try:
            if comprehensive_performance is not None:
                enhanced_analysis = monitor.run_enhanced_performance_analysis_separated(comprehensive_performance)
            else:
                print("âš ï¸ Skipping enhanced analysis due to performance calculation failure")
        except Exception as e:
            print(f"âš ï¸ Enhanced analysis failed, continuing with basic analysis: {e}")

        # Step 4: FIXED Dashboard (avoid duplication)
        print("Creating dashboard...")
        if enhanced_analysis is not None:
            print("ðŸ“Š Using enhanced dashboard")
            # Don't create basic dashboard if enhanced succeeded
        else:
            print("ðŸ“Š Using basic dashboard")
            dashboard = monitor.create_monitoring_dashboard()

        # Step 5: Generate final report with FIXED key access
        deployment_status = generate_deployment_report_fixed(
            system, compliance_report, comprehensive_performance, health_report
        )

        results = {
            'system': system,
            'compliance_report': compliance_report,
            'performance_metrics': comprehensive_performance,  # This is the comprehensive report
            'health_report': health_report,
            'deployment_status': deployment_status,
            'monitor': monitor,
            'calculator': calculator
        }

        print_summary_fixed(results)
        return results

    except Exception as e:
        print(f"âŒ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_deployment_report_fixed(system, compliance, performance, health):
    """Generate production deployment readiness report - FIXED VERSION"""
    deployment_score = 0
    max_score = 100
    issues = []

    # Carver compliance (25 points)
    if compliance['scalar_compliance'] and compliance['weight_compliance']:
        deployment_score += 25
    else:
        issues.append("Carver methodology compliance issues")

    # Performance metrics (25 points) - FIXED ACCESS
    if performance and performance.get('portfolio_metrics'):
        pm = performance['portfolio_metrics']  # Access nested metrics
        if pm.get('sharpe_ratio', 0) > 0.3:
            deployment_score += 15
        if pm.get('max_drawdown', 0) > -0.2:
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


def print_summary_fixed(results):
    """Print concise summary - FIXED VERSION"""
    print(f"\nâœ… Analysis Complete - {len(results['system'].get_instrument_list())} instruments")

    if results['performance_metrics'] and results['performance_metrics'].get('portfolio_metrics'):
        pm = results['performance_metrics']['portfolio_metrics']  # Access nested metrics
        print(
            f"ðŸ“ˆ Sharpe: {pm.get('sharpe_ratio', 0):.3f} | Return: {pm.get('annual_return', 0):.1%} | DD: {pm.get('max_drawdown', 0):.1%}")
    else:
        print("ðŸ“ˆ Performance metrics not available")

    deployment = results['deployment_status']
    print(f"ðŸš€ Status: {deployment['status']} ({deployment['score']}/100)")

    if deployment['issues']:
        print("âš ï¸ Issues:", ", ".join(deployment['issues']))


if __name__ == "__main__":
    results = main_v2(development_mode=True, test_mode=False, max_instruments=32)
    if results:
        globals().update({'final_results': results})
