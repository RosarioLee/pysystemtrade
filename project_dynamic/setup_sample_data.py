#!/usr/bin/env python3
"""
Sample Data Setup and Validation for Dynamic Optimization Backtesting
====================================================================

This script validates and prepares sample data for Robert Carver's dynamic optimization system.
It ensures all required instruments have sufficient data for meaningful backtesting.

Key functions:
- Data availability validation
- Price data quality checks
- Missing data analysis
- Data export for external analysis

Author: Systematic Trading Implementation
Date: October 2025
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# pysystemtrade imports
from sysdata.sim.csv_futures_sim_data import csvFuturesSimData
from syscore.constants import arg_not_supplied


class SampleDataManager:
    """
    Manages sample data setup and validation for dynamic optimization backtesting
    """

    def __init__(self):
        """Initialize the data manager"""
        self.data_source = csvFuturesSimData()
        self.results_dir = 'project_dynamic/data'
        self.validation_results = {}

        # Create results directory
        os.makedirs(self.results_dir, exist_ok=True)

    def validate_data_availability(self, instrument_list=None):
        """
        Comprehensive validation of data availability for backtesting

        Args:
            instrument_list: List of instruments to validate (None = all available)
        """
        print(f"🔍 VALIDATING SAMPLE DATA AVAILABILITY")
        print(f"{'=' * 60}")

        # Get available instruments
        all_available = self.data_source.get_instrument_list()
        print(f"✓ Total instruments in sample data: {len(all_available)}")

        if instrument_list is None:
            # Use a representative subset for testing
            instrument_list = [
                'US10', 'US2', 'SOFR', 'SP500micro', 'NASDAQ',
                'EUROSTX', 'CORN', 'CRUDE_W', 'GOLD',
                'EUR', 'GBP', 'JPY'
            ]

        print(f"📋 Validating {len(instrument_list)} test instruments...")

        validation_results = []

        for instrument in instrument_list:
            result = self._validate_single_instrument(instrument)
            validation_results.append(result)

            # Print validation status
            status = "✓" if result['valid'] else "❌"
            print(f"{status} {instrument:12} | "
                  f"{result['start_date']} to {result['end_date']} | "
                  f"{result['data_points']:5d} points | "
                  f"{result['years']:.1f} years | "
                  f"Missing: {result['missing_pct']:.1f}%")

        # Summary statistics
        valid_instruments = [r for r in validation_results if r['valid']]
        invalid_instruments = [r for r in validation_results if not r['valid']]

        print(f"\n📊 VALIDATION SUMMARY")
        print(f"{'─' * 40}")
        print(f"Valid instruments:      {len(valid_instruments)}/{len(instrument_list)}")
        print(f"Invalid instruments:    {len(invalid_instruments)}")

        if invalid_instruments:
            print(f"\n❌ INVALID INSTRUMENTS:")
            for result in invalid_instruments:
                print(f"   {result['instrument']}: {result['issue']}")

        # Store results
        self.validation_results = {
            'all_results': validation_results,
            'valid_instruments': [r['instrument'] for r in valid_instruments],
            'invalid_instruments': [r['instrument'] for r in invalid_instruments]
        }

        return self.validation_results

    def _validate_single_instrument(self, instrument):
        """Validate data for a single instrument"""
        try:
            # Get price data
            prices = self.data_source.get_raw_price(instrument)

            if prices is None or len(prices) == 0:
                return {
                    'instrument': instrument,
                    'valid': False,
                    'issue': 'No price data available',
                    'data_points': 0,
                    'start_date': None,
                    'end_date': None,
                    'years': 0,
                    'missing_pct': 100.0
                }

            # Calculate statistics
            data_points = len(prices)
            start_date = prices.index[0].strftime('%Y-%m-%d')
            end_date = prices.index[-1].strftime('%Y-%m-%d')
            years = (prices.index[-1] - prices.index[0]).days / 365.25
            missing_pct = (prices.isna().sum() / len(prices)) * 100

            # Validation criteria
            min_years = 3.0  # Minimum years for meaningful backtest
            max_missing_pct = 5.0  # Maximum missing data percentage

            valid = (years >= min_years and
                     missing_pct <= max_missing_pct and
                     data_points >= 500)

            issue = None
            if not valid:
                if years < min_years:
                    issue = f"Insufficient history ({years:.1f} years < {min_years})"
                elif missing_pct > max_missing_pct:
                    issue = f"Too much missing data ({missing_pct:.1f}%)"
                elif data_points < 500:
                    issue = f"Too few data points ({data_points})"

            return {
                'instrument': instrument,
                'valid': valid,
                'issue': issue,
                'data_points': data_points,
                'start_date': start_date,
                'end_date': end_date,
                'years': years,
                'missing_pct': missing_pct
            }

        except Exception as e:
            return {
                'instrument': instrument,
                'valid': False,
                'issue': f'Error loading data: {str(e)}',
                'data_points': 0,
                'start_date': None,
                'end_date': None,
                'years': 0,
                'missing_pct': 100.0
            }

    def export_sample_data(self, instrument_list=None, output_format='csv'):
        """
        Export sample data for external analysis or backup

        Args:
            instrument_list: Instruments to export (None = all valid)
            output_format: 'csv' or 'pickle'
        """
        if not self.validation_results:
            print("❌ Run validation first")
            return

        valid_instruments = self.validation_results['valid_instruments']
        if instrument_list:
            export_instruments = [inst for inst in instrument_list if inst in valid_instruments]
        else:
            export_instruments = valid_instruments

        print(f"\n💾 EXPORTING SAMPLE DATA")
        print(f"{'─' * 40}")
        print(f"Exporting {len(export_instruments)} instruments...")

        export_data = {}

        for instrument in export_instruments:
            try:
                prices = self.data_source.get_raw_price(instrument)
                export_data[instrument] = prices
                print(f"✓ Exported {instrument}: {len(prices)} data points")

            except Exception as e:
                print(f"❌ Error exporting {instrument}: {str(e)}")

        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if output_format == 'csv':
            # Save as individual CSV files
            csv_dir = f"{self.results_dir}/csv_exports_{timestamp}"
            os.makedirs(csv_dir, exist_ok=True)

            for instrument, data in export_data.items():
                filename = f"{csv_dir}/{instrument}_prices.csv"
                data.to_csv(filename)

            print(f"✓ CSV files saved to: {csv_dir}")

        elif output_format == 'pickle':
            # Save as single pickle file
            pickle_file = f"{self.results_dir}/sample_data_{timestamp}.pkl"
            pd.to_pickle(export_data, pickle_file)
            print(f"✓ Pickle file saved: {pickle_file}")

    def generate_data_report(self):
        """Generate comprehensive data quality report"""
        if not self.validation_results:
            print("❌ Run validation first")
            return

        print(f"\n📋 GENERATING DATA QUALITY REPORT")
        print(f"{'─' * 40}")

        report_lines = []
        report_lines.append("ROBERT CARVER'S DYNAMIC OPTIMIZATION - DATA QUALITY REPORT")
        report_lines.append(f"Generated: {datetime.now()}")
        report_lines.append("=" * 80)

        # Summary section
        valid_count = len(self.validation_results['valid_instruments'])
        total_count = len(self.validation_results['all_results'])

        report_lines.append(f"\nSUMMARY")
        report_lines.append(f"{'─' * 40}")
        report_lines.append(f"Total instruments validated: {total_count}")
        report_lines.append(f"Valid for backtesting:       {valid_count}")
        report_lines.append(f"Success rate:                {valid_count / total_count * 100:.1f}%")

        # Detailed results
        report_lines.append(f"\nDETAILED VALIDATION RESULTS")
        report_lines.append(f"{'─' * 80}")
        report_lines.append(
            f"{'Instrument':<12} {'Valid':<6} {'Start Date':<12} {'End Date':<12} {'Years':<6} {'Points':<7} {'Missing%':<8} {'Issue'}")
        report_lines.append(f"{'─' * 80}")

        for result in self.validation_results['all_results']:
            status = "✓" if result['valid'] else "✗"
            issue = result['issue'] or ""

            report_lines.append(
                f"{result['instrument']:<12} {status:<6} "
                f"{result['start_date'] or 'N/A':<12} "
                f"{result['end_date'] or 'N/A':<12} "
                f"{result['years']:<6.1f} "
                f"{result['data_points']:<7} "
                f"{result['missing_pct']:<8.1f} "
                f"{issue}"
            )

        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"{self.results_dir}/data_quality_report_{timestamp}.txt"

        with open(report_file, 'w') as f:
            f.write('\n'.join(report_lines))

        print(f"✓ Report saved: {report_file}")

        # Print to console too
        for line in report_lines:
            print(line)


def main():
    """Main execution for data setup and validation"""
    print(f"📊 SAMPLE DATA SETUP FOR DYNAMIC OPTIMIZATION")
    print(f"Starting at: {datetime.now()}")

    # Initialize data manager
    data_manager = SampleDataManager()

    # Define test instruments (subset of Rob's portfolio)
    test_instruments = [
        'US10', 'US2', 'SOFR',  # Interest rates
        'SP500micro', 'NASDAQ', 'EUROSTX',  # Equities
        'CORN', 'CRUDE_W', 'GOLD',  # Commodities
        'EUR', 'GBP', 'JPY'  # FX
    ]

    # Validate data availability
    validation_results = data_manager.validate_data_availability(test_instruments)

    # Generate comprehensive report
    data_manager.generate_data_report()

    # Export valid data
    valid_instruments = validation_results['valid_instruments']
    if valid_instruments:
        data_manager.export_sample_data(valid_instruments, output_format='csv')

    print(f"\n✅ DATA SETUP COMPLETED")
    print(f"Valid instruments for backtesting: {valid_instruments}")
    print(f"Ready to run: python backtest_dynamic_system.py")


if __name__ == "__main__":
    main()
