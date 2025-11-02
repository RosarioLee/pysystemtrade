# scalable_etf_system.py - FIXED class structure
import yfinance as yf
import pandas as pd
import numpy as np
import yaml
import os
import matplotlib.pyplot as plt
from systems.provided.futures_chapter15.basesystem import futures_system
from sysdata.config.configdata import Config
import sys
import traceback


class SimpleConfig:
    """Simple config wrapper for YAML data"""

    def __init__(self, config_data):
        self.data = config_data

    @property
    def instruments(self):
        return self.data.get("instruments", [])

    @property
    def instrument_weights(self):
        return self.data.get("instrument_weights", {})

    @property
    def percentage_vol_target(self):
        return self.data.get("percentage_vol_target", 12.0)

    @property
    def trading_rules(self):
        return self.data.get("trading_rules", {})


class ScalableETFSystem:
    def __init__(self):
        """Initialize with direct YAML configuration"""
        # Use direct path to your YAML file
        config_file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),  # Go up to pysystemtrade
            "private",
            "etf_system",
            "config.yaml",
        )

        try:
            with open(config_file_path, "r") as file:
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
                data = yf.download(symbol, start=start_date, auto_adjust=False)[
                    "Adj Close"
                ]
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

        returns_array = (
            returns_series.values
            if isinstance(returns_series, pd.Series)
            else np.array(returns_series)
        )
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
                strategy_returns = (
                    position.shift(1) * returns.loc[common_dates]
                ).dropna()
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
                    latest_forecast = (
                        float(latest_forecast_series.iloc[0])
                        if len(latest_forecast_series) > 0
                        else 0.0
                    )
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

        print(
            f"\n🎉 Scalable ETF system running with {len(self.config.instruments)} instruments!"
        )

        return forecasts, positions, performance

    def create_pysystemtrade_system(self):
        """Create full PySystemTrade system with dynamic IDM"""

        # Convert your config to PySystemTrade format
        pst_config_dict = {
            "instruments": self.config.instruments,
            "instrument_weights": dict(self.config.instrument_weights),
            "percentage_vol_target": self.config.percentage_vol_target,
            # Enable dynamic IDM (from your config)
            "use_instrument_div_mult_estimates": True,
            "use_instrument_weight_estimates": True,
            # IDM estimation parameters
            "instrument_div_mult_estimate": {
                "date_method": "expanding",
                "rollyears": 3,
                "frequency": "W",
                "using_exponent": True,
                "ew_lookback": 250,
                "ewma_span": 125,  # Smoothing parameter
                "dm_max": 2.5,  # Maximum IDM cap
            },
            # Trading rules
            "trading_rules": {
                "ewmac_fast": {
                    "function": "systems.provided.rules.ewmac.ewmac",
                    "data": [
                        "rawdata.get_daily_prices",
                        "rawdata.daily_returns_volatility",
                    ],
                    "other_args": {"Lfast": 8, "Lslow": 32},
                }
            },
            "forecast_weights": {"ewmac_fast": 1.0},
        }

        # Create PySystemTrade system
        pst_config = Config(pst_config_dict)
        system = futures_system(config=pst_config)

        return system

    def plot_idm_analysis(self):
        """Plot comprehensive IDM analysis"""

        print("\n=== Creating PySystemTrade System for IDM Analysis ===")

        try:
            # Create full PySystemTrade system
            system = self.create_pysystemtrade_system()

            # Plot IDM over time
            print("Plotting Instrument Diversification Multiplier...")

            plt.figure(figsize=(15, 10))

            # Plot 1: Overall portfolio IDM
            plt.subplot(2, 2, 1)
            idm_series = system.portfolio.get_instrument_diversification_multiplier()
            idm_series.plot(title="Portfolio IDM Over Time")
            plt.ylabel("IDM Value")
            plt.grid(True)

            # Plot 2: IDM for top instruments
            plt.subplot(2, 2, 2)
            top_instruments = ["IVV", "VGK", "IAU", "BWX"]  # Your largest allocations
            for instrument in top_instruments:
                if instrument in system.get_instrument_list():
                    inst_idm = (
                        system.portfolio.get_instrument_diversification_multiplier(
                            instrument
                        )
                    )
                    inst_idm.plot(label=instrument, alpha=0.7)
            plt.title("IDM by Major Instruments")
            plt.ylabel("IDM Value")
            plt.legend()
            plt.grid(True)

            # Plot 3: Portfolio correlation over time
            plt.subplot(2, 2, 3)
            # Calculate implied correlation from IDM (IDM = 1/sqrt(portfolio_correlation))
            portfolio_corr = 1.0 / (idm_series**2)
            portfolio_corr.plot(title="Implied Portfolio Correlation", color="red")
            plt.ylabel("Average Correlation")
            plt.grid(True)

            # Plot 4: IDM statistics
            plt.subplot(2, 2, 4)
            idm_rolling_mean = idm_series.rolling(252).mean()  # 1-year rolling average
            idm_series.plot(label="Daily IDM", alpha=0.5)
            idm_rolling_mean.plot(label="1-Year Average", linewidth=2)
            plt.title("IDM with Rolling Average")
            plt.ylabel("IDM Value")
            plt.legend()
            plt.grid(True)

            plt.tight_layout()
            plt.show()

            # Print IDM statistics
            print(f"\n=== IDM Statistics ===")
            print(f"Current IDM: {idm_series.iloc[-1]:.3f}")
            print(f"Average IDM: {idm_series.mean():.3f}")
            print(f"Min IDM: {idm_series.min():.3f}")
            print(f"Max IDM: {idm_series.max():.3f}")
            print(f"IDM Volatility: {idm_series.std():.3f}")

            # Theoretical bounds
            n_instruments = len(self.config.instruments)
            max_theoretical_idm = np.sqrt(n_instruments)
            print(
                f"Max Theoretical IDM ({n_instruments} instruments): {max_theoretical_idm:.3f}"
            )
            print(
                f"Current vs Max: {(idm_series.iloc[-1] / max_theoretical_idm * 100):.1f}%"
            )

            return system, idm_series

        except Exception as e:
            print(f"Error creating PySystemTrade system: {e}")
            print("This might be due to missing data or configuration issues")
            return None, None

    def run_comprehensive_analysis(self):
        """Run both your custom system and PySystemTrade IDM analysis"""

        # Run your existing system
        print("=== Running Custom ETF System ===")
        forecasts, positions, performance = self.run_system()

        # Run IDM analysis
        print("\n=== Running IDM Analysis ===")
        system, idm_series = self.plot_idm_analysis()

        if system is not None:
            # Compare with PySystemTrade results
            print(f"\n=== PySystemTrade vs Custom System Comparison ===")

            # Get PySystemTrade portfolio performance
            pst_portfolio = system.accounts.portfolio()
            pst_sharpe = pst_portfolio.sharpe()

            # Your custom system average Sharpe
            custom_avg_sharpe = np.mean(list(performance.values()))

            print(f"PySystemTrade Portfolio Sharpe: {pst_sharpe:.2f}")
            print(f"Custom System Average Sharpe: {custom_avg_sharpe:.2f}")

        return forecasts, positions, performance, system, idm_series

    def extract_actual_idm_from_system(self):
        """Extract the actual IDM time series used during backtest"""
        print("=== Extracting Actual IDM from PySystemTrade System ===")

        try:
            # Create the full PySystemTrade system
            pst_system = self.create_pysystemtrade_system()

            # Extract the actual IDM time series used in backtest
            actual_idm_series = (
                pst_system.portfolio.get_instrument_diversification_multiplier()
            )

            print(f"✅ Successfully extracted actual IDM time series")
            print(f"IDM Series Length: {len(actual_idm_series)} data points")
            print(
                f"Date Range: {actual_idm_series.index[0]} to {actual_idm_series.index[-1]}"
            )

            return actual_idm_series, pst_system

        except Exception as e:
            print(f"❌ Error extracting IDM: {e}")
            return None, None

    def analyze_actual_idm_performance(self):
        """Comprehensive analysis of actual IDM used in backtest"""
        print("=== Analyzing Actual IDM Performance ===")

        # Extract actual IDM
        idm_series, pst_system = self.extract_actual_idm_from_system()

        if idm_series is None:
            print("Cannot analyze IDM - extraction failed")
            return None

        # Get additional system data for analysis
        try:
            # Get instrument weights time series
            instrument_weights = pst_system.portfolio.get_instrument_weights()

            # Get portfolio positions (before IDM application)
            positions_before_idm = {}
            positions_after_idm = {}

            for instrument in self.config.instruments:
                try:
                    pos_before = pst_system.portfolio.get_notional_position_without_idm(
                        instrument
                    )
                    pos_after = (
                        pst_system.portfolio.get_notional_position_before_risk_scaling(
                            instrument
                        )
                    )
                    positions_before_idm[instrument] = pos_before
                    positions_after_idm[instrument] = pos_after
                except:
                    continue

            # Create comprehensive analysis
            analysis_results = self.create_idm_analysis_plots(
                idm_series,
                instrument_weights,
                positions_before_idm,
                positions_after_idm,
                pst_system,
            )

            return analysis_results

        except Exception as e:
            print(f"Error during IDM analysis: {e}")
            return None

    def extract_current_idm_simple(self):
        """Extract the actual IDM value being used, even if dynamic calculation fails"""
        print("=== Extracting Current IDM (Simple Method) ===")

        try:
            # Create basic PySystemTrade system
            pst_system = self.create_pysystemtrade_system()

            # Try to get the current IDM value being used in the system
            # This should work even if the time series calculation fails
            try:
                # Method 1: Try to get the latest IDM value directly
                current_idm = pst_system.portfolio.get_instrument_diversification_multiplier().iloc[
                    -1
                ]
                print(f"✅ Current IDM from time series: {current_idm:.4f}")
                return current_idm, "dynamic"

            except Exception as e1:
                print(f"⚠️  Dynamic IDM failed: {e1}")

                # Method 2: Try to get static IDM from config
                try:
                    static_idm = pst_system.config.instrument_div_mult
                    print(f"✅ Static IDM from config: {static_idm:.4f}")
                    return static_idm, "static_config"

                except Exception as e2:
                    print(f"⚠️  Config IDM failed: {e2}")

                    # Method 3: Try default IDM calculation (sqrt of instruments)
                    try:
                        n_instruments = len(self.config.instruments)
                        default_idm = pst_system.config.get_element_or_default(
                            "instrument_div_mult", np.sqrt(n_instruments)
                        )
                        print(f"✅ Default IDM calculation: {default_idm:.4f}")
                        return default_idm, "calculated_default"

                    except Exception as e3:
                        print(f"⚠️  Default calculation failed: {e3}")

                        # Method 4: Manual fallback
                        fallback_idm = 1.0  # No diversification benefit
                        print(f"🔄 Using fallback IDM: {fallback_idm:.4f}")
                        return fallback_idm, "fallback"

        except Exception as e:
            print(f"❌ Could not create system: {e}")
            return None, "failed"

    def get_portfolio_level_metrics(self):
        """Get key portfolio-level metrics including actual IDM used"""
        print("=== Portfolio Level Metrics ===")

        # Get the actual IDM being used
        current_idm, idm_source = self.extract_current_idm_simple()

        if current_idm is not None:
            print(f"📊 Current IDM: {current_idm:.4f} (source: {idm_source})")

            # Calculate theoretical maximum
            n_instruments = len(self.config.instruments)
            theoretical_max = np.sqrt(n_instruments)
            efficiency = (current_idm / theoretical_max) * 100

            print(f"📈 Theoretical Max IDM: {theoretical_max:.4f}")
            print(f"🎯 Diversification Efficiency: {efficiency:.1f}%")

            # Interpret the IDM source
            if idm_source == "dynamic":
                print("✅ Using dynamic IDM (time-varying)")
            elif idm_source == "static_config":
                print("⚠️  Using static IDM from configuration")
            elif idm_source == "calculated_default":
                print("🔄 Using calculated default IDM")
            else:
                print("❌ Using fallback IDM (no diversification)")

            return {
                "current_idm": current_idm,
                "idm_source": idm_source,
                "theoretical_max": theoretical_max,
                "efficiency_pct": efficiency,
                "n_instruments": n_instruments,
            }

        return None

    def analyze_idm_vs_performance(self, performance):
        """Analyze relationship between IDM and your performance"""
        print("=== IDM vs Performance Analysis ===")

        idm_metrics = self.get_portfolio_level_metrics()

        if idm_metrics and performance:
            current_idm = idm_metrics["current_idm"]
            avg_sharpe = np.mean(list(performance.values()))

            print(f"\n📊 Portfolio Analysis:")
            print(f"   Current IDM: {current_idm:.4f}")
            print(f"   Average Sharpe: {avg_sharpe:.3f}")
            print(
                f"   Risk-Adjusted Performance per IDM Unit: {avg_sharpe / current_idm:.3f}"
            )

            # Calculate what your Sharpe would be with perfect diversification
            theoretical_max = idm_metrics["theoretical_max"]
            potential_sharpe = avg_sharpe * (theoretical_max / current_idm)
            print(
                f"   Potential Sharpe with Perfect Diversification: {potential_sharpe:.3f}"
            )

            return {
                "current_performance": avg_sharpe,
                "current_idm": current_idm,
                "performance_per_idm": avg_sharpe / current_idm,
                "potential_performance": potential_sharpe,
                "diversification_gap": potential_sharpe - avg_sharpe,
            }

        return None

    def extract_current_idm_simple_corrected(self):
        """Extract IDM with proper Robert Carver 2.5 cap"""
        print("=== Extracting Current IDM (Corrected Method) ===")

        try:
            pst_system = self.create_pysystemtrade_system()

            try:
                # Method 1: Try dynamic IDM
                current_idm = pst_system.portfolio.get_instrument_diversification_multiplier().iloc[
                    -1
                ]
                print(f"✅ Current IDM from time series: {current_idm:.4f}")
                return current_idm, "dynamic"

            except Exception as e1:
                print(f"⚠️  Dynamic IDM failed: {e1}")

                try:
                    # Method 2: Try config IDM
                    static_idm = pst_system.config.instrument_div_mult
                    print(f"✅ Static IDM from config: {static_idm:.4f}")
                    return static_idm, "static_config"

                except Exception as e2:
                    print(f"⚠️  Config IDM failed: {e2}")

                    # Method 3: CORRECTED - Use Robert Carver's 2.5 cap
                    n_instruments = len(self.config.instruments)
                    theoretical_max = np.sqrt(n_instruments)
                    robert_carver_idm = min(2.5, theoretical_max)  # KEY FIX!

                    print(f"📊 Theoretical Max IDM: {theoretical_max:.4f}")
                    print(f"🎯 Robert Carver Capped IDM: {robert_carver_idm:.4f}")
                    print(f"✅ Using Robert Carver's IDM cap methodology")

                    return robert_carver_idm, "robert_carver_capped"

        except Exception as e:
            print(f"❌ Could not create system: {e}")
            return None, "failed"

    def get_portfolio_level_metrics_corrected(self):
        """Get corrected portfolio metrics with proper IDM cap"""
        print("=== Portfolio Level Metrics (Corrected) ===")

        # Get the actual IDM being used
        current_idm, idm_source = self.extract_current_idm_simple_corrected()

        if current_idm is not None:
            print(f"📊 Current IDM: {current_idm:.4f} (source: {idm_source})")

            # Calculate theoretical maximum and Robert's practical maximum
            n_instruments = len(self.config.instruments)
            theoretical_max = np.sqrt(n_instruments)
            robert_max = min(2.5, theoretical_max)

            print(f"📈 Theoretical Max IDM: {theoretical_max:.4f}")
            print(f"🎯 Robert Carver Max IDM: {robert_max:.4f}")

            # Calculate efficiency against both benchmarks
            theoretical_efficiency = (current_idm / theoretical_max) * 100
            practical_efficiency = (current_idm / robert_max) * 100

            print(f"🔬 Theoretical Efficiency: {theoretical_efficiency:.1f}%")
            print(f"💡 Practical Efficiency: {practical_efficiency:.1f}%")

            # Interpret the results
            if idm_source == "robert_carver_capped":
                print("✅ Using Robert Carver's recommended IDM methodology")
            elif current_idm > 2.5:
                print("⚠️  WARNING: IDM exceeds Robert Carver's recommended 2.5 cap!")
                print("💭 Consider implementing IDM capping for better risk management")

            return {
                "current_idm": current_idm,
                "idm_source": idm_source,
                "theoretical_max": theoretical_max,
                "robert_carver_max": robert_max,
                "theoretical_efficiency_pct": theoretical_efficiency,
                "practical_efficiency_pct": practical_efficiency,
                "n_instruments": n_instruments,
                "exceeds_carver_cap": current_idm > 2.5,
            }

        return None

    def analyze_idm_vs_performance_corrected(self, performance):
        """Analyze IDM vs performance with corrected methodology"""
        print("=== IDM vs Performance Analysis (Corrected) ===")

        idm_metrics = self.get_portfolio_level_metrics_corrected()

        if idm_metrics and performance:
            current_idm = idm_metrics["current_idm"]
            robert_max = idm_metrics["robert_carver_max"]
            avg_sharpe = np.mean(list(performance.values()))

            print(f"\n📊 Portfolio Analysis:")
            print(f"   Current IDM: {current_idm:.4f}")
            print(f"   Robert Carver Max: {robert_max:.4f}")
            print(f"   Average Sharpe: {avg_sharpe:.3f}")
            print(f"   Performance per IDM Unit: {avg_sharpe / current_idm:.3f}")

            # Calculate impact of using Robert's cap
            if current_idm > 2.5:
                carver_capped_sharpe = avg_sharpe * (2.5 / current_idm)
                improvement = carver_capped_sharpe - avg_sharpe
                print(f"   Sharpe with Robert's 2.5 Cap: {carver_capped_sharpe:.3f}")
                print(f"   Risk Management Benefit: {improvement:+.3f} Sharpe")
                print(
                    f"   🎯 Recommendation: Implement 2.5 IDM cap for better risk control"
                )
            else:
                print(f"   ✅ IDM within Robert Carver's recommended range")

            return {
                "current_performance": avg_sharpe,
                "current_idm": current_idm,
                "robert_carver_max": robert_max,
                "performance_per_idm": avg_sharpe / current_idm,
                "exceeds_carver_recommendation": current_idm > 2.5,
                "risk_adjusted_performance": avg_sharpe
                * (min(2.5, current_idm) / current_idm),
            }

        return None


