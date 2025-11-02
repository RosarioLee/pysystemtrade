# Create: my_custom_system_fixed.py
from systems.provided.futures_chapter15.basesystem import futures_system
from systems.forecasting import TradingRule
from systems.provided.rules.ewmac import ewmac

# Start with the existing system
system = futures_system()

# Let's first see how existing rules are structured
existing_rule = system.rules.trading_rules()["ewmac16_64"]
print("=== Existing Rule Structure ===")
print(f"Existing rule: {existing_rule}")
print(f"Rule type: {type(existing_rule)}")

# Create a custom rule the correct way
my_custom_rule = TradingRule(
    ewmac,  # function as first argument, not keyword
    ["rawdata.get_daily_prices", "rawdata.daily_returns_volatility"],
    dict(Lfast=8, Lslow=32),  # other_args as dict
)

print(f"\n=== Your Custom Rule ===")
print(f"Custom rule created: {my_custom_rule}")

# Test it directly with the system
instrument = "CORN"
try:
    # Get the raw forecast using the custom parameters
    forecast = ewmac(
        system.rawdata.get_daily_prices(instrument),
        system.rawdata.daily_returns_volatility(instrument),
        Lfast=8,
        Lslow=32,
    )

    print(f"\nCustom EWMAC(8,32) forecast for {instrument}:")
    print(f"Latest value: {forecast.iloc[-1]:.2f}")
    print(f"Last 5 values:")
    print(forecast.tail())

except Exception as e:
    print(f"Error: {e}")
