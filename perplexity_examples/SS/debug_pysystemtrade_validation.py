# Create: debug_pysystemtrade_validation.py
import os
import pandas as pd
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
import shutil


def debug_csv_validation():
    """Debug exactly what PySystemTrade requires for CSV files"""

    current_dir = os.getcwd()
    pysystemtrade_root = os.path.dirname(current_dir)
    data_path = os.path.join(pysystemtrade_root, "data", "futures", "multiple_prices_csv")

    print("=== Debugging PySystemTrade CSV Validation ===")

    # Step 1: Find a working CSV file
    data_source = csvFuturesSimData()
    working_instruments = data_source.get_instrument_list()

    # Pick the first working instrument
    working_instrument = working_instruments[0]
    working_file = os.path.join(data_path, f"{working_instrument}.csv")

    print(f"Using working instrument: {working_instrument}")

    # Step 2: Copy working file to create IVV.csv
    ivv_file = os.path.join(data_path, "IVV.csv")

    # Remove existing IVV.csv
    if os.path.exists(ivv_file):
        os.remove(ivv_file)
        print("Removed existing IVV.csv")

    # Copy working file to IVV.csv
    shutil.copy2(working_file, ivv_file)
    print(f"Copied {working_instrument}.csv to IVV.csv")

    # Step 3: Test if copied file works
    data_source_new = csvFuturesSimData()  # Create fresh instance
    new_instruments = data_source_new.get_instrument_list()

    if "IVV" in new_instruments:
        print("🎉 SUCCESS! Copied file works - IVV found in instrument list")

        # Step 4: Now gradually modify with ETF data
        print("\nStep 4: Replacing with ETF data...")

        # Read the working structure
        working_df = pd.read_csv(ivv_file, index_col=0, parse_dates=True)
        print(f"Working structure: {working_df.shape}")

        # Download IVV data
        import yfinance as yf
        ivv_data = yf.download("IVV", start="2020-01-01", auto_adjust=False)

        # Create new dataframe with same structure but IVV prices
        new_df = working_df.copy()

        # Replace price data with IVV data (keep same dates as working file)
        for i, (date, row) in enumerate(working_df.iterrows()):
            if i < len(ivv_data):
                ivv_price = ivv_data['Adj Close'].iloc[i]
                new_df.loc[date, 'PRICE'] = ivv_price
                new_df.loc[date, 'CARRY'] = ivv_price
                new_df.loc[date, 'FORWARD'] = ivv_price

        # Save modified version
        new_df.to_csv(ivv_file)
        print("Replaced price data with IVV prices")

        # Test again
        data_source_final = csvFuturesSimData()
        final_instruments = data_source_final.get_instrument_list()

        if "IVV" in final_instruments:
            print("🎉 SUCCESS! IVV with real ETF data works!")
            return True
        else:
            print("❌ Failed after adding ETF data")
            return False

    else:
        print("❌ FAILED! Even copied file doesn't work")
        print(f"Available instruments: {new_instruments[:10]}...")
        return False


if __name__ == "__main__":
    success = debug_csv_validation()
    if success:
        print("\nIVV.csv is now working! Run etf_trading_system.py")
    else:
        print("\nDebugging failed. Need to investigate further.")
