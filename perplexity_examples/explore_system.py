from systems.provided.futures_chapter15.basesystem import futures_system

# Create the system
system = futures_system()

# Get the portfolio performance
portfolio = system.accounts.portfolio()

print("=== System Performance ===")
print(f"Sharpe Ratio: {portfolio.sharpe():.2f}")

# Get stats the safe way
stats = portfolio.percent.stats()
print(f"Stats available: {len(stats[0])} metrics")

# Show first few stats safely
for i, (name, value) in enumerate(stats[0][:5]):
    print(f"{name}: {value}")