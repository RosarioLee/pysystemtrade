import yaml
import pandas as pd
from collections import OrderedDict

# Read your current config to get instrument list
with open('dynamic_backtest_config.yaml', 'r') as f:
    config = yaml.safe_load(f)

instruments = config['instruments']

# Define asset class groupings
asset_classes = {
    'BONDS': ['US10', 'US2', 'US20', 'US30', 'US5', 'SOFR', 'FED',
              'BUND', 'BOBL', 'SHATZ', 'BUXL', 'BTP', 'BTP3', 'OAT',
              'EURIBOR', 'JGB-SGX-mini'],
    'EQUITIES': ['SP500_micro', 'NASDAQ_micro', 'RUSSELL', 'R1000', 'DOW',
                 'EUROSTX', 'EUROSTX-LARGE', 'EURO600', 'CAC', 'DAX', 'AEX',
                 'SMI', 'MIB', 'IBEX_mini', 'FTSE100', 'NIKKEI', 'TOPIX',
                 'KOSPI_mini', 'HANG_mini', 'FTSECHINAA', 'FTSECHINAH',
                 'MSCIASIA', 'MSCIWORLD', 'BOVESPA', 'SP400', 'RUSSELL_mini',
                 'DOW_mini', 'NASDAQ', 'SP500'],
    'FX': ['EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'NOK', 'SEK',
           'NZD', 'MXP', 'SGD', 'INR'],
    'COMMODITIES': ['CRUDE_W', 'BRENT-LAST', 'GAS_US', 'HEATOIL', 'GASOILINE',
                    'GOLD', 'SILVER', 'PLAT', 'PALLAD', 'COPPER', 'ALUMINIUM',
                    'IRON', 'CORN', 'WHEAT', 'SOYBEAN', 'OATIES', 'RICE',
                    'COTTON', 'SUGAR11', 'COFFEE', 'COCOA', 'OJ', 'LEANHOG',
                    'LIVECOW', 'FEEDCOW', 'LUMBER-new', 'BBCOMM', 'SOYMEAL',
                    'SOYOIL', 'REDWHEAT', 'MILLWHEAT', 'ROBUSTA', 'CANOLA'],
    'VOLATILITY': ['VIX', 'V2X'],
    'CRYPTO': ['BITCOIN', 'ETHEREUM'],
    'US_SECTORS': ['US-TECH', 'US-HEALTH', 'US-FINANCE', 'US-ENERGY',
                   'US-DISCRETE', 'US-STAPLES', 'US-INDUSTRY', 'US-MATERIAL',
                   'US-UTILS', 'US-PROPERTY']
}


# SCENARIO 1: Equal weights within each asset class
def equal_weights_scenario(asset_allocations):
    """
    asset_allocations: dict like {'BONDS': 0.20, 'EQUITIES': 0.30, ...}
    """
    weights = {}
    for asset_class, allocation in asset_allocations.items():
        instruments_in_class = asset_classes[asset_class]
        n_instruments = len(instruments_in_class)
        weight_per_instrument = allocation / n_instruments

        for inst in instruments_in_class:
            weights[inst] = weight_per_instrument

    return normalize_weights(weights)


# SCENARIO 2: Correlation-adjusted weights
def correlation_adjusted_weights(asset_allocations, correlation_adjustments):
    """
    correlation_adjustments: dict of dicts
    Example: {'BONDS': {'US10': 0.8, 'US2': 0.8, 'BUND': 1.2}, ...}
    Instruments not listed get weight of 1.0
    """
    weights = {}

    for asset_class, allocation in asset_allocations.items():
        instruments_in_class = asset_classes[asset_class]

        # Get adjustment factors (default to 1.0 if not specified)
        adjustments = correlation_adjustments.get(asset_class, {})
        adjusted_weights = {inst: adjustments.get(inst, 1.0)
                            for inst in instruments_in_class}

        # Normalize within asset class
        total_adjusted = sum(adjusted_weights.values())

        for inst in instruments_in_class:
            weights[inst] = allocation * (adjusted_weights[inst] / total_adjusted)

    return normalize_weights(weights)


# SCENARIO 3: Custom weights per instrument
def custom_weights(custom_dict):
    """
    custom_dict: dict with exact weights per instrument
    """
    return normalize_weights(custom_dict)


def normalize_weights(weights):
    """Ensure weights sum to exactly 1.0"""
    total = sum(weights.values())
    return {k: round(v / total, 6) for k, v in weights.items()}


