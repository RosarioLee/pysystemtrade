# Create: etf_system_test_fixed_correct_path.py
import yfinance as yf
import pandas as pd
import os


def download_etf_data(symbol, start_date="2020-01-01"):
    """Download ETF data and format like PySystemTrade expects"""
    # Fix: Use auto_adjust=False to get 'Adj Close' column
    data = yf.download(symbol, start=start_date, auto_adjust=False)

    # PySystemTrade expects 'PRICE' column in simple format
    formatted_data = pd.DataFrame()
    formatted_data['PRICE'] = data['Adj Close']
    formatted_data.index.name = 'DATETIME'  # PySystemTrade expects this index name

    return formatted_data


# Find the correct PySystemTrade data directory
# Go up from perplexity_examples to pysystemtrade root, then to data directory
pysystemtrade_root = os.path.dirname(os.getcwd())  # Go up one level from perplexity_examples
correct_data_path = os.path.join(pysystemtrade_root, "data", "futures", "multiple_prices_csv")

print(f"Saving to PySystemTrade data directory: {correct_data_path}")

# Create data directory if it doesn't exist
os.makedirs(correct_data_path, exist_ok=True)

print("=== Downloading ETF Data to Correct Location ===")
try:
    # Download data for two ETFs from your config
    ivv_data = download_etf_data("IVV")  # US Equity
    hyd_data = download_etf_data("HYD")  # US Municipal Bonds

    print(f"IVV data: {len(ivv_data)} days")
    print(f"HYD data: {len(hyd_data)} days")
    print(f"IVV latest price: ${ivv_data['PRICE'].iloc[-1]:.2f}")
    print(f"HYD latest price: ${hyd_data['PRICE'].iloc[-1]:.2f}")

    # Save as CSV files in PySystemTrade's correct data directory
    ivv_path = os.path.join(correct_data_path, "IVV.csv")
    hyd_path = os.path.join(correct_data_path, "HYD.csv")

    ivv_data.to_csv(ivv_path)
    hyd_data.to_csv(hyd_path)

    print("\n✅ ETF data downloaded and saved successfully!")
    print("Files created:")
    print(f"- {ivv_path}")
    print(f"- {hyd_path}")

    # Verify PySystemTrade can now find the data
    from sysdata.sim.csv_futures_sim_data import csvFuturesSimData

    data_source = csvFuturesSimData()
    available_instruments = data_source.get_instrument_list()

    if "IVV" in available_instruments:
        print("🎉 PySystemTrade can now find IVV!")
    if "HYD" in available_instruments:
        print("🎉 PySystemTrade can now find HYD!")

except Exception as e:
    print(f"Error: {e}")
    print("Installing yfinance...")
    import subprocess

    subprocess.run(["pip", "install", "yfinance"])
