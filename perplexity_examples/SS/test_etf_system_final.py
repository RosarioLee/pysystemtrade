# Create: test_etf_system_final.py
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
from systems.provided.futures_chapter15.basesystem import futures_system
from systems.forecasting import TradingRule
from systems.provided.rules.ewmac import ewmac
from sysdata.config.configdata import Config

print("=== Testing ETF Data Recognition ===")

# Test if PySystemTrade can now find your ETFs
data_source = csvFuturesSimData()
available_instruments = data_source.get_instrument_list()

ivv_found = "IVV" in available_instruments
hyd_found = "HYD" in available_instruments

print(f"IVV found: {ivv_found}")
print(f"HYD found: {hyd_found}")

if ivv_found and hyd_found:
    print("🎉 Both ETFs found! Creating system...")

    # Create your proven EWMAC rule
    my_rule = TradingRule(ewmac, ["rawdata.get_daily_prices", "rawdata.daily_returns_volatility"],
                          dict(Lfast=8, Lslow=32))

    # Configure system for ETFs
    my_config_dict = {
        "trading_rules": {"my_ewmac": my_rule},
        "instruments": ["IVV", "HYD"],
        "forecast_weights": {"my_ewmac": 1.0}
    }

    print("\n=== Creating ETF Momentum System ===")
    my_etf_system = futures_system(config=Config(my_config_dict))

    # Test the system
    portfolio = my_etf_system.accounts.portfolio()
    print(f"ETF System Sharpe Ratio: {portfolio.sharpe():.2f}")

    # Analyze individual ETF performance
    for etf in ["IVV", "HYD"]:
        individual_performance = my_etf_system.accounts.pandl_for_instrument(etf)
        print(f"{etf} Sharpe: {individual_performance.sharpe():.2f}")

    print("\n🎉 Your ETF systematic trading system is working!")

else:
    print("❌ ETFs still not found. Need to debug further.")
    print(f"Available instruments: {available_instruments[:10]}...")
