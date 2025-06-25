# Create: fix_etf_datetime_format.py
import pandas as pd
import yfinance as yf
import os


def create_etf_data_with_correct_datetime(symbol, start_date="2020-01-01"):
    """Download ETF data with correct datetime format matching futures"""
    data = yf.download(symbol, start=start_date, auto_adjust=False)

    # Create formatted data with ALL required columns
    formatted_data = pd.DataFrame()
    formatted_data['CARRY'] = data['Adj Close']
    formatted_data['CARRY_CONTRACT'] = 20991200
    formatted_data['PRICE'] = data['Adj Close']
    formatted_data['PRICE_CONTRACT'] = 20991200
    formatted_data['FORWARD'] = data['Adj Close']
    formatted_data['FORWARD_CONTRACT'] = 20991200

    # CRITICAL FIX: Add time component to match futures format
    # Convert date-only index to datetime with time (23:00:00 like futures)
    formatted_data.index = pd.to_datetime(formatted_data.index.strftime('%Y-%m-%d') + ' 23:00:00')
    formatted_data.index.name = 'DATETIME'

    return formatted_data


# Find correct data path
pysystemtrade_root = os.path.dirname(os.getcwd())
correct_data_path = os.path.join(pysystemtrade_root, "data", "futures", "multiple_prices_csv")

print("=== Creating ETF Data with Correct Datetime Format ===")

# Download and format ETF data with correct datetime
ivv_data = create_etf_data_with_correct_datetime("IVV")
hyd_data = create_etf_data_with_correct_datetime("HYD")

print(f"IVV datetime format: {ivv_data.index[0]} (includes time: ✅)")
print(f"HYD datetime format: {hyd_data.index[0]} (includes time: ✅)")

# Save to correct location
ivv_path = os.path.join(correct_data_path, "IVV.csv")
hyd_path = os.path.join(correct_data_path, "HYD.csv")

ivv_data.to_csv(ivv_path)
hyd_data.to_csv(hyd_path)

print(f"✅ ETF data saved with correct datetime format:")
print(f"- {ivv_path}")
print(f"- {hyd_path}")

# Show sample of corrected format
print(f"\nSample corrected format (first 3 rows):")
print(ivv_data.head(3))

# Test if PySystemTrade can now find the data
try:
    from sysdata.sim.csv_futures_sim_data import csvFuturesSimData

    data_source = csvFuturesSimData()
    available_instruments = data_source.get_instrument_list()

    if "IVV" in available_instruments:
        print("🎉 PySystemTrade can now find IVV!")
    if "HYD" in available_instruments:
        print("🎉 PySystemTrade can now find HYD!")

except Exception as e:
    print(f"Error testing data access: {e}")
