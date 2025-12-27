"""
extract_static_forecast_scalars.py

Extract forecast scalars from a completed dynamic backtest and convert them
to static scalars (per instrument, per rule) suitable for freezing in config.

Workflow:
1. Load or rebuild the dynamic system (with use_forecast_scale_estimates: True)
2. For each (instrument, rule), pull the scalar time series from forecastScaleCap
3. Compute a stable static scalar as 2-year mean (or configurable)
4. Save:
   - CSVs for inspection
   - A YAML fragment you can paste into your system config

Author: Systematic Trading Implementation
Date: December 2025
"""

import os
import sys
import pickle
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

warnings.filterwarnings("ignore")

# Add project directory to path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_dir)

# Import Rob's system factory
from systems.provided.rob_system.run_system import futures_system
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData

# ============================================================================
# DEFAULT CONFIGURATION
# ============================================================================
# Set these defaults so you can run directly from PyCharm without command line args
DEFAULT_CONFIG = {
    "pickle_path": "results/pickles/system_20251227_180759.pkl",  # Path to your pickled system (FAST - recommended)
    "config_path": None,  # 'dynamic_backtest_config.yaml',  # Alternative: rebuild from config (SLOW - only if pickle unavailable)
    "lookback_days": 504,  # Lookback for scalar averaging (2 years = 504 business days)
    "method": "mean",  # Averaging method: 'mean', 'median', or 'last'
    "pool_across_instruments": True,  # Robert Carver's recommendation: same scalar per rule across all instruments
    "output_dir": "results/static_scalar_analysis",  # Where to save analysis files
}


