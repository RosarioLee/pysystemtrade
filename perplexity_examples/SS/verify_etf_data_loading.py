# Create: verify_etf_data_loading.py
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
import os

print("=== Verifying ETF Data Loading ===")

# Create data source
data_source = csvFuturesSimData()

# Check what instruments PySystemTrade can find
available_instruments = data_source.get_instrument_list()
print(f"Total instruments available: {len(available_instruments)}")

# Check specifically for your ETFs
for etf in ["IVV", "HYD"]:
    if etf in available_instruments:
        print(f"✅ {etf} found in instrument list")

        # Try to load the data
        try:
            prices = data_source.daily_prices(etf)
            print(f"✅ {etf} price data loaded: {len(prices)} rows")
            print(f"   Latest price: {prices.iloc[-1]:.2f}")
        except Exception as e:
            print(f"❌ Error loading {etf} prices: {e}")

        try:
            multiple_prices = data_source.get_multiple_prices(etf)
            print(f"✅ {etf} multiple prices loaded: {multiple_prices.shape}")
            print(f"   Columns: {list(multiple_prices.columns)}")
        except Exception as e:
            print(f"❌ Error loading {etf} multiple prices: {e}")

    else:
        print(f"❌ {etf} NOT found in instrument list")

# Check the actual file paths
pysystemtrade_root = os.path.dirname(os.getcwd())
data_path = os.path.join(pysystemtrade_root, "data", "futures", "multiple_prices_csv")

print(f"\nChecking file paths:")
print(f"Data directory: {data_path}")
print(f"Directory exists: {os.path.exists(data_path)}")

if os.path.exists(data_path):
    files = os.listdir(data_path)
    etf_files = [f for f in files if f.startswith(("IVV", "HYD"))]
    print(f"ETF files found: {etf_files}")
else:
    print("❌ Data directory doesn't exist!")
