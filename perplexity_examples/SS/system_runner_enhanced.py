# system_runner_enhanced.py - Enhanced ETF System Runner v2.0

import os
import sys
import json
from datetime import datetime
import warnings
from typing import Dict, Any, Optional
import logging

warnings.filterwarnings("ignore")

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import required modules
try:
    from perplexity_examples.enhanced_etf_system import EnhancedETFSystem
except ImportError:
    # Fallback to your existing ETF system
    print("Warning: Using fallback ETF system")
    try:
        from your_etf_system_file import YourETFSystemClass as EnhancedETFSystem
    except ImportError:
        print("Error: No ETF system found")
        sys.exit(1)

# Import performance calculator and production monitor
try:
    from performance_calculator_enhanced import AdvancedPerformanceCalculator
except ImportError as e:
    print(f"Warning: Could not import AdvancedPerformanceCalculator: {e}")
    AdvancedPerformanceCalculator = None

try:
    from production_monitor_enhanced import AdvancedProductionMonitor
except ImportError as e:
    print(f"Warning: Could not import AdvancedProductionMonitor: {e}")
    AdvancedProductionMonitor = None


class EnhancedSystemRunner:
    """Enhanced ETF System Runner with comprehensive analysis and monitoring"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self.logger = logger

    def _get_default_config_path(self) -> str:
        """Get default configuration path"""
        return os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "private",
            "etf_system",
            "config_v1.1.yaml",
        )

    def run_comprehensive_analysis(
        self,
        development_mode: bool = True,
        test_mode: bool = False,
        max_instruments: int = 32,
        save_results: bool = True,
        create_dashboards: bool = True,
        run_stress_tests: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Run comprehensive ETF system analysis"""

        print("🚀 Enhanced ETF System Runner v2.0")
        print("=" * 50)

        start_time = datetime.now()

        try:
            # Step 1: Initialize and create system
            system_results = self._initialize_system(test_mode, max_instruments)
            if not system_results:
                return None

            system = system_results["system"]
            etf_system = system_results["etf_system"]

            # Step 2: Run comprehensive performance analysis
            performance_results = self._run_performance_analysis(system)

            # Step 3: Run advanced monitoring and health checks
            monitoring_results = self._run_monitoring_analysis(
                system,
                etf_system,
                performance_results,
                create_dashboards,
                run_stress_tests,
            )

            # Step 4: Generate deployment assessment
            deployment_results = self._generate_deployment_assessment(
                system, performance_results, monitoring_results
            )

            # Step 5: Create comprehensive report
            comprehensive_results = {
                "system": system,
                "etf_system": etf_system,
                "performance_analysis": performance_results,
                "monitoring_results": monitoring_results,
                "deployment_assessment": deployment_results,
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "timestamp": datetime.now(),
                "configuration": {
                    "development_mode": development_mode,
                    "test_mode": test_mode,
                    "max_instruments": max_instruments,
                    "create_dashboards": create_dashboards,
                    "run_stress_tests": run_stress_tests,
                },
            }

            # Step 6: Save results if requested
            if save_results:
                self._save_results(comprehensive_results)

            # Step 7: Display summary
            self._display_comprehensive_summary(comprehensive_results)

            return comprehensive_results

        except Exception as e:
            self.logger.error(f"Comprehensive analysis failed: {e}")
            import traceback

            traceback.print_exc()
            return None

    def _initialize_system(
        self, test_mode: bool, max_instruments: int
    ) -> Optional[Dict[str, Any]]:
        """Initialize the ETF system"""

        print("🔧 Initializing Enhanced ETF System...")

        try:
            # Initialize ETF system
            etf_system = EnhancedETFSystem(
                config_path=self.config_path,
                test_mode=test_mode,
                max_instruments=max_instruments,
            )

            # Download data
            print("📊 Acquiring market data...")
            download_count = etf_system.download_etf_data()
            if download_count == 0:
                print("❌ No data downloaded - aborting")
                return None

            # Create system
            print("🏗️ Creating trading system...")
            system = etf_system.create_carver_compliant_system()
            if system is None:
                print("❌ System creation failed")
                return None

            # Verify compliance
            print("✅ Verifying Carver methodology compliance...")
            compliance_report = etf_system.verify_carver_compliance(system)

            return {
                "system": system,
                "etf_system": etf_system,
                "compliance_report": compliance_report,
                "download_count": download_count,
            }

        except Exception as e:
            self.logger.error(f"System initialization failed: {e}")
            return None

    def _run_performance_analysis(self, system) -> Optional[Dict[str, Any]]:
        """Run comprehensive performance analysis"""

        print("📈 Running Advanced Performance Analysis...")

        try:
            if AdvancedPerformanceCalculator is None:
                print(
                    "⚠️ AdvancedPerformanceCalculator not available, using basic analysis"
                )
                return self._run_basic_performance_analysis(system)

            calculator = AdvancedPerformanceCalculator(target_vol=0.12)

            # Run comprehensive analysis
            performance_results = calculator.calculate_comprehensive_performance(system)

            if performance_results is None:
                print("⚠️ Performance analysis failed, attempting fallback...")
                # Fallback to basic calculation
                basic_results = calculator._calculate_advanced_portfolio_metrics(system)
                if basic_results:
                    performance_results = {
                        "portfolio_metrics": basic_results,
                        "rule_performance": {},
                        "instrument_performance": {},
                        "risk_analysis": {},
                        "status": "fallback_mode",
                    }

            return performance_results

        except Exception as e:
            self.logger.error(f"Performance analysis failed: {e}")
            return self._run_basic_performance_analysis(system)

    def _run_basic_performance_analysis(self, system) -> Dict[str, Any]:
        """Basic fallback performance analysis"""

        print("📈 Running Basic Performance Analysis...")

        try:
            portfolio = system.accounts.portfolio()
            if portfolio is None:
                return {"error": "Portfolio not available"}

            # Get basic portfolio curve
            curve = portfolio.curve()
            if len(curve) == 0:
                return {"error": "No portfolio data"}

            # Calculate basic returns
            returns = curve.pct_change().dropna()
            if len(returns) == 0:
                return {"error": "No return data"}

            # Basic metrics
            annual_return = returns.mean() * 252
            annual_vol = returns.std() * np.sqrt(252)
            sharpe_ratio = annual_return / annual_vol if annual_vol > 0 else 0

            # Basic drawdown
            cumulative = (1 + returns).cumprod()
            rolling_max = cumulative.expanding().max()
            drawdown = (cumulative - rolling_max) / rolling_max
            max_drawdown = drawdown.min()

            return {
                "portfolio_metrics": {
                    "sharpe_ratio": float(sharpe_ratio),
                    "annual_return": float(annual_return),
                    "annual_volatility": float(annual_vol),
                    "max_drawdown": float(max_drawdown),
                    "win_rate": float((returns > 0).mean()),
                    "var_95": float(returns.quantile(0.05)),
                    "trading_days": len(returns),
                },
                "status": "basic_analysis",
            }

        except Exception as e:
            self.logger.error(f"Basic performance analysis failed: {e}")
            return {"error": str(e)}

    def _run_monitoring_analysis(
        self,
        system,
        etf_system,
        performance_results: Optional[Dict[str, Any]],
        create_dashboards: bool = True,
        run_stress_tests: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Run advanced monitoring and health analysis"""

        print("🏥 Running Advanced System Monitoring...")

        try:
            if AdvancedProductionMonitor is None:
                print(
                    "⚠️ AdvancedProductionMonitor not available, using basic monitoring"
                )
                return self._run_basic_monitoring(system, performance_results)

            monitor = AdvancedProductionMonitor(
                system,
                etf_system.monitoring_config
                if hasattr(etf_system, "monitoring_config")
                else {},
            )

            # Run comprehensive health check
            health_results = monitor.run_comprehensive_health_check()

            # Create advanced dashboards
            dashboard_results = None
            if create_dashboards and performance_results:
                try:
                    print("📊 Creating advanced visualization dashboards...")
                    dashboard_results = monitor.create_advanced_dashboards(
                        performance_results
                    )
                except Exception as e:
                    self.logger.warning(f"Dashboard creation failed: {e}")
                    dashboard_results = {"error": str(e)}

            # Run stress testing
            stress_results = None
            if run_stress_tests:
                try:
                    print("🧪 Running stress testing scenarios...")
                    stress_results = monitor.run_stress_testing()
                except Exception as e:
                    self.logger.warning(f"Stress testing failed: {e}")
                    stress_results = {"error": str(e)}

            return {
                "health_check": health_results,
                "dashboard_results": dashboard_results,
                "stress_testing": stress_results,
                "monitor": monitor,
            }

        except Exception as e:
            self.logger.error(f"Monitoring analysis failed: {e}")
            return self._run_basic_monitoring(system, performance_results)

    def _run_basic_monitoring(self, system, performance_results) -> Dict[str, Any]:
        """Basic fallback monitoring"""

        print("🏥 Running Basic System Monitoring...")

        return {
            "health_check": {
                "overall_status": "UNKNOWN",
                "message": "Advanced monitoring not available",
            },
            "dashboard_results": {"status": "not_available"},
            "stress_testing": {"status": "not_available"},
        }

    def _generate_deployment_assessment(
        self,
        system,
        performance_results: Optional[Dict[str, Any]],
        monitoring_results: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate comprehensive deployment readiness assessment"""

        print("🚀 Generating Deployment Assessment...")

        deployment_score = 0
        max_score = 100
        issues = []
        recommendations = []

        # Performance assessment (40 points)
        if performance_results and performance_results.get("portfolio_metrics"):
            pm = performance_results["portfolio_metrics"]

            sharpe = pm.get("sharpe_ratio", 0)
            max_dd = pm.get("max_drawdown", 0)
            vol = pm.get("annual_volatility", 0)

            if sharpe > 0.5:
                deployment_score += 20
            elif sharpe > 0.3:
                deployment_score += 15
            elif sharpe > 0.1:
                deployment_score += 10
            else:
                issues.append(f"Low Sharpe ratio: {sharpe:.3f}")

            if max_dd > -0.15:
                deployment_score += 15
            elif max_dd > -0.25:
                deployment_score += 10
            else:
                issues.append(f"High maximum drawdown: {max_dd:.1%}")

            if 0.08 <= vol <= 0.18:
                deployment_score += 5
            else:
                issues.append(f"Volatility outside target range: {vol:.1%}")
        else:
            issues.append("Performance analysis incomplete")

        # System health assessment (30 points)
        if monitoring_results and monitoring_results.get("health_check"):
            health = monitoring_results["health_check"]

            overall_status = health.get("overall_status", "UNKNOWN")
            if overall_status == "HEALTHY":
                deployment_score += 25
            elif overall_status == "WARNING":
                deployment_score += 15
            else:
                issues.append("System health concerns detected")

            # Check individual health components
            detailed_checks = health.get("detailed_checks", {})
            passed_checks = sum(
                1 for check in detailed_checks.values() if check.get("status") == "PASS"
            )
            total_checks = len(detailed_checks)

            if total_checks > 0:
                health_percentage = passed_checks / total_checks
                if health_percentage >= 0.8:
                    deployment_score += 5
                elif health_percentage >= 0.6:
                    deployment_score += 3

        # Basic system checks (20 points for fallback)
        if system is not None:
            deployment_score += 10  # System created successfully

            # Check number of instruments
            instruments = system.get_instrument_list()
            if len(instruments) >= 10:
                deployment_score += 10
            elif len(instruments) >= 5:
                deployment_score += 5
            else:
                issues.append(f"Low instrument count: {len(instruments)}")

        # Determine deployment status
        if deployment_score >= 85:
            status = "READY FOR PRODUCTION"
            recommendation = "System meets all production readiness criteria"
        elif deployment_score >= 70:
            status = "READY FOR PAPER TRADING"
            recommendation = "Address minor issues before live deployment"
        elif deployment_score >= 50:
            status = "REQUIRES IMPROVEMENT"
            recommendation = "Significant improvements needed before deployment"
        else:
            status = "NOT READY"
            recommendation = "Major issues must be resolved before consideration"

        # Generate recommendations
        if deployment_score < 85:
            recommendations.extend(
                [
                    "Conduct extended paper trading period",
                    "Monitor system closely during initial deployment",
                    "Implement additional risk controls",
                ]
            )

        if len(issues) > 3:
            recommendations.append("Prioritize addressing critical issues first")

        return {
            "status": status,
            "score": deployment_score,
            "max_score": max_score,
            "percentage": (deployment_score / max_score) * 100,
            "issues": issues,
            "recommendations": recommendations,
            "recommendation": recommendation,
        }

    def _save_results(self, results: Dict[str, Any]):
        """Save comprehensive results"""

        try:
            # Create results directory
            results_dir = os.path.join(os.path.dirname(__file__), "results")
            os.makedirs(results_dir, exist_ok=True)

            # Save summary results (without system objects)
            summary_results = {
                "performance_analysis": results.get("performance_analysis"),
                "deployment_assessment": results.get("deployment_assessment"),
                "execution_time": results.get("execution_time"),
                "timestamp": results.get("timestamp").isoformat()
                if results.get("timestamp")
                else None,
                "configuration": results.get("configuration"),
                "monitoring_summary": {
                    "health_status": results.get("monitoring_results", {})
                    .get("health_check", {})
                    .get("overall_status"),
                    "stress_test_score": results.get("monitoring_results", {})
                    .get("stress_testing", {})
                    .get("overall_assessment", {})
                    .get("overall_stress_score"),
                },
            }

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"enhanced_etf_system_analysis_{timestamp}.json"
            filepath = os.path.join(results_dir, filename)

            with open(filepath, "w") as f:
                json.dump(summary_results, f, indent=2, default=str)

            print(f"📁 Results saved to: {filepath}")

        except Exception as e:
            self.logger.warning(f"Failed to save results: {e}")

    def _display_comprehensive_summary(self, results: Dict[str, Any]):
        """Display comprehensive summary of all analyses"""

        if results is None:
            print("❌ No results to display")
            return

        print(f"\n" + "=" * 80)
        print(f"📊 ENHANCED ETF SYSTEM COMPREHENSIVE ANALYSIS SUMMARY v2.0")
        print(f"=" * 80)

        # System Information
        system = results.get("system")
        if system:
            print(f"\n🏗️ SYSTEM CONFIGURATION:")
            print(f" • Instruments: {len(system.get_instrument_list())}")
            print(
                f" • Trading Rules: {len(system.rules.trading_rules()) if hasattr(system, 'rules') else 0}"
            )
            print(
                f" • Analysis Duration: {results.get('execution_time', 0):.1f} seconds"
            )

        # Performance Summary
        perf = results.get("performance_analysis", {})
        if perf and perf.get("portfolio_metrics"):
            pm = perf["portfolio_metrics"]
            print(f"\n📈 PERFORMANCE SUMMARY:")
            print(f" • Sharpe Ratio: {pm.get('sharpe_ratio', 0):.3f}")
            print(f" • Annual Return: {pm.get('annual_return', 0):.1%}")
            print(f" • Maximum Drawdown: {pm.get('max_drawdown', 0):.1%}")
            print(f" • Win Rate: {pm.get('win_rate', 0):.1%}")
            print(f" • Volatility: {pm.get('annual_volatility', 0):.1%}")
            print(f" • VaR (95%): {pm.get('var_95', 0):.2%}")

        # Health Status
        health = results.get("monitoring_results", {}).get("health_check", {})
        if health:
            print(f"\n🏥 SYSTEM HEALTH:")
            print(f" • Overall Status: {health.get('overall_status', 'Unknown')}")

        # Deployment Assessment
        deployment = results.get("deployment_assessment", {})
        if deployment:
            print(f"\n🚀 DEPLOYMENT READINESS:")
            print(f" • Status: {deployment.get('status', 'Unknown')}")
            print(
                f" • Score: {deployment.get('score', 0)}/{deployment.get('max_score', 100)} "
                f"({deployment.get('percentage', 0):.1f}%)"
            )
            print(
                f" • Recommendation: {deployment.get('recommendation', 'No recommendation')}"
            )

            issues = deployment.get("issues", [])
            if issues:
                print(f" • Critical Issues ({len(issues)}):")
                for issue in issues[:3]:  # Show top 3 issues
                    print(f"   - {issue}")
                if len(issues) > 3:
                    print(f"   - ... and {len(issues) - 3} more")

        print(
            f"\n📅 Analysis completed: {results.get('timestamp', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print(f"=" * 80)


def main():
    """Main execution function with enhanced options"""

    runner = EnhancedSystemRunner()

    # Run comprehensive analysis with all features enabled
    results = runner.run_comprehensive_analysis(
        development_mode=True,
        test_mode=False,
        max_instruments=32,
        save_results=True,
        create_dashboards=True,
        run_stress_tests=True,
    )

    if results:
        # Store results globally for interactive use
        globals().update({"enhanced_results": results})
        print(
            f"\n✅ Enhanced analysis complete! Results stored in 'enhanced_results' variable."
        )

        # Display additional info
        performance = results.get("performance_analysis", {})
        if performance and performance.get("portfolio_metrics"):
            pm = performance["portfolio_metrics"]
            print(f"\n🎯 Quick Summary:")
            print(f" • Sharpe: {pm.get('sharpe_ratio', 0):.3f}")
            print(f" • Return: {pm.get('annual_return', 0):.1%}")
            print(f" • Drawdown: {pm.get('max_drawdown', 0):.1%}")

        deployment = results.get("deployment_assessment", {})
        if deployment:
            print(f" • Deployment: {deployment.get('status', 'Unknown')}")
            print(f" • Score: {deployment.get('percentage', 0):.1f}%")

    else:
        print(f"\n❌ Enhanced analysis failed!")


if __name__ == "__main__":
    main()
