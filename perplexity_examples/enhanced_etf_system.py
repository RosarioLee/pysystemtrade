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

warnings.filterwarnings('ignore')

from systems.provided.futures_chapter15.basesystem import futures_system
from sysdata.config.configdata import Config
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData


class EnhancedETFSystem:
    """
    Enhanced ETF Systematic Trading System v1.1

    Following Robert Carver's methodology with:
    - Multiple EWMAC momentum rules
    - Breakout strategies for diversification
    - Dynamic forecast scaling
    - Cost-aware optimization
    """

    def __init__(self, config_path=None):
        """Initialize the enhanced ETF system"""
        # Load configuration
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "config_v1.1.yaml"
            )

        try:
            with open(config_path, 'r') as file:
                self.config_data = yaml.safe_load(file)
        except FileNotFoundError:
            print(f"⚠️ Config file not found at: {config_path}")
            raise

        # Extract configuration
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
        """Download and validate ETF data"""
        print(f"=== Downloading {len(self.instruments)} ETFs ===")

        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        successful_downloads = 0
        failed_downloads = []

        for symbol in self.instruments:
            try:
                print(f"🔄 Downloading {symbol}...")

                # Download data
                raw_data = yf.download(symbol, start=start_date, end=end_date, auto_adjust=False)

                # Extract adjusted close price
                if isinstance(raw_data.columns, pd.MultiIndex):
                    if 'Adj Close' in raw_data.columns.get_level_values(0):
                        data = raw_data['Adj Close'].iloc[:, 0]
                    else:
                        data = raw_data.iloc[:, -1]
                else:
                    if 'Adj Close' in raw_data.columns:
                        data = raw_data['Adj Close']
                    else:
                        data = raw_data.iloc[:, -1]

                # Ensure Series format
                if not isinstance(data, pd.Series):
                    data = pd.Series(data.values, index=data.index, name=symbol)

                # Data quality validation
                if len(data) < 500:  # Minimum 500 days for robust analysis
                    print(f"⚠️ {symbol}: Insufficient data ({len(data)} days)")
                    failed_downloads.append(symbol)
                    continue

                # Check for excessive missing data
                null_count = data.isnull().sum()
                if null_count > len(data) * 0.05:  # More than 5% missing
                    print(f"⚠️ {symbol}: Too many missing values ({null_count})")
                    failed_downloads.append(symbol)
                    continue

                # Clean data
                data = data.ffill().bfill()

                # Final validation
                if data.isnull().sum() > 0:
                    print(f"⚠️ {symbol}: Still contains nulls after cleaning")
                    failed_downloads.append(symbol)
                    continue

                # Store successful download
                self.etf_data[symbol] = data
                self.valid_instruments.append(symbol)
                successful_downloads += 1
                print(f"✅ {symbol}: {len(data)} days")

            except Exception as e:
                print(f"❌ {symbol}: Download failed - {str(e)[:100]}...")
                failed_downloads.append(symbol)

        print(f"\n📊 Download Summary:")
        print(f"✅ Successful: {successful_downloads}")
        print(f"❌ Failed: {len(failed_downloads)}")
        if failed_downloads:
            print(f"Failed ETFs: {failed_downloads}")

        return successful_downloads

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

    def create_enhanced_system(self):
        """Create enhanced system with EWMAC + Breakout rules"""
        print("=== Creating Enhanced Multi-Strategy System ===")

        # Save data and verify configuration
        if not self.save_data_to_pysystemtrade():
            return None
        if not self.verify_instrument_config():
            return None

        # Enhanced system configuration
        system_config = {
            "instruments": self.valid_instruments,
            "instrument_weights": self.normalized_weights,
            "percentage_vol_target": self.vol_target,
            "base_currency": "USD",

            # Dynamic IDM (preserved)
            "use_instrument_div_mult_estimates": True,
            "use_instrument_weight_estimates": True,

            # Enhanced forecast estimation for mixed rule types
            "use_forecast_scale_estimates": True,
            "use_forecast_weight_estimates": True,
            "use_forecast_div_mult_estimates": True,

            # Trading rules from config
            "trading_rules": {}
        }

        # Add configuration parameters
        for key in ['instrument_div_mult_estimate', 'instrument_correlation_estimate',
                    'forecast_scalar_estimate', 'forecast_weight_estimate',
                    'forecast_div_mult_estimate']:
            if key in self.config_data:
                system_config[key] = self.config_data[key]

        # Add all rules from config
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
            data = csvFuturesSimData(csv_data_paths=data_paths)
            pst_config = Config(system_config)
            system = futures_system(config=pst_config, data=data)

            print(f"✅ Enhanced system created with {len(system.rules.trading_rules())} rules")
            return system

        except Exception as e:
            print(f"❌ Enhanced system creation failed: {e}")
            return None

    def calculate_performance_metrics(self, system):
        """Calculate comprehensive performance metrics"""
        print("=== Calculating Performance Metrics ===")

        try:
            portfolio_curve = system.accounts.portfolio()

            if portfolio_curve is None:
                print("⚠️ Portfolio curve not available")
                return None

            # Basic performance metrics
            sharpe_ratio = portfolio_curve.sharpe()
            annual_return = portfolio_curve.gross.resample('A').last().pct_change().mean()
            annual_volatility = portfolio_curve.percentage.std() * np.sqrt(252)

            # Drawdown analysis
            curve_data = portfolio_curve.curve()
            rolling_max = curve_data.expanding().max()
            drawdown = (curve_data - rolling_max) / rolling_max
            max_drawdown = drawdown.min()

            performance_metrics = {
                'sharpe_ratio': sharpe_ratio,
                'annual_return': annual_return,
                'annual_volatility': annual_volatility,
                'max_drawdown': max_drawdown,
                'portfolio_curve': portfolio_curve,
                'drawdown_series': drawdown
            }

            print(f"📊 Performance Metrics:")
            print(f"   Sharpe Ratio: {sharpe_ratio:.4f}")
            print(f"   Annual Return: {annual_return:.2%}")
            print(f"   Annual Volatility: {annual_volatility:.2%}")
            print(f"   Max Drawdown: {max_drawdown:.2%}")

            return performance_metrics

        except Exception as e:
            print(f"❌ Performance calculation failed: {e}")
            return None

    def get_system_summary(self, system):
        """Get comprehensive system summary"""
        try:
            instruments = system.get_instrument_list()
            rules = system.rules.trading_rules()

            ewmac_rules = [r for r in rules.keys() if 'ewmac' in r]
            breakout_rules = [r for r in rules.keys() if 'breakout' in r]

            summary = {
                'total_instruments': len(instruments),
                'total_rules': len(rules),
                'ewmac_rules': len(ewmac_rules),
                'breakout_rules': len(breakout_rules),
                'vol_target': self.vol_target,
                'instruments': instruments,
                'rules': rules,
                'ewmac_rule_list': ewmac_rules,
                'breakout_rule_list': breakout_rules
            }

            return summary

        except Exception as e:
            print(f"❌ System summary failed: {e}")
            return None