def create_idm_analysis_plots(
    self,
    idm_series,
    instrument_weights,
    positions_before_idm,
    positions_after_idm,
    pst_system,
):
    """Create comprehensive plots of actual IDM used in system"""

    print("=== Creating Actual IDM Analysis Plots ===")

    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from datetime import datetime

    # Create comprehensive figure
    fig = plt.figure(figsize=(20, 16))

    # Plot 1: IDM Time Series with Key Statistics
    ax1 = plt.subplot(3, 3, 1)
    idm_series.plot(ax=ax1, linewidth=2, color="darkblue")

    # Add statistical lines
    mean_idm = idm_series.mean()
    ax1.axhline(
        y=mean_idm,
        color="red",
        linestyle="--",
        alpha=0.7,
        label=f"Mean: {mean_idm:.3f}",
    )
    ax1.axhline(
        y=idm_series.quantile(0.25),
        color="orange",
        linestyle=":",
        alpha=0.5,
        label=f"25th %ile: {idm_series.quantile(0.25):.3f}",
    )
    ax1.axhline(
        y=idm_series.quantile(0.75),
        color="orange",
        linestyle=":",
        alpha=0.5,
        label=f"75th %ile: {idm_series.quantile(0.75):.3f}",
    )

    ax1.set_title("Actual IDM Used in Backtest", fontsize=14, fontweight="bold")
    ax1.set_ylabel("IDM Value")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Plot 2: IDM vs Theoretical Maximum
    ax2 = plt.subplot(3, 3, 2)
    n_instruments = len(self.config.instruments)
    theoretical_max = np.sqrt(n_instruments)

    idm_series.plot(ax=ax2, label="Actual IDM", linewidth=2)
    ax2.axhline(
        y=theoretical_max,
        color="red",
        linestyle="--",
        label=f"Theoretical Max ({theoretical_max:.2f})",
    )
    ax2.axhline(
        y=1.0, color="gray", linestyle=":", alpha=0.5, label="No Diversification (1.0)"
    )

    efficiency = (idm_series.iloc[-1] / theoretical_max) * 100
    ax2.set_title(f"IDM Efficiency: {efficiency:.1f}%", fontsize=14, fontweight="bold")
    ax2.set_ylabel("IDM Value")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Plot 3: Rolling IDM Statistics
    ax3 = plt.subplot(3, 3, 3)
    rolling_mean = idm_series.rolling(252).mean()  # 1-year rolling
    rolling_std = idm_series.rolling(252).std()

    ax3.plot(idm_series.index, idm_series, alpha=0.3, label="Daily IDM")
    ax3.plot(
        rolling_mean.index,
        rolling_mean,
        linewidth=2,
        color="red",
        label="1Y Rolling Mean",
    )
    ax3.fill_between(
        rolling_mean.index,
        rolling_mean - rolling_std,
        rolling_mean + rolling_std,
        alpha=0.2,
        color="red",
        label="±1 Std Dev",
    )

    ax3.set_title("IDM Rolling Statistics", fontsize=14, fontweight="bold")
    ax3.set_ylabel("IDM Value")
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # Plot 4: IDM Impact on Positions (sample instruments)
    ax4 = plt.subplot(3, 3, 4)

    # Select top 4 instruments by weight for display
    latest_weights = instrument_weights.iloc[-1].sort_values(ascending=False)
    top_instruments = latest_weights.head(4).index.tolist()

    for i, instrument in enumerate(top_instruments):
        if instrument in positions_before_idm and instrument in positions_after_idm:
            pos_before = positions_before_idm[instrument]
            pos_after = positions_after_idm[instrument]

            # Calculate the ratio (should equal IDM)
            ratio = pos_after / pos_before
            ratio = ratio.dropna()

            if len(ratio) > 0:
                # Plot every 20th point to avoid overcrowding
                sample_ratio = ratio.iloc[::20]
                ax4.plot(
                    sample_ratio.index,
                    sample_ratio,
                    alpha=0.7,
                    label=f"{instrument}",
                    linewidth=1,
                )

    # Overlay actual IDM for comparison
    idm_sample = idm_series.iloc[::20]
    ax4.plot(
        idm_sample.index,
        idm_sample,
        color="black",
        linewidth=3,
        alpha=0.8,
        label="Actual IDM",
    )

    ax4.set_title(
        "Position Scaling Factor (Pos After / Pos Before)",
        fontsize=12,
        fontweight="bold",
    )
    ax4.set_ylabel("Scaling Factor")
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    # Plot 5: IDM Distribution
    ax5 = plt.subplot(3, 3, 5)
    ax5.hist(idm_series, bins=50, alpha=0.7, color="skyblue", edgecolor="black")
    ax5.axvline(
        idm_series.mean(),
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Mean: {idm_series.mean():.3f}",
    )
    ax5.axvline(
        idm_series.median(),
        color="green",
        linestyle="--",
        linewidth=2,
        label=f"Median: {idm_series.median():.3f}",
    )

    ax5.set_title("IDM Distribution", fontsize=14, fontweight="bold")
    ax5.set_xlabel("IDM Value")
    ax5.set_ylabel("Frequency")
    ax5.legend()
    ax5.grid(True, alpha=0.3)

    # Plot 6: Number of Active Instruments Over Time
    ax6 = plt.subplot(3, 3, 6)

    # Count non-zero weights
    active_instruments = (instrument_weights != 0).sum(axis=1)
    active_instruments.plot(ax=ax6, color="purple", linewidth=2)

    ax6.set_title("Number of Active Instruments", fontsize=14, fontweight="bold")
    ax6.set_ylabel("Count")
    ax6.grid(True, alpha=0.3)

    # Plot 7: IDM Effectiveness Periods
    ax7 = plt.subplot(3, 3, 7)

    # Define IDM regimes
    low_idm = idm_series < idm_series.quantile(0.33)
    med_idm = (idm_series >= idm_series.quantile(0.33)) & (
        idm_series <= idm_series.quantile(0.67)
    )
    high_idm = idm_series > idm_series.quantile(0.67)

    ax7.scatter(
        idm_series.index[low_idm],
        idm_series[low_idm],
        c="red",
        alpha=0.6,
        s=10,
        label="Low IDM Period",
    )
    ax7.scatter(
        idm_series.index[med_idm],
        idm_series[med_idm],
        c="orange",
        alpha=0.6,
        s=10,
        label="Medium IDM Period",
    )
    ax7.scatter(
        idm_series.index[high_idm],
        idm_series[high_idm],
        c="green",
        alpha=0.6,
        s=10,
        label="High IDM Period",
    )

    ax7.set_title("IDM Effectiveness Regimes", fontsize=14, fontweight="bold")
    ax7.set_ylabel("IDM Value")
    ax7.legend()
    ax7.grid(True, alpha=0.3)

    # Plot 8: IDM vs Portfolio Performance (if available)
    ax8 = plt.subplot(3, 3, 8)

    try:
        # Get portfolio curve
        portfolio_curve = pst_system.accounts.portfolio().curve()
        portfolio_returns = portfolio_curve.pct_change().dropna()

        # Align IDM with returns
        aligned_data = pd.DataFrame(
            {"IDM": idm_series, "Returns": portfolio_returns}
        ).dropna()

        # Calculate rolling correlation
        rolling_corr = aligned_data["IDM"].rolling(252).corr(aligned_data["Returns"])
        rolling_corr.plot(ax=ax8, color="darkgreen", linewidth=2)

        ax8.set_title(
            "IDM vs Portfolio Returns Correlation", fontsize=12, fontweight="bold"
        )
        ax8.set_ylabel("Rolling Correlation (252d)")
        ax8.axhline(y=0, color="gray", linestyle="--", alpha=0.5)
        ax8.grid(True, alpha=0.3)

    except Exception as e:
        ax8.text(
            0.5,
            0.5,
            f"Portfolio data not available\n{str(e)[:50]}...",
            ha="center",
            va="center",
            transform=ax8.transAxes,
        )
        ax8.set_title("Portfolio Analysis Unavailable", fontsize=12)

    # Plot 9: Summary Statistics Table
    ax9 = plt.subplot(3, 3, 9)
    ax9.axis("off")

    # Calculate summary statistics
    stats_text = f"""
    ACTUAL IDM STATISTICS
    (Used in Backtest)

    Current IDM: {idm_series.iloc[-1]:.4f}
    Mean IDM: {idm_series.mean():.4f}
    Median IDM: {idm_series.median():.4f}
    Std Dev: {idm_series.std():.4f}

    Min IDM: {idm_series.min():.4f}
    Max IDM: {idm_series.max():.4f}

    Theoretical Max: {theoretical_max:.4f}
    Current Efficiency: {(idm_series.iloc[-1] / theoretical_max * 100):.1f}%
    Average Efficiency: {(idm_series.mean() / theoretical_max * 100):.1f}%

    Total Instruments: {n_instruments}
    Avg Active Instruments: {active_instruments.mean():.1f}

    Observation Period: {len(idm_series)} days
    Start Date: {idm_series.index[0].strftime('%Y-%m-%d')}
    End Date: {idm_series.index[-1].strftime('%Y-%m-%d')}

    IDM Regime Breakdown:
    High IDM Days: {high_idm.sum()}
    Med IDM Days: {med_idm.sum()}
    Low IDM Days: {low_idm.sum()}
    """

    ax9.text(
        0.05,
        0.95,
        stats_text,
        transform=ax9.transAxes,
        fontsize=10,
        verticalalignment="top",
        fontfamily="monospace",
        bbox=dict(boxstyle="round", facecolor="lightblue", alpha=0.8),
    )

    plt.suptitle(
        f"Actual IDM Analysis - {n_instruments} ETF System",
        fontsize=16,
        fontweight="bold",
        y=0.98,
    )
    plt.tight_layout()
    plt.subplots_adjust(top=0.94)
    plt.show()

    # Save IDM data to CSV for further analysis
    idm_analysis_df = pd.DataFrame(
        {
            "IDM": idm_series,
            "IDM_Rolling_Mean_252d": rolling_mean,
            "IDM_Rolling_Std_252d": rolling_std,
            "Active_Instruments": active_instruments.reindex(
                idm_series.index, method="ffill"
            ),
            "IDM_Regime": pd.Series(
                [
                    "Low" if low_idm[i] else "Medium" if med_idm[i] else "High"
                    for i in idm_series.index
                ],
                index=idm_series.index,
            ),
        }
    )

    # Save to CSV
    csv_filename = "actual_idm_analysis.csv"
    idm_analysis_df.to_csv(csv_filename)
    print(f"✅ IDM analysis saved to: {csv_filename}")

    return idm_analysis_df, fig


