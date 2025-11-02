from systems.provided.futures_chapter15.basesystem import futures_system
from matplotlib.pyplot import show

# Create the system with provided data
system = futures_system()

# Check Sharpe ratio
print("Sharpe Ratio:", system.accounts.portfolio().sharpe())

# Plot performance curve
system.accounts.portfolio().curve().plot()
show()

# Get all trading rules
rules = system.rules.trading_rules()
print("Available rules:", list(rules.keys()))
# Examine EWMAC variations
for rule_name in rules.keys():
    rule = rules[rule_name]
    print(f"{rule_name}: {rule}")

instruments = system.data.get_instrument_list()[:5]  # First 5 instruments
print(f"instruments: {instruments}")
for instrument in instruments:
    returns = system.data.daily_returns(instrument)
    print(f"{instrument} recent returns:")
    print(returns.tail())
