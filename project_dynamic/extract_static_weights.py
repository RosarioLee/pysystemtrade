"""
extract_static_weights.py

Extract forecast weights, turnover, and costs from dynamic optimization backtest
for conversion to static weights configuration.

This script:
1. Loads a completed backtest system (from pickle or re-creates it)
2. Extracts forecast weights time series for all instruments
3. Calculates turnover for each (instrument, rule) pair
4. Calculates SR costs for each instrument
5. Analyzes weight stability over time
6. Saves comprehensive analysis for static weight creation

Author: Systematic Trading Implementation
Date: December 2024
"""

import os
import sys
import pickle
import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings("ignore")

# Add project directory to path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_dir)

from systems.provided.rob_system.run_system import futures_system
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData

# ========================================================================
# CONFIGURATION - UPDATE THESE PATHS
# ========================================================================

DEFAULT_CONFIG = {
    # Path to your pickled system (FAST - recommended)
    'pickle_path': 'results/pickles/system_20251227_203003.pkl',

    # Alternative: rebuild from config (SLOW - only if pickle unavailable)
    'config_path': None,  # 'dynamic_backtest_config.yaml'

    # Analysis parameters
    'cost_threshold': 0.13,  # Max acceptable SR cost
    'weight_method': 'averagelast2y',  # How to aggregate weights
    'lookback_years': 2,  # For stability analysis

    # Output settings
    'generate_plots': True,  # Create visualization plots
    'output_dir': 'results/static_weight_analysis'
}
class ForecastWeightExtractor:
    """
    Extract and analyze forecast weights from dynamic optimization backtest
    for conversion to static configuration.
    """

    def __init__(self, system=None, system_pickle_path=None, config_path=None):
        """
        Initialize extractor with either:
        - A pre-built system object
        - Path to pickled system
        - Config path to rebuild system

        Args:
            system: Pre-built system object (if available)
            system_pickle_path: Path to pickled system file
            config_path: Path to config YAML (will rebuild system)
        """
        self.system = None
        self.instruments = []
        self.rules = []

        # Data storage
        self.forecast_weights = {}  # {instrument: DataFrame of weights over time}
        self.turnover_matrix = None  # DataFrame: instruments x rules
        self.sr_cost_vector = None   # Series: instruments
        self.annual_cost_matrix = None  # DataFrame: turnover × SR_cost

        # Analysis results
        self.weight_stability = {}
        self.cost_violations = {}
        self.recommended_weights = {}

        # Load or create system
        if system is not None:
            self.system = system
            print("✓ Using provided system object")
        elif system_pickle_path and os.path.exists(system_pickle_path):
            self.load_system_from_pickle(system_pickle_path)
        elif config_path:
            self.rebuild_system(config_path)
        else:
            raise ValueError("Must provide system, system_pickle_path, or config_path")

        # Extract instrument and rule lists
        if self.system:
            self.instruments = self.system.get_instrument_list()
            self.rules = list(self.system.rules.trading_rules().keys())
            print(f"✓ System loaded: {len(self.instruments)} instruments, {len(self.rules)} rules")

    def load_system_from_pickle(self, pickle_path):
        """Load previously saved system from pickle file"""
        print(f"Loading system from pickle: {pickle_path}")
        try:
            with open(pickle_path, 'rb') as f:
                self.system = pickle.load(f)
            print("✓ System loaded from pickle")
        except Exception as e:
            print(f"❌ Error loading pickle: {e}")
            raise

    def rebuild_system(self, config_path):
        """Rebuild system from config (useful if pickle not available)"""
        print(f"Rebuilding system from config: {config_path}")
        try:
            data = csvFuturesSimData()
            self.system = futures_system(
                sim_data=data,
                config_filename=config_path
            )
            print("✓ System rebuilt")
        except Exception as e:
            print(f"❌ Error rebuilding system: {e}")
            raise

    def save_system_to_pickle(self, output_path):
        """Save system to pickle for faster future loading"""
        print(f"Saving system to pickle: {output_path}")
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                pickle.dump(self.system, f, protocol=pickle.HIGHEST_PROTOCOL)
            print(f"✓ System saved to {output_path}")
        except Exception as e:
            print(f"❌ Error saving pickle: {e}")

    # ========================================================================
    # PART 1: EXTRACT FORECAST WEIGHTS TIME SERIES
    # ========================================================================

    def extract_all_forecast_weights(self, save_dir="results/forecast_weights_timeseries"):
        """
        Extract forecast weights time series for ALL instruments.
        This is the core data needed for static weight creation.

        Returns:
            dict: {instrument: DataFrame with columns = rules, index = dates}
        """
        print(f"\n{'=' * 70}")
        print("EXTRACTING FORECAST WEIGHTS TIME SERIES")
        print(f"{'=' * 70}")

        os.makedirs(save_dir, exist_ok=True)

        for i, instrument in enumerate(self.instruments, 1):
            print(f"[{i}/{len(self.instruments)}] Extracting {instrument}...", end=" ")

            try:
                # Get forecast weights time series
                weights = self.system.combForecast.get_forecast_weights(instrument)

                # Store in dictionary
                self.forecast_weights[instrument] = weights

                # Save to CSV for inspection
                csv_path = os.path.join(save_dir, f"{instrument}_weights.csv")
                weights.to_csv(csv_path)

                # Report statistics
                n_dates = len(weights)
                n_rules = len(weights.columns)
                print(f"✓ {n_dates} dates, {n_rules} rules")

            except Exception as e:
                print(f"❌ Error: {e}")
                self.forecast_weights[instrument] = None

        print(f"\n✓ Forecast weights extracted and saved to {save_dir}")
        return self.forecast_weights

    # ========================================================================
    # PART 2: EXTRACT TURNOVER AND COSTS
    # ========================================================================

    def calculate_turnover_matrix(self):
        """
        Calculate instrument-specific turnover using pysystemtrade's subsystem methods.
        """

        print(f"\n{'=' * 70}")
        print("CALCULATING TURNOVER MATRIX (SUBSYSTEM-LEVEL)")
        print(f"{'=' * 70}")

        turnover_data = []

        for i, instrument in enumerate(self.instruments, 1):
            print(f"[{i}/{len(self.instruments)}] {instrument:20s}", end=" ")
            row = {'instrument': instrument}

            try:
                # Get subsystem P&L for this instrument
                subsys_pandl = self.system.accounts.pandl_for_subsystem(
                    instrument_code=instrument
                )

                # Get forecast weights to decompose by rule
                weights = self.system.combForecast.get_forecast_weights(instrument)

                # For each rule, estimate its turnover contribution
                for rule in self.rules:
                    if rule not in weights.columns:
                        row[rule] = 0.0
                        continue

                    # Get rule's forecast
                    forecast = self.system.rules.get_raw_forecast(instrument, rule)

                    # Calculate rule's turnover contribution
                    rule_weight = weights[rule].mean()
                    forecast_vol = forecast.diff().abs().mean()
                    forecast_level = forecast.abs().mean()

                    if forecast_level > 1:
                        rule_turnover_rate = forecast_vol / forecast_level
                        annual_rule_turnover = rule_turnover_rate * 256 * rule_weight
                    else:
                        annual_rule_turnover = 0.0

                    row[rule] = annual_rule_turnover

                turnover_data.append(row)

                # Summary
                avg_turn = np.mean([v for k, v in row.items() if k != 'instrument'])
                print(f"→ avg turnover: {avg_turn:.1f}x/year")

            except Exception as e:
                print(f"❌ Error: {e}")
                # Fill with NaN
                for rule in self.rules:
                    row[rule] = np.nan
                turnover_data.append(row)

        self.turnover_matrix = pd.DataFrame(turnover_data)
        self.turnover_matrix.set_index('instrument', inplace=True)

        print(f"\n✓ Turnover matrix created: {self.turnover_matrix.shape}")

        # VALIDATION: Check for suspicious patterns
        print("\n🔍 Validating turnover calculations...")
        for rule in self.rules:
            unique_count = self.turnover_matrix[rule].nunique()
            if unique_count == 1:
                print(f"  ⚠️  {rule:20s}: All instruments IDENTICAL (BUG!)")
            elif unique_count < 5:
                print(f"  ⚠️  {rule:20s}: Only {unique_count} unique values (suspicious)")
            else:
                print(f"  ✓  {rule:20s}: {unique_count} different values (good!)")

        return self.turnover_matrix

    def calculate_sr_cost_vector(self):
        """
        Calculate SR cost per trade for each instrument.

        Returns:
            Series: instrument → SR_cost
        """
        print(f"\n{'=' * 70}")
        print("CALCULATING SR COSTS")
        print(f"{'=' * 70}")

        sr_costs = {}

        for i, instrument in enumerate(self.instruments, 1):
            print(f"[{i}/{len(self.instruments)}] {instrument:20s}", end=" ")

            try:
                sr_cost = self.system.accounts.get_SR_cost_per_trade_for_instrument(
                    instrument
                )
                sr_costs[instrument] = sr_cost
                print(f"SR_cost: {sr_cost:.6f}")

            except Exception as e:
                sr_costs[instrument] = np.nan
                print(f"❌ Error: {e}")

        self.sr_cost_vector = pd.Series(sr_costs, name='SR_cost')

        print(f"\n✓ SR cost vector created")
        print(f"  Mean SR cost: {self.sr_cost_vector.mean():.6f}")
        print(f"  Median SR cost: {self.sr_cost_vector.median():.6f}")
        print(f"  Min SR cost: {self.sr_cost_vector.min():.6f}")
        print(f"  Max SR cost: {self.sr_cost_vector.max():.6f}")

        return self.sr_cost_vector

    def calculate_annual_cost_matrix(self):
        """
        Calculate annual SR cost = turnover × SR_cost for each (instrument, rule).
        This is THE KEY METRIC for determining which rules to keep.

        Returns:
            DataFrame: instruments × rules, values = annual SR cost
        """
        print(f"\n{'=' * 70}")
        print("CALCULATING ANNUAL COST MATRIX (turnover × SR_cost)")
        print(f"{'=' * 70}")

        if self.turnover_matrix is None:
            self.calculate_turnover_matrix()

        if self.sr_cost_vector is None:
            self.calculate_sr_cost_vector()

        # Matrix multiplication: each cell = turnover[inst, rule] × SR_cost[inst]
        self.annual_cost_matrix = self.turnover_matrix.multiply(
            self.sr_cost_vector, axis=0
        )

        print(f"✓ Annual cost matrix created: {self.annual_cost_matrix.shape}")
        print(f"  Mean annual cost: {self.annual_cost_matrix.mean().mean():.4f}")
        print(f"  Max annual cost: {self.annual_cost_matrix.max().max():.4f}")

        return self.annual_cost_matrix

    # ========================================================================
    # PART 3: ANALYZE WEIGHT STABILITY
    # ========================================================================

    def analyze_weight_stability(self, lookback_years=3):
        """
        Analyze how stable forecast weights are over time.
        Key question: Can we trust the latest weights, or are they noisy?

        Args:
            lookback_years: Number of recent years to analyze

        Returns:
            dict: {instrument: stability_metrics}
        """
        print(f"\n{'=' * 70}")
        print(f"ANALYZING WEIGHT STABILITY (last {lookback_years} years)")
        print(f"{'=' * 70}")

        days = lookback_years * 252  # Approximate trading days

        for instrument in self.instruments:
            if self.forecast_weights.get(instrument) is None:
                continue

            weights = self.forecast_weights[instrument]

            if len(weights) < days:
                recent_weights = weights
            else:
                recent_weights = weights.iloc[-days:]

            # Calculate stability metrics
            stability = {}

            for rule in recent_weights.columns:
                rule_weights = recent_weights[rule]

                # Metrics
                stability[rule] = {
                    'mean': rule_weights.mean(),
                    'std': rule_weights.std(),
                    'cv': rule_weights.std() / rule_weights.mean() if rule_weights.mean() != 0 else np.inf,
                    'min': rule_weights.min(),
                    'max': rule_weights.max(),
                    'range': rule_weights.max() - rule_weights.min(),
                    'latest': rule_weights.iloc[-1],
                    'is_zero': (rule_weights == 0).all()  # Always zero?
                }

            self.weight_stability[instrument] = stability

        print(f"✓ Weight stability analyzed for {len(self.weight_stability)} instruments")
        return self.weight_stability

    # ========================================================================
    # PART 4: IDENTIFY COST VIOLATIONS
    # ========================================================================

    def identify_cost_violations(self, threshold=0.13):
        """
        Identify rules that violate the cost threshold.
        These rules should have ZERO weight in static config.

        Args:
            threshold: Maximum acceptable annual SR cost (default 0.13)

        Returns:
            dict: {instrument: list of rules to eliminate}
        """
        print(f"\n{'=' * 70}")
        print(f"IDENTIFYING COST VIOLATIONS (threshold: {threshold})")
        print(f"{'=' * 70}")

        if self.annual_cost_matrix is None:
            self.calculate_annual_cost_matrix()

        violations = {}
        total_violations = 0

        for instrument in self.instruments:
            if instrument not in self.annual_cost_matrix.index:
                continue

            costs = self.annual_cost_matrix.loc[instrument]
            violated_rules = costs[costs > threshold].index.tolist()

            if violated_rules:
                violations[instrument] = violated_rules
                total_violations += len(violated_rules)
                print(f"{instrument:20s}: {len(violated_rules)} rules eliminated - {violated_rules}")

        self.cost_violations = violations

        print(f"\n✓ Cost analysis complete")
        print(f"  Total rule violations: {total_violations}")
        print(f"  Instruments with violations: {len(violations)}")
        print(f"  Average violations per instrument: {total_violations / len(self.instruments):.1f}")

        return violations

    # ========================================================================
    # PART 5: CALCULATE RECOMMENDED STATIC WEIGHTS
    # ========================================================================

    def calculate_recommended_weights(
        self,
        method='average_last_2y',
        cost_threshold=0.13,
        round_to=0.001
    ):
        """
        Calculate recommended static weights for each instrument.

        Args:
            method: How to aggregate weights
                - 'latest': Use most recent value
                - 'average_last_1y': Average last year
                - 'average_last_2y': Average last 2 years (recommended)
                - 'average_last_3y': Average last 3 years
                - 'median_last_2y': Median last 2 years
            cost_threshold: Eliminate rules above this cost
            round_to: Round weights to this precision

        Returns:
            dict: {instrument: {rule: weight}}
        """
        print(f"\n{'=' * 70}")
        print(f"CALCULATING RECOMMENDED STATIC WEIGHTS")
        print(f"Method: {method}")
        print(f"Cost threshold: {cost_threshold}")
        print(f"Rounding: {round_to}")
        print(f"{'=' * 70}")

        if self.annual_cost_matrix is None:
            self.calculate_annual_cost_matrix()

        # Define lookback based on method
        lookback_days = {
            'latest': 1,
            'average_last_1y': 252,
            'average_last_2y': 504,
            'average_last_3y': 756,
            'median_last_2y': 504
        }

        days = lookback_days.get(method, 504)
        use_median = 'median' in method

        for i, instrument in enumerate(self.instruments, 1):
            print(f"[{i}/{len(self.instruments)}] {instrument:20s}", end=" ")

            if self.forecast_weights.get(instrument) is None:
                print("❌ No weights")
                continue

            weights = self.forecast_weights[instrument]

            # Get recent weights
            if len(weights) < days:
                recent = weights
            else:
                recent = weights.iloc[-days:]

            # Aggregate
            if use_median:
                aggregated = recent.median()
            else:
                aggregated = recent.mean()

            # Apply cost filter
            costs = self.annual_cost_matrix.loc[instrument]
            mask_keep = costs <= cost_threshold

            # Zero out expensive rules
            filtered = aggregated.copy()
            filtered[~mask_keep] = 0.0

            # Renormalize to sum to 1.0
            total = filtered.sum()
            if total > 0:
                normalized = filtered / total
            else:
                normalized = filtered  # All zero

            # Round
            rounded = normalized.round(int(-np.log10(round_to)))

            # Re-adjust to ensure sum ≈ 1.0 after rounding
            if rounded.sum() > 0:
                final = rounded / rounded.sum()
            else:
                final = rounded

            # Convert to dict
            self.recommended_weights[instrument] = final.to_dict()

            # Report
            n_active = (final > 0).sum()
            print(f"→ {n_active}/{len(final)} rules active, sum={final.sum():.3f}")

        print(f"\n✓ Recommended static weights calculated for {len(self.recommended_weights)} instruments")
        return self.recommended_weights

    # ========================================================================
    # PART 6: SAVE ANALYSIS RESULTS
    # ========================================================================

    def save_all_analysis(self, output_dir="results/static_weight_analysis"):
        """
        Save all analysis results to files for inspection and config generation.
        """
        print(f"\n{'=' * 70}")
        print(f"SAVING ANALYSIS RESULTS")
        print(f"{'=' * 70}")

        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 1. Turnover matrix
        if self.turnover_matrix is not None:
            path = os.path.join(output_dir, f"turnover_matrix_{timestamp}.csv")
            self.turnover_matrix.to_csv(path)
            print(f"✓ Turnover matrix: {path}")

        # 2. SR cost vector
        if self.sr_cost_vector is not None:
            path = os.path.join(output_dir, f"sr_cost_vector_{timestamp}.csv")
            self.sr_cost_vector.to_csv(path)
            print(f"✓ SR cost vector: {path}")

        # 3. Annual cost matrix
        if self.annual_cost_matrix is not None:
            path = os.path.join(output_dir, f"annual_cost_matrix_{timestamp}.csv")
            self.annual_cost_matrix.to_csv(path)
            print(f"✓ Annual cost matrix: {path}")

        # 4. Cost violations
        if self.cost_violations:
            path = os.path.join(output_dir, f"cost_violations_{timestamp}.txt")
            with open(path, 'w') as f:
                f.write("COST VIOLATIONS (Rules to Eliminate)\n")
                f.write("=" * 70 + "\n\n")
                for inst, rules in self.cost_violations.items():
                    f.write(f"{inst}: {rules}\n")
            print(f"✓ Cost violations: {path}")

        # 5. Recommended weights
        if self.recommended_weights:
            path = os.path.join(output_dir, f"recommended_weights_{timestamp}.pkl")
            with open(path, 'wb') as f:
                pickle.dump(self.recommended_weights, f)
            print(f"✓ Recommended weights (pickle): {path}")

            # Also save as readable CSV
            weights_df = pd.DataFrame(self.recommended_weights).T
            csv_path = os.path.join(output_dir, f"recommended_weights_{timestamp}.csv")
            weights_df.to_csv(csv_path)
            print(f"✓ Recommended weights (CSV): {csv_path}")

        # 6. Summary report
        summary_path = os.path.join(output_dir, f"analysis_summary_{timestamp}.txt")
        with open(summary_path, 'w') as f:
            f.write("STATIC WEIGHT EXTRACTION ANALYSIS SUMMARY\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"Analysis Date: {datetime.now()}\n")
            f.write(f"Number of Instruments: {len(self.instruments)}\n")
            f.write(f"Number of Rules: {len(self.rules)}\n\n")

            if self.sr_cost_vector is not None:
                f.write("SR COST STATISTICS:\n")
                f.write(f"  Mean: {self.sr_cost_vector.mean():.6f}\n")
                f.write(f"  Median: {self.sr_cost_vector.median():.6f}\n")
                f.write(f"  Min: {self.sr_cost_vector.min():.6f} ({self.sr_cost_vector.idxmin()})\n")
                f.write(f"  Max: {self.sr_cost_vector.max():.6f} ({self.sr_cost_vector.idxmax()})\n\n")

            if self.annual_cost_matrix is not None:
                f.write("ANNUAL COST STATISTICS:\n")
                f.write(f"  Mean: {self.annual_cost_matrix.mean().mean():.4f}\n")
                f.write(f"  Max: {self.annual_cost_matrix.max().max():.4f}\n\n")

            if self.cost_violations:
                f.write("COST VIOLATIONS:\n")
                f.write(f"  Total violations: {sum(len(v) for v in self.cost_violations.values())}\n")
                f.write(f"  Instruments affected: {len(self.cost_violations)}\n")

        print(f"✓ Analysis summary: {summary_path}")
        print(f"\n✅ All analysis results saved to {output_dir}")

    # ========================================================================
    # PART 7: VISUALIZATION
    # ========================================================================

    def plot_weight_evolution(self, instruments=None, save_dir="results/plots"):
        """
        Plot how weights evolved over time for sample instruments.
        Helps validate if we should use latest weights or need more smoothing.

        Args:
            instruments: List of instruments to plot (default: first 6)
        """
        print(f"\n{'=' * 70}")
        print("PLOTTING WEIGHT EVOLUTION")
        print(f"{'=' * 70}")

        os.makedirs(save_dir, exist_ok=True)

        if instruments is None:
            instruments = self.instruments[:6]

        for instrument in instruments:
            if self.forecast_weights.get(instrument) is None:
                continue

            weights = self.forecast_weights[instrument]

            fig, ax = plt.subplots(figsize=(14, 8))

            for rule in weights.columns:
                ax.plot(weights.index, weights[rule], label=rule, linewidth=1.5, alpha=0.7)

            ax.set_title(f"Forecast Weight Evolution: {instrument}", fontsize=14, fontweight='bold')
            ax.set_xlabel("Date", fontsize=12)
            ax.set_ylabel("Weight", fontsize=12)
            ax.legend(loc='upper left', bbox_to_anchor=(1.05, 1), frameon=True)
            ax.grid(True, alpha=0.3)

            plt.tight_layout()

            filename = os.path.join(save_dir, f"weights_{instrument}.png")
            plt.savefig(filename, dpi=150, bbox_inches='tight')
            plt.close()

            print(f"✓ Saved plot: {filename}")

    def plot_cost_heatmap(self, save_path="results/plots/cost_heatmap.png"):
        """
        Create heatmap of annual costs to visualize which rules are expensive.
        """
        print(f"\n{'=' * 70}")
        print("CREATING COST HEATMAP")
        print(f"{'=' * 70}")

        if self.annual_cost_matrix is None:
            print("❌ No cost matrix available")
            return

        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        fig, ax = plt.subplots(figsize=(16, 20))

        sns.heatmap(
            self.annual_cost_matrix,
            annot=False,
            cmap='RdYlGn_r',
            vmin=0,
            vmax=0.15,
            cbar_kws={'label': 'Annual SR Cost'},
            ax=ax
        )

        ax.set_title("Annual SR Cost Matrix (turnover × SR_cost)", fontsize=14, fontweight='bold')
        ax.set_xlabel("Trading Rule", fontsize=12)
        ax.set_ylabel("Instrument", fontsize=12)

        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"✓ Cost heatmap saved: {save_path}")

    # ========================================================================
    # MAIN EXECUTION WORKFLOW
    # ========================================================================

    def run_full_analysis(
        self,
        cost_threshold=0.13,
        weight_method='average_last_2y',
        save_plots=True
    ):
        """
        Run complete analysis pipeline.

        Args:
            cost_threshold: Maximum acceptable SR cost
            weight_method: How to aggregate weights
            save_plots: Whether to generate plots

        Returns:
            dict: Recommended static weights
        """
        print(f"\n{'=' * 90}")
        print("RUNNING FULL STATIC WEIGHT EXTRACTION ANALYSIS")
        print(f"{'=' * 90}\n")

        # Step 1: Extract forecast weights
        self.extract_all_forecast_weights()

        # Step 2: Calculate turnover and costs
        self.calculate_turnover_matrix()
        self.calculate_sr_cost_vector()
        self.calculate_annual_cost_matrix()

        # Step 3: Analyze stability
        self.analyze_weight_stability(lookback_years=3)

        # Step 4: Identify violations
        self.identify_cost_violations(threshold=cost_threshold)

        # Step 5: Calculate recommended weights
        self.calculate_recommended_weights(
            method=weight_method,
            cost_threshold=cost_threshold
        )

        # Step 6: Save everything
        self.save_all_analysis()

        # Step 7: Plots (optional)
        if save_plots:
            self.plot_weight_evolution()
            self.plot_cost_heatmap()

        print(f"\n{'=' * 90}")
        print("✅ ANALYSIS COMPLETE")
        print(f"{'=' * 90}\n")
        print("Next steps:")
        print("1. Review the analysis files in results/static_weight_analysis/")
        print("2. Run create_static_config.py to generate YAML configuration")

        return self.recommended_weights


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

