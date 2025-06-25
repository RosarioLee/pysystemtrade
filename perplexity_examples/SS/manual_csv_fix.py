# Create: manual_csv_fix.py
import pandas as pd
import os


def manual_csv_fix():
    """Manually fix CSV files based on exact PySystemTrade requirements"""

    current_dir = os.getcwd()
    pysystemtrade_root = os.path.dirname(current_dir)
    data_path = os.path.join(pysystemtrade_root, "data", "futures", "multiple_prices_csv")

    # Delete existing ETF files
    for symbol in ["IVV", "HYD"]:
        file_path = os.path.join(data_path, f"{symbol}.csv")
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted {symbol}.csv")

    print("Recreating ETF files with manual format...")

    # Create minimal test file
    test_data = {
        'CARRY': [100.0, 101.0, 102.0],
        'CARRY_CONTRACT': [20991200, 20991200, 20991200],
        'PRICE': [100.0, 101.0, 102.0],
        'PRICE_CONTRACT': [20991200, 20991200, 20991200],
        'FORWARD': [100.0, 101.0, 102.0],
        'FORWARD_CONTRACT': [20991200, 20991200, 20991200]
    }

    dates = pd.date_range('2024-01-01 23:00:00', periods=3, freq='D')
    df = pd.DataFrame(test_data, index=dates)
    df.index.name = 'DATETIME'

    # Save test ETF file
    test_path = os.path.join(data_path, "IVV.csv")
    df.to_csv(test_path)

    print("Created minimal test IVV.csv")
    print("Run etf_trading_system.py to test if this format works")


if __name__ == "__main__":
    manual_csv_fix()
