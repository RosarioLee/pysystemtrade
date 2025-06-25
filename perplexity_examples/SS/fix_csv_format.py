# Create: fix_csv_format.py
import pandas as pd
import os


def fix_etf_csv_format():
    """Fix ETF CSV format to match PySystemTrade's exact requirements"""

    # Path to your ETF files
    current_dir = os.getcwd()
    pysystemtrade_root = os.path.dirname(current_dir)
    data_path = os.path.join(pysystemtrade_root, "data", "futures", "multiple_prices_csv")

    print("=== Fixing ETF CSV Format ===")

    # Step 1: Read a working futures file to see exact format
    working_files = [f for f in os.listdir(data_path) if f.endswith('.csv') and f not in ['IVV.csv', 'HYD.csv']]
    if working_files:
        working_file = working_files[0]
        working_path = os.path.join(data_path, working_file)

        print(f"Analyzing working file: {working_file}")
        working_df = pd.read_csv(working_path, index_col=0, parse_dates=True)

        print(f"Working file columns: {list(working_df.columns)}")
        print(f"Working file index name: {working_df.index.name}")
        print(f"Working file data types:")
        print(working_df.dtypes)
        print(f"Working file sample:")
        print(working_df.head(2))

    # Step 2: Fix your ETF files to match exact format
    for symbol in ["IVV", "HYD"]:
        file_path = os.path.join(data_path, f"{symbol}.csv")

        if os.path.exists(file_path):
            print(f"\nFixing {symbol}.csv...")

            # Read current ETF file
            df = pd.read_csv(file_path, index_col=0, parse_dates=True)

            # Ensure exact data types match working files
            df['CARRY'] = df['CARRY'].astype('float64')
            df['CARRY_CONTRACT'] = df['CARRY_CONTRACT'].astype('int64')
            df['PRICE'] = df['PRICE'].astype('float64')
            df['PRICE_CONTRACT'] = df['PRICE_CONTRACT'].astype('int64')
            df['FORWARD'] = df['FORWARD'].astype('float64')
            df['FORWARD_CONTRACT'] = df['FORWARD_CONTRACT'].astype('int64')

            # Ensure index name is exactly 'DATETIME'
            df.index.name = 'DATETIME'

            # Round numeric values to match futures precision
            df['CARRY'] = df['CARRY'].round(6)
            df['PRICE'] = df['PRICE'].round(6)
            df['FORWARD'] = df['FORWARD'].round(6)

            # Save with exact format
            df.to_csv(file_path, date_format='%Y-%m-%d %H:%M:%S')

            print(f"✅ {symbol} fixed and saved")
            print(f"   Data types: {df.dtypes.to_dict()}")
            print(f"   Sample data:")
            print(df.head(2))


if __name__ == "__main__":
    fix_etf_csv_format()
    print("\nCSV format fixed! Now restart PyCharm and run etf_trading_system.py")