def main():
    """Command line interface with sensible defaults"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Extract static weights from dynamic optimization backtest'
    )

    # Make all arguments optional with defaults from config
    parser.add_argument(
        '--pickle',
        type=str,
        default=DEFAULT_CONFIG['pickle_path'],  # ← Use default
        help=f"Path to pickled system (default: {DEFAULT_CONFIG['pickle_path']})"
    )

    parser.add_argument(
        '--config',
        type=str,
        default=DEFAULT_CONFIG['config_path'],
        help='Path to config YAML (alternative to pickle - SLOW)'
    )

    parser.add_argument(
        '--cost-threshold',
        type=float,
        default=DEFAULT_CONFIG['cost_threshold'],
        help=f"Max SR cost (default: {DEFAULT_CONFIG['cost_threshold']})"
    )

    parser.add_argument(
        '--weight-method',
        type=str,
        default=DEFAULT_CONFIG['weight_method'],
        choices=['latest', 'averagelast1y', 'averagelast2y', 'averagelast3y', 'medianlast2y'],
        help=f"Aggregation method (default: {DEFAULT_CONFIG['weight_method']})"
    )

    parser.add_argument(
        '--no-plots',
        action='store_true',
        default=not DEFAULT_CONFIG['generate_plots'],
        help='Skip plot generation'
    )

    args = parser.parse_args()

    # Validate: need either pickle or config
    if not args.pickle and not args.config:
        parser.error("Must provide either --pickle or --config (or set DEFAULT_CONFIG)")

    # Create extractor
    print(f"\n{'=' * 90}")
    print("FORECAST WEIGHT EXTRACTION - STATIC CONFIGURATION")
    print(f"{'=' * 90}\n")

    if args.pickle:
        print(f"✓ Loading from pickle: {args.pickle}")
        extractor = ForecastWeightExtractor(system_pickle_path=args.pickle)
    else:
        print(f"⚠️  Rebuilding from config: {args.config}")
        print("   (This will take as long as running the backtest!)")
        extractor = ForecastWeightExtractor(config_path=args.config)

    # Run full analysis
    extractor.run_full_analysis(
        cost_threshold=args.cost_threshold,
        weight_method=args.weight_method,
        save_plots=not args.no_plots
    )

    print(f"\n{'=' * 90}")
    print("✅ EXTRACTION COMPLETE")
    print(f"{'=' * 90}\n")
    print("Next steps:")
    print("  1. Review analysis in results/static_weight_analysis/")
    print("  2. Run: python create_static_config.py --base-config dynamic_backtest_config.yaml")
    print("  3. Copy generated YAML to your production config")


if __name__ == "__main__":
    main()
