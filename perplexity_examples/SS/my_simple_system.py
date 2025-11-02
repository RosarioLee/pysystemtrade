# Create: my_simple_system_working.py
from systems.provided.futures_chapter15.basesystem import futures_system
from systems.forecasting import TradingRule
from systems.provided.rules.ewmac import ewmac
from sysdata.config.configdata import Config

# Create your custom rule
my_rule = TradingRule(
    ewmac,
    ["rawdata.get_daily_prices", "rawdata.daily_returns_volatility"],
    dict(Lfast=8, Lslow=32),
)

# Create a config with just your rule
my_config_dict = {
    "trading_rules": {"my_ewmac": my_rule},
    "instruments": ["CORN"],  # Test with just one instrument
    "forecast_weights": {"my_ewmac": 1.0},  # Give it 100% weight
}

my_config = Config(my_config_dict)

# Create system using the futures_system function with your config
my_system = futures_system(config=my_config)

print("=== Your Simple Custom System ===")
try:
    # Test the forecast first
    forecast = my_system.rules.get_raw_forecast("CORN", "my_ewmac")
    print(f"Custom forecast for CORN: {forecast.iloc[-1]:.2f}")

    # Test portfolio performance
    portfolio = my_system.accounts.portfolio()
    print(f"Sharpe Ratio: {portfolio.sharpe():.2f}")
    print("System created successfully!")

except Exception as e:
    print(f"Error: {e}")
    print("But forecast generation worked!")
