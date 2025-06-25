# direct_data_approach.py - FIXED with proper inheritance
import yfinance as yf
import pandas as pd
from systems.provided.futures_chapter15.basesystem import futures_system
from systems.forecasting import TradingRule
from systems.provided.rules.ewmac import ewmac
from sysdata.config.configdata import Config
from sysdata import base_data  # Import the base class


class DirectETFData(base_data):  # INHERIT FROM baseData
    """Custom data source that provides ETF data directly to PySystemTrade"""

    def __init__(self):
        super().__init__()  # Call parent constructor
        print("Downloading ETF data...")
        # Download ETF data directly in memory (no CSV files needed)
        self.ivv_data = yf.download("IVV", start="2020-01-01", auto_adjust=False)
        self.hyd_data = yf.download("HYD", start="2020-01-01", auto_adjust=False)

        print(f"IVV: {len(self.ivv_data)} rows")
        print(f"HYD: {len(self.hyd_data)} rows")

    def system_init(self, system):
        """Required method for PySystemTrade data sources"""
        pass

    def get_raw_price(self, instrument):  # Changed from daily_prices to get_raw_price
        """Get raw prices for instrument - required by base class"""
        if instrument == "IVV":
            prices = self.ivv_data['Adj Close']
        elif instrument == "HYD":
            prices = self.hyd_data['Adj Close']
        else:
            raise Exception(f"Unknown instrument: {instrument}")

        prices.name = 'price'
        return prices

    def daily_prices(self, instrument):
        """Get daily prices for instrument"""
        return self.get_raw_price(instrument)

    def daily_returns_volatility(self, instrument):
        """Calculate daily returns volatility"""
        prices = self.daily_prices(instrument)
        returns = prices.pct_change().dropna()
        vol = returns.rolling(30).std() * (252 ** 0.5)
        vol.name = 'volatility'
        return vol

    def get_instrument_raw_carry_data(self, instrument):
        """Get raw carry data - required by PySystemTrade"""
        if instrument == "IVV":
            etf_data = self.ivv_data
        elif instrument == "HYD":
            etf_data = self.hyd_data
        else:
            raise Exception(f"Unknown instrument: {instrument}")

        carry_data = pd.DataFrame()
        carry_data['PRICE'] = etf_data['Adj Close']
        carry_data['CARRY'] = etf_data['Adj Close']
        carry_data['PRICE_CONTRACT'] = 20991200
        carry_data['CARRY_CONTRACT'] = 20991200
        carry_data['FORWARD'] = etf_data['Adj Close']
        carry_data['FORWARD_CONTRACT'] = 20991200

        return carry_data

    def _get_fx_data(self, currency1, currency2):
        """Get FX rate data - required by PySystemTrade base class"""
        # Both ETFs are USD-denominated, so for USD/USD pairs return 1.0
        if currency1 == "USD" and currency2 == "USD":
            # Create a time series of 1.0 (no FX conversion needed)
            fx_rates = pd.Series(1.0, index=self.ivv_data.index, name='fx_rate')
            return fx_rates
        else:
            raise Exception(f"FX pair {currency1}/{currency2} not supported - only USD ETFs available")

    def get_instrument_list(self):
        """Return list of available instruments"""
        return ["IVV", "HYD"]

    def get_value_of_block_price_move(self, instrument):
        """Get value of one point move - for ETFs, this is 1.0"""
        return 1.0

    def get_raw_cost_data(self, instrument):
        """Get cost data - simple cost structure for ETFs"""
        return {'price_slippage': 0.01, 'value_of_block_price_move': 1.0, 'block_trade_size': 1.0}

    def get_instrument_currency(self, instrument):
        """Get instrument currency - both ETFs are USD"""
        return "USD"


class ETFTradingSystemDirect:
    def __init__(self, etf_symbols, ewmac_fast=8, ewmac_slow=32):
        self.etf_symbols = etf_symbols
        self.ewmac_fast = ewmac_fast
        self.ewmac_slow = ewmac_slow
        self.data_source = DirectETFData()
        self.system = None

    def create_system(self):
        """Create PySystemTrade system using direct ETF data"""

        # Create EWMAC momentum rule
        ewmac_rule = TradingRule(
            ewmac,
            ["rawdata.get_daily_prices", "rawdata.daily_returns_volatility"],
            dict(Lfast=self.ewmac_fast, Lslow=self.ewmac_slow)
        )

        # System configuration
        config_dict = {
            "trading_rules": {"ewmac_momentum": ewmac_rule},
            "instruments": self.etf_symbols,
            "forecast_weights": {"ewmac_momentum": 1.0},
            "instrument_weights": {etf: 1.0 / len(self.etf_symbols) for etf in self.etf_symbols}
        }

        # Create system with our custom data source
        self.system = futures_system(data=self.data_source, config=Config(config_dict))
        return self.system

    def get_latest_data(self):
        """Get latest price and volatility data"""
        results = {}

        for etf in self.etf_symbols:
            prices = self.data_source.daily_prices(etf)
            vol = self.data_source.daily_returns_volatility(etf)

            # Fix: Extract scalar values properly
            latest_price = prices.iloc[-1]
            if isinstance(latest_price, pd.Series):
                latest_price = latest_price.iloc[0]

            latest_vol = vol.iloc[-1]
            if isinstance(latest_vol, pd.Series):
                latest_vol = latest_vol.iloc[0]

            results[etf] = {
                "latest_price": float(latest_price),
                "latest_volatility": float(latest_vol)
            }

        return results

    def get_performance(self):
        """Get system performance metrics"""
        if not self.system:
            self.create_system()

        portfolio = self.system.accounts.portfolio()
        results = {
            "portfolio_sharpe": portfolio.sharpe(),
            "individual_performance": {}
        }

        # Individual ETF performance
        for etf in self.etf_symbols:
            individual_perf = self.system.accounts.pandl_for_instrument(etf)
            results["individual_performance"][etf] = individual_perf.sharpe()

        return results

    def get_forecasts(self):
        """Get latest trading forecasts"""
        if not self.system:
            self.create_system()

        forecasts = {}
        for etf in self.etf_symbols:
            forecast = self.system.rules.get_raw_forecast(etf, "ewmac_momentum")
            forecasts[etf] = forecast.iloc[-1]

        return forecasts


if __name__ == "__main__":
    print("=== Direct ETF Trading System ===")

    # Create ETF system using direct data (bypasses CSV entirely)
    etf_system = ETFTradingSystemDirect(["IVV", "HYD"])

    # Show latest market data
    print("\n=== Latest Market Data ===")
    latest_data = etf_system.get_latest_data()
    for etf, data in latest_data.items():
        print(f"{etf}: ${data['latest_price']:.2f}, Vol: {data['latest_volatility']:.1%}")

    # Run trading system
    try:
        print("\n=== System Performance ===")
        performance = etf_system.get_performance()

        print(f"Portfolio Sharpe Ratio: {performance['portfolio_sharpe']:.2f}")

        for etf, sharpe in performance['individual_performance'].items():
            print(f"{etf} Sharpe: {sharpe:.2f}")

        print("\n=== Latest Trading Signals ===")
        forecasts = etf_system.get_forecasts()
        for etf, forecast in forecasts.items():
            signal = "BUY" if forecast > 0 else "SELL"
            print(f"{etf}: {forecast:.2f} ({signal})")

        print("\n🎉 Your ETF systematic trading system is working!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
