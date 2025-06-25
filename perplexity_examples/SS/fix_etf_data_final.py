# Create: fix_etf_data_final.py
import pandas as pd
import yfinance as yf
import os


def create_complete_etf_data_final(symbol, start_date="2020-01-01"):
    """Download ETF data with ALL required futures columns in correct order"""
    data = yf.download(symbol, start=start_date, auto_adjust=False)

    # Create formatted data with ALL required columns in EXACT order as futures
    formatted_data = pd.DataFrame()
    formatted_data['CARRY'] = data['Adj Close']  # Same as price for ETFs
    formatted_data['CARRY_CONTRACT'] = 20991200  # Dummy far future contract
    formatted_data['PRICE'] = data['Adj Close']  # Main price column
    formatted_data['PRICE_CONTRACT'] = 20991200  # Same dummy contract
    formatted_data['FORWARD'] = data['Adj Close']  # MISSING COLUMN - same as price for ETFs
    formatted_data['FORWARD_CONTRACT'] = 20991200  # Same dummy contract

    formatted_data.index.name = 'DATETIME'
    return formatted_data


# Find correct data path
pysystemtrade_root = os.path.dirname(os.getcwd())
correct_data_path = os.path.join(pysystemtrade_root, "data", "futures", "multiple_prices_csv")

print("=== Creating Final Complete ETF Data ===")

# Download and format ETF data with ALL columns in correct order
ivv_data = create_complete_etf_data_final("IVV")
hyd_data = create_complete_etf_data_final("HYD")

print(f"IVV data columns: {list(ivv_data.columns)}")
print(f"HYD data columns: {list(hyd_data.columns)}")
print(
    f"Column order matches futures: {list(ivv_data.columns) == ['CARRY', 'CARRY_CONTRACT', 'PRICE', 'PRICE_CONTRACT', 'FORWARD', 'FORWARD_CONTRACT']}")

# Save to correct location
ivv_path = os.path.join(correct_data_path, "IVV.csv")
hyd_path = os.path.join(correct_data_path, "HYD.csv")

ivv_data.to_csv(ivv_path)
hyd_data.to_csv(hyd_path)

print(f"✅ Final complete ETF data saved:")
print(f"- {ivv_path}")
print(f"- {hyd_path}")

# Show sample of the corrected data
print(f"\nSample corrected IVV data:")
print(ivv_data.head(3))
