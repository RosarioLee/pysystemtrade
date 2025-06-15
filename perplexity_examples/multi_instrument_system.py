# Create: multi_instrument_system.py
from systems.provided.futures_chapter15.basesystem import futures_system
from systems.forecasting import TradingRule
from systems.provided.rules.ewmac import ewmac
from sysdata.config.configdata import Config

# Your best single rule
my_rule = TradingRule(ewmac, ["rawdata.get_daily_prices", "rawdata.daily_returns_volatility"], dict(Lfast=8, Lslow=32))

my_config_dict = {
    "trading_rules": {"my_ewmac": my_rule},
    "instruments": ["CORN", "EUROSTX", "US10"],  # 3 different instruments
    "forecast_weights": {"my_ewmac": 1.0}
}

my_system = futures_system(config=Config(my_config_dict))

print("=== Multi-Instrument System ===")
portfolio = my_system.accounts.portfolio()
print(f"Sharpe Ratio: {portfolio.sharpe():.2f}")
print("Three-instrument system created!")