class StaticForecastScalarExtractor:
    """
    Extract and convert dynamic forecast scalars into static scalars.

    Usage pattern is deliberately similar to ForecastWeightExtractor.
    """

    def __init__(
        self,
        system=None,
        system_pickle_path=None,
        config_path=None,
        output_dir="results/static_scalar_analysis",
    ):
        """
        Args:
            system:       Pre-built system object (optional)
            system_pickle_path: Path to pickled system (fast)
            config_path:  Path to dynamic config YAML (will rebuild system)
            output_dir:   Where to write analysis files
        """
        self.system = None
        self.instruments = []
        self.rules = []

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Data containers
        self.scalar_timeseries = {}  # {(inst, rule): Series}
        self.static_scalars = {}  # {inst: {rule: scalar}}

        # Load or create system
        if system is not None:
            self.system = system
            print("✓ Using provided system object")

        elif system_pickle_path and os.path.exists(system_pickle_path):
            self._load_system_from_pickle(system_pickle_path)

        elif config_path:
            self._rebuild_system(config_path)

        else:
            raise ValueError("Must provide system, system_pickle_path, or config_path")

        # Extract universe
        self.instruments = self.system.get_instrument_list()
        self.rules = list(self.system.rules.trading_rules().keys())
        print(
            f"✓ System loaded: {len(self.instruments)} instruments, {len(self.rules)} rules"
        )

    # ------------------------------------------------------------------
    # System loading helpers
    # ------------------------------------------------------------------

    def _load_system_from_pickle(self, pickle_path: str):
        print(f"Loading system from pickle: {pickle_path}")
        try:
            with open(pickle_path, "rb") as f:
                self.system = pickle.load(f)
            print("✓ System loaded from pickle")
        except Exception as e:
            print(f"❌ Error loading pickle: {e}")
            raise

    def _rebuild_system(self, config_path: str):
        print(f"Rebuilding system from config: {config_path}")
        print("⚠️  This will take as long as running the backtest!")
        try:
            data = csvFuturesSimData()
            self.system = futures_system(sim_data=data, config_filename=config_path)
            print("✓ System rebuilt from config")
        except Exception as e:
            print(f"❌ Error rebuilding system: {e}")
            raise

    # ------------------------------------------------------------------
    # Step 1: Extract scalar time series
    # ------------------------------------------------------------------

    def extract_scalar_timeseries(self, lookback_days: int = 504):
        """
        Extract time series of forecast scalars for each (instrument, rule).

        Works with both ForecastScaleCap and volAttenForecastScaleCap stages.
        """
        print(f"\n{'=' * 70}")
        print(f"EXTRACTING FORECAST SCALAR TIME SERIES (last {lookback_days} days)")
        print(f"{'=' * 70}")

        # Detect which type of forecastScaleCap we have
        stage = self.system.forecastScaleCap
        stage_type = type(stage).__name__
        print(f"\nForecastScaleCap stage type: {stage_type}")

        n_ok = 0
        n_err = 0
        errors_seen = {}

        for i, inst in enumerate(self.instruments, 1):
            print(f"[{i}/{len(self.instruments)}] {inst:15s}", end=" ")
            inst_success = 0

            for rule in self.rules:
                key = (inst, rule)

                try:
                    # Try multiple methods depending on stage type
                    ts = None

                    # Method 1: Direct method (standard ForecastScaleCap)
                    if hasattr(stage, "get_forecast_scalar"):
                        ts = stage.get_forecast_scalar(inst, rule)

                    # Method 2: For volAttenForecastScaleCap - get from capped forecast
                    elif hasattr(stage, "get_capped_forecast"):
                        # Get the capped forecast and extract scalar from it
                        # The scalar is stored in the forecast calculation
                        raw_forecast = self.system.rules.get_raw_forecast(inst, rule)
                        capped_forecast = stage.get_capped_forecast(inst, rule)

                        # Scalar = capped / raw (where both are non-zero)
                        # But this won't give us the scalar time series directly
                        # We need to access the _get_forecast_scalar method
                        if hasattr(stage, "_get_forecast_scalar"):
                            ts = stage._get_forecast_scalar(inst, rule)
                        else:
                            # Last resort: try to access cached data
                            cache_ref = f"get_forecast_scalar.{inst}.{rule}"
                            if hasattr(stage, "cache") and cache_ref in stage.cache:
                                ts = stage.cache[cache_ref]

                    # Method 3: Access via parent system methods
                    if ts is None:
                        # Try getting it from the combForecast stage which uses scalars
                        if hasattr(
                            self.system.combForecast, "get_forecast_scalar_estimated"
                        ):
                            ts = self.system.combForecast.get_forecast_scalar_estimated(
                                inst, rule
                            )

                    if ts is not None and len(ts) > 0:
                        # Restrict to recent history
                        if len(ts) > lookback_days:
                            ts = ts.iloc[-lookback_days:]

                        self.scalar_timeseries[key] = ts
                        n_ok += 1
                        inst_success += 1
                    else:
                        n_err += 1

                except Exception as e:
                    n_err += 1
                    error_type = type(e).__name__

                    if error_type not in errors_seen:
                        errors_seen[error_type] = {
                            "message": str(e),
                            "example": (inst, rule),
                            "count": 1,
                        }
                    else:
                        errors_seen[error_type]["count"] += 1

            status = f"→ {inst_success}/{len(self.rules)} rules extracted"
            print(status)

        print(
            f"\n✓ Time series extracted for {n_ok} (instrument, rule) pairs "
            f"({n_err} missing)"
        )

        if errors_seen:
            print(f"\n{'=' * 70}")
            print("⚠️  ERRORS ENCOUNTERED:")
            print(f"{'=' * 70}")
            for error_type, info in errors_seen.items():
                print(f"\n{error_type} ({info['count']} occurrences):")
                print(f"  Message: {info['message']}")
                print(f"  Example: {info['example'][0]} / {info['example'][1]}")
            print(f"\n{'=' * 70}")

        return self.scalar_timeseries

    # ------------------------------------------------------------------
    # Step 2: Compute static scalars from time series
    # ------------------------------------------------------------------

    def compute_static_scalars(
        self,
        method: str = "mean",
        lookback_days: int = 504,
        # round_to: float = 0.001,
        pool_across_instruments: bool = True,  # NEW PARAMETER
    ):
        """
        Compute static scalars from scalar time series.

        Args:
            method: 'mean' (recommended), 'median', or 'last'
            lookback_days: Ensure consistency with extract_scalar_timeseries
            round_to: e.g., 0.01 for 2 decimal places
            pool_across_instruments: If True, use same scalar for each rule across
                                    all instruments (Robert Carver's recommendation)

        Returns:
            dict: {instrument: {rule: scalar}}
        """

        print(f"\n{'=' * 70}")
        print(f"COMPUTING STATIC FORECAST SCALARS")
        print(f"Method: {method}, lookback_days: {lookback_days}")
        print(f"Pooling across instruments: {pool_across_instruments}")
        print(f"{'=' * 70}")

        if not self.scalar_timeseries:
            self.extract_scalar_timeseries(lookback_days=lookback_days)

        # dec = int(-np.log10(round_to))

        if pool_across_instruments:
            # CARVER'S RECOMMENDED APPROACH: One scalar per rule
            print("\n✓ Using POOLED scalars (Robert Carver's recommendation)")
            print("  → Same scalar for each rule across all instruments")

            pooled_scalars_by_rule = {}

            for rule in self.rules:
                all_values_for_rule = []

                for inst in self.instruments:
                    key = (inst, rule)
                    ts = self.scalar_timeseries.get(key, None)

                    if ts is not None and len(ts) > 0:
                        all_values_for_rule.append(ts)

                if len(all_values_for_rule) == 0:
                    pooled_scalars_by_rule[rule] = 1.0
                    continue

                # Carver's method: Cross-sectional median, then time average
                combined_df = pd.DataFrame(
                    {f"inst_{i}": ts for i, ts in enumerate(all_values_for_rule)}
                )

                daily_median = combined_df.median(axis=1)

                if method == "last":
                    # Use last value (already computed with expanding window)
                    pooled_value = daily_median.iloc[-1]
                elif method == "mean":
                    # Mean over ENTIRE history (not just last 504 days)
                    pooled_value = daily_median.mean()
                elif method == "median":
                    pooled_value = daily_median.median()
                else:
                    raise ValueError(f"Unknown method: {method}")

                # pooled_scalars_by_rule[rule] = round(float(pooled_value), dec)
                pooled_scalars_by_rule[rule] = float(pooled_value)

            # Apply pooled scalar to all instruments
            for inst in self.instruments:
                self.static_scalars[inst] = {}
                for rule in self.rules:
                    self.static_scalars[inst][rule] = pooled_scalars_by_rule[rule]

            print(f"\n✓ Pooled scalars by rule:")
            for rule, scalar in pooled_scalars_by_rule.items():
                # print(f"   {rule:20s}: {scalar:.3f}")
                print(f"  {rule:20s}: {scalar}")

        else:
            # INSTRUMENT-SPECIFIC (NOT Carver's recommendation)
            print("\n⚠️  Using INSTRUMENT-SPECIFIC scalars")
            print("   (Not Robert Carver's recommendation)")

            for inst in self.instruments:
                self.static_scalars[inst] = {}
                for rule in self.rules:
                    key = (inst, rule)
                    ts = self.scalar_timeseries.get(key, None)

                    if ts is None or len(ts) == 0:
                        self.static_scalars[inst][rule] = 1.0
                        continue

                    if method == "mean":
                        val = ts.mean()
                    elif method == "median":
                        val = ts.median()
                    elif method == "last":
                        val = ts.iloc[-1]
                    else:
                        raise ValueError(f"Unknown method: {method}")

                    # self.static_scalars[inst][rule] = round(float(val), dec)
                    self.static_scalars[inst][rule] = float(val)

        all_vals = [v for d in self.static_scalars.values() for v in d.values()]
        print(f"\n✓ Static scalars computed for {len(self.instruments)} instruments")
        print(f"  Mean: {np.mean(all_vals):.2f}, Median: {np.median(all_vals):.2f}")
        print(f"  Range: {np.min(all_vals):.2f} to {np.max(all_vals):.2f}")

        if pool_across_instruments:
            print(f"\n  → All instruments share the same scalar per rule ✓")

        return self.static_scalars

    # ------------------------------------------------------------------
    # Step 3: Save analysis outputs
    # ------------------------------------------------------------------

    def save_analysis(self):
        """
        Save scalar time series and static scalars to CSVs for inspection.
        """
        ts_out = (
            self.output_dir / f"scalar_timeseries_{datetime.now():%Y%m%d_%H%M%S}.csv"
        )
        st_out = self.output_dir / f"static_scalars_{datetime.now():%Y%m%d_%H%M%S}.csv"

        # Flatten time series into wide format (optional)
        # Here we only save static scalars in a simple table
        if self.static_scalars:
            df_static = pd.DataFrame(self.static_scalars).T
            df_static.to_csv(st_out)
            print(f"✓ Static scalars saved: {st_out}")

        return

    # ------------------------------------------------------------------
    # Step 4: Generate YAML fragment for config
    # ------------------------------------------------------------------

    def generate_yaml_fragment(self, yaml_path="results/static_forecast_scalars.yaml"):
        """
        Generate a YAML file with forecast_scalars you can copy into your main config.

        Args:
            yaml_path: Output YAML path

        Returns:
            dict: {'forecast_scalars': {inst: {rule: scalar}}}
        """
        print(f"\n{'='*70}")
        print("GENERATING YAML FRAGMENT FOR CONFIG")
        print(f"{'='*70}")

        if not self.static_scalars:
            self.compute_static_scalars()

        cfg = {"forecast_scalars": self.static_scalars}

        yaml_path = Path(yaml_path)
        yaml_path.parent.mkdir(parents=True, exist_ok=True)

        with yaml_path.open("w") as f:
            f.write("# Static forecast scalars\n")
            f.write(f"# Generated: {datetime.now()}\n")
            f.write("# Paste 'forecast_scalars' under your main config root\n\n")
            yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)

        print(f"✓ YAML fragment written: {yaml_path}")
        return cfg

    # ------------------------------------------------------------------
    # High-level runner
    # ------------------------------------------------------------------

    def run_full_extraction(
        self,
        lookback_days: int = 504,
        method: str = "last",
        # round_to: float = 0.001,
        pool_across_instruments: bool = True,  # NEW
    ):
        """
        Full workflow:
        1. Extract scalar time series
        2. Compute static scalars (pooled or instrument-specific)
        3. Save CSVs
        4. Generate YAML fragment
        """

        print(f"\n{'=' * 90}")
        print("RUNNING STATIC FORECAST SCALAR EXTRACTION")
        print(f"Pooling: {pool_across_instruments} (Carver's rec: True)")
        print(f"{'=' * 90}\n")

        self.extract_scalar_timeseries(lookback_days=lookback_days)

        self.compute_static_scalars(
            method=method,
            lookback_days=lookback_days,
            # round_to=round_to,
            pool_across_instruments=pool_across_instruments,  # Pass through
        )

        self.save_analysis()
        self.generate_yaml_fragment()

        print(f"\n{'=' * 90}")
        print("✅ STATIC FORECAST SCALAR EXTRACTION COMPLETE")
        print(f"{'=' * 90}\n")


