#!/usr/bin/env python3

"""
Robert Carver's Comprehensive Turnover Analysis Module

Following Robert's methodology from "Systematic Trading" and latest pysystemtrade implementations.
Essential for validating backtest results and understanding system trading costs.

Based on:
- syscore.pandas.strategy_functions.turnover()
- systems.accounts.account_instruments.turnover_at_portfolio_level()
- Robert's speed limit framework from Systematic Trading Chapter 8
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional


class RobertCarverTurnoverAnalyzer:
    """
    Comprehensive turnover analysis following Robert Carver's systematic trading methodology
    """

    def __init__(self, system, standardized_costs: Optional[Dict[str, float]] = None):
        """
        Initialize turnover analyzer

        Args:
            system: pysystemtrade System object
            standardized_costs: Dict of {instrument: standardized_cost_SR}
                               If None, uses conservative defaults
        """
        self.system = system
        self.results = {}

        # Robert's recommended standardized costs (SR units per round trip)
        if standardized_costs is None:
            self.standardized_costs = self._get_default_standardized_costs()
        else:
            self.standardized_costs = standardized_costs

        # Robert's speed limits (max round trips per year by cost level)
        self.speed_limits = {
            0.001: 130,  # Cheapest futures
            0.002: 65,  # Average futures
            0.005: 26,  # Expensive futures
            0.01: 13,  # Very expensive (spread bets)
        }

    def _get_default_standardized_costs(self) -> Dict[str, float]:
        """Get conservative standardized cost estimates for different asset classes"""

        default_costs = {}
        instruments = self.system.get_instrument_list()

        for instrument in instruments:
            # Asset class-based cost estimation (conservative)
            if any(x in instrument for x in ['US10', 'US2', 'BUND', 'SOFR', 'FED']):
                default_costs[instrument] = 0.001  # Interest rate futures (cheapest)
            elif any(x in instrument for x in ['SP500', 'NASDAQ', 'EUROSTX', 'DAX']):
                default_costs[instrument] = 0.002  # Equity index futures
            elif any(x in instrument for x in ['EUR', 'GBP', 'JPY', 'AUD']):
                default_costs[instrument] = 0.002  # Major FX futures
            elif any(x in instrument for x in ['CRUDE', 'GOLD', 'CORN', 'COPPER']):
                default_costs[instrument] = 0.003  # Commodity futures
            else:
                default_costs[instrument] = 0.005  # Conservative default

        return default_costs

    def extract_all_turnover_metrics(self) -> Dict:
        """
        Extract comprehensive turnover metrics following Robert's methodology
        """
        print(f"\n🔄 ROBERT CARVER'S TURNOVER ANALYSIS")
        print(f"{'═' * 60}")
        print(f"Following methodology from 'Systematic Trading' Chapter 8")

        results = {}
        instruments = self.system.get_instrument_list()

        # 1. PORTFOLIO-LEVEL TURNOVER (Primary metric)
        print(f"\n📊 1. PORTFOLIO-LEVEL TURNOVER BY INSTRUMENT")
        print(f"{'─' * 50}")

        portfolio_turnovers = {}
        for instrument in instruments:
            try:
                turnover = self.system.accounts.turnover_at_portfolio_level(
                    instrument, roundpositions=True
                )
                portfolio_turnovers[instrument] = turnover

                # Apply Robert's speed limits
                cost = self.standardized_costs.get(instrument, 0.005)
                speed_limit = self._get_speed_limit(cost)

                status = "✓" if turnover <= speed_limit else "⚠"
                print(f"{status} {instrument:12} {turnover:6.1f} trips/yr "
                      f"(limit: {speed_limit:3.0f}, cost: {cost:.3f})")

            except Exception as e:
                print(f"❌ {instrument:12} Error: {str(e)[:40]}")
                portfolio_turnovers[instrument] = 0.0

        results['portfolio_turnovers'] = portfolio_turnovers

        # 2. SYSTEM-WIDE TURNOVER AGGREGATION
        print(f"\n📈 2. SYSTEM-WIDE TURNOVER ANALYSIS")
        print(f"{'─' * 50}")

        # Weighted average turnover
        try:
            instrument_weights = self._get_instrument_weights()
            total_weighted_turnover = 0
            total_weight = 0

            for instrument in instruments:
                weight = instrument_weights.get(instrument, 0)
                turnover = portfolio_turnovers.get(instrument, 0)
                total_weighted_turnover += weight * turnover
                total_weight += weight

            system_avg_turnover = total_weighted_turnover / max(total_weight, 0.001)
            results['system_average_turnover'] = system_avg_turnover

            print(f"✓ System average turnover: {system_avg_turnover:.1f} round trips/year")

            # Compare to Robert's benchmarks
            if system_avg_turnover <= 12.5:
                print(f"✓ Within Robert's recommended range (≤12.5 for systematic traders)")
            elif system_avg_turnover <= 65:
                print(f"⚠ Moderate turnover - check cost impact")
            else:
                print(f"❌ HIGH TURNOVER - likely unprofitable after costs")

        except Exception as e:
            print(f"❌ System turnover calculation failed: {e}")
            results['system_average_turnover'] = 0.0

        # 3. COST IMPACT ANALYSIS (Critical for profitability)
        print(f"\n💰 3. COST IMPACT ANALYSIS")
        print(f"{'─' * 50}")

        cost_analysis = self._analyze_cost_impact(portfolio_turnovers)
        results['cost_analysis'] = cost_analysis

        # 4. TURNOVER DECOMPOSITION (Advanced diagnostic)
        print(f"\n🔍 4. TURNOVER SOURCE DECOMPOSITION")
        print(f"{'─' * 50}")

        decomposition = self._decompose_turnover_sources()
        results['turnover_decomposition'] = decomposition

        # 5. HOLDING PERIOD ANALYSIS
        print(f"\n⏱ 5. HOLDING PERIOD ANALYSIS")
        print(f"{'─' * 50}")

        holding_periods = self._calculate_holding_periods(portfolio_turnovers)
        results['holding_periods'] = holding_periods

        self.results = results
        return results

    def _get_speed_limit(self, standardized_cost: float) -> float:
        """Get speed limit for given standardized cost"""
        # Robert's formula: Max turnover = 0.13 / standardized_cost
        # But capped at reasonable levels
        max_theoretical = 0.13 / standardized_cost

        # Find closest speed limit tier
        for cost_tier, limit in sorted(self.speed_limits.items()):
            if standardized_cost <= cost_tier:
                return min(limit, max_theoretical)

        return min(13, max_theoretical)  # Conservative fallback

    def _get_instrument_weights(self) -> Dict[str, float]:
        """Extract instrument weights from system"""
        try:
            # Try to get dynamic weights first
            if hasattr(self.system, 'optimisedPositions'):
                weights = self.system.optimisedPositions.get_optimised_weights_df()
                return weights.abs().mean().to_dict()

            # Fallback to config weights
            config_weights = getattr(self.system.config, 'instrument_weights', {})
            if config_weights:
                return config_weights

            # Equal weights fallback
            instruments = self.system.get_instrument_list()
            return {inst: 1.0 / len(instruments) for inst in instruments}

        except Exception:
            # Final fallback
            instruments = self.system.get_instrument_list()
            return {inst: 1.0 / len(instruments) for inst in instruments}

    def _analyze_cost_impact(self, portfolio_turnovers: Dict[str, float]) -> Dict:
        """Analyze cost impact using Robert's Cost = Standardized_Cost × Turnover formula"""

        cost_analysis = {
            'individual_costs': {},
            'total_cost_sr': 0.0,
            'cost_warnings': [],
            'profitability_check': None
        }

        total_cost = 0.0
        instruments = self.system.get_instrument_list()
        instrument_weights = self._get_instrument_weights()

        print(f"Using Robert's formula: Annual Cost (SR) = Standardized Cost × Turnover")
        print(f"Individual instrument costs:")

        for instrument in instruments:
            turnover = portfolio_turnovers.get(instrument, 0)
            std_cost = self.standardized_costs.get(instrument, 0.005)
            weight = instrument_weights.get(instrument, 0)

            # Annual cost in SR units for this instrument
            annual_cost_sr = std_cost * turnover

            # Weight by portfolio allocation
            weighted_cost = annual_cost_sr * weight
            total_cost += weighted_cost

            cost_analysis['individual_costs'][instrument] = {
                'turnover': turnover,
                'standardized_cost': std_cost,
                'annual_cost_sr': annual_cost_sr,
                'weight': weight,
                'weighted_cost': weighted_cost
            }

            # Warnings for high-cost instruments
            if annual_cost_sr > 0.05:  # More than 5% of a typical SR
                cost_analysis['cost_warnings'].append(
                    f"{instrument}: {annual_cost_sr:.3f} SR units/year (HIGH)"
                )

            status = "✓" if annual_cost_sr < 0.05 else "⚠"
            print(f"  {status} {instrument:12} {annual_cost_sr:.4f} SR units/yr "
                  f"(turnover: {turnover:4.1f}, cost: {std_cost:.3f})")

        cost_analysis['total_cost_sr'] = total_cost

        # Robert's profitability check
        print(f"\n💡 PROFITABILITY ASSESSMENT:")
        print(f"Total system cost: {total_cost:.3f} SR units/year")

        if total_cost <= 0.13:
            print(f"✅ EXCELLENT: Within Robert's 0.13 SR limit (max 1/3 of profits)")
            cost_analysis['profitability_check'] = 'excellent'
        elif total_cost <= 0.20:
            print(f"⚠ ACCEPTABLE: Moderate cost impact, monitor closely")
            cost_analysis['profitability_check'] = 'acceptable'
        else:
            print(f"❌ DANGER: Costs likely exceed profitability threshold!")
            cost_analysis['profitability_check'] = 'dangerous'

        return cost_analysis

    def _decompose_turnover_sources(self) -> Dict:
        """Decompose turnover into different sources (forecast vs volatility changes)"""

        decomposition = {
            'forecast_driven': {},
            'volatility_driven': {},
            'other_sources': {}
        }

        try:
            instruments = self.system.get_instrument_list()

            for instrument in instruments[:5]:  # Sample first 5 for performance
                try:
                    # Get different position series to analyze sources
                    positions = self.system.portfolio.get_notional_position(instrument)

                    if len(positions) > 100:  # Need sufficient data
                        # Calculate position changes
                        position_changes = positions.diff().abs()
                        avg_change = position_changes.mean()

                        decomposition['forecast_driven'][instrument] = avg_change
                        print(f"  {instrument}: Avg daily position change: {avg_change:.2f}")

                except Exception as e:
                    print(f"  ⚠ {instrument}: Decomposition failed - {str(e)[:30]}")

        except Exception as e:
            print(f"❌ Turnover decomposition failed: {e}")

        return decomposition

    def _calculate_holding_periods(self, portfolio_turnovers: Dict[str, float]) -> Dict:
        """Calculate implied holding periods from turnover rates"""

        holding_periods = {}

        print(f"Implied holding periods (12 months ÷ turnover):")

        for instrument, turnover in portfolio_turnovers.items():
            if turnover > 0:
                # Holding period in months
                holding_period_months = 12.0 / turnover
                holding_periods[instrument] = holding_period_months

                # Format for readability
                if holding_period_months >= 12:
                    period_str = f"{holding_period_months / 12:.1f} years"
                elif holding_period_months >= 1:
                    period_str = f"{holding_period_months:.1f} months"
                else:
                    period_str = f"{holding_period_months * 30:.0f} days"

                print(f"  {instrument:12} {period_str:12} (turnover: {turnover:.1f})")
            else:
                holding_periods[instrument] = float('inf')
                print(f"  {instrument:12} {'∞ (no trading)':12}")

        return holding_periods

    def generate_turnover_report(self, output_dir: str = 'project_dynamic/results') -> str:
        """Generate comprehensive turnover report for backtest validation"""

        if not self.results:
            self.extract_all_turnover_metrics()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"{output_dir}/turnover_analysis_report_{timestamp}.txt"

        try:
            import os
            os.makedirs(output_dir, exist_ok=True)

            with open(report_file, 'w') as f:
                f.write("ROBERT CARVER'S TURNOVER ANALYSIS REPORT\n")
                f.write("=" * 60 + "\n")
                f.write(f"Generated: {datetime.now()}\n")
                f.write(f"System: Dynamic Optimization Backtest\n\n")

                # Executive Summary
                f.write("EXECUTIVE SUMMARY\n")
                f.write("-" * 20 + "\n")
                cost = self.results['cost_analysis']['total_cost_sr']
                avg_turnover = self.results['system_average_turnover']
                status = self.results['cost_analysis']['profitability_check']

                f.write(f"System Average Turnover: {avg_turnover:.1f} round trips/year\n")
                f.write(f"Total Annual Costs: {cost:.3f} SR units\n")
                f.write(f"Profitability Status: {status.upper()}\n\n")

                # Detailed Results
                f.write("DETAILED TURNOVER BY INSTRUMENT\n")
                f.write("-" * 35 + "\n")
                f.write(f"{'Instrument':<15} {'Turnover':<10} {'Cost (SR)':<12} {'Status':<10}\n")
                f.write("-" * 50 + "\n")

                for instrument, data in self.results['cost_analysis']['individual_costs'].items():
                    turnover = data['turnover']
                    cost_sr = data['annual_cost_sr']
                    status = "OK" if cost_sr < 0.05 else "HIGH"
                    f.write(f"{instrument:<15} {turnover:<10.1f} {cost_sr:<12.4f} {status:<10}\n")

                # Warnings
                warnings = self.results['cost_analysis']['cost_warnings']
                if warnings:
                    f.write(f"\nWARNINGS\n")
                    f.write("-" * 10 + "\n")
                    for warning in warnings:
                        f.write(f"⚠ {warning}\n")

                # Recommendations
                f.write(f"\nROBERT CARVER'S RECOMMENDATIONS\n")
                f.write("-" * 35 + "\n")

                if status == 'excellent':
                    f.write("✅ System passes turnover analysis\n")
                    f.write("✅ Costs are within acceptable limits\n")
                    f.write("✅ Proceed with confidence\n")
                elif status == 'acceptable':
                    f.write("⚠ Monitor turnover closely\n")
                    f.write("⚠ Consider reducing forecast speed or increasing buffers\n")
                else:
                    f.write("❌ URGENT: Turnover too high for profitability\n")
                    f.write("❌ Reduce number of trading rules\n")
                    f.write("❌ Increase position buffers\n")
                    f.write("❌ Focus on slower, more persistent signals\n")

            print(f"✅ Turnover report saved: {report_file}")
            return report_file

        except Exception as e:
            print(f"❌ Failed to save turnover report: {e}")
            return ""

    def plot_turnover_analysis(self, output_dir: str = 'project_dynamic/results'):
        """Create visualizations of turnover analysis"""

        try:
            import matplotlib.pyplot as plt
            import os

            os.makedirs(output_dir, exist_ok=True)

            if not self.results:
                self.extract_all_turnover_metrics()

            # Create turnover vs cost scatter plot
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

            # Plot 1: Turnover by Instrument
            instruments = list(self.results['portfolio_turnovers'].keys())
            turnovers = list(self.results['portfolio_turnovers'].values())

            ax1.bar(range(len(instruments)), turnovers, alpha=0.7, color='steelblue')
            ax1.set_xlabel('Instruments')
            ax1.set_ylabel('Annual Turnover (Round Trips)')
            ax1.set_title('Portfolio Turnover by Instrument\n(Robert Carver Analysis)')
            ax1.set_xticks(range(0, len(instruments), max(1, len(instruments) // 10)))
            ax1.set_xticklabels([instruments[i] for i in range(0, len(instruments), max(1, len(instruments) // 10))],
                                rotation=45, ha='right')

            # Add Robert's speed limit line
            avg_speed_limit = 65  # Conservative average
            ax1.axhline(y=avg_speed_limit, color='red', linestyle='--',
                        label=f'Conservative Speed Limit ({avg_speed_limit})')
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            # Plot 2: Cost Impact Analysis
            costs = [self.results['cost_analysis']['individual_costs'][inst]['annual_cost_sr']
                     for inst in instruments]

            ax2.scatter(turnovers, costs, alpha=0.7, s=50, color='darkred')
            ax2.set_xlabel('Annual Turnover (Round Trips)')
            ax2.set_ylabel('Annual Cost (SR Units)')
            ax2.set_title('Cost vs Turnover Analysis\n(Following Robert\'s Formula)')

            # Add Robert's cost limit line
            ax2.axhline(y=0.05, color='orange', linestyle='--', label='High Cost Threshold (0.05 SR)')
            ax2.axhline(y=0.13, color='red', linestyle='--', label='Robert\'s Max Limit (0.13 SR)')
            ax2.legend()
            ax2.grid(True, alpha=0.3)

            plt.tight_layout()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            plot_file = f"{output_dir}/turnover_analysis_{timestamp}.png"
            plt.savefig(plot_file, dpi=300, bbox_inches='tight')
            print(f"✅ Turnover plots saved: {plot_file}")

            plt.show()
            return plot_file

        except ImportError:
            print("❌ Matplotlib not available for turnover plots")
            return ""
        except Exception as e:
            print(f"❌ Failed to create turnover plots: {e}")
            return ""


def quick_turnover_check(system) -> Dict:
    """
    Quick turnover check for immediate feedback during backtesting
    """
    print(f"\n⚡ QUICK TURNOVER CHECK")
    print(f"{'─' * 30}")

    analyzer = RobertCarverTurnoverAnalyzer(system)

    # Just check first few instruments for speed
    instruments = system.get_instrument_list()[:10]
    quick_results = {}

    total_turnover = 0
    high_turnover_count = 0

    for instrument in instruments:
        try:
            turnover = system.accounts.turnover_at_portfolio_level(instrument)
            quick_results[instrument] = turnover
            total_turnover += turnover

            if turnover > 65:  # Robert's moderate threshold
                high_turnover_count += 1
                print(f"⚠ {instrument}: {turnover:.1f} trips/yr (HIGH)")
            else:
                print(f"✓ {instrument}: {turnover:.1f} trips/yr")

        except Exception as e:
            print(f"❌ {instrument}: Error calculating turnover")

    avg_turnover = total_turnover / len(instruments)

    print(f"\n📊 Quick Summary:")
    print(f"Average turnover: {avg_turnover:.1f} round trips/year")
    print(f"High turnover instruments: {high_turnover_count}/{len(instruments)}")

    if avg_turnover <= 12.5:
        print(f"✅ GOOD: Within Robert's systematic trader range")
    elif avg_turnover <= 65:
        print(f"⚠ MODERATE: Check detailed cost analysis")
    else:
        print(f"❌ HIGH: Likely unprofitable - detailed analysis needed")

    return quick_results
