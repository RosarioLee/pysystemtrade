# performance_calculator_enhanced.py - Advanced ETF Performance Calculator v5.0

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from scipy import stats
import warnings
from typing import Dict, Any, Optional, List, Tuple
import logging

warnings.filterwarnings('ignore')


class AdvancedPerformanceCalculator:
    """
    Advanced ETF-compatible performance calculator with enhanced analytics
    """

    def __init__(self, target_vol: float = 0.12, warm_up_days: Optional[int] = None,
                 risk_free_rate: float = 0.02):
        self.target_vol = target_vol
        self.warm_up_days = warm_up_days
        self.risk_free_rate = risk_free_rate
        self.trading_days_per_year = 252

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def calculate_comprehensive_performance(self, system, timeout_seconds: int = 300) -> Optional[Dict[str, Any]]:
        """Calculate comprehensive performance analysis with enhanced metrics"""

        print("=== Advanced ETF Performance Analysis v5.0 ===")
        start_time = datetime.now()

        try:
            # Core portfolio performance with advanced metrics
            portfolio_metrics = self._calculate_advanced_portfolio_metrics(system)
            if portfolio_metrics is None:
                return None

            # Enhanced rule analysis with statistical significance
            rule_performance = self._analyze_rule_performance_advanced(system)

            # Advanced instrument analysis with correlation metrics
            instrument_performance = self._analyze_instrument_performance_advanced(system)

            # Comprehensive risk analysis
            risk_analysis = self._calculate_comprehensive_risk_metrics(system)

            # Market regime analysis
            regime_analysis = self._analyze_market_regimes(system)

            # Performance attribution
            attribution_analysis = self._calculate_performance_attribution(system)

            # Enhanced cost analysis
            cost_analysis = self._analyze_comprehensive_costs(system)

            # Advanced statistics
            advanced_stats = self._calculate_advanced_statistics(system)

            # Combine all analyses
            comprehensive_report = {
                'portfolio_metrics': portfolio_metrics,
                'rule_performance': rule_performance,
                'instrument_performance': instrument_performance,
                'risk_analysis': risk_analysis,
                'regime_analysis': regime_analysis,
                'attribution_analysis': attribution_analysis,
                'cost_analysis': cost_analysis,
                'advanced_statistics': advanced_stats,
                'calculation_time': (datetime.now() - start_time).total_seconds(),
                'timestamp': datetime.now(),
                'system_info': self._get_system_info(system)
            }

            self._display_comprehensive_report(comprehensive_report)
            return comprehensive_report

        except Exception as e:
            self.logger.error(f"Comprehensive performance calculation failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _calculate_advanced_portfolio_metrics(self, system) -> Optional[Dict[str, Any]]:
        """Calculate advanced portfolio performance metrics"""

        print("📈 Calculating Advanced Portfolio Metrics...")

        try:
            portfolio = system.accounts.portfolio()
            if portfolio is None:
                print("❌ Portfolio unavailable")
                return None

            # Get returns with multiple methods
            daily_returns = self._get_portfolio_returns(portfolio)
            if daily_returns is None or len(daily_returns) == 0:
                return None

            # Apply warm-up if specified
            if self.warm_up_days and len(daily_returns) > self.warm_up_days:
                daily_returns = daily_returns.iloc[self.warm_up_days:]
                print(f"🔧 Applied {self.warm_up_days}-day warm-up buffer")

            # Calculate comprehensive metrics
            metrics = self._calculate_enhanced_metrics(daily_returns)

            # Add rolling performance analysis
            rolling_metrics = self._calculate_rolling_metrics(daily_returns)
            metrics.update(rolling_metrics)

            # Add regime-specific performance
            regime_metrics = self._calculate_regime_performance(daily_returns)
            metrics.update(regime_metrics)

            return metrics

        except Exception as e:
            self.logger.error(f"Portfolio metrics calculation failed: {e}")
            return None

    def _get_portfolio_returns(self, portfolio) -> Optional[pd.Series]:
        """Extract portfolio returns using multiple fallback methods"""

        methods = [
            self._get_returns_percent_method,
            self._get_returns_pnl_method,
            self._get_returns_curve_method
        ]

        for i, method in enumerate(methods):
            try:
                returns = method(portfolio)
                if returns is not None and len(returns) > 0:
                    print(f"✅ Returns extracted using method {i + 1}")
                    return returns
            except Exception as e:
                print(f"⚠️ Method {i + 1} failed: {e}")
                continue

        return None

    def _get_returns_percent_method(self, portfolio) -> Optional[pd.Series]:
        """Method 1: Built-in percentage returns"""
        percent_portfolio = portfolio.percent
        if percent_portfolio is not None:
            percent_curve = percent_portfolio.curve()
            if len(percent_curve) > 1:
                return percent_curve.pct_change().dropna()
        return None

    def _get_returns_pnl_method(self, portfolio) -> Optional[pd.Series]:
        """Method 2: P&L curve conversion - CORRECTED"""
        try:
            pnl_curve = portfolio.curve()
            if len(pnl_curve) >= 2:
                pnl_clean = pnl_curve.dropna()
                if len(pnl_clean) >= 2:

                    # Check the scale and range of values
                    max_val = pnl_clean.max()
                    min_val = pnl_clean.min()
                    value_range = max_val - min_val

                    print(f"🔍 PnL curve analysis: min={min_val:.2f}, max={max_val:.2f}, range={value_range:.2f}")

                    # Method 1: If values look like cumulative P&L (starting near 0)
                    if abs(pnl_clean.iloc[0]) < 1.0 and value_range < 100:
                        # These are likely cumulative percentage returns
                        returns = pnl_clean.diff().dropna()
                        print("✅ Using diff() method for cumulative returns")

                    # Method 2: If values are large (absolute dollar amounts)
                    elif max_val > 1000 or abs(min_val) > 1000:
                        # Convert to percentage returns
                        initial_value = abs(pnl_clean.iloc[0]) if pnl_clean.iloc[
                                                                      0] != 0 else 1000000  # Assume $1M starting
                        returns = pnl_clean.pct_change().dropna()
                        print("✅ Using pct_change() method for large values")

                    # Method 3: Standard percentage change
                    else:
                        returns = pnl_clean.pct_change().dropna()
                        print("✅ Using standard pct_change() method")

                    # Clean extreme values
                    returns = returns.replace([np.inf, -np.inf], np.nan).dropna()

                    # Cap extreme daily returns at reasonable levels
                    returns = returns.clip(-0.20, 0.20)  # Cap at ±20% daily

                    # Additional validation
                    if len(returns) > 0:
                        daily_vol = returns.std()
                        if daily_vol > 0.1:  # More than 10% daily volatility is suspicious
                            print(f"⚠️ High daily volatility detected: {daily_vol:.1%}")
                            # Scale down if necessary
                            if daily_vol > 0.5:  # Extremely high volatility
                                returns = returns * 0.01  # Scale down by 100x
                                print("🔧 Scaled down extreme volatility")

                    return returns

            return None

        except Exception as e:
            print(f"❌ PnL method failed: {e}")
            return None

    def _get_returns_curve_method(self, portfolio) -> Optional[pd.Series]:
        """Method 3: Direct curve method"""
        curve = portfolio.curve()
        if len(curve) > 1:
            return curve.pct_change().dropna()
        return None

    def _calculate_enhanced_metrics(self, returns: pd.Series) -> Dict[str, Any]:
        """Calculate enhanced performance metrics"""

        # Clean returns
        returns = returns.replace([np.inf, -np.inf], np.nan).dropna()

        # Basic statistics
        mean_return = returns.mean()
        daily_std = returns.std()
        annual_return = mean_return * self.trading_days_per_year
        annual_vol = daily_std * np.sqrt(self.trading_days_per_year)

        # Risk-adjusted returns
        excess_return = annual_return - self.risk_free_rate
        sharpe_ratio = excess_return / annual_vol if annual_vol > 0 else 0

        # Drawdown analysis
        cumulative_returns = (1 + returns).cumprod()
        rolling_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        # Advanced risk metrics
        downside_returns = returns[returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(self.trading_days_per_year)
        sortino_ratio = excess_return / downside_deviation if downside_deviation > 0 else float('inf')

        # Calmar ratio
        calmar_ratio = abs(annual_return / max_drawdown) if max_drawdown != 0 else float('inf')

        # Win/loss analysis
        positive_returns = returns[returns > 0]
        negative_returns = returns[returns < 0]
        win_rate = len(positive_returns) / len(returns)
        avg_win = positive_returns.mean() if len(positive_returns) > 0 else 0
        avg_loss = negative_returns.mean() if len(negative_returns) > 0 else 0
        profit_factor = abs(avg_win * len(positive_returns)) / abs(avg_loss * len(negative_returns)) if len(
            negative_returns) > 0 and avg_loss != 0 else float('inf')

        # Statistical measures
        skewness = returns.skew()
        kurtosis = returns.kurtosis()

        # Value at Risk (VaR)
        var_95 = returns.quantile(0.05)
        var_99 = returns.quantile(0.01)
        cvar_95 = returns[returns <= var_95].mean()
        cvar_99 = returns[returns <= var_99].mean()

        # Maximum consecutive losses
        consecutive_losses = self._calculate_consecutive_losses(returns)

        # Tail ratio
        tail_ratio = returns.quantile(0.95) / abs(returns.quantile(0.05))

        return {
            'sharpe_ratio': float(sharpe_ratio),
            'sortino_ratio': float(sortino_ratio),
            'calmar_ratio': float(calmar_ratio),
            'annual_return': float(annual_return),
            'annual_volatility': float(annual_vol),
            'max_drawdown': float(max_drawdown),
            'downside_deviation': float(downside_deviation),
            'win_rate': float(win_rate),
            'profit_factor': float(profit_factor),
            'skewness': float(skewness),
            'kurtosis': float(kurtosis),
            'var_95': float(var_95),
            'var_99': float(var_99),
            'cvar_95': float(cvar_95),
            'cvar_99': float(cvar_99),
            'tail_ratio': float(tail_ratio),
            'max_consecutive_losses': consecutive_losses,
            'trading_days': len(returns),
            'years_analyzed': len(returns) / self.trading_days_per_year,
            'avg_daily_return': float(mean_return),
            'daily_volatility': float(daily_std)
        }

    def _calculate_rolling_metrics(self, returns: pd.Series) -> Dict[str, Any]:
        """Calculate rolling performance metrics"""

        windows = [30, 60, 120, 252]  # 1M, 2M, 4M, 1Y
        rolling_metrics = {}

        for window in windows:
            if len(returns) > window:
                rolling_returns = returns.rolling(window)
                rolling_sharpe = (rolling_returns.mean() / rolling_returns.std()) * np.sqrt(self.trading_days_per_year)

                rolling_metrics[f'rolling_sharpe_{window}d'] = {
                    'current': float(rolling_sharpe.iloc[-1]) if not np.isnan(rolling_sharpe.iloc[-1]) else 0,
                    'mean': float(rolling_sharpe.mean()),
                    'std': float(rolling_sharpe.std()),
                    'min': float(rolling_sharpe.min()),
                    'max': float(rolling_sharpe.max())
                }

        return {'rolling_metrics': rolling_metrics}

    def _calculate_regime_performance(self, returns: pd.Series) -> Dict[str, Any]:
        """Calculate performance in different market regimes"""

        # Define regimes based on volatility
        rolling_vol = returns.rolling(30).std() * np.sqrt(self.trading_days_per_year)
        vol_median = rolling_vol.median()

        low_vol_regime = returns[rolling_vol <= vol_median]
        high_vol_regime = returns[rolling_vol > vol_median]

        regime_metrics = {}

        for regime_name, regime_returns in [('low_volatility', low_vol_regime), ('high_volatility', high_vol_regime)]:
            if len(regime_returns) > 10:
                regime_sharpe = (regime_returns.mean() / regime_returns.std()) * np.sqrt(self.trading_days_per_year)
                regime_metrics[f'{regime_name}_regime'] = {
                    'sharpe': float(regime_sharpe) if not np.isnan(regime_sharpe) else 0,
                    'annual_return': float(regime_returns.mean() * self.trading_days_per_year),
                    'annual_vol': float(regime_returns.std() * np.sqrt(self.trading_days_per_year)),
                    'observations': len(regime_returns)
                }

        return {'regime_performance': regime_metrics}

    def _calculate_consecutive_losses(self, returns: pd.Series) -> int:
        """Calculate maximum consecutive losses"""

        losses = (returns < 0).astype(int)
        consecutive = []
        current_streak = 0

        for loss in losses:
            if loss:
                current_streak += 1
            else:
                if current_streak > 0:
                    consecutive.append(current_streak)
                current_streak = 0

        if current_streak > 0:
            consecutive.append(current_streak)

        return max(consecutive) if consecutive else 0

    def _analyze_rule_performance_advanced(self, system) -> Dict[str, Any]:
        """Advanced rule performance analysis with statistical significance"""

        print("🎯 Analyzing Advanced Rule Performance...")

        rule_performance = {}

        try:
            if not hasattr(system, 'rules') or not hasattr(system.rules, 'trading_rules'):
                return {}

            rules = system.rules.trading_rules()
            instruments = system.get_instrument_list()
            sample_instruments = instruments[:min(10, len(instruments))]

            for rule_name in rules.keys():
                try:
                    rule_data = self._analyze_single_rule_advanced(system, rule_name, sample_instruments)
                    if rule_data:
                        rule_performance[rule_name] = rule_data

                except Exception as e:
                    self.logger.warning(f"Could not analyze rule {rule_name}: {e}")
                    continue

            return rule_performance

        except Exception as e:
            self.logger.error(f"Rule performance analysis failed: {e}")
            return {}

    def _analyze_single_rule_advanced(self, system, rule_name: str, instruments: List[str]) -> Optional[Dict[str, Any]]:
        """Analyze single rule with advanced metrics"""

        rule_forecasts = []
        rule_returns = []

        for instrument in instruments:
            try:
                forecast = system.rules.get_raw_forecast(instrument, rule_name)
                if forecast is not None and len(forecast) > 0:
                    prices = system.rawdata.get_daily_prices(instrument)
                    if prices is not None and len(prices) > 1:
                        returns = prices.pct_change().dropna()

                        # Align data
                        aligned_data = pd.concat([forecast, returns], axis=1, join='inner')
                        aligned_data.columns = ['forecast', 'returns']
                        aligned_data = aligned_data.dropna()

                        if len(aligned_data) > 50:
                            rule_forecasts.extend(aligned_data['forecast'].values)
                            rule_returns.extend(aligned_data['returns'].values)

            except Exception as e:
                continue

        if len(rule_forecasts) < 100:
            return None

        rule_forecasts = np.array(rule_forecasts)
        rule_returns = np.array(rule_returns)

        # Calculate rule performance
        forecast_std = np.std(rule_forecasts)
        if forecast_std <= 1e-10:
            return None

        # Normalize forecasts
        normalized_forecasts = np.clip(rule_forecasts / forecast_std, -2, 2)

        # Calculate rule returns
        rule_specific_returns = normalized_forecasts * rule_returns

        if len(rule_specific_returns) < 50 or np.std(rule_specific_returns) <= 1e-10:
            return None

        # Advanced metrics
        mean_return = np.mean(rule_specific_returns)
        vol = np.std(rule_specific_returns)
        sharpe = (mean_return / vol) * np.sqrt(252) if vol > 0 else 0

        # Statistical significance
        t_stat, p_value = stats.ttest_1samp(rule_specific_returns, 0)

        # Information ratio
        tracking_error = np.std(rule_specific_returns - np.mean(rule_specific_returns))
        information_ratio = mean_return / tracking_error if tracking_error > 0 else 0

        # Hit rate analysis
        hit_rate = np.mean(rule_specific_returns > 0)

        # Consistency (% of rolling periods with positive Sharpe)
        if len(rule_specific_returns) > 252:
            rolling_sharpe = pd.Series(rule_specific_returns).rolling(63).apply(
                lambda x: (x.mean() / x.std()) * np.sqrt(252) if x.std() > 0 else 0
            )
            consistency = np.mean(rolling_sharpe > 0)
        else:
            consistency = 0.5

        return {
            'sharpe': float(sharpe),
            'information_ratio': float(information_ratio),
            'annual_return': float(mean_return * 252),
            'annual_volatility': float(vol * np.sqrt(252)),
            'hit_rate': float(hit_rate),
            'consistency': float(consistency),
            't_statistic': float(t_stat),
            'p_value': float(p_value),
            'is_significant': bool(p_value < 0.05),
            'data_points': len(rule_specific_returns),
            'instruments_used': len(instruments)
        }

    def _analyze_instrument_performance_advanced(self, system) -> Dict[str, Any]:
        """Advanced instrument performance analysis"""

        print("📊 Analyzing Advanced Instrument Performance...")

        instrument_performance = {}
        instruments = system.get_instrument_list()

        # Calculate correlation matrix
        returns_matrix = []
        valid_instruments = []

        for instrument in instruments:
            try:
                prices = system.rawdata.get_daily_prices(instrument)
                if prices is not None and len(prices) > 50:
                    returns = prices.pct_change().dropna()
                    if len(returns) > 0 and returns.std() > 0:
                        returns_matrix.append(returns)
                        valid_instruments.append(instrument)

                        # Individual instrument metrics
                        instrument_performance[instrument] = self._calculate_instrument_metrics(returns)

            except Exception as e:
                self.logger.warning(f"Could not analyze instrument {instrument}: {e}")
                continue

        # Calculate correlation matrix
        if len(returns_matrix) > 1:
            # Align all return series
            aligned_returns = pd.concat(returns_matrix, axis=1, join='inner')
            aligned_returns.columns = valid_instruments

            correlation_matrix = aligned_returns.corr()

            # Portfolio diversification metrics
            avg_correlation = correlation_matrix.values[np.triu_indices_from(correlation_matrix.values, k=1)].mean()
            max_correlation = correlation_matrix.values[np.triu_indices_from(correlation_matrix.values, k=1)].max()
            min_correlation = correlation_matrix.values[np.triu_indices_from(correlation_matrix.values, k=1)].min()

            diversification_metrics = {
                'average_correlation': float(avg_correlation),
                'max_correlation': float(max_correlation),
                'min_correlation': float(min_correlation),
                'correlation_matrix': correlation_matrix.to_dict()
            }

            return {
                'individual_performance': instrument_performance,
                'diversification_metrics': diversification_metrics,
                'valid_instruments': len(valid_instruments)
            }

        return {'individual_performance': instrument_performance}

    def _calculate_instrument_metrics(self, returns: pd.Series) -> Dict[str, Any]:
        """Calculate comprehensive metrics for individual instrument"""

        sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0
        annual_return = returns.mean() * 252
        annual_vol = returns.std() * np.sqrt(252)

        # Drawdown
        cumulative = (1 + returns).cumprod()
        rolling_max = cumulative.expanding().max()
        drawdown = (cumulative - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        # Tail risk
        var_95 = returns.quantile(0.05)

        return {
            'sharpe': float(sharpe),
            'annual_return': float(annual_return),
            'annual_volatility': float(annual_vol),
            'max_drawdown': float(max_drawdown),
            'var_95': float(var_95),
            'data_points': len(returns)
        }

    def _calculate_comprehensive_risk_metrics(self, system) -> Dict[str, Any]:
        """Calculate comprehensive risk analysis"""

        print("⚠️ Calculating Comprehensive Risk Metrics...")

        try:
            portfolio = system.accounts.portfolio()
            if portfolio is None:
                return {}

            returns = self._get_portfolio_returns(portfolio)
            if returns is None:
                return {}

            # Risk decomposition
            risk_metrics = {
                'volatility_analysis': self._analyze_volatility_patterns(returns),
                'tail_risk_analysis': self._analyze_tail_risk(returns),
                'drawdown_analysis': self._analyze_drawdown_patterns(returns),
                'correlation_risk': self._analyze_correlation_risk(system)
            }

            return risk_metrics

        except Exception as e:
            self.logger.error(f"Risk metrics calculation failed: {e}")
            return {}

    def _analyze_volatility_patterns(self, returns: pd.Series) -> Dict[str, Any]:
        """Analyze volatility clustering and patterns"""

        # Rolling volatility
        rolling_vol = returns.rolling(30).std() * np.sqrt(252)

        # Volatility clustering (ARCH effects)
        squared_returns = returns ** 2
        vol_autocorr = squared_returns.autocorr(lag=1)

        return {
            'current_volatility': float(rolling_vol.iloc[-1]) if len(rolling_vol) > 0 else 0,
            'average_volatility': float(rolling_vol.mean()),
            'volatility_std': float(rolling_vol.std()),
            'volatility_clustering': float(vol_autocorr) if not np.isnan(vol_autocorr) else 0
        }

    def _analyze_tail_risk(self, returns: pd.Series) -> Dict[str, Any]:
        """Analyze tail risk characteristics"""

        # Extreme value analysis
        tail_threshold = returns.quantile(0.05)
        tail_returns = returns[returns <= tail_threshold]

        return {
            'var_95': float(returns.quantile(0.05)),
            'var_99': float(returns.quantile(0.01)),
            'expected_shortfall_95': float(tail_returns.mean()) if len(tail_returns) > 0 else 0,
            'tail_events_count': len(tail_returns),
            'tail_frequency': float(len(tail_returns) / len(returns))
        }

    def _analyze_drawdown_patterns(self, returns: pd.Series) -> Dict[str, Any]:
        """Analyze drawdown patterns and recovery"""

        cumulative = (1 + returns).cumprod()
        rolling_max = cumulative.expanding().max()
        drawdown = (cumulative - rolling_max) / rolling_max

        # Drawdown periods
        in_drawdown = drawdown < -0.001
        drawdown_periods = []
        current_period = 0

        for is_dd in in_drawdown:
            if is_dd:
                current_period += 1
            else:
                if current_period > 0:
                    drawdown_periods.append(current_period)
                current_period = 0

        if current_period > 0:
            drawdown_periods.append(current_period)

        return {
            'max_drawdown': float(drawdown.min()),
            'average_drawdown_duration': float(np.mean(drawdown_periods)) if drawdown_periods else 0,
            'max_drawdown_duration': int(max(drawdown_periods)) if drawdown_periods else 0,
            'time_underwater': float(in_drawdown.mean()),
            'drawdown_periods_count': len(drawdown_periods)
        }

    def _analyze_correlation_risk(self, system) -> Dict[str, Any]:
        """Analyze correlation risk in the portfolio"""

        # This would analyze correlation breakdown during stress periods
        # Simplified implementation for now
        return {
            'correlation_breakdown_risk': 'Medium',  # Placeholder
            'stress_correlation': 0.7  # Placeholder
        }

    def _analyze_market_regimes(self, system) -> Dict[str, Any]:
        """Analyze performance across different market regimes"""

        print("📈 Analyzing Market Regimes...")

        try:
            portfolio = system.accounts.portfolio()
            if portfolio is None:
                return {}

            returns = self._get_portfolio_returns(portfolio)
            if returns is None:
                return {}

            # Define market regimes based on volatility and trend
            regimes = self._identify_market_regimes(returns)

            regime_performance = {}
            for regime_name, regime_mask in regimes.items():
                regime_returns = returns[regime_mask]
                if len(regime_returns) > 10:
                    regime_performance[regime_name] = {
                        'sharpe': float((regime_returns.mean() / regime_returns.std()) * np.sqrt(
                            252)) if regime_returns.std() > 0 else 0,
                        'annual_return': float(regime_returns.mean() * 252),
                        'hit_rate': float((regime_returns > 0).mean()),
                        'observations': len(regime_returns),
                        'frequency': float(len(regime_returns) / len(returns))
                    }

            return regime_performance

        except Exception as e:
            self.logger.error(f"Market regime analysis failed: {e}")
            return {}

    def _identify_market_regimes(self, returns: pd.Series) -> Dict[str, pd.Series]:
        """Identify different market regimes"""

        # Rolling statistics
        rolling_vol = returns.rolling(30).std()
        rolling_return = returns.rolling(30).mean()

        vol_median = rolling_vol.median()
        return_median = rolling_return.median()

        regimes = {
            'bull_low_vol': (rolling_return > return_median) & (rolling_vol <= vol_median),
            'bull_high_vol': (rolling_return > return_median) & (rolling_vol > vol_median),
            'bear_low_vol': (rolling_return <= return_median) & (rolling_vol <= vol_median),
            'bear_high_vol': (rolling_return <= return_median) & (rolling_vol > vol_median)
        }

        return regimes

    def _calculate_performance_attribution(self, system) -> Dict[str, Any]:
        """Calculate performance attribution analysis"""

        print("🔍 Calculating Performance Attribution...")

        # Simplified attribution analysis
        # In a full implementation, this would break down returns by:
        # - Asset allocation
        # - Security selection
        # - Trading rules contribution
        # - Interaction effects

        return {
            'asset_allocation_effect': 'TBD',  # Placeholder
            'security_selection_effect': 'TBD',  # Placeholder
            'trading_rules_contribution': 'TBD'  # Placeholder
        }

    def _analyze_comprehensive_costs(self, system) -> Dict[str, Any]:
        """Analyze comprehensive trading costs"""

        print("💰 Analyzing Comprehensive Costs...")

        # Enhanced cost analysis would include:
        # - Transaction costs
        # - Market impact
        # - Opportunity costs
        # - Financing costs

        return {
            'estimated_transaction_costs': 0.001,  # 10 bps estimate for ETFs
            'market_impact_costs': 0.0005,  # 5 bps estimate
            'total_estimated_costs': 0.0015,
            'cost_efficiency_score': 'High'  # ETFs are generally cost-efficient
        }

    def _calculate_advanced_statistics(self, system) -> Dict[str, Any]:
        """Calculate advanced statistical measures"""

        print("📊 Calculating Advanced Statistics...")

        try:
            portfolio = system.accounts.portfolio()
            if portfolio is None:
                return {}

            returns = self._get_portfolio_returns(portfolio)
            if returns is None:
                return {}

            # Advanced statistical tests
            from scipy.stats import jarque_bera, normaltest

            # Normality tests
            jb_stat, jb_pvalue = jarque_bera(returns.dropna())
            normal_stat, normal_pvalue = normaltest(returns.dropna())

            # Autocorrelation
            autocorr_1 = returns.autocorr(lag=1)
            autocorr_5 = returns.autocorr(lag=5)

            return {
                'normality_tests': {
                    'jarque_bera_stat': float(jb_stat),
                    'jarque_bera_pvalue': float(jb_pvalue),
                    'normal_test_stat': float(normal_stat),
                    'normal_test_pvalue': float(normal_pvalue),
                    'is_normal': bool(jb_pvalue > 0.05)
                },
                'autocorrelation': {
                    'lag_1': float(autocorr_1) if not np.isnan(autocorr_1) else 0,
                    'lag_5': float(autocorr_5) if not np.isnan(autocorr_5) else 0
                }
            }

        except Exception as e:
            self.logger.error(f"Advanced statistics calculation failed: {e}")
            return {}

    def _get_system_info(self, system) -> Dict[str, Any]:
        """Get system information"""

        return {
            'instruments_count': len(system.get_instrument_list()),
            'rules_count': len(system.rules.trading_rules()) if hasattr(system, 'rules') else 0,
            'system_type': 'Enhanced_ETF_System',
            'target_volatility': self.target_vol
        }

    def _display_comprehensive_report(self, report: Dict[str, Any]):
        """Display comprehensive performance report"""

        print(f"\n" + "=" * 100)
        print(f"📊 ENHANCED ETF SYSTEM COMPREHENSIVE PERFORMANCE REPORT v5.0")
        print(f"=" * 100)

        if 'portfolio_metrics' in report and report['portfolio_metrics']:
            metrics = report['portfolio_metrics']
            print(f"\n📈 PORTFOLIO PERFORMANCE:")
            print(f" • Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.3f}")
            print(f" • Sortino Ratio: {metrics.get('sortino_ratio', 0):.3f}")
            print(f" • Calmar Ratio: {metrics.get('calmar_ratio', 0):.3f}")
            print(f" • Annual Return: {metrics.get('annual_return', 0):.1%}")
            print(f" • Annual Volatility: {metrics.get('annual_volatility', 0):.1%}")
            print(f" • Maximum Drawdown: {metrics.get('max_drawdown', 0):.1%}")
            print(f" • Win Rate: {metrics.get('win_rate', 0):.1%}")
            print(f" • Profit Factor: {metrics.get('profit_factor', 0):.2f}")
            print(f" • VaR (95%): {metrics.get('var_95', 0):.2%}")
            print(f" • Tail Ratio: {metrics.get('tail_ratio', 0):.2f}")

        if 'rule_performance' in report and report['rule_performance']:
            print(f"\n🎯 TRADING RULE PERFORMANCE:")
            significant_rules = 0
            for rule_name, perf in report['rule_performance'].items():
                significance = "***" if perf.get('is_significant', False) else ""
                print(f" • {rule_name}: Sharpe {perf.get('sharpe', 0):.3f} "
                      f"(p={perf.get('p_value', 1):.3f}){significance}")
                if perf.get('is_significant', False):
                    significant_rules += 1
            print(f" • Statistically Significant Rules: {significant_rules}/{len(report['rule_performance'])}")

        if 'risk_analysis' in report and report['risk_analysis']:
            print(f"\n⚠️ RISK ANALYSIS:")
            risk = report['risk_analysis']
            if 'volatility_analysis' in risk:
                vol_analysis = risk['volatility_analysis']
                print(f" • Current Volatility: {vol_analysis.get('current_volatility', 0):.1%}")
                print(f" • Volatility Clustering: {vol_analysis.get('volatility_clustering', 0):.3f}")

            if 'tail_risk_analysis' in risk:
                tail_risk = risk['tail_risk_analysis']
                print(f" • VaR (99%): {tail_risk.get('var_99', 0):.2%}")
                print(f" • Expected Shortfall: {tail_risk.get('expected_shortfall_95', 0):.2%}")

        print(f"\n⏱️ Analysis completed in {report.get('calculation_time', 0):.1f} seconds")
        print(f"📅 Report generated: {report.get('timestamp', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"=" * 100)

    def diagnose_portfolio_data(self, system):
        """Diagnose portfolio data issues"""
        print("🔍 PORTFOLIO DATA DIAGNOSIS")
        print("=" * 40)

        try:
            portfolio = system.accounts.portfolio()
            if portfolio is None:
                print("❌ Portfolio is None")
                return

            # Check different curve methods
            methods = {
                'curve()': portfolio.curve(),
                'percent.curve()': portfolio.percent.curve() if hasattr(portfolio, 'percent') else None
            }

            for method_name, data in methods.items():
                if data is not None:
                    print(f"\n📊 {method_name}:")
                    print(f"   Length: {len(data)}")
                    print(f"   Range: {data.min():.2f} to {data.max():.2f}")
                    print(f"   First 5: {data.head().values}")
                    print(f"   Last 5: {data.tail().values}")

                    # Calculate returns
                    returns = data.pct_change().dropna()
                    if len(returns) > 0:
                        print(f"   Daily vol: {returns.std():.4f} ({returns.std() * np.sqrt(252):.1%} annual)")
                        print(f"   Daily mean: {returns.mean():.6f}")
                else:
                    print(f"\n❌ {method_name}: Not available")

        except Exception as e:
            print(f"❌ Diagnosis failed: {e}")


# Export the class
__all__ = ['AdvancedPerformanceCalculator']
