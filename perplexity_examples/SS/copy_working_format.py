# Create: copy_working_format.py
import pandas as pd
import yfinance as yf
import os


def copy_working_csv_format():
    """Copy exact format from working PySystemTrade file"""

    # Path to PySystemTrade data
    current_dir = os.getcwd()
    pysystemtrade_root = os.path.dirname(current_dir)
    data_path = os.path.join(
        pysystemtrade_root, "data", "futures", "multiple_prices_csv"
    )

    print("=== Copying Working CSV Format ===")

    # Find a working CSV file to use as template
    working_files = [
        f
        for f in os.listdir(data_path)
        if f.endswith(".csv") and f not in ["IVV.csv", "HYD.csv"]
    ]

    if not working_files:
        print("No working CSV files found!")
        return

    template_file = working_files[0]  # Use first working file as template
    template_path = os.path.join(data_path, template_file)

    print(f"Using template: {template_file}")

    # Read the template to understand exact format
    template_df = pd.read_csv(template_path, index_col=0, parse_dates=True)
    print(f"Template columns: {list(template_df.columns)}")
    print(f"Template index name: {template_df.index.name}")
    print(f"Template shape: {template_df.shape}")

    # Download and format ETF data using EXACT template format
    for symbol in ["IVV", "HYD"]:
        print(f"\nProcessing {symbol}...")

        # Download fresh ETF data
        etf_data = yf.download(symbol, start="2020-01-01", auto_adjust=False)

        # Create new dataframe with EXACT same structure as template
        new_df = pd.DataFrame(index=template_df.index[: len(etf_data)])

        # Create datetime index matching template style
        etf_dates = pd.to_datetime(etf_data.index.strftime("%Y-%m-%d") + " 23:00:00")

        # Trim to available ETF data length
        available_dates = etf_dates[: len(template_df)]

        # Create ETF dataframe with template's exact structure
        etf_df = pd.DataFrame(index=available_dates)
        etf_df.index.name = template_df.index.name  # Exact same index name

        # Fill with ETF data using exact same column order as template
        price_data = etf_data["Adj Close"].values

        for col in template_df.columns:
            if col == "PRICE":
                etf_df[col] = price_data[: len(etf_df)]
            elif col == "CARRY":
                etf_df[col] = price_data[: len(etf_df)]
            elif col == "FORWARD":
                etf_df[col] = price_data[: len(etf_df)]
            elif col in ["PRICE_CONTRACT", "CARRY_CONTRACT", "FORWARD_CONTRACT"]:
                etf_df[col] = 20991200
            else:
                # Copy any other columns from template
                etf_df[col] = template_df[col].iloc[0]

        # Ensure exact same data types as template
        for col in template_df.columns:
            etf_df[col] = etf_df[col].astype(template_df[col].dtype)

        # Save with exact same format as template
        output_path = os.path.join(data_path, f"{symbol}.csv")
        etf_df.to_csv(output_path, date_format="%Y-%m-%d %H:%M:%S")

        print(f"✅ {symbol} saved with template format")
        print(f"   Shape: {etf_df.shape}")
        print(f"   Columns: {list(etf_df.columns)}")
        print(
            f"   Data types match template: {all(etf_df[col].dtype == template_df[col].dtype for col in template_df.columns)}"
        )


if __name__ == "__main__":
    copy_working_csv_format()
    print("\nETF files recreated with exact working format!")
    print("Now restart PyCharm completely and run etf_trading_system.py")