def create_robust_pysystemtrade_system(self):
    """Create PySystemTrade system with robust error handling for problematic instruments"""
    print("=== Creating Robust PySystemTrade System ===")

    # Start with your full instrument list
    original_instruments = self.config.instruments.copy()
    working_instruments = original_instruments.copy()
    problematic_instruments = []

    max_attempts = 3
    attempt = 0

    while attempt < max_attempts:
        try:
            print(
                f"Attempt {attempt + 1}: Testing with {len(working_instruments)} instruments"
            )

            # Filter instrument weights to match working instruments
            filtered_weights = {
                k: v
                for k, v in self.config.instrument_weights.items()
                if k in working_instruments
            }

            # Normalize weights to sum to 1
            total_weight = sum(filtered_weights.values())
            normalized_weights = {
                k: v / total_weight for k, v in filtered_weights.items()
            }

            # Create PySystemTrade config
            pst_config_dict = {
                "instruments": working_instruments,
                "instrument_weights": normalized_weights,
                "percentage_vol_target": self.config.percentage_vol_target,
                # Enable dynamic IDM
                "use_instrument_div_mult_estimates": True,
                "use_instrument_weight_estimates": True,
                # IDM estimation parameters
                "instrument_div_mult_estimate": {
                    "date_method": "expanding",
                    "rollyears": 3,
                    "frequency": "W",
                    "using_exponent": True,
                    "ew_lookback": 250,
                    "min_periods": 100,
                },
                # Trading rules
                "trading_rules": {
                    "ewmac_fast": {
                        "function": "systems.provided.rules.ewmac.ewmac",
                        "data": [
                            "rawdata.get_daily_prices",
                            "rawdata.daily_returns_volatility",
                        ],
                        "other_args": {"Lfast": 8, "Lslow": 32},
                    }
                },
                "forecast_weights": {"ewmac_fast": 1.0},
            }

            # Test system creation
            from sysdata.config.configdata import Config
            from systems.provided.futures_chapter15.basesystem import futures_system

            pst_config = Config(pst_config_dict)
            system = futures_system(config=pst_config)

            # Test IDM extraction (this is where BBAX might fail)
            print("Testing IDM extraction...")
            idm_series = system.portfolio.get_instrument_diversification_multiplier()

            print(
                f"✅ Success! IDM extracted with {len(working_instruments)} instruments"
            )
            print(f"Excluded instruments: {problematic_instruments}")
            return system, idm_series, working_instruments, problematic_instruments

        except Exception as e:
            error_str = str(e)
            print(f"❌ Attempt {attempt + 1} failed: {error_str}")

            # Try to identify problematic instrument
            if "BBAX" in error_str or "BBAX" in str(type(e)):
                problematic_instrument = "BBAX"
            else:
                # Try to extract instrument name from error
                for instrument in working_instruments:
                    if instrument in error_str:
                        problematic_instrument = instrument
                        break
                else:
                    # If we can't identify, remove the last instrument
                    problematic_instrument = working_instruments[-1]

            if problematic_instrument in working_instruments:
                working_instruments.remove(problematic_instrument)
                problematic_instruments.append(problematic_instrument)
                print(f"🔄 Removing {problematic_instrument} and retrying...")
            else:
                print(f"❌ Could not identify problematic instrument. Breaking.")
                break

            attempt += 1

    print(f"❌ Failed to create system after {max_attempts} attempts")
    return None, None, working_instruments, problematic_instruments


