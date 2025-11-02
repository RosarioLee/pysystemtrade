# Create: diversified_system.py
from systems.provided.futures_chapter15.basesystem import futures_system
from systems.forecasting import TradingRule
from systems.provided.rules.ewmac import ewmac
from sysdata.config.configdata import Config

# Create two different custom rules
rule1 = TradingRule(
    ewmac,
    ["rawdata.get_daily_prices", "rawdata.daily_returns_volatility"],
    dict(Lfast=8, Lslow=32),
)
rule2 = TradingRule(
    ewmac,
    ["rawdata.get_daily_prices", "rawdata.daily_returns_volatility"],
    dict(Lfast=16, Lslow=64),
)

my_config_dict = {
    "trading_rules": {"fast_ewmac": rule1, "slow_ewmac": rule2},
    "instruments": ["CORN"],
    "forecast_weights": {"fast_ewmac": 0.5, "slow_ewmac": 0.5},  # Equal weights
}

my_system = futures_system(config=Config(my_config_dict))

print("=== Diversified Custom System ===")
portfolio = my_system.accounts.portfolio()
print(f"Sharpe Ratio: {portfolio.sharpe():.2f}")
print("Two-rule system created!")
