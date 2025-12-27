"""
create_static_config.py

Generate static forecast weights YAML configuration from extracted weight analysis.

This script:
1. Loads the recommended weights from extract_static_weights.py
2. Groups instruments into cost/liquidity tiers
3. Identifies common weight patterns
4. Creates templates to reduce duplication
5. Generates complete YAML config with static forecast_weights section
6. Optionally validates against original dynamic optimization

Author: Systematic Trading Implementation
Date: December 2024
"""

import os
import sys
import pickle
import warnings
from datetime import datetime
from pathlib import Path
from collections import defaultdict

import pandas as pd
import numpy as np
import yaml

warnings.filterwarnings("ignore")

# ========================================================================
# CONFIGURATION - UPDATE THESE PATHS
# ========================================================================

DEFAULT_CONFIG = {
    # Input paths
    "base_config": "dynamic_backtest_config.yaml",
    "analysis_dir": "results/static_weight_analysis",
    # Output paths
    "weights_yaml": "results/static_forecast_weights.yaml",
    "complete_config": "results/static_system_config.yaml",
    "documentation": "results/static_weights_documentation.md",
    # Generation options
    "use_templates": True,  # Group similar instruments
    "generate_docs": True,  # Create markdown docs
    "include_comments": True,  # Add comments to YAML
}