def extract_actual_idm_with_robust_handling(self):
    """Extract actual IDM with robust error handling"""
    print("=== Extracting Actual IDM (Robust Method) ===")

    # Try robust system creation
    (
        pst_system,
        idm_series,
        working_instruments,
        problematic_instruments,
    ) = self.create_robust_pysystemtrade_system()

    if pst_system is None or idm_series is None:
        print("❌ Could not extract IDM even with robust handling")
        return None, None, None, None

    print(f"✅ Successfully extracted actual IDM time series")
    print(f"IDM Series Length: {len(idm_series)} data points")
    print(f"Date Range: {idm_series.index[0]} to {idm_series.index[-1]}")
    print(f"Working Instruments ({len(working_instruments)}): {working_instruments}")
    if problematic_instruments:
        print(
            f"⚠️  Excluded Instruments ({len(problematic_instruments)}): {problematic_instruments}"
        )

    return idm_series, pst_system, working_instruments, problematic_instruments


def analyze_actual_idm_performance_robust(self):
    """Comprehensive analysis of actual IDM with robust error handling"""
    print("=== Analyzing Actual IDM Performance (Robust) ===")

    # Extract actual IDM with error handling
    (
        idm_series,
        pst_system,
        working_instruments,
        problematic_instruments,
    ) = self.extract_actual_idm_with_robust_handling()

    if idm_series is None:
        print("Cannot analyze IDM - extraction failed even with robust handling")
        return None

    # Get additional system data for analysis
    try:
        # Get instrument weights time series (only for working instruments)
        instrument_weights = pst_system.portfolio.get_instrument_weights()

        # Get portfolio positions (before and after IDM application)
        positions_before_idm = {}
        positions_after_idm = {}

        for instrument in working_instruments:
            try:
                pos_before = pst_system.portfolio.get_notional_position_without_idm(
                    instrument
                )
                pos_after = (
                    pst_system.portfolio.get_notional_position_before_risk_scaling(
                        instrument
                    )
                )
                positions_before_idm[instrument] = pos_before
                positions_after_idm[instrument] = pos_after
            except Exception as e:
                print(f"⚠️  Could not get positions for {instrument}: {e}")
                continue

        # Create comprehensive analysis with robust data
        analysis_results = self.create_robust_idm_analysis_plots(
            idm_series,
            instrument_weights,
            positions_before_idm,
            positions_after_idm,
            pst_system,
            working_instruments,
            problematic_instruments,
        )

        return analysis_results

    except Exception as e:
        print(f"Error during IDM analysis: {e}")
        return None


