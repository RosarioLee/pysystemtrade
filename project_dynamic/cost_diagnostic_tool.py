#!/usr/bin/env python3
"""
TIMELINE COST DIAGNOSTIC - Multi-Period Analysis
Checks costs across multiple dates to show what changed and when
"""
import sys, os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
import pandas as pd
import yaml
from collections import defaultdict
import numpy as np

print("=" * 80)
print("TIMELINE COST DIAGNOSTIC - Multi-Period Analysis")
print("=" * 80)

# ==============================================================================
# LOAD YOUR CONFIG
# ==============================================================================
config_path = "dynamic_backtest_config.yaml"

try:
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    print(f"\n✅ Loaded config: {config_path}")
except Exception as e:
    print(f"\n❌ Could not load config: {e}")
    sys.exit(1)

# Extract instrument list
if "instruments" in config and config["instruments"]:
    my_instruments = config["instruments"]
    print(f"✅ Found {len(my_instruments)} instruments in YOUR config")
else:
    print("❌ No instruments found in config!")
    sys.exit(1)

# Config settings
use_sr_costs = config.get("use_SR_costs", False)
shadow_cost = config.get("small_system", {}).get("shadow_cost", 50)
start_date = pd.Timestamp(config.get("start_date", "2000-01-01"))

print(f"\nConfig Settings:")
print(f"  use_SR_costs: {use_sr_costs}")
print(f"  shadow_cost: {shadow_cost}")
print(f"  start_date: {start_date}")

# ==============================================================================
# DEFINE CHECK DATES
# ==============================================================================
check_dates = [
    ("Backtest Start", start_date),
    ("1 Month Before Problem", pd.Timestamp("2005-04-23")),
    ("1 Week Before Problem", pd.Timestamp("2005-05-16")),
    ("3 Days Before Problem", pd.Timestamp("2005-05-20")),
    ("PROBLEM DATE", pd.Timestamp("2005-05-23")),
    ("1 Day After Problem", pd.Timestamp("2005-05-24")),
    ("1 Week After Problem", pd.Timestamp("2005-05-30")),
    ("1 Month After Problem", pd.Timestamp("2005-06-23")),
]

print(f"\n📅 Will check costs at {len(check_dates)} different dates")

# ==============================================================================
# LOAD DATA
# ==============================================================================
data = csvFuturesSimData()
print(f"✅ Data source initialized")

# Validate instruments
available_instruments = []
for inst in my_instruments:
    try:
        prices = data.daily_prices(inst)
        if len(prices) > 0:
            available_instruments.append(inst)
    except:
        pass

print(f"✅ {len(available_instruments)} instruments valid")


# ==============================================================================
# HELPER FUNCTION: Analyze costs at a single date
# ==============================================================================
def analyze_costs_at_date(instruments, date, data):
    """Analyze cost quality for all instruments at a specific date"""
    results = {
        "date": date,
        "active": 0,
        "valid": 0,
        "invalid_price": [],
        "zero_cost": [],
        "negative_price_ok": [],
        "all_ok": [],
    }

    for inst in instruments:
        try:
            prices = data.daily_prices(inst)

            # Check if instrument has data at this date
            if date not in prices.index:
                continue

            results["active"] += 1

            price = prices.loc[date]
            cost_obj = data.get_raw_cost_data(inst)

            slippage = cost_obj.price_slippage
            block = cost_obj.value_of_block_commission
            sr_cash = slippage + block

            # Categorize
            if pd.isna(price) or price == 0:
                results["invalid_price"].append(
                    {
                        "instrument": inst,
                        "price": price,
                        "slippage": slippage,
                        "block": block,
                    }
                )
            elif sr_cash == 0 or np.isnan(sr_cash):
                results["zero_cost"].append(
                    {
                        "instrument": inst,
                        "price": price,
                        "slippage": slippage,
                        "block": block,
                    }
                )
            elif price < 0:
                # Negative price but calculable cost (Panama backadjustment)
                sr_pct = sr_cash / abs(price)
                results["negative_price_ok"].append(
                    {"instrument": inst, "price": price, "sr_cost": sr_pct}
                )
                results["valid"] += 1
            else:
                # Normal valid instrument
                results["all_ok"].append(inst)
                results["valid"] += 1

        except Exception:
            continue

    return results


# ==============================================================================
# PHASE 1: ANALYZE EACH DATE
# ==============================================================================
print(f"\n{'=' * 80}")
print("PHASE 1: COST QUALITY ACROSS TIME")
print("=" * 80)

timeline_results = []

for label, date in check_dates:
    print(f"\n{label}: {date}")
    print("-" * 80)

    results = analyze_costs_at_date(available_instruments, date, data)
    timeline_results.append((label, date, results))

    # Print summary
    print(f"  Active instruments:     {results['active']}")
    print(f"  ✅ Valid costs:         {results['valid']}")
    print(f"  ❌ Invalid price (NaN): {len(results['invalid_price'])}")
    print(f"  ❌ Zero costs:          {len(results['zero_cost'])}")
    print(
        f"  ⚠️  Negative prices:    {len(results['negative_price_ok'])} (OK with abs)"
    )

    # Show problem instruments if any
    if results["invalid_price"]:
        print(f"\n  🔴 Invalid Price Instruments:")
        for item in results["invalid_price"]:
            print(f"     - {item['instrument']}: price={item['price']}")

    if results["zero_cost"]:
        print(f"\n  🔴 Zero Cost Instruments:")
        for item in results["zero_cost"]:
            print(
                f"     - {item['instrument']}: slippage=${item['slippage']:.4f}, block=${item['block']:.2f}"
            )

# ==============================================================================
# PHASE 2: IDENTIFY WHAT CHANGED
# ==============================================================================
print(f"\n{'=' * 80}")
print("PHASE 2: WHAT CHANGED OVER TIME?")
print("=" * 80)

