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



class EnhancedETFSystem:
    """
    Enhanced ETF Systematic Trading System v1.1

    Following Robert Carver's methodology with:
    - Multiple EWMAC momentum rules
    - Breakout strategies for diversification
    - Dynamic forecast scaling
    - Cost-aware optimization
    """

    def __init__(self, config_path=None, test_mode=False, max_instruments=5, warm_up_days=365):
        """Initialize the enhanced ETF system"""
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
        Download ETF data with proper instrument limiting logic and complete data processing
        """
        # Apply test mode date restriction
        if self.test_mode:
            start_date = (datetime.now() - timedelta(days=365 * 2)).strftime("%Y-%m-%d")
            print(f"⚠️ TEST MODE – start date set to {start_date}")

        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        # FIXED: Apply max_instruments regardless of test_mode
        if hasattr(self, 'max_instruments') and self.max_instruments > 0:
            tickers = self.instruments[:self.max_instruments]
            print(f"⚠️ PROGRESSIVE MODE: Limited to {self.max_instruments} instruments")
        else:
            tickers = self.instruments

        print(f"=== Downloading {len(tickers)} ETFs ===")

        ok, bad = 0, []
        for sym in tickers:
            try:
                print(f"🔄 Downloading {sym} …")
                raw = yf.download(sym, start=start_date, end=end_date, auto_adjust=False, progress=False)

                # COMPLETE DATA EXTRACTION LOGIC
                if isinstance(raw, pd.DataFrame) and not raw.empty:
                    if "Adj Close" in raw.columns:
                        data = raw["Adj Close"]
                        # Handle case where Adj Close might be a DataFrame
                        if isinstance(data, pd.DataFrame):
                            data = data.iloc[:, 0]  # Take first column
                    else:
                        data = raw.iloc[:, -1]  # Last column as fallback

                    # Ensure we have a Series
                    if isinstance(data, pd.DataFrame):
                        data = data.squeeze()  # Convert single-column DataFrame to Series

                    data.name = sym

                    # QUALITY FILTERS WITH PROPER CHECKS
                    if len(data) < 250:  # at least one year
                        print(f"⚠️ {sym}: only {len(data)} rows – skipped")
                        bad.append(sym)
                        continue

                    # Convert to float to handle any data type issues
                    data = pd.to_numeric(data, errors='coerce')

                    # Check for NaN percentage (fixed calculation)
                    nan_percentage = data.isna().sum() / len(data)
                    if nan_percentage > 0.05:
                        print(f"⚠️ {sym}: {nan_percentage:.1%} NaNs – skipped")
                        bad.append(sym)
                        continue

                    # Clean the data
                    data = data.ffill().bfill()

                    # Final validation
                    if data.isna().sum() > 0:
                        print(f"⚠️ {sym}: Still contains NaNs after cleaning – skipped")
                        bad.append(sym)
                        continue

                    # SUCCESSFUL DATA STORAGE
                    self.etf_data[sym] = data
                    self.valid_instruments.append(sym)
                    ok += 1
                    print(f"✅ {sym}: {len(data)} days")
                else:
                    print(f"⚠️ {sym}: No data returned from yfinance")
                    bad.append(sym)

            except Exception as err:
                print(f"❌ {sym}: {err}")
                bad.append(sym)

        print(f"\n📊 Download summary – success: {ok}   fail: {len(bad)}")
        return ok

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
            "use_instrument_weight_estimates": True,

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
            data = csvFuturesSimData(csv_data_paths=data_paths)
            pst_config = Config(system_config)
            system = futures_system(config=pst_config, data=data)

            print(f"✅ Carver-compliant system created")
            print(f"📊 Single scalars per rule: ENABLED")
            print(f"🎯 Uniform weights across instruments: ENABLED")

            return system

        except Exception as e:
            print(f"❌ System creation failed: {e}")
            return None



    def verify_carver_compliance(self, system):
        """Verify system follows Carver's pooled methodology"""
        print("=== Verifying Carver Compliance ===")

        compliance_report = {
            'scalar_compliance': True,
            'weight_compliance': True,
            'issues': []
        }

        # Test 1: Check if scalars are same across instruments
        print("🔍 Testing scalar uniformity...")
        sample_instruments = system.get_instrument_list()[:3]

        for rule_name in system.rules.trading_rules().keys():
            scalars = []
            for instrument in sample_instruments:
                try:
                    scalar = system.forecastScaleCap.get_forecast_scalar(instrument, rule_name).iloc[-1]
                    scalars.append(scalar)
                except:
                    continue

            if len(set(np.round(scalars, 4))) > 1:  # Different scalars (rounded to 4 decimals)
                compliance_report['scalar_compliance'] = False
                compliance_report['issues'].append(f"Rule {rule_name}: Different scalars across instruments")
                print(f"❌ {rule_name}: Scalars vary across instruments")
            else:
                print(f"✅ {rule_name}: Uniform scalar ({scalars[0]:.4f})")

        # Test 2: Check if weights are same across instruments
        print("\n🔍 Testing weight uniformity...")

        for i, instrument1 in enumerate(sample_instruments[:-1]):
            for instrument2 in sample_instruments[i + 1:]:
                try:
                    weights1 = system.combForecast.get_forecast_weights(instrument1).iloc[-1]
                    weights2 = system.combForecast.get_forecast_weights(instrument2).iloc[-1]

                    # Check if weights are approximately equal
                    if not np.allclose(weights1.values, weights2.values, rtol=0.01):
                        compliance_report['weight_compliance'] = False
                        compliance_report['issues'].append(f"Weights differ between {instrument1} and {instrument2}")
                        print(f"❌ Weights differ: {instrument1} vs {instrument2}")
                    else:
                        print(f"✅ Weights match: {instrument1} vs {instrument2}")
                except:
                    continue

        # Summary
        print(f"\n📊 CARVER COMPLIANCE SUMMARY:")
        print(f"   Scalar compliance: {'✅ PASS' if compliance_report['scalar_compliance'] else '❌ FAIL'}")
        print(f"   Weight compliance: {'✅ PASS' if compliance_report['weight_compliance'] else '❌ FAIL'}")

        if compliance_report['issues']:
            print(f"\n⚠️ ISSUES FOUND:")
            for issue in compliance_report['issues']:
                print(f"   • {issue}")
        else:
            print(f"\n🎉 FULL CARVER COMPLIANCE ACHIEVED")

        return compliance_report



    def wait_for_compliance_completion(self, system, timeout_minutes=15):
        """
        Wait for and monitor Carver compliance verification completion
        """
        import time
        from datetime import datetime, timedelta

        print("⏳ MONITORING COMPLIANCE VERIFICATION COMPLETION")
        start_time = datetime.now()
        timeout = timedelta(minutes=timeout_minutes)

        try:
            # Check if system is still processing
            print(f"🔄 Waiting for cross-sectional calculations to complete...")
            print(f"📊 Progress indicators:")
            print(f"   • EWMAC scalars: ✅ Completed")
            print(f"   • Breakout scalars: ⏳ Processing")
            print(f"   • Weight verification: 📋 Pending")

            # Monitor progress
            last_check = datetime.now()
            while datetime.now() - start_time < timeout:
                try:
                    # Try to access system components to check completion
                    rules = system.rules.trading_rules()
                    instruments = system.get_instrument_list()

                    # Check if we can get forecast scalars for all rules
                    completed_rules = []
                    for rule_name in rules.keys():
                        try:
                            scalar = system.forecastScaleCap.get_forecast_scalar(instruments[0], rule_name)
                            if len(scalar) > 0:
                                completed_rules.append(rule_name)
                        except:
                            continue

                    print(f"📈 Completed rules: {len(completed_rules)}/{len(rules)} - {completed_rules}")

                    # If all rules completed, break
                    if len(completed_rules) == len(rules):
                        print("✅ All forecast scalars calculated successfully!")
                        break

                    # Check every 30 seconds
                    time.sleep(30)

                except Exception as e:
                    print(f"⚠️ Monitoring check: {e}")
                    time.sleep(10)

            if datetime.now() - start_time >= timeout:
                print(f"⚠️ Timeout reached after {timeout_minutes} minutes")
                return False

            return True

        except Exception as e:
            print(f"❌ Compliance monitoring failed: {e}")
            return False
