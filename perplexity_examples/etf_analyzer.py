# etf_analyzer.py - Analyze your ETF system performance
from perplexity_examples.SS.etf_trading_system import ETFTradingSystem


def analyze_etf_system(etf_symbols):
    """Comprehensive analysis of ETF trading system"""

    system = ETFTradingSystem(etf_symbols)
    system.create_system()

    print("=== ETF System Analysis ===")

    # Performance metrics
    performance = system.get_performance()
    print(f"Portfolio Sharpe: {performance['portfolio_sharpe']:.2f}")

    # Individual forecasts
    print("\n=== Latest Forecasts ===")
    for etf in etf_symbols:
        forecast = system.system.rules.get_raw_forecast(etf, "ewmac_momentum")
        print(f"{etf} forecast: {forecast.iloc[-1]:.2f}")

    # Portfolio curve
    portfolio = system.system.accounts.portfolio()
    portfolio_curve = portfolio.percent.curve()

    print(f"\nPortfolio Stats:")
    print(f"Annual Return: {portfolio_curve.pct_change().mean() * 252 * 100:.1f}%")
    print(f"Annual Volatility: {portfolio_curve.pct_change().std() * (252 ** 0.5) * 100:.1f}%")

    return system


if __name__ == "__main__":
    # Analyze your ETF system
    etf_system = analyze_etf_system(["IVV", "HYD"])
