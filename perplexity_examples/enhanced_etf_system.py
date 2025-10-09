# enhanced_etf_system.py - Enhanced ETF Systematic Trading System v1.1

import yfinance as yf
import pandas as pd
import numpy as np
import yaml
import os
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings
import time


warnings.filterwarnings('ignore')

from systems.provided.futures_chapter15.basesystem import futures_system
from sysdata.config.configdata import Config
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
from performance_calculator_v3 import SimplePerformanceCalculator


# ADD THIS CLASS before EnhancedETFSystem
class ETFSimData(csvFuturesSimData):
    def __init__(self, csv_data_paths, dividend_data=None):
        super().__init__(csv_data_paths)
        self.dividend_data = dividend_data or {}

    # ADD THIS METHOD for rawdata compatibility
    def get_dividend_yield(self, instrument):
        """Return dividend yield for carry calculation - matches rawdata interface"""
        if instrument in self.dividend_data:
            return self.dividend_data[instrument]
        else:
            # Return zero yield series with same index as price data
            price_data = self.get_daily_prices(instrument)
            return pd.Series(0.0, index=price_data.index, name=f"{instrument}_dividend_yield")




class EnhancedETFSystem:
    """
    Enhanced ETF Systematic Trading System v1.1

    Following Robert Carver's methodology with:
    - Multiple EWMAC momentum rules
    - Breakout strategies for diversification
    - Dynamic forecast scaling
    - Cost-aware optimization
    """

    def __init__(self, config_path=None, test_mode=False, max_instruments=5, warm_up_days=365, data_source="yfinance"):
        """Initialize the enhanced ETF system"""

        # Add data source configuration
        self.data_source = data_source  # "yfinance" or "ib"

        # IB-specific configuration
        self.ib_config = {
            'host': '127.0.0.1',
            'port': 7497,
            'client_id': 100
        }

        # Load configuration
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "config_v1.1.yaml"
            )  # Fixed: Added closing parenthesis

        try:
            with open(config_path, 'r') as file:
                self.config_data = yaml.safe_load(file)
        except FileNotFoundError:
            print(f"⚠️ Config file not found at: {config_path}")
            raise

        # Extract configuration
        self.warm_up_days = warm_up_days
        self.instruments = self.config_data['instruments']
        self.instrument_weights = self.config_data['instrument_weights']
        self.vol_target = self.config_data['percentage_vol_target']
        self.trading_rules = self.config_data['trading_rules']
        self.monitoring_config = self.config_data.get('monitoring', {})

        # Initialize data storage
        self.etf_data = {}
        self.valid_instruments = []
        self.normalized_weights = {}

        # Set up PySystemTrade directory structure
        self.setup_directories()

        self.test_mode = test_mode
        self.max_instruments = max_instruments  # New: Limit for testing

        print(f"✅ Enhanced ETF System v1.1 initialized")
        print(f"📊 Total ETFs: {len(self.instruments)}")
        print(f"🎯 Trading Rules: {len(self.trading_rules)}")
        print(f"🎯 Volatility Target: {self.vol_target}%")
        print(f"📈 EWMAC Rules: {len([r for r in self.trading_rules if 'ewmac' in r])}")
        print(f"📈 Breakout Rules: {len([r for r in self.trading_rules if 'breakout' in r])}")

    def setup_directories(self):
        """Setup PySystemTrade directory structure"""
        pst_root = self.find_pysystemtrade_root()
        self.data_dir = os.path.join(pst_root, "data")
        self.futures_dir = os.path.join(self.data_dir, "futures")
        self.csv_dir = os.path.join(self.futures_dir, "adjusted_prices")
        self.config_dir = os.path.join(self.futures_dir, "csvconfig")

        # Ensure directories exist
        for directory in [self.csv_dir, self.config_dir]:
            os.makedirs(directory, exist_ok=True)

        print(f"📁 Data directory: {self.data_dir}")

    def find_pysystemtrade_root(self):
        """Find the pysystemtrade root directory"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        while current_dir != os.path.dirname(current_dir):
            if 'pysystemtrade' in os.path.basename(current_dir):
                return current_dir
            if os.path.exists(os.path.join(current_dir, 'pysystemtrade')):
                return os.path.join(current_dir, 'pysystemtrade')
            current_dir = os.path.dirname(current_dir)
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def download_etf_data(self, start_date="2018-01-01", end_date=None):
        """
        Download ETF data using either yfinance or Interactive Brokers
        """
        # Apply test mode date restriction
        if self.test_mode:
            start_date = (datetime.now() - timedelta(days=365 * 2)).strftime("%Y-%m-%d")
            print(f"⚠️ TEST MODE – start date set to {start_date}")

        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        # Apply instrument limiting
        if hasattr(self, 'max_instruments') and self.max_instruments > 0:
            tickers = self.instruments[:self.max_instruments]
            print(f"⚠️ LIMITED MODE: Using {self.max_instruments} instruments")
        else:
            tickers = self.instruments

        print(f"=== Downloading {len(tickers)} ETFs via {self.data_source.upper()} ===")

        if self.data_source == "yfinance":
            return self._download_yfinance_data(tickers, start_date, end_date)
        elif self.data_source == "ib":
            return self._download_ib_data(tickers, start_date, end_date)
        else:
            raise ValueError(f"Unknown data source: {self.data_source}")

    def _download_yfinance_data(self, tickers, start_date, end_date):
        """Original yfinance download logic"""
        # Move your existing yfinance download code here
        # ... (existing yfinance logic)

    def _download_ib_data(self, tickers, start_date, end_date):
        """New IB download method using our custom downloader"""
        try:
            from etf_ib_data_downloader import ETFIBDataDownloader

            # Initialize IB downloader
            ib_downloader = ETFIBDataDownloader(
                host=self.ib_config['host'],
                port=self.ib_config['port'],
                client_id=self.ib_config['client_id']
            )

            # Download data
            ib_data = ib_downloader.download_etf_data(
                etf_list=tickers,
                duration_str="5 Y",
                start_date=start_date,
                end_date=end_date
            )

            # Convert IB data to our internal format
            success_count = 0
            for ticker, df in ib_data.items():
                if not df.empty:
                    # Extract close prices (matching yfinance format)
                    price_data = df['close'].copy()
                    price_data.name = ticker

                    # Apply same quality filters as yfinance
                    if len(price_data) >= 250:  # At least 1 year
                        nan_percentage = price_data.isna().sum() / len(price_data)
                        if nan_percentage <= 0.05:  # Less than 5% NaN
                            # Clean data
                            price_data = price_data.ffill().bfill()

                            # Store in same format as yfinance
                            self.etf_data[ticker] = price_data
                            self.valid_instruments.append(ticker)
                            success_count += 1

            print(f"✅ IB Download complete: {success_count} successful")
            return success_count

        except ImportError:
            print("❌ etf_ib_data_downloader module not found")
            return 0
        except Exception as e:
            print(f"❌ IB download failed: {str(e)}")
            return 0

    # Add this method to your EnhancedETFSystem class
    def get_dividend_yield_data(self):
        """Get dividend yield data for carry calculations"""
        dividend_data = {}

        for instrument in self.valid_instruments:
            try:
                # Get ETF distribution yield
                etf = yf.Ticker(instrument)
                info = etf.info
                dividend_yield = info.get('dividendYield', info.get('yield', 0.0))

                # Convert to pandas Series with same index as price data
                price_data = self.etf_data[instrument]
                yield_series = pd.Series(
                    dividend_yield,
                    index=price_data.index,
                    name=f"{instrument}_dividend_yield"
                )
                dividend_data[instrument] = yield_series

            except Exception as e:
                print(f"{instrument}: Dividend yield fetch failed - {e}")
                # Default to 0% yield
                price_data = self.etf_data[instrument]
                dividend_data[instrument] = pd.Series(
                    0.0,
                    index=price_data.index,
                    name=f"{instrument}_dividend_yield"
                )

        return dividend_data

    def save_data_to_pysystemtrade(self):
        """Save ETF data in PySystemTrade CSV format"""
        print("=== Saving Data to PySystemTrade Format ===")

        if not self.etf_data:
            print("❌ No data to save")
            return False

        saved_count = 0

        for instrument, data in self.etf_data.items():
            try:
                # PySystemTrade expects PRICE column with DATETIME index
                df = pd.DataFrame({'PRICE': data})
                df.index.name = 'DATETIME'

                # Ensure datetime index
                if not isinstance(df.index, pd.DatetimeIndex):
                    df.index = pd.to_datetime(df.index)

                # Remove duplicates and sort
                df = df[~df.index.duplicated(keep='first')]
                df = df.sort_index()

                # Save to CSV
                csv_path = os.path.join(self.csv_dir, f"{instrument}.csv")
                df.to_csv(csv_path)

                print(f"✅ {instrument}: Saved ({len(df)} rows)")
                saved_count += 1

            except Exception as e:
                print(f"❌ {instrument}: Save failed - {e}")
                if instrument in self.valid_instruments:
                    self.valid_instruments.remove(instrument)

        print(f"📁 Saved {saved_count} instruments to PySystemTrade format")
        return saved_count > 0

    def verify_instrument_config(self):
        """Verify instrumentconfig.csv contains our ETFs"""
        print("=== Verifying Instrument Configuration ===")

        cfg_path = os.path.join(self.config_dir, "instrumentconfig.csv")

        if not os.path.exists(cfg_path):
            print(f"❌ instrumentconfig.csv not found at: {cfg_path}")
            return False

        try:
            config_df = pd.read_csv(cfg_path)
            available_instruments = set(config_df['Instrument'].tolist())

            # Check which ETFs are available
            found_instruments = []
            missing_instruments = []

            for instrument in self.valid_instruments:
                if instrument in available_instruments:
                    found_instruments.append(instrument)
                else:
                    missing_instruments.append(instrument)

            print(f"✅ Found {len(found_instruments)} ETFs in instrumentconfig.csv")
            if missing_instruments:
                print(f"⚠️ Missing {len(missing_instruments)} ETFs: {missing_instruments}")
                print("💡 These ETFs need to be added to instrumentconfig.csv")

            # Update valid instruments list
            self.valid_instruments = found_instruments

            # New: Limit instruments in test mode for faster computation
            if self.test_mode:
                print(f"⚠️ TEST MODE: Limiting to {self.max_instruments} instruments for faster execution")
                self.valid_instruments = self.valid_instruments[:self.max_instruments]
                # Recalculate normalized weights for limited set
                valid_weights = {k: v for k, v in self.instrument_weights.items() if k in self.valid_instruments}
                total_weight = sum(valid_weights.values())
                self.normalized_weights = {k: v / total_weight for k, v in valid_weights.items()}

            # Prepare normalized weights for valid instruments only
            valid_weights = {k: v for k, v in self.instrument_weights.items()
                             if k in self.valid_instruments}

            if valid_weights:
                total_weight = sum(valid_weights.values())
                self.normalized_weights = {k: v / total_weight for k, v in valid_weights.items()}
                print(f"🔄 Normalized weights for {len(self.valid_instruments)} working ETFs")

            return len(found_instruments) > 0

        except Exception as e:
            print(f"❌ Error reading instrumentconfig.csv: {e}")
            return False

    def calculate_performance_metrics(self, system, timeout_seconds=300):
        """
        Calculate performance metrics using the simplified performance calculator v3
        with proper P&L to capital conversion
        """
        print("=== Calculating Performance Metrics (Simplified Calculator v3) ===")
        try:
            # Initialize the simplified performance calculator
            calculator = SimplePerformanceCalculator(target_vol=self.vol_target / 100)

            # Calculate performance using the working calculator
            performance_metrics = calculator.calculate_performance(system)

            if performance_metrics is None:
                print("❌ Performance calculation failed")
                return None

            # Add system-specific metadata
            performance_metrics.update({
                'warm_up_days_applied': self.warm_up_days,
                'vol_target_percent': self.vol_target,
                'system_version': 'Enhanced ETF System v1.1'
            })

            return performance_metrics

        except Exception as e:
            print(f"❌ Performance calculation failed: {e}")
            import traceback
            traceback.print_exc()
            return None


    def create_carver_compliant_system(self):
        """Create system following strict Carver methodology"""
        print("=== Creating Carver-Compliant System ===")

        # Save data and verify configuration
        if not self.save_data_to_pysystemtrade():
            return None
        if not self.verify_instrument_config():
            return None

        # Carver-compliant system configuration
        system_config = {
            "instruments": self.valid_instruments,
            "instrument_weights": self.normalized_weights,
            "percentage_vol_target": self.vol_target,
            "base_currency": "USD",

            # Dynamic IDM (preserved)
            "use_instrument_div_mult_estimates": True,
            "use_instrument_weight_estimates": False,

            # CARVER METHODOLOGY: Pooled estimation
            "use_forecast_scale_estimates": True,
            "use_forecast_weight_estimates": True,
            "use_forecast_div_mult_estimates": True,

            # SINGLE SCALAR PER RULE
            "forecast_scalar_estimate": {
                "pool_instruments": True,
                "func": "sysquant.estimators.forecast_scalar.forecast_scalar",
                "window": 250000,
                "min_periods": 500,
                "backfill": True
            },

            # UNIFORM RULE WEIGHTS
            "forecast_weight_estimate": {
                "func": "sysquant.optimisation.generic_optimiser.genericOptimiser",
                "pool_gross_returns": True,
                "cost_multiplier": 2.5,
                "frequency": "W",
                "date_method": "expanding",
                "rollyears": 3,
                "method": "handcraft",
                "cleaning": True,
                "equalise_SR": False,
                "ann_target_SR": 0.5,
                "equalise_vols": True,
                "apply_cost_weight_filter": True
            },

            # Trading rules from config
            "trading_rules": {}
        }

        # Add all trading rules
        for rule_name, rule_config in self.trading_rules.items():
            system_config["trading_rules"][rule_name] = {
                "function": rule_config["function"],
                "data": rule_config["data"],
                "other_args": rule_config["other_args"]
            }

        try:
            data_paths = {
                'csvFuturesAdjustedPricesData': self.csv_dir,
                'csvFuturesInstrumentData': self.config_dir
            }
            # data = csvFuturesSimData(csv_data_paths=data_paths)
            dividend_data = self.get_dividend_yield_data()
            data = ETFSimData(csv_data_paths=data_paths, dividend_data=dividend_data)
            pst_config = Config(system_config)
            system = futures_system(config=pst_config, data=data)

            print(f"✅ Carver-compliant system created")
            print(f"📊 Single scalars per rule: ENABLED")
            print(f"🎯 Uniform weights across instruments: ENABLED")

            return system

        except Exception as e:
            print(f"❌ System creation failed: {e}")
            return None
