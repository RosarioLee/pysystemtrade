# post_completion_analysis.py - Comprehensive Post-Execution Analysis

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime


class PostCompletionAnalyzer:
    """Analyze completed system results and generate reports"""

    def __init__(self, results):
        self.results = results
        self.system = results.get("system")
        self.compliance_report = results.get("compliance_report")
        self.performance_metrics = results.get("performance_metrics")
        self.health_report = results.get("health_report")

    def generate_final_report(self):
        """Generate comprehensive final analysis report"""
        print("📊 GENERATING FINAL SYSTEM REPORT")
        print("=" * 60)

        report = {
            "execution_summary": self._analyze_execution(),
            "carver_compliance": self._analyze_compliance(),
            "performance_analysis": self._analyze_performance(),
            "production_readiness": self._assess_production_readiness(),
            "next_steps": self._recommend_next_steps(),
        }

        self._display_executive_summary(report)
        return report

    def _analyze_execution(self):
        """Analyze system execution success"""
        if not self.system:
            return {"status": "FAILED", "message": "System creation failed"}

        instruments = self.system.get_instrument_list()
        rules = self.system.rules.trading_rules()

        return {
            "status": "SUCCESS",
            "instruments_processed": len(instruments),
            "rules_implemented": len(rules),
            "ewmac_rules": len([r for r in rules if "ewmac" in r]),
            "breakout_rules": len([r for r in rules if "breakout" in r]),
            "total_combinations": len(instruments) * len(rules),
        }

    def _analyze_compliance(self):
        """Analyze Carver methodology compliance"""
        if not self.compliance_report:
            return {"status": "UNKNOWN", "message": "Compliance check not completed"}

        scalar_compliance = self.compliance_report.get("scalar_compliance", False)
        weight_compliance = self.compliance_report.get("weight_compliance", False)
        issues = self.compliance_report.get("issues", [])

        return {
            "scalar_compliance": scalar_compliance,
            "weight_compliance": weight_compliance,
            "overall_compliance": scalar_compliance and weight_compliance,
            "issues_count": len(issues),
            "issues": issues[:5],  # Show first 5 issues
        }

    def _analyze_performance(self):
        """Analyze system performance metrics"""
        if not self.performance_metrics:
            return {
                "status": "UNAVAILABLE",
                "message": "Performance calculation not completed",
            }

        return {
            "sharpe_ratio": self.performance_metrics.get("sharpe_ratio", 0),
            "annual_return": self.performance_metrics.get("annual_return", 0),
            "annual_volatility": self.performance_metrics.get("annual_volatility", 0),
            "max_drawdown": self.performance_metrics.get("max_drawdown", 0),
            "win_rate": self.performance_metrics.get("win_rate", 0),
            "profit_factor": self.performance_metrics.get("profit_factor", 0),
            "calculation_time": self.performance_metrics.get("run_seconds", 0),
        }

    def _assess_production_readiness(self):
        """Assess production deployment readiness"""
        readiness_score = 0
        max_score = 100
        issues = []

        # Execution success (25 points)
        execution = self._analyze_execution()
        if execution["status"] == "SUCCESS":
            readiness_score += 25
        else:
            issues.append("System execution incomplete")

        # Carver compliance (25 points)
        compliance = self._analyze_compliance()
        if compliance.get("overall_compliance", False):
            readiness_score += 25
        else:
            issues.append("Carver methodology compliance issues")

        # Performance metrics (25 points)
        performance = self._analyze_performance()
        if performance.get("sharpe_ratio", 0) > 0.3:
            readiness_score += 15
        if performance.get("max_drawdown", -1) > -0.2:
            readiness_score += 10
        else:
            issues.append("Performance metrics below production threshold")

        # System health (25 points)
        if self.health_report and self.health_report.get("overall_status") == "HEALTHY":
            readiness_score += 25
        else:
            issues.append("System health concerns detected")

        # Determine readiness level
        if readiness_score >= 80:
            status = "PRODUCTION READY"
            recommendation = "System meets all production criteria"
        elif readiness_score >= 60:
            status = "PAPER TRADING READY"
            recommendation = "Address minor issues before live deployment"
        else:
            status = "DEVELOPMENT REQUIRED"
            recommendation = "Significant improvements needed"

        return {
            "status": status,
            "score": readiness_score,
            "max_score": max_score,
            "percentage": readiness_score / max_score * 100,
            "issues": issues,
            "recommendation": recommendation,
        }

    def _recommend_next_steps(self):
        """Recommend immediate next steps"""
        production_readiness = self._assess_production_readiness()

        if production_readiness["score"] >= 80:
            return {
                "priority": "HIGH",
                "actions": [
                    "Begin paper trading with live data feeds",
                    "Implement real-time monitoring alerts",
                    "Set up execution framework for trade placement",
                    "Establish performance benchmarking vs buy-and-hold",
                    "Prepare risk management protocols",
                ],
            }
        elif production_readiness["score"] >= 60:
            return {
                "priority": "MEDIUM",
                "actions": [
                    "Address flagged compliance issues",
                    "Validate performance calculation accuracy",
                    "Enhance system monitoring capabilities",
                    "Conduct additional backtesting validation",
                    "Review cost multiplier effectiveness",
                ],
            }
        else:
            return {
                "priority": "LOW",
                "actions": [
                    "Resolve system execution issues",
                    "Fix Carver methodology compliance problems",
                    "Improve performance calculation reliability",
                    "Enhance error handling and logging",
                    "Conduct thorough system debugging",
                ],
            }

    def _display_executive_summary(self, report):
        """Display executive summary of analysis"""
        print("\n🎯 EXECUTIVE SUMMARY")
        print("=" * 40)

        # Execution Status
        exec_status = report["execution_summary"]["status"]
        print(f"📈 System Execution: {exec_status}")

        if exec_status == "SUCCESS":
            print(
                f"   • Instruments: {report['execution_summary']['instruments_processed']}"
            )
            print(
                f"   • Trading Rules: {report['execution_summary']['rules_implemented']}"
            )
            print(
                f"   • Total Combinations: {report['execution_summary']['total_combinations']}"
            )

        # Compliance Status
        compliance = report["carver_compliance"]
        compliance_status = (
            "✅ COMPLIANT" if compliance.get("overall_compliance") else "❌ NON-COMPLIANT"
        )
        print(f"🎯 Carver Compliance: {compliance_status}")

        # Performance Status
        performance = report["performance_analysis"]
        if performance.get("sharpe_ratio"):
            print(
                f"📊 Performance: Sharpe {performance['sharpe_ratio']:.3f}, "
                f"Return {performance['annual_return']:.1%}, "
                f"Drawdown {performance['max_drawdown']:.1%}"
            )

        # Production Readiness
        readiness = report["production_readiness"]
        print(
            f"🚀 Production Readiness: {readiness['status']} ({readiness['percentage']:.0f}%)"
        )
        print(f"💡 Recommendation: {readiness['recommendation']}")

        # Next Steps
        next_steps = report["next_steps"]
        print(f"\n🎯 IMMEDIATE PRIORITY: {next_steps['priority']}")
        print("📋 Next Actions:")
        for i, action in enumerate(next_steps["actions"][:3], 1):
            print(f"   {i}. {action}")
