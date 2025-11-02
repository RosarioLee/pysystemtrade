# etf_data_manager.py - CORRECTED VERSION
import yfinance as yf
import pandas as pd
import os


def download_and_format_etf_data(symbols, start_date="2020-01-01"):
    """Download ETF data and format for PySystemTrade"""

    # Find correct PySystemTrade data path - FIXED PATH
    current_dir = os.getcwd()
    # Go up from perplexity_examples to pysystemtrade root
    pysystemtrade_root = os.path.dirname(current_dir)
    data_path = os.path.join(
        pysystemtrade_root, "data", "futures", "multiple_prices_csv"
    )

    print(f"Creating data directory: {data_path}")
    os.makedirs(data_path, exist_ok=True)

    for symbol in symbols:
        print(f"Downloading {symbol}...")
        data = yf.download(symbol, start=start_date, auto_adjust=False)

        # Format with all required columns in correct order
        formatted_data = pd.DataFrame()
        formatted_data["CARRY"] = data["Adj Close"]
        formatted_data["CARRY_CONTRACT"] = 20991200
        formatted_data["PRICE"] = data["Adj Close"]
        formatted_data["PRICE_CONTRACT"] = 20991200
        formatted_data["FORWARD"] = data["Adj Close"]
        formatted_data["FORWARD_CONTRACT"] = 20991200

        # Add time component for PySystemTrade compatibility
        formatted_data.index = pd.to_datetime(
            formatted_data.index.strftime("%Y-%m-%d") + " 23:00:00"
        )
        formatted_data.index.name = "DATETIME"

        # Save to PySystemTrade directory
        file_path = os.path.join(data_path, f"{symbol}.csv")
        formatted_data.to_csv(file_path)
        print(f"✅ {symbol} saved: {len(formatted_data)} rows to {file_path}")

    # Verify files were created
    print(f"\nVerification:")
    for symbol in symbols:
        file_path = os.path.join(data_path, f"{symbol}.csv")
        exists = os.path.exists(file_path)
        print(f"{symbol}.csv exists: {exists}")


if __name__ == "__main__":
    # Download your ETF data
    etf_symbols = ["IVV", "HYD"]
    download_and_format_etf_data(etf_symbols)
    print("\nData download complete! Now run etf_trading_system.py")
