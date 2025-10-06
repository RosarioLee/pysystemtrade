# etf_ib_data_downloader.py - Enhanced IB Data Downloader for ETF Systematic Trading

from ib_insync import IB, Stock, util
from datetime import datetime, timedelta
import pandas as pd
from typing import List, Optional, Dict
import time
import os
import warnings

warnings.filterwarnings('ignore')


class ETFIBDataDownloader:
    """
    Enhanced Interactive Brokers data downloader specifically designed for ETF systematic trading.

    Based on proven working pattern from your original ib_download_data.py
    """

    def __init__(self,
                 host="127.0.0.1",
                 port=7497,
                 client_id=100,
                 max_concurrent=5,
                 cache_dir="./ib_data_cache"):
        """Initialize the ETF IB data downloader"""

        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        self.max_concurrent = max_concurrent
        self.cache_dir = cache_dir

        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)

        # Data storage
        self.etf_data = {}
        self.valid_instruments = []
        self.failed_downloads = []

        # Connection management
        self.connected = False

        print(f"🔧 ETF IB Data Downloader initialized")
        print(f"🏠 Host: {host}:{port} (Client ID: {client_id})")
        print(f"📁 Cache directory: {cache_dir}")

    def connect(self):
        """Connect to TWS/IB Gateway with enhanced error handling"""
        if self.connected:
            print("✅ Already connected to IB")
            return True

        try:
            self.ib.connect(self.host, self.port, self.client_id)
            self.connected = True
            print("✅ Successfully connected to Interactive Brokers")
            return True

        except ConnectionRefusedError:
            print("❌ Connection refused - ensure TWS/IB Gateway is running with API enabled")
            print("💡 Check: Enable API in TWS Global Configuration > API Settings")
            return False

        except Exception as e:
            print(f"❌ Connection error: {str(e)}")
            return False

    def disconnect(self):
        """Safely disconnect from IB"""
        try:
            if self.connected and self.ib.isConnected():
                self.ib.disconnect()
                self.connected = False
                print("🔌 Disconnected from Interactive Brokers")
        except Exception as e:
            print(f"⚠️ Disconnect warning: {str(e)}")

    def _fetch_single_etf(self,
                          ticker: str,
                          duration_str: str = "5 Y",
                          start_date: datetime = None,
                          end_date: datetime = None) -> Optional[pd.DataFrame]:
        """
        Fetch historical data for a single ETF using the PROVEN WORKING PATTERN
        from your original ib_download_data.py
        """
        try:
            # Create ETF contract (Stock type works for ETFs)
            contract = Stock(ticker, 'SMART', 'USD')

            # Request historical data - same pattern as original
            bars = self.ib.reqHistoricalData(
                contract,
                endDateTime='',
                durationStr=duration_str,
                barSizeSetting='1 day',
                whatToShow='ADJUSTED_LAST',
                useRTH=True,
                keepUpToDate=False,
                formatDate=2
            )

            if not bars:
                print(f"⚠️ {ticker}: No data received from IB")
                return None

            # Convert to DataFrame - same as original
            df = util.df(bars)[['date', 'open', 'high', 'low', 'close']]

            # **KEY FIX**: Use the EXACT same filtering pattern as your working original
            if start_date or end_date:
                start_date_obj = pd.to_datetime(start_date) if start_date else None
                end_date_obj = pd.to_datetime(end_date) if end_date else None
                df['date'] = pd.to_datetime(df['date'])

                if start_date_obj is not None and end_date_obj is not None:
                    df = df[(df['date'] >= start_date_obj) & (df['date'] <= end_date_obj)]
                elif start_date_obj is not None:
                    df = df[df['date'] >= start_date_obj]
                elif end_date_obj is not None:
                    df = df[df['date'] <= end_date_obj]

            # Set index - same as original
            return df.set_index('date')

        except Exception as e:
            print(f"❌ {ticker}: Fetch failed - {str(e)}")
            return None

    def _get_cache_path(self, ticker: str, duration_str: str, start_date: str, end_date: str) -> str:
        """Generate cache file path"""
        cache_filename = f"{ticker}_{duration_str.replace(' ', '')}_{start_date}_{end_date}.csv"
        return os.path.join(self.cache_dir, cache_filename)

    def fetch_with_cache(self,
                         ticker: str,
                         duration_str: str = "5 Y",
                         start_date: datetime = None,
                         end_date: datetime = None,
                         force_refresh: bool = False) -> Optional[pd.DataFrame]:
        """
        Fetch data with intelligent caching - using datetime objects like original
        """
        # Set defaults using datetime objects (like original)
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = datetime.now() - timedelta(days=1825)  # ~5 years

        # Generate cache path using string dates
        start_str = start_date.strftime('%Y%m%d')
        end_str = end_date.strftime('%Y%m%d')
        cache_path = self._get_cache_path(ticker, duration_str, start_str, end_str)

        if not force_refresh and os.path.exists(cache_path):
            try:
                cached_data = pd.read_csv(cache_path, index_col=0, parse_dates=True)
                print(f"📋 {ticker}: Loaded from cache ({len(cached_data)} rows)")
                return cached_data
            except Exception as e:
                print(f"⚠️ {ticker}: Cache read failed - {str(e)}, fetching fresh data")

        # Fetch fresh data using datetime objects (not strings!)
        df = self._fetch_single_etf(ticker, duration_str, start_date, end_date)

        if df is not None and not df.empty:
            # Cache the data
            try:
                df.to_csv(cache_path)
                print(f"💾 {ticker}: Cached data ({len(df)} rows)")
            except Exception as e:
                print(f"⚠️ {ticker}: Cache save failed - {str(e)}")

        return df

    def download_etf_data(self,
                          etf_list: List[str],
                          duration_str: str = "5 Y",
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None,
                          force_refresh: bool = False) -> Dict[str, pd.DataFrame]:
        """
        Download data for multiple ETFs with rate limiting and quality control
        """
        if not self.connect():
            return {}

        print(f"=== Downloading {len(etf_list)} ETFs from Interactive Brokers ===")

        # Convert string dates to datetime objects (like original)
        start_dt = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None

        success_count = 0
        self.etf_data = {}
        self.valid_instruments = []
        self.failed_downloads = []

        for i, ticker in enumerate(etf_list):
            try:
                # Rate limiting - pause every few requests
                if i > 0 and i % self.max_concurrent == 0:
                    print(f"⏸️ Rate limiting pause...")
                    time.sleep(2)

                print(f"🔄 [{i + 1}/{len(etf_list)}] Downloading {ticker}...")

                # Fetch data using datetime objects
                df = self.fetch_with_cache(
                    ticker=ticker,
                    duration_str=duration_str,
                    start_date=start_dt,
                    end_date=end_dt,
                    force_refresh=force_refresh
                )

                if df is not None and not df.empty:
                    # Quality validation
                    if self._validate_etf_data(ticker, df):
                        self.etf_data[ticker] = df
                        self.valid_instruments.append(ticker)
                        success_count += 1
                        print(f"✅ {ticker}: Success ({len(df)} days)")
                    else:
                        self.failed_downloads.append(ticker)
                else:
                    print(f"❌ {ticker}: No data received")
                    self.failed_downloads.append(ticker)

                # Brief pause between requests
                time.sleep(0.5)

            except Exception as e:
                print(f"❌ {ticker}: Download failed - {str(e)}")
                self.failed_downloads.append(ticker)

        print(f"\n📊 Download Summary:")
        print(f"✅ Successful: {success_count}")
        print(f"❌ Failed: {len(self.failed_downloads)}")

        if self.failed_downloads:
            print(f"Failed ETFs: {', '.join(self.failed_downloads)}")

        return self.etf_data

    def _validate_etf_data(self, ticker: str, df: pd.DataFrame) -> bool:
        """Validate ETF data quality using Robert Carver's standards"""

        # Minimum data requirement
        if len(df) < 250:  # At least 1 year of daily data
            print(f"⚠️ {ticker}: Insufficient data ({len(df)} days < 250)")
            return False

        # Check for excessive missing data
        close_data = df['close']
        nan_percentage = close_data.isna().sum() / len(close_data)

        if nan_percentage > 0.05:  # More than 5% missing
            print(f"⚠️ {ticker}: Too many missing values ({nan_percentage:.1%})")
            return False

        # Check for price anomalies
        price_changes = close_data.pct_change().abs()
        extreme_moves = (price_changes > 0.5).sum()  # 50%+ moves

        if extreme_moves > len(close_data) * 0.001:  # More than 0.1% extreme moves
            print(f"⚠️ {ticker}: Suspicious price movements detected")
            return False

        return True

    def save_to_pysystemtrade_format(self,
                                     output_dir: str,
                                     price_column: str = 'close') -> bool:
        """
        Save ETF data in PySystemTrade CSV format
        """
        if not self.etf_data:
            print("❌ No data to save")
            return False

        os.makedirs(output_dir, exist_ok=True)
        saved_count = 0

        print(f"=== Saving {len(self.etf_data)} ETFs to PySystemTrade format ===")

        for ticker, df in self.etf_data.items():
            try:
                # Extract price data
                price_data = df[price_column].copy()

                # Clean data
                price_data = price_data.ffill().bfill()

                # Create PySystemTrade format DataFrame
                pst_df = pd.DataFrame({'PRICE': price_data})
                pst_df.index.name = 'DATETIME'

                # Remove duplicates and sort
                pst_df = pst_df[~pst_df.index.duplicated(keep='first')]
                pst_df = pst_df.sort_index()

                # Save to CSV
                output_path = os.path.join(output_dir, f"{ticker}.csv")
                pst_df.to_csv(output_path)

                print(f"✅ {ticker}: Saved to {output_path} ({len(pst_df)} rows)")
                saved_count += 1

            except Exception as e:
                print(f"❌ {ticker}: Save failed - {str(e)}")

        print(f"📁 Saved {saved_count}/{len(self.etf_data)} ETFs successfully")
        return saved_count > 0

    def get_download_summary(self) -> Dict:
        """Get comprehensive download summary"""
        return {
            'total_requested': len(self.valid_instruments) + len(self.failed_downloads),
            'successful_downloads': len(self.valid_instruments),
            'failed_downloads': len(self.failed_downloads),
            'success_rate': len(self.valid_instruments) / (
                        len(self.valid_instruments) + len(self.failed_downloads)) if (len(self.valid_instruments) + len(
                self.failed_downloads)) > 0 else 0,
            'valid_instruments': self.valid_instruments,
            'failed_instruments': self.failed_downloads
        }

    def __del__(self):
        """Cleanup on object destruction"""
        self.disconnect()


# Usage example and testing
if __name__ == "__main__":
    # Initialize downloader
    downloader = ETFIBDataDownloader(
        host="127.0.0.1",
        port=7497,
        client_id=100
    )

    # Test with a few ETFs
    test_etfs = ['SPY', 'QQQ', 'IVV', 'VTI']

    # Download data
    data = downloader.download_etf_data(
        etf_list=test_etfs,
        duration_str="2 Y",
        start_date="2022-01-01"
    )

    # Save to PySystemTrade format
    if data:
        downloader.save_to_pysystemtrade_format("./test_data_output")

    # Print summary
    summary = downloader.get_download_summary()
    print(f"\nFinal Summary: {summary}")
