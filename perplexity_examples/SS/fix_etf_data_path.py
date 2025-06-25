# Create: fix_etf_data_path_corrected.py
import os
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
import pandas as pd

print("=== Debugging Data Path Issue (Fixed) ===")

# Check where PySystemTrade expects data
data_source = csvFuturesSimData()

# Find the correct data path attribute
print("Available attributes:")
data_attrs = [attr for attr in dir(data_source) if not attr.startswith('_')]
print(data_attrs[:10])  # Show first 10 attributes

# Try to get the data path using different methods
try:
    # Method 1: Check if there's a data directory attribute
    if hasattr(data_source, 'data_directory'):
        print(f"Data directory: {data_source.data_directory}")
    elif hasattr(data_source, '_datapath'):
        print(f"Data path: {data_source._datapath}")
    else:
        print("No obvious data path attribute found")

    # Method 2: Try to get instrument list to see what PySystemTrade can find
    available_instruments = data_source.get_instrument_list()
    print(f"Available instruments: {len(available_instruments)}")
    print(f"First 10 instruments: {available_instruments[:10]}")

    # Check if your ETFs are in the list
    if "IVV" in available_instruments:
        print("✅ PySystemTrade found IVV")
    else:
        print("❌ PySystemTrade cannot find IVV")

    if "HYD" in available_instruments:
        print("✅ PySystemTrade found HYD")
    else:
        print("❌ PySystemTrade cannot find HYD")

except Exception as e:
    print(f"Error checking instruments: {e}")

# Check your file locations
print(f"\nCurrent working directory: {os.getcwd()}")

# Check if your data files exist
data_files = [
    "data/futures/multiple_prices_csv/IVV.csv",
    "data/futures/multiple_prices_csv/HYD.csv"
]

for file_path in data_files:
    if os.path.exists(file_path):
        print(f"✅ Found: {file_path}")
        # Try to read the file
        try:
            df = pd.read_csv(file_path, index_col=0, parse_dates=True)
            print(f"   - {len(df)} rows, latest date: {df.index[-1]}")
        except Exception as e:
            print(f"   - Error reading file: {e}")
    else:
        print(f"❌ Missing: {file_path}")