# ----------------------------------------------------------------------------
# CLI Entrypoint
# ----------------------------------------------------------------------------


def main():
    """
    Command line interface with DEFAULT_CONFIG fallback.

    Examples:
        # Using defaults from DEFAULT_CONFIG (easiest - just run in PyCharm)
        python extract_static_forecast_scalars.py

        # Override with command line args
        python extract_static_forecast_scalars.py --pickle results/system.pkl
        python extract_static_forecast_scalars.py --config dynamic_backtest_config.yaml
        python extract_static_forecast_scalars.py --pickle system.pkl --lookback 756
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract static forecast scalars from dynamic backtest"
    )

    # Make all arguments optional with defaults from DEFAULT_CONFIG
    parser.add_argument(
        "--pickle",
        type=str,
        default=DEFAULT_CONFIG["pickle_path"],
        help=f"Path to pickled system (default: {DEFAULT_CONFIG['pickle_path']})",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=DEFAULT_CONFIG["config_path"],
        help="Path to dynamic config YAML (alternative to pickle - SLOW)",
    )
    parser.add_argument(
        "--lookback",
        type=int,
        default=DEFAULT_CONFIG["lookback_days"],
        help=f"Lookback days for scalar averaging (default: {DEFAULT_CONFIG['lookback_days']} = 2 years)",
    )
    parser.add_argument(
        "--method",
        type=str,
        default=DEFAULT_CONFIG["method"],
        choices=["mean", "median", "last"],
        help=f"Averaging method (default: {DEFAULT_CONFIG['method']})",
    )
    parser.add_argument(
        "--no-pool",
        action="store_true",
        default=not DEFAULT_CONFIG["pool_across_instruments"],
        help="Use instrument-specific scalars instead of pooled (NOT Robert Carver's recommendation)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=DEFAULT_CONFIG["output_dir"],
        help=f"Directory to save analysis outputs (default: {DEFAULT_CONFIG['output_dir']})",
    )

    args = parser.parse_args()

    # Validate: need either pickle or config
    if not args.pickle and not args.config:
        parser.error("Must provide either --pickle or --config, or set DEFAULT_CONFIG")

    # Create extractor
    print("=" * 90)
    print("FORECAST SCALAR EXTRACTION - STATIC CONFIGURATION")
    print("=" * 90)

    if args.pickle:
        print(f"Loading from pickle: {args.pickle}")
        extractor = StaticForecastScalarExtractor(
            system_pickle_path=args.pickle, output_dir=args.output_dir
        )
    else:
        print(f"Rebuilding from config: {args.config}")
        print("⚠️  This will take as long as running the backtest!")
        extractor = StaticForecastScalarExtractor(
            config_path=args.config, output_dir=args.output_dir
        )

    # Run full extraction
    pool_across_instruments = not args.no_pool

    extractor.run_full_extraction(
        lookback_days=args.lookback,
        method=args.method,
        pool_across_instruments=pool_across_instruments,
    )

    print("=" * 90)
    print("EXTRACTION COMPLETE")
    print("=" * 90)
    print("Next steps:")
    print("  1. Review the generated YAML: results/static_forecast_scalars.yaml")
    print("  2. Copy forecast_scalars section into your config")
    print("  3. Set use_forecast_scale_estimates: False")
    print("  4. Re-run your backtest with static scalars")
    print("  5. THEN extract static forecast weights")


if __name__ == "__main__":
    main()