# Find the problem date index
problem_idx = next(
    i for i, (label, _, _) in enumerate(timeline_results) if label == "PROBLEM DATE"
)

# Get before/after
if problem_idx > 0:
    before_label, before_date, before_results = timeline_results[problem_idx - 1]
    problem_label, problem_date, problem_results = timeline_results[problem_idx]

    print(f"\n📊 Comparing: {before_label} vs {problem_label}")
    print("-" * 80)

    # What changed in active instruments?
    before_active = before_results["active"]
    problem_active = problem_results["active"]

    print(f"\nActive Instruments:")
    print(f"  Before ({before_date}): {before_active}")
    print(f"  Problem ({problem_date}): {problem_active}")
    print(f"  Change: {problem_active - before_active:+d}")

    # What changed in problems?
    before_problems = set(
        [x["instrument"] for x in before_results["invalid_price"]]
        + [x["instrument"] for x in before_results["zero_cost"]]
    )
    problem_problems = set(
        [x["instrument"] for x in problem_results["invalid_price"]]
        + [x["instrument"] for x in problem_results["zero_cost"]]
    )

    new_problems = problem_problems - before_problems
    fixed_problems = before_problems - problem_problems
    persistent_problems = before_problems & problem_problems

    print(f"\nProblem Instruments:")
    print(f"  Before: {len(before_problems)}")
    print(f"  Problem Date: {len(problem_problems)}")

    if new_problems:
        print(f"\n  🆕 NEW problems on {problem_date}:")
        for inst in new_problems:
            print(f"     - {inst}")

    if fixed_problems:
        print(f"\n  ✅ FIXED since {before_date}:")
        for inst in fixed_problems:
            print(f"     - {inst}")

    if persistent_problems:
        print(f"\n  ⚠️  PERSISTENT problems:")
        for inst in persistent_problems:
            print(f"     - {inst}")

# ==============================================================================
# PHASE 3: DETAILED CANOLA TIMELINE
# ==============================================================================
print(f"\n{'=' * 80}")
print("PHASE 3: CANOLA PRICE TIMELINE (Suspected Culprit)")
print("=" * 80)

canola_timeline = []

for label, date, _ in timeline_results:
    try:
        prices = data.daily_prices("CANOLA")
        if date in prices.index:
            price = prices.loc[date]
            cost_obj = data.get_raw_cost_data("CANOLA")
            sr_cash = cost_obj.price_slippage + cost_obj.value_of_block_commission

            canola_timeline.append(
                {
                    "date": date,
                    "label": label,
                    "price": price,
                    "has_price": not pd.isna(price),
                    "sr_cost": sr_cash / abs(price)
                    if not pd.isna(price) and price != 0
                    else 0,
                }
            )
    except:
        canola_timeline.append(
            {
                "date": date,
                "label": label,
                "price": None,
                "has_price": False,
                "sr_cost": 0,
            }
        )

print(
    f"\n{'Date':<12} {'Label':<25} {'Price':<15} {'Has Valid Price?':<20} {'SR Cost %'}"
)
print("-" * 90)

for item in canola_timeline:
    date_str = str(item["date"])[:10]
    price_str = (
        f"${item['price']:.2f}"
        if item["price"] is not None and not pd.isna(item["price"])
        else "NaN/Missing"
    )
    valid_str = "✅ YES" if item["has_price"] else "❌ NO"
    cost_str = f"{item['sr_cost'] * 100:.4f}%" if item["sr_cost"] > 0 else "N/A"

    print(
        f"{date_str:<12} {item['label']:<25} {price_str:<15} {valid_str:<20} {cost_str}"
    )

# ==============================================================================
# PHASE 4: SUMMARY & RECOMMENDATION
# ==============================================================================
print(f"\n{'=' * 80}")
print("PHASE 4: SUMMARY & RECOMMENDATION")
print("=" * 80)

# Find all problem instruments across all dates
all_problem_instruments = set()
for label, date, results in timeline_results:
    problems = [x["instrument"] for x in results["invalid_price"]] + [
        x["instrument"] for x in results["zero_cost"]
    ]
    all_problem_instruments.update(problems)

print(f"\n📊 Instruments with cost problems at ANY point in timeline:")
print(f"   Total: {len(all_problem_instruments)}")

if all_problem_instruments:
    print(f"\n   List:")
    for inst in sorted(all_problem_instruments):
        # Count how many dates had problems
        problem_count = 0
        for label, date, results in timeline_results:
            problems = [x["instrument"] for x in results["invalid_price"]] + [
                x["instrument"] for x in results["zero_cost"]
            ]
            if inst in problems:
                problem_count += 1

        print(
            f"     - {inst:<15} (problems at {problem_count}/{len(check_dates)} dates)"
        )

print(f"\n{'=' * 80}")
print("RECOMMENDED FIX")
print("=" * 80)

print(f"\nAdd to {config_path}:")
print(f"\nignore_instruments:")
for inst in sorted(all_problem_instruments):
    print(f"  - '{inst}'")

remaining = len(available_instruments) - len(all_problem_instruments)
print(f"\n📊 After exclusion:")
print(f"  Original: {len(available_instruments)} instruments")
print(f"  Excluded: {len(all_problem_instruments)} instruments")
print(f"  Remaining: {remaining} instruments")

if remaining >= 20:
    print(f"  ✅ {remaining} instruments = Excellent diversification!")
elif remaining >= 10:
    print(f"  ✅ {remaining} instruments = Good diversification")
else:
    print(f"  ⚠️  {remaining} instruments = Consider fixing cost data instead")

print(f"\n{'=' * 80}")
print("DIAGNOSTIC COMPLETE")
print("=" * 80)