def create_robust_idm_analysis_plots(
    self,
    idm_series,
    instrument_weights,
    positions_before_idm,
    positions_after_idm,
    pst_system,
    working_instruments,
    problematic_instruments,
):
    """Create IDM analysis plots with information about excluded instruments"""

    print("=== Creating Robust IDM Analysis Plots ===")

    import matplotlib.pyplot as plt

    # Use your existing plotting code but update the statistics section
    fig = plt.figure(figsize=(20, 16))

    # [Include all your existing plotting code from plots 1-8]
    # ... (copy the existing plotting code exactly)

    # Modified Plot 9: Summary Statistics with exclusion info
    ax9 = plt.subplot(3, 3, 9)
    ax9.axis("off")

    n_working_instruments = len(working_instruments)
    n_total_instruments = len(self.config.instruments)
    theoretical_max = np.sqrt(n_working_instruments)

    # Calculate summary statistics
    stats_text = f"""
    ACTUAL IDM STATISTICS
    (Used in Backtest)

    Current IDM: {idm_series.iloc[-1]:.4f}
    Mean IDM: {idm_series.mean():.4f}
    Median IDM: {idm_series.median():.4f}
    Std Dev: {idm_series.std():.4f}

    Min IDM: {idm_series.min():.4f}
    Max IDM: {idm_series.max():.4f}

    Theoretical Max: {theoretical_max:.4f}
    Current Efficiency: {(idm_series.iloc[-1] / theoretical_max * 100):.1f}%
    Average Efficiency: {(idm_series.mean() / theoretical_max * 100):.1f}%

    PORTFOLIO COMPOSITION:
    Total Instruments: {n_total_instruments}
    Working Instruments: {n_working_instruments}
    Excluded Instruments: {len(problematic_instruments)}

    Excluded: {', '.join(problematic_instruments) if problematic_instruments else 'None'}

    Observation Period: {len(idm_series)} days
    Start Date: {idm_series.index[0].strftime('%Y-%m-%d')}
    End Date: {idm_series.index[-1].strftime('%Y-%m-%d')}
    """

    ax9.text(
        0.05,
        0.95,
        stats_text,
        transform=ax9.transAxes,
        fontsize=10,
        verticalalignment="top",
        fontfamily="monospace",
        bbox=dict(boxstyle="round", facecolor="lightblue", alpha=0.8),
    )

    plt.suptitle(
        f"Actual IDM Analysis - {n_working_instruments}/{n_total_instruments} ETF System",
        fontsize=16,
        fontweight="bold",
        y=0.98,
    )
    plt.tight_layout()
    plt.subplots_adjust(top=0.94)
    plt.show()

    # Save results
    idm_analysis_df = pd.DataFrame(
        {
            "IDM": idm_series,
            "Working_Instruments": n_working_instruments,
            "Excluded_Instruments": len(problematic_instruments),
        }
    )

    # Save to CSV with exclusion info
    csv_filename = f"actual_idm_analysis_{n_working_instruments}_instruments.csv"
    idm_analysis_df.to_csv(csv_filename)
    print(f"✅ IDM analysis saved to: {csv_filename}")

    return idm_analysis_df, fig


