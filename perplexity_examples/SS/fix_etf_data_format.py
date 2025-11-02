# Create: fix_etf_data_format.py
import pandas as pd
import yfinance as yf
import os


def create_etf_data_with_futures_format(symbol, start_date="2020-01-01"):
    """Download ETF data and format with all required futures columns"""
    data = yf.download(symbol, start=start_date, auto_adjust=False)

    # Create formatted data with all required columns
    formatted_data = pd.DataFrame()
    formatted_data["PRICE"] = data["Adj Close"]

    # For ETFs, we don't have carry or contracts, so we'll use the price
    formatted_data["CARRY"] = data["Adj Close"]  # Same as price for ETFs
    formatted_data["PRICE_CONTRACT"] = "20991200"  # Dummy contract (far future)
    formatted_data["CARRY_CONTRACT"] = "20991200"  # Same dummy contract

    formatted_data.index.name = "DATETIME"
    return formatted_data


# Find correct data path
pysystemtrade_root = os.path.dirname(os.getcwd())
correct_data_path = os.path.join(
    pysystemtrade_root, "data", "futures", "multiple_prices_csv"
)

print("=== Creating ETF Data with Futures Format ===")

# Download and format ETF data
ivv_data = create_etf_data_with_futures_format("IVV")
hyd_data = create_etf_data_with_futures_format("HYD")

print(f"IVV data columns: {list(ivv_data.columns)}")
print(f"HYD data columns: {list(hyd_data.columns)}")

# Save to correct location
ivv_path = os.path.join(correct_data_path, "IVV.csv")
hyd_path = os.path.join(correct_data_path, "HYD.csv")

ivv_data.to_csv(ivv_path)
hyd_data.to_csv(hyd_path)

print(f"✅ Fixed ETF data saved:")
print(f"- {ivv_path}")
print(f"- {hyd_path}")

# Test if PySystemTrade can now process the data
try:
    from sysdata.sim.csv_futures_sim_data import csvFuturesSimData

    data_source = csvFuturesSimData()

    # Test carry data access
    ivv_carry_data = data_source.get_instrument_raw_carry_data("IVV")
    print(f"✅ IVV carry data accessible: {len(ivv_carry_data)} rows")
    print(f"Columns: {list(ivv_carry_data.columns)}")

except Exception as e:
    print(f"❌ Error accessing carry data: {e}")
