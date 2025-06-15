# Create: etf_system_working.py
from systems.provided.futures_chapter15.basesystem import futures_system
from systems.forecasting import TradingRule
from systems.provided.rules.ewmac import ewmac
from sysdata.config.configdata import Config
import pandas as pd

# Verify your ETF data loaded correctly
print("=== Verifying ETF Data ===")
ivv_data = pd.read_csv("data/futures/multiple_prices_csv/IVV.csv", index_col=0, parse_dates=True)
hyd_data = pd.read_csv("data/futures/multiple_prices_csv/HYD.csv", index_col=0, parse_dates=True)

print(f"IVV data: {len(ivv_data)} days, latest: ${ivv_data['PRICE'].iloc[-1]:.2f}")
print(f"HYD data: {len(hyd_data)} days, latest: ${hyd_data['PRICE'].iloc[-1]:.2f}")

# Create your proven EWMAC rule
my_rule = TradingRule(ewmac, ["rawdata.get_daily_prices", "rawdata.daily_returns_volatility"], dict(Lfast=8, Lslow=32))

# Configure system for ETFs
my_config_dict = {
    "trading_rules": {"my_ewmac": my_rule},
    "instruments": ["IVV", "HYD"],  # Your two ETFs
    "forecast_weights": {"my_ewmac": 1.0}
}

print("\n=== Creating ETF System ===")
my_etf_system = futures_system(config=Config(my_config_dict))

# Test the system
portfolio = my_etf_system.accounts.portfolio()
print(f"ETF System Sharpe Ratio: {portfolio.sharpe():.2f}")

# Analyze individual ETF performance
for etf in ["IVV", "HYD"]:
    individual_performance = my_etf_system.accounts.pandl_for_instrument(etf)
    print(f"{etf} Sharpe: {individual_performance.sharpe():.2f}")

print("\n🎉 Your first ETF systematic trading system is working!")
