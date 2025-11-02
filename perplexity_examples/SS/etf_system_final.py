# etf_system_final.py - Using PySystemTrade's native CSV approach
import yfinance as yf
import pandas as pd
import os
from systems.provided.futures_chapter15.basesystem import futures_system
from systems.forecasting import TradingRule
from systems.provided.rules.ewmac import ewmac
from sysdata.config.configdata import Config
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData


def create_etf_csv_files():
    """Create ETF CSV files in PySystemTrade's exact expected format"""

    # Find PySystemTrade's data directory
    current_dir = os.getcwd()
    pysystemtrade_root = os.path.dirname(current_dir)
    data_path = os.path.join(
        pysystemtrade_root, "data", "futures", "multiple_prices_csv"
    )

    print("=== Creating ETF CSV Files ===")
    os.makedirs(data_path, exist_ok=True)

    # Download and format ETF data exactly like PySystemTrade expects
    for symbol in ["IVV", "HYD"]:
        print(f"Processing {symbol}...")

        # Download ETF data
        etf_data = yf.download(symbol, start="2020-01-01", auto_adjust=False)

        # Create PySystemTrade-compatible CSV with exact column order from search results
        formatted_data = pd.DataFrame()
        formatted_data["CARRY"] = etf_data["Adj Close"]
        formatted_data["CARRY_CONTRACT"] = 20991200  # Far future contract date
        formatted_data["PRICE"] = etf_data["Adj Close"]
        formatted_data["PRICE_CONTRACT"] = 20991200
        formatted_data["FORWARD"] = etf_data["Adj Close"]
        formatted_data["FORWARD_CONTRACT"] = 20991200

        # Add time component to dates (required by PySystemTrade)
        formatted_data.index = pd.to_datetime(
            formatted_data.index.strftime("%Y-%m-%d") + " 23:00:00"
        )
        formatted_data.index.name = "DATETIME"

        # Ensure exact data types
        formatted_data["CARRY"] = formatted_data["CARRY"].astype("float64")
        formatted_data["PRICE"] = formatted_data["PRICE"].astype("float64")
        formatted_data["FORWARD"] = formatted_data["FORWARD"].astype("float64")
        formatted_data["CARRY_CONTRACT"] = formatted_data["CARRY_CONTRACT"].astype(
            "int64"
        )
        formatted_data["PRICE_CONTRACT"] = formatted_data["PRICE_CONTRACT"].astype(
            "int64"
        )
        formatted_data["FORWARD_CONTRACT"] = formatted_data["FORWARD_CONTRACT"].astype(
            "int64"
        )

        # Save in PySystemTrade's expected location
        file_path = os.path.join(data_path, f"{symbol}.csv")
        formatted_data.to_csv(file_path, date_format="%Y-%m-%d %H:%M:%S")

        print(f"✅ {symbol} saved: {len(formatted_data)} rows")

    return data_path


def create_etf_trading_system():
    """Create ETF trading system using PySystemTrade's native approach"""

    # Ensure ETF CSV files exist
    data_path = create_etf_csv_files()

    # Use PySystemTrade's native CSV data source (as shown in search results [7])
    data_source = csvFuturesSimData()

    # Verify ETF data is available
    available_instruments = data_source.get_instrument_list()
    etf_symbols = ["IVV", "HYD"]

    for etf in etf_symbols:
        if etf not in available_instruments:
            raise Exception(
                f"{etf} not found in PySystemTrade data. Available: {available_instruments[:10]}..."
            )
        else:
            print(f"✅ {etf} found in PySystemTrade")

    # Create EWMAC trading rule
    ewmac_rule = TradingRule(
        ewmac,
        ["rawdata.get_daily_prices", "rawdata.daily_returns_volatility"],
        dict(Lfast=8, Lslow=32),
    )

    # System configuration (following search results [7] pattern)
    config_dict = {
        "trading_rules": {"ewmac_momentum": ewmac_rule},
        "instruments": etf_symbols,
        "forecast_weights": {"ewmac_momentum": 1.0},
        "instrument_weights": {etf: 0.5 for etf in etf_symbols},  # Equal weights
    }

    # Create system using PySystemTrade's standard approach
    system = futures_system(data=data_source, config=Config(config_dict))

    return system


def run_etf_analysis():
    """Run complete ETF trading system analysis"""

    print("=== ETF Trading System (PySystemTrade Native) ===")

    try:
        # Create system
        system = create_etf_trading_system()

        # Get performance
        portfolio = system.accounts.portfolio()
        print(f"\nPortfolio Sharpe Ratio: {portfolio.sharpe():.2f}")

        # Individual ETF performance
        for etf in ["IVV", "HYD"]:
            individual_perf = system.accounts.pandl_for_instrument(etf)
            print(f"{etf} Sharpe: {individual_perf.sharpe():.2f}")

        # Latest forecasts
        print(f"\n=== Latest Trading Signals ===")
        for etf in ["IVV", "HYD"]:
            forecast = system.rules.get_raw_forecast(etf, "ewmac_momentum")
            signal = "BUY" if forecast.iloc[-1] > 0 else "SELL"
            print(f"{etf}: {forecast.iloc[-1]:.2f} ({signal})")

        print(
            f"\n🎉 Your ETF systematic trading system is working using PySystemTrade's native approach!"
        )

        return system

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    etf_system = run_etf_analysis()
