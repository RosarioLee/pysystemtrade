# Create: etf_system_momentum_only.py
from systems.provided.futures_chapter15.basesystem import futures_system
from systems.forecasting import TradingRule
from systems.provided.rules.ewmac import ewmac
from sysdata.config.configdata import Config

# Create your proven EWMAC rule (no carry needed)
my_rule = TradingRule(
    ewmac,
    ["rawdata.get_daily_prices", "rawdata.daily_returns_volatility"],
    dict(Lfast=8, Lslow=32),
)

# Configure system for ETFs - MOMENTUM ONLY
my_config_dict = {
    "trading_rules": {"my_ewmac": my_rule},  # Only momentum, no carry
    "instruments": ["IVV", "HYD"],
    "forecast_weights": {"my_ewmac": 1.0},
}

print("=== ETF Momentum-Only System ===")
my_etf_system = futures_system(config=Config(my_config_dict))

try:
    # Test the system
    portfolio = my_etf_system.accounts.portfolio()
    print(f"ETF System Sharpe Ratio: {portfolio.sharpe():.2f}")

    # Analyze individual ETF performance
    for etf in ["IVV", "HYD"]:
        individual_performance = my_etf_system.accounts.pandl_for_instrument(etf)
        print(f"{etf} Sharpe: {individual_performance.sharpe():.2f}")

    print("\n🎉 ETF momentum system working without carry!")

except Exception as e:
    print(f"Error: {e}")
