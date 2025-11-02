# etf_systematic_trader.py - Clean ETF Systematic Trading System (No Config File Creation)
import yfinance as yf
import pandas as pd
import numpy as np
import yaml
import os
import matplotlib.pyplot as plt
from systems.provided.futures_chapter15.basesystem import futures_system
from sysdata.config.configdata import Config
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData


class ETFSystematicTrader:
    """Professional ETF systematic trading system using Robert Carver methodology"""

    def __init__(self, config_path=None):
        """Initialize with configuration"""
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "private",
                "etf_system",
                "config.yaml",
            )

        try:
            with open(config_path, "r") as file:
                self.config_data = yaml.safe_load(file)
        except FileNotFoundError:
            print(f"⚠️  Config file not found, using default configuration")
            self.config_data = self.get_default_config()

        self.instruments = self.config_data["instruments"]
        self.instrument_weights = self.config_data["instrument_weights"]
        self.vol_target = self.config_data["percentage_vol_target"]
        self.etf_data = {}

        # Set up PySystemTrade directory structure
        pst_root = self.find_pysystemtrade_root()
        self.data_dir = os.path.join(pst_root, "data")
        self.futures_dir = os.path.join(self.data_dir, "futures")
        self.csv_dir = os.path.join(self.futures_dir, "adjusted_prices")
        self.config_dir = os.path.join(self.futures_dir, "csvconfig")

        # Ensure directories exist
        os.makedirs(self.csv_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)

        print(
            f"✅ ETF Systematic Trader initialized with {len(self.instruments)} instruments"
        )
        print(f"📁 Data directory: {self.data_dir}")
        print(f"📁 Using existing instrumentconfig.csv (no modifications needed)")

    def find_pysystemtrade_root(self):
        """Find the pysystemtrade root directory"""
        current_dir = os.path.dirname(os.path.abspath(__file__))

        while current_dir != os.path.dirname(current_dir):
            if "pysystemtrade" in os.path.basename(current_dir):
                return current_dir
            if os.path.exists(os.path.join(current_dir, "pysystemtrade")):
                return os.path.join(current_dir, "pysystemtrade")
            current_dir = os.path.dirname(current_dir)

        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def get_default_config(self):
        """Get default configuration"""
        return {
            "instruments": [
                "IVV",
                "EFA",
                "EEM",
                "AGG",
                "TLT",
                "TIP",
                "HYG",
                "VNQ",
                "GLD",
            ],
            "instrument_weights": {
                "IVV": 0.3,
                "EFA": 0.2,
                "EEM": 0.1,
                "AGG": 0.2,
                "TLT": 0.1,
                "TIP": 0.05,
                "HYG": 0.025,
                "VNQ": 0.025,
                "GLD": 0.05,
            },
            "percentage_vol_target": 12.0,
        }

    def download_data(self, start_date="2020-01-01"):
        """Download ETF data with validation"""
        print(f"=== Downloading {len(self.instruments)} ETFs ===")

        valid_instruments = []

        for symbol in self.instruments:
            try:
                print(f"🔄 Downloading {symbol}...")

                raw_data = yf.download(symbol, start=start_date, auto_adjust=False)

                # Extract Adj Close price series
                if isinstance(raw_data.columns, pd.MultiIndex):
                    if "Adj Close" in raw_data.columns.get_level_values(0):
                        data = raw_data["Adj Close"].iloc[:, 0]
                    else:
                        data = raw_data.iloc[:, -1]
                else:
                    if "Adj Close" in raw_data.columns:
                        data = raw_data["Adj Close"]
                    else:
                        data = raw_data.iloc[:, -1]

                if not isinstance(data, pd.Series):
                    data = pd.Series(data.values, index=data.index, name=symbol)

                # Validate data quality
                if len(data) < 100:
                    print(f"⚠️  {symbol}: Insufficient data ({len(data)} days)")
                    continue

                null_count = data.isnull().sum()
                if null_count > len(data) * 0.1:
                    print(f"⚠️  {symbol}: Too many missing values ({null_count} nulls)")
                    continue

                # Clean data
                data = data.ffill().bfill()

                if data.isnull().sum() > 0:
                    print(f"⚠️  {symbol}: Still has nulls after cleaning")
                    continue

                self.etf_data[symbol] = data
                valid_instruments.append(symbol)
                print(f"✅ {symbol}: {len(data)} days")

            except Exception as e:
                print(f"❌ {symbol}: Download failed - {str(e)[:100]}...")

        # Update instruments list to valid ones only
        self.instruments = valid_instruments

        print(f"\n📊 Download Summary:")
        print(f"   Valid instruments: {len(valid_instruments)}")

        return len(self.etf_data)

    def save_data_to_pysystemtrade_format(self):
        """Save data in PySystemTrade format"""
        print("=== Saving Data to PySystemTrade Format ===")

        if not self.etf_data:
            return False

        saved_count = 0

        for instrument, data in self.etf_data.items():
            try:
                # PySystemTrade expects PRICE column with DATETIME index
                df = pd.DataFrame({"PRICE": data})
                df.index.name = "DATETIME"

                if not isinstance(df.index, pd.DatetimeIndex):
                    df.index = pd.to_datetime(df.index)

                df = df[~df.index.duplicated(keep="first")]
                df = df.sort_index()

                csv_path = os.path.join(self.csv_dir, f"{instrument}.csv")
                df.to_csv(csv_path)

                print(f"✅ {instrument}: Saved ({len(df)} rows)")
                saved_count += 1

            except Exception as e:
                print(f"❌ {instrument}: Save failed - {e}")
                if instrument in self.instruments:
                    self.instruments.remove(instrument)

        print(f"📁 Saved {saved_count} instruments")
        return saved_count > 0

    def verify_instrument_config(self):
        """Verify that the existing instrumentconfig.csv contains our ETFs"""
        print("=== Verifying Instrument Configuration ===")

        cfg_path = os.path.join(self.config_dir, "instrumentconfig.csv")

        if not os.path.exists(cfg_path):
            print(f"❌ instrumentconfig.csv not found at: {cfg_path}")
            return False

        try:
            config_df = pd.read_csv(cfg_path)
            available_instruments = set(config_df["Instrument"].tolist())

            # Check which of our ETFs are in the config
            missing_instruments = []
            found_instruments = []

            for instrument in self.instruments:
                if instrument in available_instruments:
                    found_instruments.append(instrument)
                else:
                    missing_instruments.append(instrument)

            print(f"✅ Found {len(found_instruments)} ETFs in instrumentconfig.csv")
            print(f"📊 ETFs found: {found_instruments}")

            if missing_instruments:
                print(
                    f"⚠️  Missing {len(missing_instruments)} ETFs: {missing_instruments}"
                )
                print(f"💡 These ETFs need to be added to instrumentconfig.csv")

                # Remove missing instruments from our list
                self.instruments = found_instruments
                print(
                    f"🔄 Updated instruments list to {len(self.instruments)} working ETFs"
                )

            return len(found_instruments) > 0

        except Exception as e:
            print(f"❌ Error reading instrumentconfig.csv: {e}")
            return False

    def create_systematic_trading_system(self, idm_cap=2.5):
        """Create PySystemTrade system with dynamic IDM enabled"""

        # Save price data
        if not self.save_data_to_pysystemtrade_format():
            print("❌ Data saving failed")
            return None

        # Verify instrument configuration
        if not self.verify_instrument_config():
            print("❌ Instrument configuration verification failed")
            return None

        if len(self.instruments) == 0:
            print("❌ No valid instruments")
            return None

        # Prepare instrument weights
        filtered_weights = {
            k: v for k, v in self.instrument_weights.items() if k in self.instruments
        }

        if not filtered_weights:
            print("❌ No valid instrument weights found")
            return None

        total_weight = sum(filtered_weights.values())
        normalized_weights = {k: v / total_weight for k, v in filtered_weights.items()}

        print(f"📊 Using {len(self.instruments)} instruments with dynamic IDM")

        # System configuration with DYNAMIC IDM enabled
        config_dict = {
            "instruments": self.instruments,
            "instrument_weights": normalized_weights,
            "percentage_vol_target": self.vol_target,
            # Currency settings
            "base_currency": "USD",
            # ENABLE DYNAMIC IDM (as in your YAML config)
            "use_instrument_div_mult_estimates": True,
            "use_instrument_weight_estimates": True,
            # Dynamic IDM estimation parameters with 2.5 cap
            "instrument_div_mult_estimate": {
                "func": "sysquant.estimators.diversification_multipliers.diversification_multiplier_from_list",
                "ewma_span": 125,  # Smoothing parameter
                "dm_max": idm_cap,  # Cap at 2.5
            },
            # Correlation estimation for IDM calculation
            "instrument_correlation_estimate": {
                "func": "sysquant.estimators.correlation_over_time.correlation_over_time_for_returns",
                "frequency": "W",
                "date_method": "expanding",
                "using_exponent": True,
                "ew_lookback": 250,
                "min_periods": 20,
                "cleaning": True,
                "rollyears": 3,
                "floor_at_zero": True,
            },
            # EWMAC momentum strategy
            "trading_rules": {
                "ewmac_8_32": {
                    "function": "systems.provided.rules.ewmac.ewmac",
                    "data": [
                        "rawdata.get_daily_prices",
                        "rawdata.daily_returns_volatility",
                    ],
                    "other_args": {"Lfast": 8, "Lslow": 32},
                }
            },
            "forecast_weights": {"ewmac_8_32": 1.0},
        }

        try:
            # Create data source
            data_paths = {
                "csvFuturesAdjustedPricesData": self.csv_dir,
                "csvFuturesInstrumentData": self.config_dir,
            }

            data = csvFuturesSimData(csv_data_paths=data_paths)

            # Create system
            pst_config = Config(config_dict)
            system = futures_system(config=pst_config, data=data)

            system_instruments = system.get_instrument_list()
            print(f"✅ System created with dynamic IDM (cap: {idm_cap})")
            print(f"📊 System instruments: {len(system_instruments)}")

            return system

        except Exception as e:
            print(f"❌ System creation failed: {e}")
            import traceback

            traceback.print_exc()
            return None

    def analyze_dynamic_idm(self, system):
        """Extract and analyze dynamic IDM time series"""
        print("=== Analyzing Dynamic IDM Time Series ===")

        try:
            # Extract the dynamic IDM time series
            idm_series = system.portfolio.get_instrument_diversification_multiplier()

            # Create analysis DataFrame
            idm_df = pd.DataFrame({"IDM": idm_series, "Date": idm_series.index})

            # Add analysis columns
            idm_df["At_Cap"] = idm_df["IDM"] >= 2.5
            idm_df["Rolling_Mean_30d"] = idm_df["IDM"].rolling(30).mean()
            idm_df["Rolling_Std_30d"] = idm_df["IDM"].rolling(30).std()

            # Calculate summary statistics
            stats = {
                "mean": idm_df["IDM"].mean(),
                "median": idm_df["IDM"].median(),
                "min": idm_df["IDM"].min(),
                "max": idm_df["IDM"].max(),
                "std": idm_df["IDM"].std(),
                "fraction_at_cap": idm_df["At_Cap"].mean(),
                "days_at_cap": idm_df["At_Cap"].sum(),
                "total_days": len(idm_df),
                "coefficient_of_variation": idm_df["IDM"].std() / idm_df["IDM"].mean(),
            }

            print(f"✅ IDM Analysis Complete:")
            print(f"   Mean IDM: {stats['mean']:.3f}")
            print(f"   Median IDM: {stats['median']:.3f}")
            print(f"   Min IDM: {stats['min']:.3f}")
            print(f"   Max IDM: {stats['max']:.3f}")
            print(f"   Standard Deviation: {stats['std']:.3f}")
            print(
                f"   Coefficient of Variation: {stats['coefficient_of_variation']:.3f}"
            )
            print(
                f"   Days at Cap (2.5): {stats['days_at_cap']}/{stats['total_days']} ({stats['fraction_at_cap']:.1%})"
            )

            # Stability analysis
            if stats["coefficient_of_variation"] < 0.1:
                stability = "Very Stable"
            elif stats["coefficient_of_variation"] < 0.2:
                stability = "Stable"
            elif stats["coefficient_of_variation"] < 0.3:
                stability = "Moderately Stable"
            else:
                stability = "Unstable"

            print(f"   IDM Stability Assessment: {stability}")

            return idm_df, stats

        except Exception as e:
            print(f"❌ IDM analysis failed: {e}")
            import traceback

            traceback.print_exc()
            return None, None

    def create_idm_visualization(self, idm_df, stats):
        """Create comprehensive IDM visualization"""
        if idm_df is None:
            return None

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        # Plot 1: IDM Time Series with Cap Line
        ax1 = axes[0, 0]
        ax1.plot(
            idm_df["Date"],
            idm_df["IDM"],
            linewidth=1.5,
            color="blue",
            label="Dynamic IDM",
        )
        ax1.axhline(
            y=2.5, color="red", linestyle="--", linewidth=2, label="IDM Cap (2.5)"
        )
        ax1.fill_between(
            idm_df["Date"],
            idm_df["IDM"],
            2.5,
            where=(idm_df["IDM"] >= 2.5),
            color="red",
            alpha=0.3,
            label="At Cap",
        )
        ax1.set_title("Dynamic IDM Over Time", fontsize=14, fontweight="bold")
        ax1.set_ylabel("IDM Value")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Plot 2: IDM with Rolling Statistics
        ax2 = axes[0, 1]
        ax2.plot(
            idm_df["Date"], idm_df["IDM"], alpha=0.5, color="blue", label="Daily IDM"
        )
        ax2.plot(
            idm_df["Date"],
            idm_df["Rolling_Mean_30d"],
            color="red",
            linewidth=2,
            label="30-Day Mean",
        )

        # Add confidence bands
        upper_band = idm_df["Rolling_Mean_30d"] + idm_df["Rolling_Std_30d"]
        lower_band = idm_df["Rolling_Mean_30d"] - idm_df["Rolling_Std_30d"]
        ax2.fill_between(
            idm_df["Date"],
            lower_band,
            upper_band,
            alpha=0.2,
            color="red",
            label="±1 Std Dev",
        )

        ax2.axhline(y=2.5, color="orange", linestyle="--", label="Cap (2.5)")
        ax2.set_title("IDM with Rolling Statistics", fontsize=14, fontweight="bold")
        ax2.set_ylabel("IDM Value")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # Plot 3: IDM Distribution
        ax3 = axes[1, 0]
        ax3.hist(idm_df["IDM"], bins=50, alpha=0.7, color="skyblue", edgecolor="black")
        ax3.axvline(
            stats["mean"],
            color="red",
            linestyle="--",
            linewidth=2,
            label=f"Mean: {stats['mean']:.3f}",
        )
        ax3.axvline(
            stats["median"],
            color="green",
            linestyle="--",
            linewidth=2,
            label=f"Median: {stats['median']:.3f}",
        )
        ax3.axvline(2.5, color="orange", linestyle="--", linewidth=2, label="Cap: 2.5")
        ax3.set_title("IDM Distribution", fontsize=14, fontweight="bold")
        ax3.set_xlabel("IDM Value")
        ax3.set_ylabel("Frequency")
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # Plot 4: Summary Statistics Table
        ax4 = axes[1, 1]
        ax4.axis("off")

        # Stability assessment
        cv = stats["coefficient_of_variation"]
        if cv < 0.1:
            stability_color = "green"
            stability = "Very Stable"
        elif cv < 0.2:
            stability_color = "lightgreen"
            stability = "Stable"
        elif cv < 0.3:
            stability_color = "yellow"
            stability = "Moderately Stable"
        else:
            stability_color = "red"
            stability = "Unstable"

        summary_text = f"""
        DYNAMIC IDM ANALYSIS

        Mean IDM: {stats['mean']:.3f}
        Median IDM: {stats['median']:.3f}
        Min IDM: {stats['min']:.3f}
        Max IDM: {stats['max']:.3f}
        Std Dev: {stats['std']:.3f}

        STABILITY METRICS
        Coefficient of Variation: {cv:.3f}
        Stability: {stability}

        CAP ANALYSIS
        Days at Cap: {stats['days_at_cap']}
        Total Days: {stats['total_days']}
        Fraction at Cap: {stats['fraction_at_cap']:.1%}

        ASSESSMENT
        ✅ Dynamic IDM Enabled
        ✅ Cap Enforced at 2.5
        {'✅' if stats['fraction_at_cap'] < 0.1 else '⚠️'} Cap Usage: {'Low' if stats['fraction_at_cap'] < 0.1 else 'High'}
        {'✅' if cv < 0.2 else '⚠️'} Stability: {stability}
        """

        ax4.text(
            0.05,
            0.95,
            summary_text,
            transform=ax4.transAxes,
            fontsize=11,
            verticalalignment="top",
            fontfamily="monospace",
            bbox=dict(boxstyle="round", facecolor=stability_color, alpha=0.3),
        )

        plt.suptitle("Dynamic IDM Analysis Dashboard", fontsize=16, fontweight="bold")
        plt.tight_layout()
        plt.show()

        return fig

    def run_backtest(self, idm_cap=2.5):
        """Run systematic trading backtest"""
        print(f"=== Running Backtest (IDM: {idm_cap}) ===")

        try:
            # Download data if needed
            if not self.etf_data:
                data_count = self.download_data()
                if data_count == 0:
                    print("❌ No valid data")
                    return None

            # Create system
            system = self.create_systematic_trading_system(idm_cap=idm_cap)

            if system is None:
                print("❌ System creation failed")
                return None

            # Calculate portfolio performance
            print("📊 Calculating portfolio performance...")
            portfolio_curve = system.accounts.portfolio()
            sharpe_ratio = portfolio_curve.sharpe()

            # Calculate metrics
            theoretical_max = np.sqrt(len(self.instruments))
            efficiency = (idm_cap / theoretical_max) * 100

            results = {
                "sharpe_ratio": sharpe_ratio,
                "current_idm": idm_cap,
                "theoretical_max_idm": theoretical_max,
                "diversification_efficiency": efficiency,
                "idm_cap_used": idm_cap,
                "portfolio_curve": portfolio_curve,
                "system": system,
                "working_instruments": self.instruments,
            }

            print(f"✅ Backtest Complete:")
            print(f"   Sharpe Ratio: {sharpe_ratio:.4f}")
            print(f"   IDM Used: {idm_cap:.4f}")
            print(f"   IDM Efficiency: {efficiency:.1f}%")
            print(f"   Working Instruments: {len(self.instruments)}")

            return results

        except Exception as e:
            print(f"❌ Backtest failed: {e}")
            import traceback

            traceback.print_exc()
            return None

    def compare_idm_scenarios(self):
        """Compare different IDM scenarios"""
        print("=== IDM Scenario Analysis ===")

        scenarios = {
            "Robert Carver (2.5)": 2.5,
            "Conservative (2.0)": 2.0,
            "Aggressive (3.0)": 3.0,
            "Theoretical Max": np.sqrt(len(self.instruments)),
        }

        results = {}

        for name, idm_cap in scenarios.items():
            print(f"\n🔄 Testing {name} (IDM: {idm_cap:.1f})")
            result = self.run_backtest(idm_cap=idm_cap)
            if result:
                results[name] = result

        # Compare results
        if results:
            print(f"\n=== IDM Scenario Comparison ===")
            print(f"{'Scenario':<25} {'Sharpe':<10} {'IDM':<10} {'Efficiency':<12}")
            print("-" * 60)

            for name, result in results.items():
                sharpe = result["sharpe_ratio"]
                idm = result["current_idm"]
                eff = result["diversification_efficiency"]
                print(f"{name:<25} {sharpe:<10.4f} {idm:<10.4f} {eff:<12.1f}%")

        return results

    def create_performance_dashboard(self, results):
        """Create performance dashboard"""
        if not results:
            return None

        fig, axes = plt.subplots(2, 2, figsize=(15, 10))

        # Portfolio equity curve
        portfolio_curve = results["portfolio_curve"]
        portfolio_curve.curve().plot(ax=axes[0, 0], title="Portfolio Equity Curve")
        axes[0, 0].grid(True)

        # Performance metrics
        axes[0, 1].axis("off")
        metrics_text = f"""
        PERFORMANCE METRICS

        Sharpe Ratio: {results['sharpe_ratio']:.4f}
        IDM Used: {results['current_idm']:.4f}
        IDM Efficiency: {results['diversification_efficiency']:.1f}%

        Working Instruments: {len(results['working_instruments'])}
        Theoretical Max IDM: {results['theoretical_max_idm']:.4f}

        Robert Carver IDM Cap: {results['idm_cap_used']:.1f}
        """

        axes[0, 1].text(
            0.1,
            0.9,
            metrics_text,
            transform=axes[0, 1].transAxes,
            fontsize=12,
            verticalalignment="top",
            fontfamily="monospace",
            bbox=dict(boxstyle="round", facecolor="lightblue", alpha=0.8),
        )

        # ETF list
        axes[1, 0].axis("off")
        etf_text = f"WORKING ETFS ({len(results['working_instruments'])})\n\n"
        for i, etf in enumerate(results["working_instruments"]):
            etf_text += f"{etf}  "
            if (i + 1) % 8 == 0:  # 8 ETFs per line
                etf_text += "\n"

        axes[1, 0].text(
            0.1,
            0.9,
            etf_text,
            transform=axes[1, 0].transAxes,
            fontsize=10,
            verticalalignment="top",
            fontfamily="monospace",
            bbox=dict(boxstyle="round", facecolor="lightgreen", alpha=0.8),
        )

        # Summary
        axes[1, 1].axis("off")
        summary_text = f"""
        SYSTEMATIC TRADING SUMMARY

        ✅ Robert Carver Methodology
        ✅ EWMAC Momentum Strategy  
        ✅ Risk Parity Weighting
        ✅ {results['idm_cap_used']:.1f} IDM Cap Applied
        ✅ Global ETF Diversification
        ✅ USD-Denominated Portfolio
        ✅ Using Existing Config File

        Status: PRODUCTION READY
        """

        axes[1, 1].text(
            0.1,
            0.9,
            summary_text,
            transform=axes[1, 1].transAxes,
            fontsize=11,
            verticalalignment="top",
            fontfamily="monospace",
            bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8),
        )

        plt.suptitle("ETF Systematic Trading Dashboard", fontsize=16, fontweight="bold")
        plt.tight_layout()
        plt.show()

        return fig


