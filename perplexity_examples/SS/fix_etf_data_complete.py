# Create: fix_etf_data_complete.py
import pandas as pd
import yfinance as yf
import os


def create_complete_etf_data(symbol, start_date="2020-01-01"):
    """Download ETF data with ALL required futures columns"""
    data = yf.download(symbol, start=start_date, auto_adjust=False)

    # Create formatted data with ALL required columns
    formatted_data = pd.DataFrame()
    formatted_data['PRICE'] = data['Adj Close']
    formatted_data['CARRY'] = data['Adj Close']  # Same as price for ETFs
    formatted_data['PRICE_CONTRACT'] = '20991200'  # Dummy far future contract
    formatted_data['CARRY_CONTRACT'] = '20991200'  # Same dummy contract
    formatted_data['FORWARD_CONTRACT'] = '20991200'  # Missing column!

    formatted_data.index.name = 'DATETIME'
    return formatted_data


# Find correct data path
pysystemtrade_root = os.path.dirname(os.getcwd())
correct_data_path = os.path.join(pysystemtrade_root, "data", "futures", "multiple_prices_csv")

print("=== Creating Complete ETF Data ===")

# Download and format ETF data with ALL columns
ivv_data = create_complete_etf_data("IVV")
hyd_data = create_complete_etf_data("HYD")

print(f"IVV data columns: {list(ivv_data.columns)}")
print(f"HYD data columns: {list(hyd_data.columns)}")

# Save to correct location
ivv_path = os.path.join(correct_data_path, "IVV.csv")
hyd_path = os.path.join(correct_data_path, "HYD.csv")

ivv_data.to_csv(ivv_path)
hyd_data.to_csv(hyd_path)

print(f"✅ Complete ETF data saved with FORWARD_CONTRACT column:")
print(f"- {ivv_path}")
print(f"- {hyd_path}")

# Show sample of the data
print(f"\nSample IVV data:")
print(ivv_data.head(3))
