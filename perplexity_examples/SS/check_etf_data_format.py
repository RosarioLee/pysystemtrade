# Create: check_etf_data_format.py
import pandas as pd
import os

# Find your ETF data files
pysystemtrade_root = os.path.dirname(os.getcwd())
data_path = os.path.join(pysystemtrade_root, "data", "futures", "multiple_prices_csv")

print("=== Checking ETF Data Format ===")

for symbol in ["IVV", "HYD"]:
    file_path = os.path.join(data_path, f"{symbol}.csv")

    if os.path.exists(file_path):
        print(f"\n{symbol} file exists: {file_path}")

        # Read and examine the data
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)

        print(f"Columns: {list(df.columns)}")
        print(f"Index name: {df.index.name}")
        print(f"Data shape: {df.shape}")
        print(f"First few rows:")
        print(df.head(3))

        # Check for any NaN values
        nan_count = df.isnull().sum().sum()
        print(f"NaN values: {nan_count}")

        # Check data types
        print(f"Data types:")
        print(df.dtypes)

    else:
        print(f"❌ {symbol} file not found: {file_path}")

# Also check what a working futures file looks like for comparison
print("\n=== Checking Working Futures File for Comparison ===")
try:
    from sysdata.sim.csv_futures_sim_data import csvFuturesSimData

    data_source = csvFuturesSimData()

    # Get a working futures instrument for comparison
    working_data = data_source.get_multiple_prices("AUD")  # AUD was in the working list
    print(f"Working futures data columns: {list(working_data.columns)}")
    print(f"Working futures data shape: {working_data.shape}")
    print(f"Working futures sample:")
    print(working_data.head(3))

except Exception as e:
    print(f"Error checking working futures data: {e}")
