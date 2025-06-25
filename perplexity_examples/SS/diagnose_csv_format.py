# Create: diagnose_csv_format.py
import pandas as pd
import os

# Check your ETF files
pysystemtrade_root = os.path.dirname(os.getcwd())
data_path = os.path.join(pysystemtrade_root, "data", "futures", "multiple_prices_csv")

print("=== Diagnosing CSV Format Issues ===")

for symbol in ["IVV", "HYD"]:
    file_path = os.path.join(data_path, f"{symbol}.csv")

    print(f"\n{symbol} File Analysis:")

    # Read raw file content first
    with open(file_path, 'r') as f:
        first_lines = [f.readline().strip() for _ in range(5)]

    print("First 5 raw lines:")
    for i, line in enumerate(first_lines):
        print(f"  {i + 1}: {line}")

    # Try to read with pandas
    try:
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)
        print(f"✅ Pandas can read file: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        print(f"Index name: {df.index.name}")
        print(f"Index type: {type(df.index)}")

        # Check for any issues
        if df.isnull().any().any():
            print("❌ Contains NaN values")
        else:
            print("✅ No NaN values")

        # Check data types
        print(f"Data types: {df.dtypes.to_dict()}")

    except Exception as e:
        print(f"❌ Pandas error: {e}")

# Compare with a working futures file
print(f"\n=== Comparing with Working Futures File ===")
working_files = [f for f in os.listdir(data_path) if f.endswith('.csv') and f not in ['IVV.csv', 'HYD.csv']]
if working_files:
    working_file = working_files[0]
    working_path = os.path.join(data_path, working_file)

    print(f"Checking working file: {working_file}")

    with open(working_path, 'r') as f:
        working_lines = [f.readline().strip() for _ in range(5)]

    print("Working file first 5 lines:")
    for i, line in enumerate(working_lines):
        print(f"  {i + 1}: {line}")

    # Read working file
    working_df = pd.read_csv(working_path, index_col=0, parse_dates=True)
    print(f"Working file columns: {list(working_df.columns)}")
    print(f"Working file index name: {working_df.index.name}")