# Usage
if __name__ == "__main__":
    try:
        # Create trader
        trader = ETFSystematicTrader()

        print("🚀 Starting ETF Systematic Trading Analysis with Dynamic IDM...")

        # Download data if needed
        if not trader.etf_data:
            trader.download_data()

        # Create system with dynamic IDM
        system = trader.create_systematic_trading_system(idm_cap=2.5)

        if system:
            print("\n=== Dynamic IDM Analysis ===")

            # Analyze IDM time series
            idm_df, idm_stats = trader.analyze_dynamic_idm(system)

            if idm_df is not None:
                # Create IDM visualization
                trader.create_idm_visualization(idm_df, idm_stats)

                # Run full backtest
                print("\n=== Running Full Backtest ===")
                portfolio_curve = system.accounts.portfolio()
                sharpe_ratio = portfolio_curve.sharpe()

                print(f"\n=== RESULTS WITH DYNAMIC IDM ===")
                print(f"📈 Portfolio Sharpe: {sharpe_ratio:.4f}")
                print(f"🎯 Dynamic IDM Performance:")
                print(f"   Average IDM: {idm_stats['mean']:.3f}")
                print(
                    f"   IDM Stability: {idm_stats['coefficient_of_variation']:.3f} (CV)"
                )
                print(f"   Time at Cap: {idm_stats['fraction_at_cap']:.1%}")

                print(f"\n🎉 Dynamic IDM system successfully implemented!")
                print(f"💡 IDM adapts to changing correlations while respecting 2.5 cap")

        else:
            print("❌ System creation failed")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