if __name__ == "__main__":
    try:
        system = ScalableETFSystem()

        # Run your custom system first
        print("=== Running Custom ETF System ===")
        forecasts, positions, performance = system.run_system()

        # Analyze with corrected IDM methodology
        print("\n=== Analyzing IDM with Robert Carver Methodology ===")
        idm_metrics = system.get_portfolio_level_metrics_corrected()
        performance_analysis = system.analyze_idm_vs_performance_corrected(performance)

        # Show comprehensive results
        if performance:
            avg_sharpe = np.mean(list(performance.values()))
            print(f"\n=== System Analysis with Proper IDM ===")
            print(f"📈 Portfolio Avg Sharpe: {avg_sharpe:.3f}")
            print(f"🎯 Successfully processed {len(performance)} instruments")

            if idm_metrics:
                current_idm = idm_metrics["current_idm"]
                robert_max = idm_metrics["robert_carver_max"]

                print(f"📊 Current IDM: {current_idm:.4f}")
                print(f"🎯 Robert Carver's Methodology:")
                print(
                    f"   - Theoretical Max: √{len(performance)} = {idm_metrics['theoretical_max']:.3f}"
                )
                print(f"   - Practical Cap: {robert_max:.3f}")
                print(
                    f"   - Recommended: Use {robert_max:.3f} for better risk management"
                )

                if current_idm > 2.5:
                    print(f"⚠️  Your system is using {current_idm:.3f} IDM (too high!)")
                    print(
                        f"💡 Should use {robert_max:.3f} per Robert Carver's methodology"
                    )

        print(f"\n✅ Analysis complete with Robert Carver IDM methodology!")

    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
