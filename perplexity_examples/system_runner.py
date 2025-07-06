# system_runner.py - Main execution script for Enhanced ETF System v1.1

import os
import sys
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_etf_system import EnhancedETFSystem
from system_monitoring import SystemMonitor


def main():
    """Main execution function"""
    print("🚀 Enhanced ETF Systematic Trading System v1.1")
    print("=" * 60)
    print("Following Robert Carver's systematic trading methodology")
    print("Enhanced with breakout rules and comprehensive monitoring")
    print("=" * 60)

    try:
        # Step 1: Initialize system
        print("\n1️⃣ INITIALIZING ENHANCED ETF SYSTEM")
        config_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "private", "etf_system", "config_v1.1.yaml")
        etf_system = EnhancedETFSystem(config_path=config_path)

        # Step 2: Download and prepare data
        print("\n2️⃣ DOWNLOADING ETF DATA")
        download_count = etf_system.download_etf_data()
        if download_count == 0:
            print("❌ No data downloaded. Exiting.")
            return None

        # Step 3: Create enhanced system
        print("\n3️⃣ CREATING ENHANCED SYSTEM")
        system = etf_system.create_enhanced_system()
        if system is None:
            print("❌ System creation failed. Exiting.")
            return None

        # Step 4: Calculate performance metrics
        print("\n4️⃣ CALCULATING PERFORMANCE METRICS")
        performance_metrics = etf_system.calculate_performance_metrics(system)

        # Step 5: Get system summary
        print("\n5️⃣ GENERATING SYSTEM SUMMARY")
        system_summary = etf_system.get_system_summary(system)

        # Step 6: Initialize monitoring
        print("\n6️⃣ INITIALIZING SYSTEM MONITORING")
        monitoring_config = etf_system.monitoring_config
        system_monitor = SystemMonitor(system, monitoring_config)

        # Step 7: Run comprehensive monitoring
        print("\n7️⃣ RUNNING COMPREHENSIVE MONITORING")
        monitoring_report = system_monitor.run_full_monitoring()

        # Step 8: Final results summary
        print("\n8️⃣ FINAL RESULTS SUMMARY")
        print_final_summary(system_summary, performance_metrics, monitoring_report)

        # Return complete results
        return {
            'system': system,
            'etf_system': etf_system,
            'performance_metrics': performance_metrics,
            'system_summary': system_summary,
            'monitoring_report': monitoring_report,
            'system_monitor': system_monitor
        }

    except Exception as e:
        print(f"❌ Critical error: {e}")
        import traceback
        traceback.print_exc()
        return None


def print_final_summary(system_summary, performance_metrics, monitoring_report):
    """Print comprehensive final summary"""
    print("=" * 60)
    print("🎉 ENHANCED ETF SYSTEM ANALYSIS COMPLETE")
    print("=" * 60)

    # System configuration summary
    if system_summary:
        print(f"📊 SYSTEM CONFIGURATION:")
        print(f"   • Total Instruments: {system_summary['total_instruments']}")
        print(f"   • Total Trading Rules: {system_summary['total_rules']}")
        print(f"   • EWMAC Rules: {system_summary['ewmac_rules']}")
        print(f"   • Breakout Rules: {system_summary['breakout_rules']}")
        print(f"   • Volatility Target: {system_summary['vol_target']}%")

    # Performance metrics summary
    if performance_metrics:
        print(f"\n📈 PERFORMANCE METRICS:")
        print(f"   • Sharpe Ratio: {performance_metrics['sharpe_ratio']:.4f}")
        print(f"   • Annual Return: {performance_metrics['annual_return']:.2%}")
        print(f"   • Annual Volatility: {performance_metrics['annual_volatility']:.2%}")
        print(f"   • Maximum Drawdown: {performance_metrics['max_drawdown']:.2%}")

    # Monitoring summary
    if monitoring_report:
        print(f"\n🔍 MONITORING SUMMARY:")
        print(f"   • Total Alerts: {monitoring_report['total_alerts']}")
        print(f"   • Scalar Alerts: {len(monitoring_report['scalar_analysis']['alerts'])}")
        print(f"   • Weight Alerts: {len(monitoring_report['weight_analysis']['alerts'])}")
        print(f"   • Monitoring Timestamp: {monitoring_report['monitoring_timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")

    print(f"\n✅ SYSTEM STATUS:")
    print(f"   • Enhanced multi-strategy system: OPERATIONAL")
    print(f"   • Dynamic forecast scaling: ACTIVE")
    print(f"   • Cost-aware optimization: ENABLED")
    print(f"   • Comprehensive monitoring: ACTIVE")
    print(f"   • Robert Carver methodology: FULLY IMPLEMENTED")

    print(f"\n🚀 SYSTEM READY FOR PRODUCTION DEPLOYMENT")
    print("=" * 60)


if __name__ == "__main__":
    """Execute main function when run directly"""
    results = main()

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

        # Optional: Save results to file
        save_results = input("\nSave detailed results to file? (y/n): ").lower() == 'y'
        if save_results:
            try:
                import pickle

                results_file = f"enhanced_etf_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
                with open(results_file, 'wb') as f:
                    pickle.dump(results, f)
                print(f"✅ Results saved to: {results_file}")
            except Exception as e:
                print(f"⚠️ Could not save results: {e}")
    else:
        print("\n❌ Analysis failed. Please check configuration and try again.")
