DATA DIRECTORY SETUP
====================

Place your price data CSV files in this directory.

Expected format for each instrument (e.g., SP500micro.csv):
- Columns: DATETIME, OPEN, HIGH, LOW, CLOSE, VOLUME
- Date format: YYYY-MM-DD
- Price data should be continuous (no gaps)

Example file structure:
¢u¢w¢w SP500micro.csv
¢u¢w¢w NASDAQmicro.csv  
¢u¢w¢w US10.csv
¢u¢w¢w EURUSD.csv
¢|¢w¢w ... (other instruments)

For sample data, you can:
1. Download from Yahoo Finance, Quandl, or other sources
2. Use the pysystemtrade data utilities
3. Create synthetic data for testing

Note: Make sure your CSV filenames match the instrument names 
in your dynamic_config.yaml file.