def weights_to_yaml_string(weights, scenario_name):
    """Convert weights dict to properly formatted YAML string"""
    # Create ordered dict to maintain instrument order
    ordered_weights = OrderedDict()

    # Group by asset class for readability
    for asset_class, instruments_list in asset_classes.items():
        for inst in instruments_list:
            if inst in weights:
                ordered_weights[inst] = weights[inst]

    # Format as YAML
    yaml_lines = [f"\n# === SCENARIO: {scenario_name} ==="]
    yaml_lines.append("instrument_weights:")

    current_class = None
    for asset_class, instruments_list in asset_classes.items():
        class_weights = {k: v for k, v in ordered_weights.items()
                         if k in instruments_list}
        if class_weights:
            yaml_lines.append(f"  # {asset_class} ({len(class_weights)} instruments)")
            for inst, weight in class_weights.items():
                yaml_lines.append(f"  {inst}: {weight:.6f}")

    return '\n'.join(yaml_lines)


# ========== DEFINE YOUR SCENARIOS ==========

# Scenario 1: Equal weights with your preferred asset allocation
scenario1_allocation = {
    'BONDS': 0.15,
    'EQUITIES': 0.25,
    'FX': 0.15,
    'COMMODITIES': 0.35,
    'VOLATILITY': 0.045,
    'CRYPTO': 0.045,
    'US_SECTORS': 0.01
}

weights_scenario1 = equal_weights_scenario(scenario1_allocation)

# Scenario 2: Correlation-adjusted (reduce highly correlated instruments)
scenario2_adjustments = {
    'BONDS': {
        # Reduce correlated US rates
        'US2': 0.7, 'US5': 0.7, 'US10': 0.7, 'US20': 0.7, 'US30': 0.7,
        # Increase independent rates
        'SOFR': 1.3, 'FED': 1.3, 'JGB-SGX-mini': 1.5
    },
    'EQUITIES': {
        # Reduce correlated US equity indices
        'SP500_micro': 0.6, 'NASDAQ_micro': 0.6, 'RUSSELL': 0.6,
        'DOW': 0.6, 'SP500': 0.6, 'NASDAQ': 0.6,
        # Increase regional diversity
        'NIKKEI': 1.2, 'HANG_mini': 1.2, 'BOVESPA': 1.2
    },
    'COMMODITIES': {
        # Reduce correlated energy
        'CRUDE_W': 0.8, 'BRENT-LAST': 0.8,
        # Reduce correlated grains
        'WHEAT': 0.7, 'REDWHEAT': 0.7, 'MILLWHEAT': 0.7
    }
}

weights_scenario2 = correlation_adjusted_weights(scenario1_allocation,
                                                 scenario2_adjustments)

# ========== ANALYSIS AND OUTPUT ==========

# Create comparison DataFrame
df_comparison = pd.DataFrame({
    'Scenario_1_Equal': pd.Series(weights_scenario1),
    'Scenario_2_Corr_Adjusted': pd.Series(weights_scenario2)
})

# Add asset class column
df_comparison['Asset_Class'] = ''
for asset_class, instruments_list in asset_classes.items():
    for inst in instruments_list:
        if inst in df_comparison.index:
            df_comparison.loc[inst, 'Asset_Class'] = asset_class

# Reorder columns
df_comparison = df_comparison[['Asset_Class', 'Scenario_1_Equal',
                               'Scenario_2_Corr_Adjusted']]

# Save to Excel for review
df_comparison.to_excel('instrument_weights_comparison.xlsx')

print("Comparison saved to: instrument_weights_comparison.xlsx")
print(f"\nScenario 1 sum: {sum(weights_scenario1.values()):.6f}")
print(f"Scenario 2 sum: {sum(weights_scenario2.values()):.6f}")

# Generate YAML strings ready to paste into PyCharm
yaml_s1 = weights_to_yaml_string(weights_scenario1, "Equal Weights")
yaml_s2 = weights_to_yaml_string(weights_scenario2, "Correlation Adjusted")

# Save to text files for easy copy-paste
with open('weights_scenario1.txt', 'w') as f:
    f.write(yaml_s1)

with open('weights_scenario2.txt', 'w') as f:
    f.write(yaml_s2)

print("\nYAML snippets saved to:")
print("  - weights_scenario1.txt")
print("  - weights_scenario2.txt")
print("\nJust copy-paste the content into your config file!")

# Preview first scenario
print("\n" + "=" * 60)
print("PREVIEW - Scenario 1 (first 10 instruments):")
print("=" * 60)
print('\n'.join(yaml_s1.split('\n')[:15]))
