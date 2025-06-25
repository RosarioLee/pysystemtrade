# scalable_etf_system.py - FIXED class structure
import yfinance as yf
import pandas as pd
import numpy as np
import yaml
import os


class SimpleConfig:
    """Simple config wrapper for YAML data"""

    def __init__(self, config_data):
        self.data = config_data

    @property
    def instruments(self):
        return self.data.get('instruments', [])

    @property
    def instrument_weights(self):
        return self.data.get('instrument_weights', {})

    @property
    def percentage_vol_target(self):
        return self.data.get('percentage_vol_target', 12.0)

    @property
    def trading_rules(self):
        return self.data.get('trading_rules', {})


class ScalableETFSystem:
    def __init__(self):
        """Initialize with direct YAML configuration"""
        # Use direct path to your YAML file
        config_file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),  # Go up to pysystemtrade
            "private", "etf_system", "config.yaml"
        )

        try:
            with open(config_file_path, 'r') as file:
                self.config_data = yaml.safe_load(file)
            print(f"✅ Configuration loaded from: {config_file_path}")

            # Create simple config object
            self.config = SimpleConfig(self.config_data)

        except FileNotFoundError as e:
            print(f"❌ Config file not found: {config_file_path}")
            print("Make sure config.yaml exists in private/etf_system/ directory")
            raise
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            raise

        self.etf_data = {}

    def download_etf_data(self, start_date="2020-01-01"):
        """Download data for all ETFs in configuration"""
        instruments = self.config.instruments

        print(f"=== Downloading {len(instruments)} ETFs ===")
        for symbol in instruments:
            print(f"Downloading {symbol}...")
            try:
                data = yf.download(symbol, start=start_date, auto_adjust=False)['Adj Close']
                self.etf_data[symbol] = data
                print(f"✅ {symbol}: {len(data)} days")
            except Exception as e:
                print(f"❌ {symbol}: Error - {e}")

        return self.etf_data

    def calculate_ewmac_forecast(self, prices, fast=8, slow=32):
        """Calculate EWMAC forecast - same as your working system"""
        ewma_fast = prices.ewm(span=fast).mean()
        ewma_slow = prices.ewm(span=slow).mean()
        raw_forecast = (ewma_fast - ewma_slow) / prices.rolling(32).std()
        scaled_forecast = raw_forecast * 2.5
        capped_forecast = np.clip(scaled_forecast, -20, 20)
        return capped_forecast.dropna()

    def safe_sharpe(self, returns_series, name="Unknown"):
        """Calculate Sharpe ratio - same as your working system"""
        if len(returns_series) == 0:
            print(f"Warning: No returns data for {name}")
            return np.nan

        returns_array = returns_series.values if isinstance(returns_series, pd.Series) else np.array(returns_series)
        std_val = np.std(returns_array)
        mean_val = np.mean(returns_array)

        if std_val == 0:
            print(f"Warning: Zero variance in returns for {name}")
            return np.nan

        sharpe = mean_val / std_val * np.sqrt(252)
        return float(sharpe)

    def run_system(self):
        """Run complete system using YAML configuration"""
        print("=== Scalable ETF System (YAML Configuration) ===")
        print(f"Instruments: {self.config.instruments}")
        print(f"Instrument weights: {self.config.instrument_weights}")
        print(f"Vol target: {self.config.percentage_vol_target}%")

        # Download data
        self.download_etf_data()

        # Calculate forecasts and performance for each instrument
        print(f"\n=== Calculating Forecasts ===")
        forecasts = {}
        positions = {}
        performance = {}

        for instrument in self.config.instruments:
            if instrument not in self.etf_data:
                continue

            prices = self.etf_data[instrument]

            # Use your working EWMAC calculation
            forecast = self.calculate_ewmac_forecast(prices, fast=8, slow=32)
            forecasts[instrument] = forecast

            # Calculate position (same as your working system)
            returns = prices.pct_change().dropna()
            volatility = returns.rolling(30).std() * np.sqrt(252)

            # Align data
            common_dates = forecast.index.intersection(volatility.index)
            if len(common_dates) > 0:
                normalized_forecast = forecast.loc[common_dates] / 10.0
                vol_target = self.config.percentage_vol_target / 100.0
                vol_scalar = vol_target / volatility.loc[common_dates]
                position = normalized_forecast * vol_scalar
                positions[instrument] = position

                # Calculate strategy returns
                strategy_returns = (position.shift(1) * returns.loc[common_dates]).dropna()
                sharpe = self.safe_sharpe(strategy_returns, instrument)
                performance[instrument] = sharpe

        # Display results
        print(f"\n=== Performance Results ===")
        for instrument in performance:
            sharpe = performance[instrument]
            print(f"{instrument} Sharpe Ratio: {sharpe:.2f}")

        print(f"\n=== Latest Signals ===")
        for instrument in forecasts:
            if len(forecasts[instrument]) > 0:
                # FIX: Ensure we get a scalar value
                latest_forecast_series = forecasts[instrument].iloc[-1]

                # Convert Series to scalar if needed
                if isinstance(latest_forecast_series, pd.Series):
                    latest_forecast = float(latest_forecast_series.iloc[0]) if len(latest_forecast_series) > 0 else 0.0
                else:
                    latest_forecast = float(latest_forecast_series)

                signal = "BUY" if latest_forecast > 0 else "SELL"
                print(f"{instrument}: {latest_forecast:.2f} ({signal})")

        print(f"\n=== Current Positions ===")
        for instrument in positions:
            if len(positions[instrument]) > 0:
                # FIX: Ensure scalar value for positions too
                latest_position_raw = positions[instrument].iloc[-1]
                latest_position = float(np.asarray(latest_position_raw).flatten()[-1])
                print(f"{instrument}: {latest_position:.3f}")

        # Calculate portfolio performance
        if len(performance) > 1:
            avg_sharpe = np.mean(list(performance.values()))
            print(f"\n=== Portfolio Summary ===")
            print(f"Average Sharpe Ratio: {avg_sharpe:.2f}")
            print(f"Number of instruments: {len(performance)}")

        print(f"\n🎉 Scalable ETF system running with {len(self.config.instruments)} instruments!")

        return forecasts, positions, performance


if __name__ == "__main__":
    try:
        system = ScalableETFSystem()
        forecasts, positions, performance = system.run_system()
    except Exception as e:
        print(f"Error: {e}")
        print(f"\nCheck that your config.yaml file exists in:")
        print(f"pysystemtrade/private/etf_system/config.yaml")
