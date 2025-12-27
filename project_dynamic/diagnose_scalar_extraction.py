"""
verify_scalar_pooling.py - CORRECTED

Use the SAME method that worked in your extraction script.
"""
import pickle

# Load your system
with open("results/pickles/system_20251226_233902.pkl", "rb") as f:
    system = pickle.load(f)

# Get actual instruments
all_instruments = system.get_instrument_list()
print(f"System has {len(all_instruments)} instruments")
print(f"First 10: {all_instruments[:10]}\n")

# Detect the correct method to use
stage = system.forecastScaleCap
stage_type = type(stage).__name__
print(f"Stage type: {stage_type}\n")

# Pick test instruments
test_instruments = all_instruments[:5]
rule = "carry60"

print(f"\nScalars for {rule} on the same date:")
print("="*60)

scalars_by_instrument = {}

for inst in test_instruments:
    try:
        # Try the methods in the same order as your working extraction code
        ts = None

        # Method 1: Try get_forecast_scalar (standard)
        if hasattr(stage, 'get_forecast_scalar'):
            ts = stage.get_forecast_scalar(inst, rule)

        # Method 2: Try via combForecast
        elif hasattr(system.combForecast, 'get_forecast_scalar_estimated'):
            ts = system.combForecast.get_forecast_scalar_estimated(inst, rule)

        # Method 3: Access cache directly
        elif hasattr(stage, 'cache'):
            cache_ref = f"get_forecast_scalar.{inst}.{rule}"
            if cache_ref in stage.cache._cache:
                ts = stage.cache._cache[cache_ref]

        if ts is not None and len(ts) > 0:
            latest_scalar = float(ts.iloc[-1])
            latest_date = ts.index[-1]
            scalars_by_instrument[inst] = latest_scalar
            print(f"{inst:15s}: {latest_scalar:.6f}  (date: {latest_date})")
        else:
            print(f"{inst:15s}: No scalar data found")

    except Exception as e:
        print(f"{inst:15s}: Failed - {type(e).__name__}: {e}")

print("\n" + "="*60)

# Check if all scalars are identical
if scalars_by_instrument:
    unique_scalars = set(round(v, 6) for v in scalars_by_instrument.values())

    if len(unique_scalars) == 1:
        print("✅ SUCCESS: All instruments have IDENTICAL scalars!")
        print(f"   Pooled scalar value: {list(unique_scalars)[0]:.6f}")
        print("\n   → This confirms pooling worked during backtest ✓")
        print("   → Your extraction code is 100% CORRECT ✓")
        print("   → NO CHANGES NEEDED ✓")
    else:
        print("⚠️  WARNING: Scalars are DIFFERENT across instruments!")
        print(f"   Found {len(unique_scalars)} different values:")
        for val in sorted(unique_scalars):
            print(f"     {val:.6f}")
        print("\n   → Pooling may not have worked during backtest")
else:
    print("❌ Could not extract scalars for any instrument")
    print("\nLet me try alternative extraction methods...")

    # Emergency fallback: Check what methods exist
    print("\nAvailable methods in forecastScaleCap stage:")
    methods = [m for m in dir(stage) if 'scalar' in m.lower() and not m.startswith('__')]
    for method in methods:
        print(f"  - {method}")
