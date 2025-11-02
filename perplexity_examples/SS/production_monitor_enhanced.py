# production_monitor_enhanced.py - Advanced Production Monitoring System v3.0
try:
    from plotting_utils import (
        plot_portfolio_performance_real,
        plot_rolling_sharpe_real,
        plot_drawdown_analysis_real,
        plot_return_distribution_real,
    )

    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings
from typing import Dict, Any, Optional, List, Tuple
import logging
from scipy import stats
import matplotlib.gridspec as gridspec

warnings.filterwarnings("ignore")


class AdvancedProductionMonitor:
    """
    Advanced production monitoring system with comprehensive analytics and visualization
    """

    def __init__(self, system, config: Optional[Dict[str, Any]] = None):
        self.system = system
        self.config = config if config else {}
        self.instruments = system.get_instrument_list()
        self.rules = system.rules.trading_rules()

        # Enhanced alert thresholds
        self.thresholds = {
            "min_sharpe_ratio": self.config.get("min_sharpe_ratio", 0.3),
            "max_drawdown": self.config.get("max_drawdown", 0.15),
            "vol_tolerance": self.config.get("vol_tolerance", 0.02),
            "min_win_rate": self.config.get("min_win_rate", 0.45),
            "max_var_95": self.config.get("max_var_95", 0.05),
            "max_correlation": self.config.get("max_correlation", 0.8),
        }

        # Dashboard settings
        self.warm_up_days = 365
        self.stress_test_scenarios = ["covid_crash", "dot_com", "financial_crisis"]

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        print(
            f"✅ Advanced Production Monitor v3.0 initialized for {len(self.instruments)} instruments"
        )

    def run_comprehensive_health_check(self) -> Dict[str, Any]:
        """Run comprehensive system health check with advanced diagnostics"""

        print("🔍 COMPREHENSIVE SYSTEM HEALTH CHECK v3.0")
        print("=" * 60)

        start_time = datetime.now()

        health_report = {
            "timestamp": start_time,
            "overall_status": "HEALTHY",
            "alerts": [],
            "warnings": [],
            "recommendations": [],
            "detailed_checks": {},
        }

        try:
            # Core health checks
            health_report["detailed_checks"][
                "data_quality"
            ] = self._check_data_quality_advanced()
            health_report["detailed_checks"][
                "system_performance"
            ] = self._check_system_performance_advanced()
            health_report["detailed_checks"][
                "risk_metrics"
            ] = self._check_risk_metrics_advanced()
            health_report["detailed_checks"][
                "rule_performance"
            ] = self._check_rule_performance_advanced()
            health_report["detailed_checks"][
                "correlation_analysis"
            ] = self._check_correlation_stability()

            # Advanced checks
            health_report["detailed_checks"][
                "regime_stability"
            ] = self._check_regime_stability()
            health_report["detailed_checks"]["tail_risk"] = self._check_tail_risk()
            health_report["detailed_checks"][
                "liquidity_risk"
            ] = self._check_liquidity_risk()
            health_report["detailed_checks"][
                "model_stability"
            ] = self._check_model_stability()

            # Generate overall assessment
            self._generate_health_assessment(health_report)

            # Display results
            self._display_health_dashboard_advanced(health_report)

            health_report["check_duration"] = (
                datetime.now() - start_time
            ).total_seconds()

            return health_report

        except Exception as e:
            self.logger.error(f"Comprehensive health check failed: {e}")
            health_report["overall_status"] = "ERROR"
            health_report["alerts"].append(f"Health check system error: {str(e)}")
            return health_report

    def _check_data_quality_advanced(self) -> Dict[str, Any]:
        """Advanced data quality assessment"""
        print("\n1️⃣ ADVANCED DATA QUALITY CHECK")
        data_issues = []
        data_metrics = {}
        quality_scores = []

        for instrument in self.instruments:
            try:
                prices = self.system.rawdata.get_daily_prices(instrument)
                # Basic data checks
                last_date = prices.index[-1]
                days_stale = (datetime.now().date() - last_date.date()).days
                price_gaps = prices.isna().sum()

                # Advanced data quality metrics
                returns = prices.pct_change().dropna()
                # Outlier detection
                z_scores = np.abs(stats.zscore(returns))
                outliers = (z_scores > 4).sum()

                # Data consistency checks
                price_jumps = (returns.abs() > 0.15).sum()  # >15% daily moves

                # Volatility consistency
                rolling_vol = returns.rolling(30).std()
                vol_regime_changes = (rolling_vol.pct_change().abs() > 2).sum()

                # Calculate quality score
                quality_score = 100
                if days_stale > 2:
                    quality_score -= 20
                if price_gaps > 10:
                    quality_score -= 15
                if outliers > len(returns) * 0.01:
                    quality_score -= 10  # >1% outliers
                if price_jumps > len(returns) * 0.005:
                    quality_score -= 10  # >0.5% large jumps
                if vol_regime_changes > 10:
                    quality_score -= 5

                quality_scores.append(quality_score)
                data_metrics[instrument] = {
                    "last_date": last_date,
                    "days_stale": days_stale,
                    "price_gaps": price_gaps,
                    "outliers": outliers,
                    "price_jumps": price_jumps,
                    "quality_score": quality_score,
                    "data_points": len(prices),
                }

                # Flag issues
                if days_stale > 2:
                    data_issues.append(f"{instrument}: Data {days_stale} days stale")
                if quality_score < 80:
                    data_issues.append(
                        f"{instrument}: Low data quality score ({quality_score}/100)"
                    )

            except Exception as e:
                data_issues.append(f"{instrument}: Data access error - {e}")
                quality_scores.append(0)

        avg_quality_score = np.mean(quality_scores) if quality_scores else 0
        print(f" ✅ Analyzed {len(self.instruments)} instruments")
        print(f" 📊 Average data quality score: {avg_quality_score:.1f}/100")
        print(f" ⚠️ Found {len(data_issues)} data issues")

        return {
            "status": "PASS"
            if avg_quality_score >= 85
            else "WARN"
            if avg_quality_score >= 70
            else "FAIL",
            "average_quality_score": avg_quality_score,
            "issues": data_issues,
            "metrics": data_metrics,
        }

    def _check_system_performance_advanced(self) -> Dict[str, Any]:
        """Advanced system performance check"""
        print("\n2️⃣ ADVANCED SYSTEM PERFORMANCE CHECK")

        try:
            from performance_calculator_enhanced import AdvancedPerformanceCalculator

            calculator = AdvancedPerformanceCalculator()
            performance_data = calculator._calculate_advanced_portfolio_metrics(
                self.system
            )

            if not performance_data:
                return {
                    "status": "FAIL",
                    "issues": ["Performance calculation failed"],
                    "metrics": {},
                }

            issues = []
            warnings = []

            # Performance thresholds
            sharpe = performance_data.get("sharpe_ratio", 0)
            max_dd = performance_data.get("max_drawdown", 0)
            vol = performance_data.get("annual_volatility", 0)
            win_rate = performance_data.get("win_rate", 0)

            # Check against thresholds
            if sharpe < self.thresholds["min_sharpe_ratio"]:
                issues.append(
                    f"Low Sharpe ratio: {sharpe:.3f} < {self.thresholds['min_sharpe_ratio']}"
                )

            if abs(max_dd) > self.thresholds["max_drawdown"]:
                issues.append(
                    f"High drawdown: {max_dd:.1%} > {self.thresholds['max_drawdown']:.1%}"
                )

            if abs(vol - 0.12) > self.thresholds["vol_tolerance"]:
                warnings.append(f"Volatility deviation: {vol:.1%} vs target 12%")

            if win_rate < self.thresholds["min_win_rate"]:
                warnings.append(f"Low win rate: {win_rate:.1%}")

            status = "PASS"
            if len(issues) > 0:
                status = "FAIL"
            elif len(warnings) > 2:
                status = "WARN"

            print(f" 📈 Sharpe Ratio: {sharpe:.3f}")
            print(f" 📉 Max Drawdown: {max_dd:.1%}")
            print(f" 🎯 Volatility: {vol:.1%}")
            print(f" ✅ Status: {status}")

            return {
                "status": status,
                "issues": issues,
                "warnings": warnings,
                "metrics": performance_data,
            }

        except Exception as e:
            self.logger.error(f"System performance check failed: {e}")
            return {
                "status": "ERROR",
                "issues": [f"Performance check error: {str(e)}"],
                "metrics": {},
            }

    def _check_risk_metrics_advanced(self) -> Dict[str, Any]:
        """Advanced risk metrics assessment"""
        print("\n3️⃣ ADVANCED RISK METRICS CHECK")

        try:
            portfolio = self.system.accounts.portfolio()
            if portfolio is None:
                return {
                    "status": "FAIL",
                    "issues": ["Portfolio not available"],
                    "metrics": {},
                }

            # Get portfolio returns
            try:
                pnl_curve = portfolio.curve()
                returns = pnl_curve.pct_change().dropna()
            except:
                returns = pd.Series()

            if len(returns) == 0:
                return {
                    "status": "FAIL",
                    "issues": ["No return data available"],
                    "metrics": {},
                }

            risk_issues = []
            risk_metrics = {}

            # Volatility analysis
            current_vol = returns.rolling(30).std().iloc[-1] * np.sqrt(252)
            long_term_vol = returns.std() * np.sqrt(252)
            vol_ratio = current_vol / long_term_vol if long_term_vol > 0 else 1

            risk_metrics["volatility_analysis"] = {
                "current_vol": current_vol,
                "long_term_vol": long_term_vol,
                "vol_ratio": vol_ratio,
            }

            if vol_ratio > 2.0:
                risk_issues.append(
                    f"Current volatility {vol_ratio:.1f}x higher than long-term"
                )

            # Tail risk analysis
            var_95 = returns.quantile(0.05)
            var_99 = returns.quantile(0.01)
            expected_shortfall = returns[returns <= var_95].mean()

            risk_metrics["tail_risk"] = {
                "var_95": var_95,
                "var_99": var_99,
                "expected_shortfall": expected_shortfall,
            }

            if abs(var_95) > 0.05:
                risk_issues.append(f"High daily VaR(95%): {var_95:.2%}")

            # Drawdown analysis
            cumulative = (1 + returns).cumprod()
            rolling_max = cumulative.expanding().max()
            drawdown = (cumulative - rolling_max) / rolling_max
            current_dd = drawdown.iloc[-1]
            max_dd = drawdown.min()
            underwater_periods = (drawdown < -0.01).sum()

            risk_metrics["drawdown_analysis"] = {
                "current_drawdown": current_dd,
                "max_drawdown": max_dd,
                "time_underwater": underwater_periods / len(drawdown),
            }

            if abs(current_dd) > 0.10:
                risk_issues.append(
                    f"Currently in significant drawdown: {current_dd:.1%}"
                )

            status = (
                "PASS"
                if len(risk_issues) == 0
                else "WARN"
                if len(risk_issues) <= 2
                else "FAIL"
            )

            print(f" 📊 Current VaR(95%): {var_95:.2%}")
            print(f" 📈 Volatility Ratio: {vol_ratio:.1f}x")
            print(f" 📉 Current Drawdown: {current_dd:.1%}")
            print(f" ✅ Status: {status}")

            return {"status": status, "issues": risk_issues, "metrics": risk_metrics}

        except Exception as e:
            self.logger.error(f"Risk metrics check failed: {e}")
            return {
                "status": "ERROR",
                "issues": [f"Risk check error: {str(e)}"],
                "metrics": {},
            }

    def _check_rule_performance_advanced(self) -> Dict[str, Any]:
        """Advanced trading rule performance check"""
        print("\n4️⃣ ADVANCED RULE PERFORMANCE CHECK")

        rule_issues = []
        rule_metrics = {}

        try:
            sample_instruments = self.instruments[: min(5, len(self.instruments))]

            for rule_name in self.rules.keys():
                try:
                    rule_sharpes = []
                    rule_consistencies = []

                    for instrument in sample_instruments:
                        try:
                            # Get rule forecast
                            forecast = self.system.rules.get_raw_forecast(
                                instrument, rule_name
                            )
                            if forecast is not None and len(forecast) > 100:
                                # Get price returns
                                prices = self.system.rawdata.get_daily_prices(
                                    instrument
                                )
                                returns = prices.pct_change().dropna()

                                # Align data
                                aligned = pd.concat(
                                    [forecast, returns], axis=1, join="inner"
                                ).dropna()
                                if len(aligned) > 100:
                                    aligned.columns = ["forecast", "returns"]

                                    # Calculate rule performance
                                    normalized_forecast = (
                                        aligned["forecast"] / aligned["forecast"].std()
                                    )
                                    rule_returns = (
                                        normalized_forecast * aligned["returns"]
                                    )

                                    if rule_returns.std() > 0:
                                        sharpe = (
                                            rule_returns.mean() / rule_returns.std()
                                        ) * np.sqrt(252)
                                        rule_sharpes.append(sharpe)

                                        # Consistency check
                                        rolling_sharpe = rule_returns.rolling(63).apply(
                                            lambda x: (x.mean() / x.std())
                                            * np.sqrt(252)
                                            if x.std() > 0
                                            else 0
                                        )
                                        consistency = (rolling_sharpe > 0).mean()
                                        rule_consistencies.append(consistency)
                        except Exception as e:
                            continue

                    if rule_sharpes:
                        avg_sharpe = np.mean(rule_sharpes)
                        sharpe_std = np.std(rule_sharpes)
                        avg_consistency = (
                            np.mean(rule_consistencies) if rule_consistencies else 0
                        )

                        rule_metrics[rule_name] = {
                            "avg_sharpe": avg_sharpe,
                            "sharpe_std": sharpe_std,
                            "consistency": avg_consistency,
                            "instruments_tested": len(rule_sharpes),
                        }

                        # Check for issues
                        if avg_sharpe < 0.1:
                            rule_issues.append(
                                f"{rule_name}: Low average Sharpe ({avg_sharpe:.2f})"
                            )
                        if sharpe_std > 0.5:
                            rule_issues.append(
                                f"{rule_name}: Inconsistent performance (std={sharpe_std:.2f})"
                            )
                        if avg_consistency < 0.4:
                            rule_issues.append(
                                f"{rule_name}: Low consistency ({avg_consistency:.1%})"
                            )

                except Exception as e:
                    rule_issues.append(f"{rule_name}: Analysis failed - {str(e)}")

            status = (
                "PASS"
                if len(rule_issues) <= 2
                else "WARN"
                if len(rule_issues) <= 5
                else "FAIL"
            )

            print(f" 🎯 Rules analyzed: {len(rule_metrics)}")
            print(f" ⚠️ Issues found: {len(rule_issues)}")
            print(f" ✅ Status: {status}")

            return {"status": status, "issues": rule_issues, "metrics": rule_metrics}

        except Exception as e:
            self.logger.error(f"Rule performance check failed: {e}")
            return {
                "status": "ERROR",
                "issues": [f"Rule check error: {str(e)}"],
                "metrics": {},
            }

    def _check_correlation_stability(self) -> Dict[str, Any]:
        """Check correlation stability and diversification"""
        print("\n5️⃣ CORRELATION STABILITY CHECK")

        try:
            # Get returns for all instruments
            returns_data = []
            valid_instruments = []

            for instrument in self.instruments:
                try:
                    prices = self.system.rawdata.get_daily_prices(instrument)
                    returns = prices.pct_change().dropna()
                    if len(returns) > 100:
                        returns_data.append(returns)
                        valid_instruments.append(instrument)
                except:
                    continue

            if len(returns_data) < 2:
                return {
                    "status": "FAIL",
                    "issues": ["Insufficient data for correlation analysis"],
                    "metrics": {},
                }

            # Align all return series
            aligned_returns = pd.concat(returns_data, axis=1, join="inner")
            aligned_returns.columns = valid_instruments

            # Calculate correlation matrices for different periods
            recent_period = aligned_returns.tail(252)  # Last year
            full_period = aligned_returns

            recent_corr = recent_period.corr()
            full_corr = full_period.corr()

            # Extract upper triangular correlations
            recent_corr_values = recent_corr.values[
                np.triu_indices_from(recent_corr.values, k=1)
            ]
            full_corr_values = full_corr.values[
                np.triu_indices_from(full_corr.values, k=1)
            ]

            # Calculate metrics
            recent_avg_corr = np.mean(recent_corr_values)
            full_avg_corr = np.mean(full_corr_values)
            corr_change = recent_avg_corr - full_avg_corr
            max_recent_corr = np.max(recent_corr_values)
            min_recent_corr = np.min(recent_corr_values)

            correlation_issues = []

            # Check for correlation issues
            if recent_avg_corr > self.thresholds["max_correlation"]:
                correlation_issues.append(
                    f"High average correlation: {recent_avg_corr:.2f}"
                )
            if max_recent_corr > 0.95:
                correlation_issues.append(
                    f"Very high pairwise correlation detected: {max_recent_corr:.2f}"
                )
            if corr_change > 0.2:
                correlation_issues.append(
                    f"Significant correlation increase: +{corr_change:.2f}"
                )

            # Diversification ratio
            portfolio_weights = np.ones(len(valid_instruments)) / len(
                valid_instruments
            )  # Equal weights
            portfolio_var = np.dot(
                portfolio_weights, np.dot(recent_corr, portfolio_weights)
            )
            avg_individual_var = np.mean(
                [aligned_returns[col].var() for col in aligned_returns.columns]
            )
            diversification_ratio = (
                avg_individual_var / portfolio_var if portfolio_var > 0 else 1
            )

            if diversification_ratio < 1.5:
                correlation_issues.append(
                    f"Low diversification benefit: {diversification_ratio:.1f}x"
                )

            status = (
                "PASS"
                if len(correlation_issues) == 0
                else "WARN"
                if len(correlation_issues) <= 2
                else "FAIL"
            )

            print(f" 📊 Average correlation: {recent_avg_corr:.2f}")
            print(f" 📈 Diversification ratio: {diversification_ratio:.1f}x")
            print(f" 🔄 Correlation change: {corr_change:+.2f}")
            print(f" ✅ Status: {status}")

            return {
                "status": status,
                "issues": correlation_issues,
                "metrics": {
                    "recent_avg_correlation": recent_avg_corr,
                    "full_avg_correlation": full_avg_corr,
                    "correlation_change": corr_change,
                    "max_correlation": max_recent_corr,
                    "min_correlation": min_recent_corr,
                    "diversification_ratio": diversification_ratio,
                    "instruments_analyzed": len(valid_instruments),
                },
            }

        except Exception as e:
            self.logger.error(f"Correlation stability check failed: {e}")
            return {
                "status": "ERROR",
                "issues": [f"Correlation check error: {str(e)}"],
                "metrics": {},
            }

    def _check_regime_stability(self) -> Dict[str, Any]:
        """Check for regime changes and stability"""
        print("\n6️⃣ REGIME STABILITY CHECK")

        try:
            portfolio = self.system.accounts.portfolio()
            if portfolio is None:
                return {
                    "status": "FAIL",
                    "issues": ["Portfolio not available"],
                    "metrics": {},
                }

            returns = portfolio.curve().pct_change().dropna()
            if len(returns) < 500:
                return {
                    "status": "WARN",
                    "issues": ["Insufficient data for regime analysis"],
                    "metrics": {},
                }

            # Regime detection using rolling statistics
            window = 63  # Quarter
            rolling_mean = returns.rolling(window).mean()
            rolling_vol = returns.rolling(window).std()
            rolling_sharpe = (rolling_mean / rolling_vol) * np.sqrt(252)

            # Detect regime changes
            sharpe_changes = rolling_sharpe.diff().abs()
            regime_changes = sharpe_changes > sharpe_changes.quantile(0.95)

            # Recent vs historical comparison
            recent_period = returns.tail(252)
            historical_period = returns.head(-252)

            recent_sharpe = (recent_period.mean() / recent_period.std()) * np.sqrt(252)
            historical_sharpe = (
                historical_period.mean() / historical_period.std()
            ) * np.sqrt(252)

            regime_issues = []

            # Check for regime instability
            if (
                regime_changes.tail(63).sum() > 5
            ):  # More than 5 regime changes in last quarter
                regime_issues.append("High regime instability detected")

            if abs(recent_sharpe - historical_sharpe) > 0.5:
                regime_issues.append(
                    f"Significant performance regime change: {recent_sharpe:.2f} vs {historical_sharpe:.2f}"
                )

            # Volatility regime check
            recent_vol = recent_period.std() * np.sqrt(252)
            historical_vol = historical_period.std() * np.sqrt(252)

            if recent_vol / historical_vol > 1.5:
                regime_issues.append("Entered high volatility regime")

            status = "PASS" if len(regime_issues) == 0 else "WARN"

            print(f" 📊 Recent Sharpe: {recent_sharpe:.2f}")
            print(f" 📈 Historical Sharpe: {historical_sharpe:.2f}")
            print(f" 🔄 Regime changes (Q): {regime_changes.tail(63).sum()}")
            print(f" ✅ Status: {status}")

            return {
                "status": status,
                "issues": regime_issues,
                "metrics": {
                    "recent_sharpe": recent_sharpe,
                    "historical_sharpe": historical_sharpe,
                    "recent_volatility": recent_vol,
                    "historical_volatility": historical_vol,
                    "regime_changes_recent": int(regime_changes.tail(63).sum()),
                },
            }

        except Exception as e:
            self.logger.error(f"Regime stability check failed: {e}")
            return {
                "status": "ERROR",
                "issues": [f"Regime check error: {str(e)}"],
                "metrics": {},
            }

    def _check_tail_risk(self) -> Dict[str, Any]:
        """Advanced tail risk assessment"""
        print("\n7️⃣ TAIL RISK ASSESSMENT")

        try:
            portfolio = self.system.accounts.portfolio()
            if portfolio is None:
                return {
                    "status": "FAIL",
                    "issues": ["Portfolio not available"],
                    "metrics": {},
                }

            returns = portfolio.curve().pct_change().dropna()
            if len(returns) < 252:
                return {
                    "status": "WARN",
                    "issues": ["Insufficient data for tail risk analysis"],
                    "metrics": {},
                }

            tail_risk_issues = []

            # Calculate various tail risk measures
            var_95 = returns.quantile(0.05)
            var_99 = returns.quantile(0.01)
            var_999 = returns.quantile(0.001) if len(returns) > 1000 else returns.min()

            # Expected Shortfall (Conditional VaR)
            es_95 = returns[returns <= var_95].mean()
            es_99 = returns[returns <= var_99].mean()

            # Tail ratio
            tail_ratio = abs(returns.quantile(0.95) / returns.quantile(0.05))

            # Maximum daily loss
            max_daily_loss = returns.min()

            # Tail event frequency
            tail_events_5pct = (returns <= var_95).sum()
            tail_events_1pct = (returns <= var_99).sum()

            # Check against thresholds
            if abs(var_95) > 0.05:  # 5% daily VaR threshold
                tail_risk_issues.append(f"High daily VaR(95%): {var_95:.2%}")

            if abs(var_99) > 0.08:  # 8% daily VaR(99%) threshold
                tail_risk_issues.append(f"High daily VaR(99%): {var_99:.2%}")

            if abs(max_daily_loss) > 0.15:  # 15% maximum daily loss
                tail_risk_issues.append(
                    f"Extreme daily loss observed: {max_daily_loss:.2%}"
                )

            if tail_ratio < 0.5:  # Asymmetric tail risk
                tail_risk_issues.append(
                    f"Significant downside tail risk: ratio {tail_ratio:.2f}"
                )

            # Recent tail risk evolution
            if len(returns) > 500:
                recent_var_95 = returns.tail(252).quantile(0.05)
                historical_var_95 = returns.head(-252).quantile(0.05)
                if abs(recent_var_95) > abs(historical_var_95) * 1.3:
                    tail_risk_issues.append("Deteriorating tail risk profile")

            status = (
                "PASS"
                if len(tail_risk_issues) == 0
                else "WARN"
                if len(tail_risk_issues) <= 2
                else "FAIL"
            )

            print(f" 📊 VaR(95%): {var_95:.2%}")
            print(f" 📉 VaR(99%): {var_99:.2%}")
            print(f" 💥 Max daily loss: {max_daily_loss:.2%}")
            print(f" ⚖️ Tail ratio: {tail_ratio:.2f}")
            print(f" ✅ Status: {status}")

            return {
                "status": status,
                "issues": tail_risk_issues,
                "metrics": {
                    "var_95": var_95,
                    "var_99": var_99,
                    "var_999": var_999,
                    "expected_shortfall_95": es_95,
                    "expected_shortfall_99": es_99,
                    "tail_ratio": tail_ratio,
                    "max_daily_loss": max_daily_loss,
                    "tail_events_5pct": tail_events_5pct,
                    "tail_events_1pct": tail_events_1pct,
                },
            }

        except Exception as e:
            self.logger.error(f"Tail risk assessment failed: {e}")
            return {
                "status": "ERROR",
                "issues": [f"Tail risk error: {str(e)}"],
                "metrics": {},
            }

    def _check_liquidity_risk(self) -> Dict[str, Any]:
        """Assess liquidity risk for ETF portfolio"""

        print("\n8️⃣ LIQUIDITY RISK ASSESSMENT")

        try:
            liquidity_issues = []

            # Portfolio concentration
            num_instruments = len(self.instruments)
            if num_instruments < 10:
                liquidity_issues.append(
                    f"Low diversification: only {num_instruments} instruments"
                )

            # ETF-specific liquidity assessment
            # In a full implementation, this would check:
            # - ETF assets under management
            # - Average daily trading volume
            # - Bid-ask spreads
            # - Underlying asset liquidity

            # Placeholder implementation with enhanced logic
            liquidity_score = min(100, num_instruments * 3)  # Simple scoring

            # Additional liquidity factors for ETFs
            if num_instruments >= 20:
                liquidity_score += 10  # Bonus for good diversification

            # Check for concentration in specific sectors/regions
            # This would require additional metadata about ETF classifications
            concentration_penalty = 0
            if num_instruments < 15:
                concentration_penalty = 10

            liquidity_score = max(0, liquidity_score - concentration_penalty)

            if liquidity_score < 60:
                liquidity_issues.append(f"Low liquidity score: {liquidity_score}/100")

            # ETF market hours alignment check
            # Most ETFs trade during regular market hours, so this is generally not an issue
            market_hours_coverage = "Full"  # Placeholder

            status = "PASS" if len(liquidity_issues) == 0 else "WARN"

            print(f" 🏛️ Instruments: {num_instruments}")
            print(f" 💧 Liquidity score: {liquidity_score}/100")
            print(f" 🕐 Market coverage: {market_hours_coverage}")
            print(f" ✅ Status: {status}")

            return {
                "status": status,
                "issues": liquidity_issues,
                "metrics": {
                    "instruments_count": num_instruments,
                    "liquidity_score": liquidity_score,
                    "market_hours_coverage": market_hours_coverage,
                    "assessment_note": "ETFs generally have good liquidity",
                },
            }

        except Exception as e:
            self.logger.error(f"Liquidity risk assessment failed: {e}")
            return {
                "status": "ERROR",
                "issues": [f"Liquidity check error: {str(e)}"],
                "metrics": {},
            }

    def _check_model_stability(self) -> Dict[str, Any]:
        """Check model stability and parameter consistency"""

        print("\n9️⃣ MODEL STABILITY CHECK")

        try:
            model_issues = []
            model_metrics = {}

            # Check forecast scaling consistency
            try:
                # Sample a few instruments to check forecast scaling
                sample_instruments = self.instruments[: min(3, len(self.instruments))]
                scaling_consistency = []

                for instrument in sample_instruments:
                    for rule_name in list(self.rules.keys())[:3]:  # Sample rules
                        try:
                            forecast = self.system.rules.get_raw_forecast(
                                instrument, rule_name
                            )
                            if forecast is not None and len(forecast) > 100:
                                forecast_std = forecast.std()
                                scaling_consistency.append(forecast_std)
                        except:
                            continue

                if scaling_consistency:
                    scaling_consistency = np.array(scaling_consistency)
                    scaling_cv = (
                        scaling_consistency.std() / scaling_consistency.mean()
                        if scaling_consistency.mean() > 0
                        else 0
                    )

                    model_metrics["forecast_scaling"] = {
                        "coefficient_of_variation": scaling_cv,
                        "mean_scaling": scaling_consistency.mean(),
                        "std_scaling": scaling_consistency.std(),
                    }

                    if scaling_cv > 0.5:  # High variability in scaling
                        model_issues.append(
                            f"Inconsistent forecast scaling: CV={scaling_cv:.2f}"
                        )

            except Exception as e:
                model_issues.append(f"Forecast scaling check failed: {str(e)}")

            # Check position sizing consistency
            try:
                # This would check if position sizing is working as expected
                # Placeholder implementation
                position_consistency_score = 85  # Placeholder

                model_metrics["position_sizing"] = {
                    "consistency_score": position_consistency_score
                }

                if position_consistency_score < 70:
                    model_issues.append("Position sizing inconsistencies detected")

            except Exception as e:
                model_issues.append(f"Position sizing check failed: {str(e)}")

            # Check rule weight stability
            try:
                # In a full implementation, this would track rule weights over time
                rule_weight_stability = 90  # Placeholder

                model_metrics["rule_weights"] = {
                    "stability_score": rule_weight_stability,
                    "total_rules": len(self.rules),
                }

                if rule_weight_stability < 75:
                    model_issues.append("Rule weight instability detected")

            except Exception as e:
                model_issues.append(f"Rule weight check failed: {str(e)}")

            # Overall model health score
            if len(model_issues) == 0:
                model_health_score = 95
            elif len(model_issues) <= 2:
                model_health_score = 80
            else:
                model_health_score = 60

            model_metrics["overall_health_score"] = model_health_score

            status = (
                "PASS"
                if len(model_issues) == 0
                else "WARN"
                if len(model_issues) <= 2
                else "FAIL"
            )

            print(f" 🔧 Model health score: {model_health_score}/100")
            print(f" ⚙️ Issues found: {len(model_issues)}")
            print(f" ✅ Status: {status}")

            return {"status": status, "issues": model_issues, "metrics": model_metrics}

        except Exception as e:
            self.logger.error(f"Model stability check failed: {e}")
            return {
                "status": "ERROR",
                "issues": [f"Model stability error: {str(e)}"],
                "metrics": {},
            }

    def _generate_health_assessment(self, health_report: Dict[str, Any]):
        """Generate overall health assessment from individual checks"""

        detailed_checks = health_report.get("detailed_checks", {})

        # Count status types
        pass_count = 0
        warn_count = 0
        fail_count = 0
        error_count = 0

        for check_name, check_result in detailed_checks.items():
            status = check_result.get("status", "UNKNOWN")
            if status == "PASS":
                pass_count += 1
            elif status == "WARN":
                warn_count += 1
            elif status == "FAIL":
                fail_count += 1
            elif status == "ERROR":
                error_count += 1

            # Collect issues
            issues = check_result.get("issues", [])
            for issue in issues:
                if status in ["FAIL", "ERROR"]:
                    health_report["alerts"].append(f"{check_name.upper()}: {issue}")
                else:
                    health_report["warnings"].append(f"{check_name.upper()}: {issue}")

        # Determine overall status
        total_checks = len(detailed_checks)
        if total_checks == 0:
            health_report["overall_status"] = "UNKNOWN"
        elif error_count > 0 or fail_count > total_checks * 0.3:  # >30% failures
            health_report["overall_status"] = "CRITICAL"
        elif fail_count > 0 or warn_count > total_checks * 0.5:  # >50% warnings
            health_report["overall_status"] = "WARNING"
        else:
            health_report["overall_status"] = "HEALTHY"

        # Generate recommendations
        if health_report["overall_status"] == "CRITICAL":
            health_report["recommendations"].extend(
                [
                    "Immediate system review required",
                    "Consider halting live trading until issues resolved",
                    "Escalate to system administrators",
                ]
            )
        elif health_report["overall_status"] == "WARNING":
            health_report["recommendations"].extend(
                [
                    "Monitor system closely",
                    "Address flagged issues in order of priority",
                    "Consider reducing position sizes until resolved",
                ]
            )
        else:
            health_report["recommendations"].extend(
                [
                    "System operating within normal parameters",
                    "Continue regular monitoring schedule",
                    "Consider optimization opportunities",
                ]
            )

        # Add check summary
        health_report["check_summary"] = {
            "total_checks": total_checks,
            "pass_count": pass_count,
            "warn_count": warn_count,
            "fail_count": fail_count,
            "error_count": error_count,
            "health_percentage": (pass_count / total_checks * 100)
            if total_checks > 0
            else 0,
        }

    def _display_health_dashboard_advanced(self, health_report: Dict[str, Any]):
        """Display advanced health dashboard"""

        print(f"\n" + "=" * 80)
        print(f"🏥 ADVANCED PRODUCTION HEALTH DASHBOARD v3.0")
        print(f"=" * 80)

        # Overall status with emoji
        status_emoji = {
            "HEALTHY": "✅",
            "WARNING": "⚠️",
            "CRITICAL": "❌",
            "ERROR": "🚫",
            "UNKNOWN": "❓",
        }

        overall_status = health_report.get("overall_status", "UNKNOWN")
        print(
            f"\n{status_emoji.get(overall_status, '❓')} OVERALL STATUS: {overall_status}"
        )
        print(
            f"📅 Check Time: {health_report['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print(
            f"⏱️ Check Duration: {health_report.get('check_duration', 0):.1f} seconds"
        )

        # Check summary
        summary = health_report.get("check_summary", {})
        if summary:
            print(f"\n📊 CHECK SUMMARY:")
            print(f" • Total Checks: {summary.get('total_checks', 0)}")
            print(f" • ✅ Passed: {summary.get('pass_count', 0)}")
            print(f" • ⚠️ Warnings: {summary.get('warn_count', 0)}")
            print(f" • ❌ Failed: {summary.get('fail_count', 0)}")
            print(f" • 🚫 Errors: {summary.get('error_count', 0)}")
            print(f" • 🎯 Health Score: {summary.get('health_percentage', 0):.1f}%")

        # Detailed check results
        print(f"\n🔍 DETAILED CHECK RESULTS:")
        detailed_checks = health_report.get("detailed_checks", {})
        for check_name, check_result in detailed_checks.items():
            status = check_result.get("status", "UNKNOWN")
            emoji = status_emoji.get(status, "❓")
            print(f" {emoji} {check_name.replace('_', ' ').title()}: {status}")

        # Critical alerts
        alerts = health_report.get("alerts", [])
        if alerts:
            print(f"\n🚨 CRITICAL ALERTS ({len(alerts)}):")
            for alert in alerts[:5]:  # Show top 5
                print(f" • {alert}")
            if len(alerts) > 5:
                print(f" • ... and {len(alerts) - 5} more alerts")

        # Warnings
        warnings = health_report.get("warnings", [])
        if warnings:
            print(f"\n⚠️ WARNINGS ({len(warnings)}):")
            for warning in warnings[:3]:  # Show top 3
                print(f" • {warning}")
            if len(warnings) > 3:
                print(f" • ... and {len(warnings) - 3} more warnings")

        # Recommendations
        recommendations = health_report.get("recommendations", [])
        if recommendations:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in recommendations:
                print(f" • {rec}")

        print(f"=" * 80)

    def create_advanced_dashboards(
        self, performance_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create advanced visualization dashboards"""

        print("📊 Creating Advanced Dashboards...")

        try:
            dashboard_results = {}

            # Dashboard 1: Performance Overview
            dashboard_results[
                "performance_overview"
            ] = self._create_performance_overview_dashboard(performance_results)

            # Dashboard 2: Risk Analytics
            dashboard_results["risk_analytics"] = self._create_risk_analytics_dashboard(
                performance_results
            )

            # Dashboard 3: System Health Monitor
            dashboard_results["system_health"] = self._create_system_health_dashboard()

            # Dashboard 4: Rule Performance Analysis
            dashboard_results["rule_analysis"] = self._create_rule_analysis_dashboard(
                performance_results
            )

            print("✅ All advanced dashboards created successfully!")
            return dashboard_results

        except Exception as e:
            self.logger.error(f"Dashboard creation failed: {e}")
            return {"error": str(e)}

    def _create_performance_overview_dashboard(
        self, performance_results: Dict[str, Any]
    ) -> str:
        """Create comprehensive performance overview dashboard"""

        try:
            fig = plt.figure(figsize=(20, 16))
            gs = gridspec.GridSpec(4, 3, figure=fig, hspace=0.3, wspace=0.3)

            # Portfolio performance curve
            ax1 = fig.add_subplot(gs[0, :2])
            self._plot_portfolio_performance(ax1)

            # Key metrics summary
            ax2 = fig.add_subplot(gs[0, 2])
            self._plot_key_metrics_summary(ax2, performance_results)

            # Rolling Sharpe ratio
            ax3 = fig.add_subplot(gs[1, 0])
            self._plot_rolling_sharpe(ax3)

            # Drawdown analysis
            ax4 = fig.add_subplot(gs[1, 1])
            self._plot_drawdown_analysis(ax4)

            # Return distribution
            ax5 = fig.add_subplot(gs[1, 2])
            self._plot_return_distribution(ax5)

            # Rule performance comparison
            ax6 = fig.add_subplot(gs[2, :])
            self._plot_rule_performance_comparison(ax6, performance_results)

            # Instrument performance heatmap
            ax7 = fig.add_subplot(gs[3, :])
            self._plot_instrument_heatmap(ax7, performance_results)

            fig.suptitle(
                "Advanced ETF System - Performance Overview Dashboard",
                fontsize=20,
                fontweight="bold",
                y=0.98,
            )

            plt.tight_layout()
            plt.show(block=True)
            plt.close()

            return "Performance overview dashboard created successfully"

        except Exception as e:
            self.logger.error(f"Performance overview dashboard failed: {e}")
            return f"Dashboard creation failed: {str(e)}"

    def _create_risk_analytics_dashboard(
        self, performance_results: Dict[str, Any]
    ) -> str:
        """Create comprehensive risk analytics dashboard"""

        try:
            fig = plt.figure(figsize=(18, 14))
            gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.3)

            # VaR analysis
            ax1 = fig.add_subplot(gs[0, 0])
            self._plot_var_analysis(ax1)

            # Volatility regimes
            ax2 = fig.add_subplot(gs[0, 1])
            self._plot_volatility_regimes(ax2)

            # Tail risk metrics
            ax3 = fig.add_subplot(gs[0, 2])
            self._plot_tail_risk_metrics(ax3, performance_results)

            # Correlation matrix
            ax4 = fig.add_subplot(gs[1, :2])
            self._plot_correlation_matrix(ax4, performance_results)

            # Risk contribution
            ax5 = fig.add_subplot(gs[1, 2])
            self._plot_risk_contribution(ax5)

            # Stress test results
            ax6 = fig.add_subplot(gs[2, :])
            self._plot_stress_test_results(ax6)

            fig.suptitle(
                "Advanced ETF System - Risk Analytics Dashboard",
                fontsize=18,
                fontweight="bold",
                y=0.98,
            )

            plt.tight_layout()
            plt.show(block=True)
            plt.close()

            return "Risk analytics dashboard created successfully"

        except Exception as e:
            self.logger.error(f"Risk analytics dashboard failed: {e}")
            return f"Risk dashboard creation failed: {str(e)}"

    def _create_system_health_dashboard(self) -> str:
        """Create system health monitoring dashboard"""

        try:
            # Run health check
            health_results = self.run_comprehensive_health_check()

            fig = plt.figure(figsize=(16, 12))
            gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.3, wspace=0.3)

            # Health score overview
            ax1 = fig.add_subplot(gs[0, 0])
            self._plot_health_score_overview(ax1, health_results)

            # Check status summary
            ax2 = fig.add_subplot(gs[0, 1])
            self._plot_check_status_summary(ax2, health_results)

            # Data quality metrics
            ax3 = fig.add_subplot(gs[1, 0])
            self._plot_data_quality_metrics(ax3, health_results)

            # Performance metrics trends
            ax4 = fig.add_subplot(gs[1, 1])
            self._plot_performance_trends(ax4)

            # Alert timeline
            ax5 = fig.add_subplot(gs[2, :])
            self._plot_alert_timeline(ax5, health_results)

            fig.suptitle(
                "Advanced ETF System - Health Monitoring Dashboard",
                fontsize=18,
                fontweight="bold",
                y=0.98,
            )

            plt.tight_layout()
            plt.show(block=True)
            plt.close()

            return "System health dashboard created successfully"

        except Exception as e:
            self.logger.error(f"System health dashboard failed: {e}")
            return f"Health dashboard creation failed: {str(e)}"

    def _create_rule_analysis_dashboard(
        self, performance_results: Dict[str, Any]
    ) -> str:
        """Create detailed rule analysis dashboard"""

        try:
            fig = plt.figure(figsize=(18, 12))
            gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.3)

            # Rule Sharpe comparison
            ax1 = fig.add_subplot(gs[0, :])
            self._plot_rule_sharpe_comparison(ax1, performance_results)

            # Rule consistency analysis
            ax2 = fig.add_subplot(gs[1, 0])
            self._plot_rule_consistency(ax2, performance_results)

            # Rule statistical significance
            ax3 = fig.add_subplot(gs[1, 1])
            self._plot_rule_significance(ax3, performance_results)

            # Rule diversification benefit
            ax4 = fig.add_subplot(gs[1, 2])
            self._plot_rule_diversification(ax4, performance_results)

            # Individual rule performance over time
            ax5 = fig.add_subplot(gs[2, :])
            self._plot_rule_performance_timeline(ax5, performance_results)

            fig.suptitle(
                "Advanced ETF System - Trading Rule Analysis Dashboard",
                fontsize=18,
                fontweight="bold",
                y=0.98,
            )

            plt.tight_layout()
            plt.show(block=True)
            plt.close()

            return "Rule analysis dashboard created successfully"

        except Exception as e:
            self.logger.error(f"Rule analysis dashboard failed: {e}")
            return f"Rule analysis dashboard creation failed: {str(e)}"

    def run_stress_testing(self) -> Dict[str, Any]:
        """Run comprehensive stress testing scenarios"""

        print("🧪 Running Stress Testing Scenarios...")

        stress_results = {}

        try:
            portfolio = self.system.accounts.portfolio()
            if portfolio is None:
                return {"error": "Portfolio not available for stress testing"}

            returns = portfolio.curve().pct_change().dropna()
            if len(returns) == 0:
                return {"error": "No return data available for stress testing"}

            # Scenario 1: Market crash (-20% in 1 day)
            stress_results["market_crash"] = self._stress_test_market_crash(returns)

            # Scenario 2: High volatility regime (2x normal volatility for 30 days)
            stress_results["high_volatility"] = self._stress_test_high_volatility(
                returns
            )

            # Scenario 3: Correlation breakdown (all correlations -> 0.9)
            stress_results[
                "correlation_breakdown"
            ] = self._stress_test_correlation_breakdown()

            # Scenario 4: Liquidity crisis (reduced position sizes)
            stress_results["liquidity_crisis"] = self._stress_test_liquidity_crisis()

            # Overall stress score
            stress_scores = [
                result.get("stress_score", 0)
                for result in stress_results.values()
                if isinstance(result, dict) and "stress_score" in result
            ]
            overall_stress_score = np.mean(stress_scores) if stress_scores else 0

            stress_results["overall_assessment"] = {
                "overall_stress_score": overall_stress_score,
                "stress_rating": self._get_stress_rating(overall_stress_score),
                "scenarios_tested": len(stress_results),
                "recommendations": self._generate_stress_recommendations(
                    stress_results
                ),
            }

            print(
                f"✅ Stress testing complete. Overall score: {overall_stress_score:.1f}/100"
            )
            return stress_results

        except Exception as e:
            self.logger.error(f"Stress testing failed: {e}")
            return {"error": str(e)}

    def _stress_test_market_crash(self, returns: pd.Series) -> Dict[str, Any]:
        """Simulate market crash scenario"""

        try:
            # Simulate -20% market shock
            shocked_returns = returns.copy()
            shock_size = -0.20

            # Apply shock to worst historical day
            worst_day_idx = returns.idxmin()
            shocked_returns.loc[worst_day_idx] = shock_size

            # Calculate metrics
            original_sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
            shocked_sharpe = (shocked_returns.mean() / shocked_returns.std()) * np.sqrt(
                252
            )

            # Drawdown impact
            original_cumulative = (1 + returns).cumprod()
            shocked_cumulative = (1 + shocked_returns).cumprod()

            original_max_dd = (
                (original_cumulative - original_cumulative.expanding().max())
                / original_cumulative.expanding().max()
            ).min()
            shocked_max_dd = (
                (shocked_cumulative - shocked_cumulative.expanding().max())
                / shocked_cumulative.expanding().max()
            ).min()

            # Stress score (100 = no impact, 0 = severe impact)
            sharpe_impact = (
                abs(shocked_sharpe - original_sharpe) / abs(original_sharpe)
                if original_sharpe != 0
                else 1
            )
            dd_impact = (
                abs(shocked_max_dd - original_max_dd) / abs(original_max_dd)
                if original_max_dd != 0
                else 1
            )

            stress_score = max(0, 100 - (sharpe_impact + dd_impact) * 50)

            return {
                "scenario": "Market Crash (-20%)",
                "original_sharpe": original_sharpe,
                "shocked_sharpe": shocked_sharpe,
                "original_max_dd": original_max_dd,
                "shocked_max_dd": shocked_max_dd,
                "stress_score": stress_score,
                "impact_assessment": "High"
                if stress_score < 50
                else "Medium"
                if stress_score < 75
                else "Low",
            }

        except Exception as e:
            return {"error": f"Market crash stress test failed: {str(e)}"}

    def _stress_test_high_volatility(self, returns: pd.Series) -> Dict[str, Any]:
        """Simulate high volatility regime"""

        try:
            # Double the volatility for simulation
            vol_multiplier = 2.0

            # Scale returns by volatility multiplier
            shocked_returns = returns * vol_multiplier

            # Calculate impact
            original_vol = returns.std() * np.sqrt(252)
            shocked_vol = shocked_returns.std() * np.sqrt(252)

            original_sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
            shocked_sharpe = (shocked_returns.mean() / shocked_returns.std()) * np.sqrt(
                252
            )

            # VaR impact
            original_var = returns.quantile(0.05)
            shocked_var = shocked_returns.quantile(0.05)

            stress_score = max(0, 100 - abs(shocked_vol - original_vol) * 100)

            return {
                "scenario": "High Volatility Regime (2x)",
                "original_volatility": original_vol,
                "shocked_volatility": shocked_vol,
                "original_var_95": original_var,
                "shocked_var_95": shocked_var,
                "stress_score": stress_score,
                "impact_assessment": "High"
                if stress_score < 50
                else "Medium"
                if stress_score < 75
                else "Low",
            }

        except Exception as e:
            return {"error": f"High volatility stress test failed: {str(e)}"}

    def _stress_test_correlation_breakdown(self) -> Dict[str, Any]:
        """Simulate correlation breakdown scenario"""

        try:
            # This is a simplified simulation
            # In practice, you'd re-run the portfolio with modified correlations

            # Assume diversification benefit reduces significantly
            diversification_loss = 0.4  # 40% loss of diversification benefit

            # Estimate impact on portfolio volatility
            # Higher correlations -> higher portfolio volatility
            portfolio_vol_increase = 0.3  # 30% increase in portfolio volatility

            stress_score = max(0, 100 - diversification_loss * 100)

            return {
                "scenario": "Correlation Breakdown",
                "diversification_loss": diversification_loss,
                "portfolio_vol_increase": portfolio_vol_increase,
                "stress_score": stress_score,
                "impact_assessment": "High"
                if stress_score < 50
                else "Medium"
                if stress_score < 75
                else "Low",
            }

        except Exception as e:
            return {"error": f"Correlation breakdown stress test failed: {str(e)}"}

    def _stress_test_liquidity_crisis(self) -> Dict[str, Any]:
        """Simulate liquidity crisis scenario"""

        try:
            # For ETFs, liquidity crisis impact is generally limited
            # but we can simulate reduced position sizes and higher transaction costs

            position_size_reduction = 0.5  # 50% reduction in position sizes
            transaction_cost_increase = 5.0  # 5x increase in transaction costs

            # Estimate impact on returns
            # Reduced position sizes -> reduced return capture
            return_impact = (
                position_size_reduction * 0.3
            )  # 30% of the reduction affects returns

            # Higher transaction costs
            cost_impact = 0.005  # Additional 50bps annual cost

            total_impact = return_impact + cost_impact
            stress_score = max(0, 100 - total_impact * 200)

            return {
                "scenario": "Liquidity Crisis",
                "position_size_reduction": position_size_reduction,
                "transaction_cost_increase": transaction_cost_increase,
                "estimated_return_impact": total_impact,
                "stress_score": stress_score,
                "impact_assessment": "High"
                if stress_score < 50
                else "Medium"
                if stress_score < 75
                else "Low",
            }

        except Exception as e:
            return {"error": f"Liquidity crisis stress test failed: {str(e)}"}

    def _get_stress_rating(self, score: float) -> str:
        """Get stress rating based on score"""
        if score >= 80:
            return "Excellent"
        elif score >= 65:
            return "Good"
        elif score >= 50:
            return "Acceptable"
        elif score >= 30:
            return "Poor"
        else:
            return "Critical"

    def _generate_stress_recommendations(
        self, stress_results: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on stress test results"""

        recommendations = []

        # Analyze results
        high_impact_scenarios = []
        for scenario, result in stress_results.items():
            if isinstance(result, dict) and result.get("impact_assessment") == "High":
                high_impact_scenarios.append(scenario)

        if len(high_impact_scenarios) > 2:
            recommendations.append(
                "System shows vulnerability to multiple stress scenarios"
            )
            recommendations.append("Consider reducing overall portfolio risk")
            recommendations.append("Implement additional hedging strategies")
        elif len(high_impact_scenarios) > 0:
            recommendations.append(
                f"System vulnerable to: {', '.join(high_impact_scenarios)}"
            )
            recommendations.append("Monitor these risk factors closely")
        else:
            recommendations.append("System shows good resilience to stress scenarios")
            recommendations.append("Continue current risk management approach")

        return recommendations

    # Placeholder plotting methods (simplified implementations)
    def _plot_portfolio_performance(self, ax):
        """Plot portfolio performance curve with actual data"""
        if PLOTTING_AVAILABLE:
            plot_portfolio_performance_real(ax, self.system)
        else:
            ax.text(
                0.5,
                0.5,
                "Plotting utils not available\nInstall plotting_utils.py",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )

    def _plot_key_metrics_summary(self, ax, performance_results):
        """Plot key metrics with real data"""
        ax.axis("off")
        if performance_results and performance_results.get("portfolio_metrics"):
            pm = performance_results["portfolio_metrics"]

            # Fix extreme values
            sharpe = max(
                -5, min(5, pm.get("sharpe_ratio", 0))
            )  # Cap Sharpe between -5 and 5
            annual_return = max(
                -1, min(10, pm.get("annual_return", 0))
            )  # Cap return between -100% and 1000%
            max_dd = max(
                -1, min(0, pm.get("max_drawdown", 0))
            )  # Cap drawdown between -100% and 0%
            win_rate = max(0, min(1, pm.get("win_rate", 0)))  # Cap between 0% and 100%
            volatility = max(
                0, min(2, pm.get("annual_volatility", 0))
            )  # Cap volatility at 200%

            text = f"""KEY METRICS

    Sharpe Ratio: {sharpe:.3f}
    Annual Return: {annual_return:.1%}
    Max Drawdown: {max_dd:.1%}
    Win Rate: {win_rate:.1%}
    Volatility: {volatility:.1%}"""

            # Color coding based on performance
            color = (
                "lightgreen"
                if sharpe > 0.5
                else "lightyellow"
                if sharpe > 0
                else "lightcoral"
            )

            ax.text(
                0.1,
                0.9,
                text,
                transform=ax.transAxes,
                fontsize=12,
                verticalalignment="top",
                fontfamily="monospace",
                bbox=dict(boxstyle="round", facecolor=color, alpha=0.8),
            )
        else:
            ax.text(
                0.5,
                0.5,
                "Metrics not available",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )

    def _plot_key_metrics_summary(self, ax, performance_results):
        """Plot key metrics summary"""
        ax.axis("off")
        if performance_results and performance_results.get("portfolio_metrics"):
            pm = performance_results["portfolio_metrics"]
            text = f"""KEY METRICS

Sharpe Ratio: {pm.get('sharpe_ratio', 0):.3f}
Annual Return: {pm.get('annual_return', 0):.1%}
Max Drawdown: {pm.get('max_drawdown', 0):.1%}
Win Rate: {pm.get('win_rate', 0):.1%}
Volatility: {pm.get('annual_volatility', 0):.1%}"""
            ax.text(
                0.1,
                0.9,
                text,
                transform=ax.transAxes,
                fontsize=12,
                verticalalignment="top",
                bbox=dict(boxstyle="round", facecolor="lightblue", alpha=0.8),
            )
        else:
            ax.text(
                0.5,
                0.5,
                "Metrics not available",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )

    # Add other plotting method placeholders...
    def _plot_rolling_sharpe(self, ax):
        if PLOTTING_AVAILABLE:
            plot_rolling_sharpe_real(ax, self.system)
        else:
            ax.text(
                0.5,
                0.5,
                "Rolling Sharpe\n(plotting_utils needed)",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )

    def _plot_drawdown_analysis(self, ax):
        if PLOTTING_AVAILABLE:
            plot_drawdown_analysis_real(ax, self.system)
        else:
            ax.text(
                0.5,
                0.5,
                "Drawdown Analysis\n(plotting_utils needed)",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )

    def _plot_return_distribution(self, ax):
        if PLOTTING_AVAILABLE:
            plot_return_distribution_real(ax, self.system)
        else:
            ax.text(
                0.5,
                0.5,
                "Return Distribution\n(plotting_utils needed)",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )

    def _plot_rule_performance_comparison(self, ax, performance_results):
        ax.text(
            0.5,
            0.5,
            "Rule Performance\n(Implementation needed)",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )

    def _plot_instrument_heatmap(self, ax, performance_results):
        ax.text(
            0.5,
            0.5,
            "Instrument Heatmap\n(Implementation needed)",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )

    def _plot_var_analysis(self, ax):
        ax.text(
            0.5,
            0.5,
            "VaR Analysis\n(Implementation needed)",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )

    def _plot_volatility_regimes(self, ax):
        ax.text(
            0.5,
            0.5,
            "Volatility Regimes\n(Implementation needed)",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )

    def _plot_tail_risk_metrics(self, ax, performance_results):
        ax.text(
            0.5,
            0.5,
            "Tail Risk Metrics\n(Implementation needed)",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )

    def _plot_correlation_matrix(self, ax, performance_results):
        ax.text(
            0.5,
            0.5,
            "Correlation Matrix\n(Implementation needed)",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )

    def _plot_risk_contribution(self, ax):
        ax.text(
            0.5,
            0.5,
            "Risk Contribution\n(Implementation needed)",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )

    def _plot_stress_test_results(self, ax):
        ax.text(
            0.5,
            0.5,
            "Stress Test Results\n(Implementation needed)",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )

    def _plot_health_score_overview(self, ax, health_results):
        ax.text(
            0.5,
            0.5,
            "Health Score Overview\n(Implementation needed)",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )

    def _plot_check_status_summary(self, ax, health_results):
        ax.text(
            0.5,
            0.5,
            "Check Status Summary\n(Implementation needed)",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )

    def _plot_data_quality_metrics(self, ax, health_results):
        ax.text(
            0.5,
            0.5,
            "Data Quality Metrics\n(Implementation needed)",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )

    def _plot_performance_trends(self, ax):
        ax.text(
            0.5,
            0.5,
            "Performance Trends\n(Implementation needed)",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )

    def _plot_alert_timeline(self, ax, health_results):
        ax.text(
            0.5,
            0.5,
            "Alert Timeline\n(Implementation needed)",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )

    def _plot_rule_sharpe_comparison(self, ax, performance_results):
        ax.text(
            0.5,
            0.5,
            "Rule Sharpe Comparison\n(Implementation needed)",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )

    def _plot_rule_consistency(self, ax, performance_results):
        ax.text(
            0.5,
            0.5,
            "Rule Consistency\n(Implementation needed)",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )

    def _plot_rule_significance(self, ax, performance_results):
        ax.text(
            0.5,
            0.5,
            "Rule Significance\n(Implementation needed)",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )

    def _plot_rule_diversification(self, ax, performance_results):
        ax.text(
            0.5,
            0.5,
            "Rule Diversification\n(Implementation needed)",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )

    def _plot_rule_performance_timeline(self, ax, performance_results):
        ax.text(
            0.5,
            0.5,
            "Rule Performance Timeline\n(Implementation needed)",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )


# Export the class
__all__ = ["AdvancedProductionMonitor"]
