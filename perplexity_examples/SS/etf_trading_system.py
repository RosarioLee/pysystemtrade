# etf_trading_system.py - SIMPLIFIED VERSION (edit your existing file)
from systems.provided.futures_chapter15.basesystem import futures_system
from systems.forecasting import TradingRule
from systems.provided.rules.ewmac import ewmac
from sysdata.config.configdata import Config
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
import os


class ETFTradingSystem:
    def __init__(self, etf_symbols, ewmac_fast=8, ewmac_slow=32):
        self.etf_symbols = etf_symbols
        self.ewmac_fast = ewmac_fast
        self.ewmac_slow = ewmac_slow
        self.system = None

    def verify_data_available(self):
        """Check if ETF data is available to PySystemTrade"""
        # Use default data source (should find your ETF files)
        data_source = csvFuturesSimData()
        available_instruments = data_source.get_instrument_list()

        print(f"Total instruments found: {len(available_instruments)}")

        # Debug: Check if ETF files exist in expected location
        current_dir = os.getcwd()
        pysystemtrade_root = os.path.dirname(current_dir)
        data_path = os.path.join(
            pysystemtrade_root, "data", "futures", "multiple_prices_csv"
        )

        for etf in self.etf_symbols:
            file_path = os.path.join(data_path, f"{etf}.csv")
            file_exists = os.path.exists(file_path)
            in_instrument_list = etf in available_instruments

            print(
                f"{etf}: file exists={file_exists}, in instrument list={in_instrument_list}"
            )

            if not in_instrument_list:
                print(f"❌ {etf} data not found in PySystemTrade!")
                if file_exists:
                    print(
                        f"   File exists at {file_path} but PySystemTrade can't read it"
                    )
                    # Try to read the file manually to check format
                    try:
                        import pandas as pd

                        df = pd.read_csv(file_path, index_col=0, parse_dates=True)
                        print(
                            f"   File has {len(df)} rows, columns: {list(df.columns)}"
                        )
                    except Exception as e:
                        print(f"   Error reading file: {e}")
                return False
            else:
                print(f"✅ {etf} data found")
        return True

    def create_system(self):
        """Create PySystemTrade system for ETF trading"""

        # Verify data exists first
        if not self.verify_data_available():
            raise Exception(
                "ETF data not available. Check file format or restart Python session."
            )

        # Create EWMAC momentum rule
        ewmac_rule = TradingRule(
            ewmac,
            ["rawdata.get_daily_prices", "rawdata.daily_returns_volatility"],
            dict(Lfast=self.ewmac_fast, Lslow=self.ewmac_slow),
        )

        # System configuration
        config_dict = {
            "trading_rules": {"ewmac_momentum": ewmac_rule},
            "instruments": self.etf_symbols,
            "forecast_weights": {"ewmac_momentum": 1.0},
            "instrument_weights": {
                etf: 1.0 / len(self.etf_symbols) for etf in self.etf_symbols
            },
        }

        # Use default data source (no custom paths)
        self.system = futures_system(config=Config(config_dict))
        return self.system

    def get_performance(self):
        """Get system performance metrics"""
        if not self.system:
            self.create_system()

        portfolio = self.system.accounts.portfolio()
        results = {"portfolio_sharpe": portfolio.sharpe(), "individual_performance": {}}

        # Individual ETF performance
        for etf in self.etf_symbols:
            individual_perf = self.system.accounts.pandl_for_instrument(etf)
            results["individual_performance"][etf] = individual_perf.sharpe()

        return results


if __name__ == "__main__":
    print("=== ETF Trading System Results ===")

    # IMPORTANT: Restart your Python session to clear any cached instrument lists
    print("Note: If this fails, restart Python/PyCharm and run again")

    etf_system = ETFTradingSystem(["IVV", "HYD"])

    try:
        performance = etf_system.get_performance()

        print(f"Portfolio Sharpe Ratio: {performance['portfolio_sharpe']:.2f}")

        for etf, sharpe in performance["individual_performance"].items():
            print(f"{etf} Sharpe: {sharpe:.2f}")

    except Exception as e:
        print(f"Error: {e}")
