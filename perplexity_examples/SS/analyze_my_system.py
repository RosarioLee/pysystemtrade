# Create: analyze_my_system.py
from systems.provided.futures_chapter15.basesystem import futures_system
from systems.forecasting import TradingRule
from systems.provided.rules.ewmac import ewmac
from sysdata.config.configdata import Config

# Recreate your successful system
my_rule = TradingRule(
    ewmac,
    ["rawdata.get_daily_prices", "rawdata.daily_returns_volatility"],
    dict(Lfast=8, Lslow=32),
)
my_config_dict = {
    "trading_rules": {"my_ewmac": my_rule},
    "instruments": ["CORN", "EUROSTX", "US10"],
    "forecast_weights": {"my_ewmac": 1.0},
}
my_system = futures_system(config=Config(my_config_dict))

print("=== Your System Analysis ===")
print(f"System Sharpe Ratio: {my_system.accounts.portfolio().sharpe():.2f}")

# Analyze individual instrument performance
for instrument in ["CORN", "EUROSTX", "US10"]:
    individual_performance = my_system.accounts.pandl_for_instrument(instrument)
    print(f"{instrument} Sharpe: {individual_performance.sharpe():.2f}")

print("\n=== Congratulations! ===")
print("You've built a professional systematic trading system!")
print("Ready to adapt this for equity/ETF trading?")