class StaticConfigGenerator:
    """
    Generate static forecast weights configuration from analysis results.
    """

    def __init__(self, analysis_dir="results/static_weight_analysis"):
        """
        Initialize with directory containing analysis results.

        Args:
            analysis_dir: Directory with pickled recommended_weights file
        """
        self.analysis_dir = analysis_dir
        self.recommended_weights = None
        self.sr_costs = None
        self.instrument_tiers = {}
        self.weight_templates = {}
        self.template_assignments = {}

        print(f"Static Config Generator initialized")
        print(f"Analysis directory: {analysis_dir}")

    def load_analysis_results(self):
        """Load previously generated analysis results"""
        print(f"\n{'=' * 70}")
        print("LOADING ANALYSIS RESULTS")
        print(f"{'=' * 70}")

        # Find latest files
        weights_file = self._find_latest_file("recommended_weights_*.pkl")
        costs_file = self._find_latest_file("sr_cost_vector_*.csv")
        turnover_file = self._find_latest_file("turnover_matrix_*.csv")

        if not all([weights_file, costs_file, turnover_file]):
            raise FileNotFoundError(
                "Missing analysis files. Run extract_static_weights.py first."
            )

        # Load weights
        print(f"Loading weights: {weights_file}")
        with open(weights_file, "rb") as f:
            self.recommended_weights = pickle.load(f)
        print(f"✓ Loaded weights for {len(self.recommended_weights)} instruments")

        # Load costs - FIXED for pandas 2.0+
        print(f"Loading costs: {costs_file}")
        self.sr_costs = pd.read_csv(costs_file, index_col=0).squeeze("columns")
        print(f"✓ Loaded SR costs for {len(self.sr_costs)} instruments")

        # Load turnover - FIXED for pandas 2.0+
        print(f"Loading turnover: {turnover_file}")
        self.turnover = pd.read_csv(turnover_file, index_col=0).squeeze("columns")
        print(f"✓ Loaded turnover for {len(self.turnover)} instruments")

        print(f"{'=' * 70}\n")

        return True

    def _find_latest_file(self, pattern):
        """Find the most recent file matching pattern in analysis_dir"""
        import glob

        files = glob.glob(os.path.join(self.analysis_dir, pattern))
        if not files:
            raise FileNotFoundError(
                f"No files matching {pattern} in {self.analysis_dir}"
            )
        latest = max(files, key=os.path.getmtime)
        return latest

    # ========================================================================
    # PART 1: CATEGORIZE INSTRUMENTS BY COST TIER
    # ========================================================================

    def categorize_instruments_by_cost(self):
        """
        Group instruments into cost/liquidity tiers based on SR_cost.

        Returns:
            dict: {tier_name: [list of instruments]}
        """
        print(f"\n{'=' * 70}")
        print("CATEGORIZING INSTRUMENTS BY COST TIER")
        print(f"{'=' * 70}")

        # Define tier boundaries (based on Robert's patterns)
        tier_definitions = [
            ("Tier 1: Ultra Liquid", 0, 0.002),
            ("Tier 2: Liquid", 0.002, 0.005),
            ("Tier 3: Medium", 0.005, 0.010),
            ("Tier 4: Expensive", 0.010, 0.020),
            ("Tier 5: Very Expensive", 0.020, np.inf),
        ]

        tiers = {name: [] for name, _, _ in tier_definitions}

        for instrument in self.sr_costs.index:
            cost = self.sr_costs[instrument]

            # Find appropriate tier
            for tier_name, min_cost, max_cost in tier_definitions:
                if min_cost <= cost < max_cost:
                    tiers[tier_name].append(instrument)
                    break

        self.instrument_tiers = tiers

        # Print summary
        print(f"\nTier Distribution:")
        for tier_name, instruments in tiers.items():
            if instruments:
                min_cost = self.sr_costs[instruments].min()
                max_cost = self.sr_costs[instruments].max()
                avg_cost = self.sr_costs[instruments].mean()
                print(
                    f"  {tier_name:30s}: {len(instruments):3d} instruments "
                    f"(SR_cost: {min_cost:.6f} to {max_cost:.6f}, avg: {avg_cost:.6f})"
                )

        return tiers

    # ========================================================================
    # PART 2: IDENTIFY COMMON WEIGHT PATTERNS
    # ========================================================================

    def identify_weight_patterns(self, similarity_threshold=0.02):
        """
        Identify common weight patterns across instruments to create templates.

        Instruments with similar weights get grouped into same template.

        Args:
            similarity_threshold: Maximum difference to consider weights "same"

        Returns:
            dict: {pattern_id: {'weights': dict, 'instruments': list}}
        """
        print(f"\n{'=' * 70}")
        print("IDENTIFYING COMMON WEIGHT PATTERNS")
        print(f"Similarity threshold: {similarity_threshold}")
        print(f"{'=' * 70}")

        # Convert weights to DataFrame for easier comparison
        weights_df = pd.DataFrame(self.recommended_weights).T.fillna(0)

        # Cluster similar weight vectors
        patterns = {}
        pattern_id = 0
        assigned = set()

        for inst1 in weights_df.index:
            if inst1 in assigned:
                continue

            # Start new pattern
            pattern_id += 1
            pattern_instruments = [inst1]
            pattern_weights = weights_df.loc[inst1].copy()

            # Find similar instruments
            for inst2 in weights_df.index:
                if inst2 == inst1 or inst2 in assigned:
                    continue

                # Calculate difference
                diff = (weights_df.loc[inst2] - weights_df.loc[inst1]).abs().max()

                if diff < similarity_threshold:
                    pattern_instruments.append(inst2)
                    # Update pattern weights to average
                    pattern_weights = weights_df.loc[pattern_instruments].mean()

            # Store pattern
            patterns[pattern_id] = {
                "weights": pattern_weights.to_dict(),
                "instruments": pattern_instruments,
                "n_instruments": len(pattern_instruments),
                "n_active_rules": (pattern_weights > 0).sum(),
            }

            # Mark as assigned
            assigned.update(pattern_instruments)

            # Report
            print(
                f"Pattern {pattern_id:2d}: {len(pattern_instruments):3d} instruments, "
                f"{(pattern_weights > 0).sum():2d} active rules - "
                f"{pattern_instruments[:3]} {'...' if len(pattern_instruments) > 3 else ''}"
            )

        self.weight_templates = patterns

        # Create reverse mapping
        for pattern_id, info in patterns.items():
            for inst in info["instruments"]:
                self.template_assignments[inst] = pattern_id

        print(f"\n✓ Identified {len(patterns)} distinct weight patterns")
        print(
            f"  Instruments per pattern: {np.mean([p['n_instruments'] for p in patterns.values()]):.1f} average"
        )

        return patterns

    # ========================================================================
    # PART 3: GENERATE YAML CONFIGURATION
    # ========================================================================

    def generate_forecast_weights_yaml(
        self,
        output_file="results/static_forecast_weights.yaml",
        use_templates=True,
        include_comments=True,
    ):
        """
        Generate the forecast_weights YAML section.

        Args:
            output_file: Where to save YAML
            use_templates: If True, group similar instruments (cleaner)
            include_comments: Add explanatory comments

        Returns:
            dict: Complete forecast_weights configuration
        """
        print(f"\n{'=' * 70}")
        print("GENERATING FORECAST WEIGHTS YAML")
        print(f"Using templates: {use_templates}")
        print(f"{'=' * 70}")

        forecast_weights = {}

        if use_templates and self.weight_templates:
            # Group by pattern, then list instruments
            print("\nUsing template-based approach...")

            for pattern_id, pattern_info in sorted(self.weight_templates.items()):
                instruments = pattern_info["instruments"]
                weights = pattern_info["weights"]

                # Round weights to 3 decimals
                weights = {k: round(v, 3) for k, v in weights.items() if v > 0.0005}

                # Add all instruments with this pattern
                for inst in instruments:
                    forecast_weights[inst] = weights

                print(
                    f"  Pattern {pattern_id}: {len(instruments)} instruments with {len(weights)} active rules"
                )

        else:
            # Individual weights for each instrument
            print("\nUsing individual weights approach...")

            for inst, weights in self.recommended_weights.items():
                # Round and filter
                weights = {k: round(v, 3) for k, v in weights.items() if v > 0.0005}
                forecast_weights[inst] = weights

                if len(forecast_weights) % 20 == 0:
                    print(f"  Processed {len(forecast_weights)} instruments...")

        # Create full config structure
        config = {"forecast_weights": forecast_weights}

        # Save to file
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with open(output_file, "w") as f:
            if include_comments:
                f.write("# Static Forecast Weights Configuration\n")
                f.write(f"# Generated: {datetime.now()}\n")
                f.write(f"# From dynamic optimization analysis\n")
                f.write(f"#\n")
                f.write(f"# Statistics:\n")
                f.write(f"#   Instruments: {len(forecast_weights)}\n")
                if use_templates:
                    f.write(f"#   Weight patterns: {len(self.weight_templates)}\n")
                f.write(f"#   Generated by: create_static_config.py\n")
                f.write("\n")

            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        print(f"\n✓ Forecast weights YAML saved: {output_file}")
        print(f"  Total instruments: {len(forecast_weights)}")

        # Summary statistics
        rules_per_inst = [len(weights) for weights in forecast_weights.values()]
        print(f"\nSummary Statistics:")
        print(f"  Active rules per instrument:")
        print(f"    Mean: {np.mean(rules_per_inst):.1f}")
        print(f"    Median: {np.median(rules_per_inst):.0f}")
        print(f"    Min: {np.min(rules_per_inst)}")
        print(f"    Max: {np.max(rules_per_inst)}")

        return config

    # ========================================================================
    # PART 4: GENERATE COMPLETE CONFIG FILE
    # ========================================================================

    def generate_complete_config(
        self, base_config_file, output_file="results/static_system_config.yaml"
    ):
        """
        Generate a complete config file with static weights.

        Takes your existing dynamic config and converts it to static.

        Args:
            base_config_file: Your existing dynamic_backtest_config.yaml
            output_file: Where to save the new static config

        Returns:
            dict: Complete configuration
        """
        print(f"\n{'=' * 70}")
        print("GENERATING COMPLETE STATIC CONFIG")
        print(f"{'=' * 70}")

        # Load base config
        print(f"Loading base config: {base_config_file}")
        with open(base_config_file, "r") as f:
            config = yaml.safe_load(f)

        print(f"✓ Base config loaded")

        # Modify key settings
        print(f"\nModifying config for static weights...")

        # Turn OFF dynamic optimization
        config["use_forecast_weight_estimates"] = False
        config["use_forecast_div_mult_estimates"] = False  # Optional
        print("  ✓ use_forecast_weight_estimates = False")

        # Add static forecast weights
        forecast_weights = {}
        for inst, weights in self.recommended_weights.items():
            # Round and filter
            weights = {k: round(v, 3) for k, v in weights.items() if v > 0.0005}
            forecast_weights[inst] = weights

        config["forecast_weights"] = forecast_weights
        print(
            f"  ✓ Added static forecast_weights for {len(forecast_weights)} instruments"
        )

        # Save
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with open(output_file, "w") as f:
            f.write("# Static Trading System Configuration\n")
            f.write(f"# Generated: {datetime.now()}\n")
            f.write(f"# Converted from dynamic optimization\n")
            f.write("\n")
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        print(f"\n✓ Complete static config saved: {output_file}")

        return config

    # ========================================================================
    # PART 5: VALIDATION AND COMPARISON
    # ========================================================================

    def validate_static_weights(self):
        """
        Validate the generated static weights for common issues.
        """
        print(f"\n{'=' * 70}")
        print("VALIDATING STATIC WEIGHTS")
        print(f"{'=' * 70}")

        issues = []

        for inst, weights in self.recommended_weights.items():
            # Check 1: Total weight ≈ 1.0
            total = sum(weights.values())
            if abs(total - 1.0) > 0.01:
                issues.append(f"{inst}: Total weight = {total:.3f} (should be ≈ 1.0)")

            # Check 2: No negative weights
            if any(v < 0 for v in weights.values()):
                issues.append(f"{inst}: Contains negative weights")

            # Check 3: No single rule dominates (>50%)
            if weights and max(weights.values()) > 0.5:
                max_rule = max(weights, key=weights.get)
                issues.append(
                    f"{inst}: Rule {max_rule} has weight {weights[max_rule]:.3f} (>50%)"
                )

            # Check 4: At least one active rule
            active = sum(1 for v in weights.values() if v > 0)
            if active == 0:
                issues.append(f"{inst}: No active rules (all weights = 0)")

        if issues:
            print(f"\n⚠️  Found {len(issues)} validation issues:\n")
            for issue in issues[:20]:  # Show first 20
                print(f"  - {issue}")
            if len(issues) > 20:
                print(f"  ... and {len(issues) - 20} more")
        else:
            print("\n✅ All validation checks passed!")

        return issues

    def create_comparison_report(
        self,
        dynamic_system=None,
        static_system=None,
        output_file="results/dynamic_vs_static_comparison.txt",
    ):
        """
        Compare dynamic vs static system performance (if systems provided).

        Args:
            dynamic_system: System object with dynamic optimization
            static_system: System object with static weights
            output_file: Where to save comparison
        """
        print(f"\n{'=' * 70}")
        print("CREATING DYNAMIC VS STATIC COMPARISON")
        print(f"{'=' * 70}")

        if dynamic_system is None or static_system is None:
            print("⚠️  Systems not provided - skipping performance comparison")
            print("   (You can run this later after backtesting static config)")
            return

        # Extract performance metrics
        dynamic_portfolio = dynamic_system.accounts.portfolio()
        static_portfolio = static_system.accounts.portfolio()

        comparison = {
            "Dynamic Optimization": {
                "Sharpe Ratio": dynamic_portfolio.sharpe(),
                "Annual Return": dynamic_portfolio.percent.mean() * 256,
                "Annual Vol": dynamic_portfolio.percent.std() * np.sqrt(256),
                "Max Drawdown": dynamic_portfolio.percent.drawdown().min(),
            },
            "Static Weights": {
                "Sharpe Ratio": static_portfolio.sharpe(),
                "Annual Return": static_portfolio.percent.mean() * 256,
                "Annual Vol": static_portfolio.percent.std() * np.sqrt(256),
                "Max Drawdown": static_portfolio.percent.drawdown().min(),
            },
        }

        # Save report
        with open(output_file, "w") as f:
            f.write("DYNAMIC VS STATIC WEIGHTS COMPARISON\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"Generated: {datetime.now()}\n\n")

            for system_name, metrics in comparison.items():
                f.write(f"{system_name}:\n")
                for metric, value in metrics.items():
                    f.write(f"  {metric:20s}: {value:.3f}\n")
                f.write("\n")

            # Calculate degradation
            sr_diff = (
                comparison["Static Weights"]["Sharpe Ratio"]
                - comparison["Dynamic Optimization"]["Sharpe Ratio"]
            )
            sr_pct = (
                sr_diff / comparison["Dynamic Optimization"]["Sharpe Ratio"]
            ) * 100

            f.write("DEGRADATION ANALYSIS:\n")
            f.write(f"  Sharpe Ratio change: {sr_diff:.3f} ({sr_pct:.1f}%)\n")

            if abs(sr_pct) < 10:
                f.write("\n✅ ACCEPTABLE: Sharpe degradation < 10%\n")
            else:
                f.write("\n⚠️  WARNING: Significant performance degradation\n")

        print(f"✓ Comparison saved: {output_file}")

        return comparison

    # ========================================================================
    # PART 6: GENERATE DOCUMENTATION
    # ========================================================================

    def generate_documentation(
        self, output_file="results/static_weights_documentation.md"
    ):
        """
        Generate markdown documentation explaining the static weights.
        """
        print(f"\n{'=' * 70}")
        print("GENERATING DOCUMENTATION")
        print(f"{'=' * 70}")

        # FIX: Use UTF-8 encoding to handle special characters
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# Static Forecast Weights Documentation\n\n")
            f.write(f"**Generated:** {datetime.now()}\n\n")

            f.write("## Overview\n\n")
            f.write(
                f"This configuration contains static forecast weights for "
                f"{len(self.recommended_weights)} instruments, derived from "
                f"dynamic optimization analysis.\n\n"
            )

            f.write("## Cost Tier Distribution\n\n")
            f.write("Instruments are grouped by trading cost (SR_cost):\n\n")

            for tier_name, instruments in self.instrument_tiers.items():
                if instruments:
                    avg_cost = self.sr_costs[instruments].mean()
                    f.write(
                        f"- **{tier_name}**: {len(instruments)} instruments "
                        f"(avg SR_cost: {avg_cost:.6f})\n"
                    )

            f.write("\n## Weight Patterns\n\n")

            if self.weight_templates:
                f.write(
                    f"Identified {len(self.weight_templates)} distinct weight patterns "
                    f"to reduce configuration duplication:\n\n"
                )

                for pattern_id, info in sorted(self.weight_templates.items()):
                    f.write(f"### Pattern {pattern_id}\n\n")
                    f.write(f"- **Instruments:** {len(info['instruments'])}\n")
                    f.write(f"- **Active rules:** {info['n_active_rules']}\n")
                    f.write(
                        f"- **Example instruments:** {', '.join(info['instruments'][:5])}\n"
                    )
                    f.write("\n")

            f.write("## Usage\n\n")
            f.write("To use these static weights:\n\n")
            f.write("1. Copy the `forecast_weights` section to your config\n")
            f.write("2. Set `use_forecast_weight_estimates: False`\n")
            f.write("3. Run backtest to validate performance\n")
            f.write("4. Review annually and update if needed\n")

            f.write("\n## Methodology\n\n")
            f.write("These weights were generated using:\n\n")
            f.write(
                "- Cost threshold: 0.13 SR (rules exceeding this were eliminated)\n"
            )
            f.write(
                "- Time aggregation: Average of last 2 years of dynamic optimization\n"
            )
            f.write("- Rounding: 0.001 precision\n")
            f.write(
                "- Normalization: Total weight per instrument approximately 1.0\n"
            )  # ← Changed

        print(f"✓ Documentation saved: {output_file}")

    # ========================================================================
    # MAIN WORKFLOW
    # ========================================================================

    def run_full_generation(
        self, base_config_file, use_templates=True, generate_docs=True
    ):
        """
        Run complete static config generation workflow.

        Args:
            base_config_file: Your dynamic_backtest_config.yaml
            use_templates: Group similar instruments (recommended)
            generate_docs: Create documentation

        Returns:
            dict: Complete static configuration
        """
        print(f"\n{'=' * 90}")
        print("RUNNING FULL STATIC CONFIG GENERATION")
        print(f"{'=' * 90}\n")

        # Step 1: Load analysis
        self.load_analysis_results()

        # Step 2: Categorize by cost
        self.categorize_instruments_by_cost()

        # Step 3: Identify patterns
        if use_templates:
            self.identify_weight_patterns()

        # Step 4: Generate YAML
        self.generate_forecast_weights_yaml(use_templates=use_templates)

        # Step 5: Generate complete config
        config = self.generate_complete_config(base_config_file)

        # Step 6: Validate
        self.validate_static_weights()

        # Step 7: Documentation
        if generate_docs:
            self.generate_documentation()

        print(f"\n{'=' * 90}")
        print("✅ STATIC CONFIG GENERATION COMPLETE")
        print(f"{'=' * 90}\n")
        print("Generated files:")
        print("  - results/static_forecast_weights.yaml (just weights)")
        print("  - results/static_system_config.yaml (complete config)")
        print("  - results/static_weights_documentation.md (documentation)")
        print("\nNext steps:")
        print("  1. Review the generated config files")
        print("  2. Run backtest with static config to validate")
        print("  3. Compare performance vs dynamic optimization")

        return config


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================


def main():
    """Command line interface with sensible defaults"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate static forecast weights configuration"
    )

    parser.add_argument(
        "--base-config",
        type=str,
        default=DEFAULT_CONFIG["base_config"],  # ← Use default
        help=f"Path to dynamic config (default: {DEFAULT_CONFIG['base_config']})",
    )

    parser.add_argument(
        "--analysis-dir",
        type=str,
        default=DEFAULT_CONFIG["analysis_dir"],
        help=f"Analysis directory (default: {DEFAULT_CONFIG['analysis_dir']})",
    )

    parser.add_argument(
        "--no-templates",
        action="store_true",
        default=not DEFAULT_CONFIG["use_templates"],
        help="Do not group similar instruments",
    )

    parser.add_argument(
        "--no-docs",
        action="store_true",
        default=not DEFAULT_CONFIG["generate_docs"],
        help="Skip documentation",
    )

    args = parser.parse_args()

    # Create generator
    print(f"\n{'=' * 90}")
    print("STATIC CONFIG GENERATION - FORECAST WEIGHTS")
    print(f"{'=' * 90}\n")

    generator = StaticConfigGenerator(analysis_dir=args.analysis_dir)

    # Run generation
    generator.run_full_generation(
        base_config_file=args.base_config,
        use_templates=not args.no_templates,
        generate_docs=not args.no_docs,
    )


if __name__ == "__main__":
    main()
