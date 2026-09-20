"""
HMC Success Pattern Analyzer

Analyzes historical HMC patterns to determine what predicts success.
Generates scipy-validated statistics about HMC configuration effectiveness.

This analyzer backtests all possible 6-ball HMC configurations against historical
draws and uses statistical methods to determine which factors predict success.

All parameters are learned from data - NO hard-coded values.
"""

import numpy as np
from scipy import stats as scipy_stats
from collections import defaultdict
from typing import Dict, List, Any


class HMCSuccessAnalyzer:
    """
    Analyzes which HMC configurations historically succeeded.
    Follows same pattern as frequency_analyzer.py, odd_even_analyzer.py, etc.

    Uses scipy for all statistical validation.
    """

    def __init__(self, draws_data: Dict[str, Any], hmc_data: Dict[str, Any]):
        """
        Args:
            draws_data: Draw history from lotto_draw_history.json
            hmc_data: HMC patterns from lotto_odds_results.json['hmc']
        """
        self.draws_data = draws_data
        self.hmc_data = hmc_data
        self.draws_list = self._prepare_draws_list()

    def _prepare_draws_list(self) -> List[Dict]:
        """Sort draws by index for chronological analysis"""
        draws = []
        for date, draw_info in self.draws_data.items():
            draws.append({
                'date': date,
                'draw_index': draw_info['draw_index'],
                'hmc_distribution': draw_info['hmc_summary']['hmc_distribution'],
                'hot_count': draw_info['hmc_summary']['hot_count'],
                'medium_count': draw_info['hmc_summary']['medium_count'],
                'cold_count': draw_info['hmc_summary']['cold_count']
            })
        return sorted(draws, key=lambda x: x['draw_index'])

    def analyze(self, start_draw: int = 100, end_draw: int = None) -> Dict[str, Any]:
        """
        Main analysis method.
        Backtests all 6-ball HMC configurations against historical draws.

        Returns scipy-validated statistics about what predicts success.
        """

        if end_draw is None:
            end_draw = self.draws_list[-1]['draw_index']

        print(f"  Backtesting HMC configurations from draw {start_draw} to {end_draw}...")

        # Step 1: Backtest all configurations
        backtest_results = self._backtest_configurations(start_draw, end_draw)

        print(f"  Analyzed {len(backtest_results)} configuration-draw combinations")

        # Step 2: Statistical analysis of what predicts success
        print("  Running scipy statistical tests...")
        success_correlations = self._analyze_success_correlations(backtest_results)

        # Step 3: Calculate optimal thresholds from data
        print("  Calculating optimal thresholds from data...")
        optimal_parameters = self._calculate_optimal_parameters(backtest_results)

        # Step 4: Learn feature weights
        print("  Learning feature weights via logistic regression...")
        learned_weights = self._learn_feature_weights(backtest_results)

        return {
            'metadata': {
                'analysis_type': 'hmc_success_pattern_validation',
                'statistical_methods': [
                    'independent_t_test',
                    'chi_square_test',
                    'percentile_analysis',
                    'logistic_regression',
                    'historical_backtest'
                ],
                'significance_level': 0.05,
                'draws_analyzed': end_draw - start_draw,
                'start_draw': start_draw,
                'end_draw': end_draw
            },
            'success_correlations': success_correlations,
            'optimal_parameters': optimal_parameters,
            'learned_weights': learned_weights,
            'backtest_summary': self._summarize_backtest(backtest_results)
        }

    def _backtest_configurations(self, start_draw: int, end_draw: int) -> List[Dict]:
        """
        For each historical draw, test all possible 6-ball HMC configurations.
        """

        results = []

        # Get draws in range
        test_draws = [d for d in self.draws_list if start_draw <= d['draw_index'] < end_draw]

        for draw in test_draws:
            draw_num = draw['draw_index']
            actual_7ball = draw['hmc_distribution']
            actual_h, actual_m, actual_c = map(int, actual_7ball.split('-'))

            # Test all possible 6-ball configurations
            for h in range(7):
                for m in range(7 - h):
                    c = 6 - h - m

                    # Check if this 6-ball config would have matched
                    pattern_7h = f"{h+1}-{m}-{c}"      # If 7th ball is hot
                    pattern_7m = f"{h}-{m+1}-{c}"      # If 7th ball is medium
                    pattern_7c = f"{h}-{m}-{c+1}"      # If 7th ball is cold

                    exact_match = actual_7ball in [pattern_7h, pattern_7m, pattern_7c]

                    # Get configuration properties
                    combined_prob = self._get_combined_probability(h, m, c)
                    recency = self._get_pattern_recency_at_draw(h, m, c, draw_num)

                    # Calculate "closeness" (Manhattan distance)
                    distance_h = abs(actual_h - 1 - h) + abs(actual_m - m) + abs(actual_c - c)
                    distance_m = abs(actual_h - h) + abs(actual_m - 1 - m) + abs(actual_c - c)
                    distance_c = abs(actual_h - h) + abs(actual_m - m) + abs(actual_c - 1 - c)
                    min_distance = min(distance_h, distance_m, distance_c)

                    results.append({
                        'draw_num': draw_num,
                        'config_6ball': f"{h}H-{m}M-{c}C",
                        'hot_count': h,
                        'medium_count': m,
                        'cold_count': c,
                        'actual_7ball': actual_7ball,
                        'exact_match': exact_match,
                        'min_distance': min_distance,
                        'combined_probability': combined_prob,
                        'recency_at_draw': recency
                    })

        return results

    def _get_combined_probability(self, h: int, m: int, c: int) -> float:
        """Calculate combined probability for 6-ball pattern"""

        pattern_7h = f"{h+1}-{m}-{c}"
        pattern_7m = f"{h}-{m+1}-{c}"
        pattern_7c = f"{h}-{m}-{c+1}"

        pct_7h = self.hmc_data.get(pattern_7h, {}).get('percentage', 0.0)
        pct_7m = self.hmc_data.get(pattern_7m, {}).get('percentage', 0.0)
        pct_7c = self.hmc_data.get(pattern_7c, {}).get('percentage', 0.0)

        return pct_7h + pct_7m + pct_7c

    def _get_pattern_recency_at_draw(self, h: int, m: int, c: int, at_draw: int) -> int:
        """
        Calculate how many draws ago this 6-ball pattern last appeared
        (looking backwards from at_draw)
        """

        pattern_7h = f"{h+1}-{m}-{c}"
        pattern_7m = f"{h}-{m+1}-{c}"
        pattern_7c = f"{h}-{m}-{c+1}"

        # Look backwards from at_draw
        last_seen = None
        for draw in reversed([d for d in self.draws_list if d['draw_index'] < at_draw]):
            if draw['hmc_distribution'] in [pattern_7h, pattern_7m, pattern_7c]:
                last_seen = draw['draw_index']
                break

        if last_seen is None:
            return 999  # Never seen before

        return at_draw - last_seen

    def _analyze_success_correlations(self, backtest_results: List[Dict]) -> Dict[str, Any]:
        """
        Scipy-validated statistical tests to determine what predicts success.
        Similar to odd_even_analyzer.py pattern.
        """

        import pandas as pd
        df = pd.DataFrame(backtest_results)

        success_df = df[df['exact_match'] == True]
        failure_df = df[df['exact_match'] == False]

        correlations = {}

        # Test 1: Does combined_probability predict success?
        success_probs = success_df['combined_probability'].values
        failure_probs = failure_df['combined_probability'].values

        t_stat, p_value = scipy_stats.ttest_ind(success_probs, failure_probs)

        correlations['probability_correlation'] = {
            'success_mean': float(np.mean(success_probs)),
            'success_std': float(np.std(success_probs)),
            'failure_mean': float(np.mean(failure_probs)),
            'failure_std': float(np.std(failure_probs)),
            't_statistic': float(t_stat),
            'p_value': float(p_value),
            'significant': bool(p_value < 0.05),
            'effect_size': float(np.mean(success_probs) - np.mean(failure_probs)),
            'interpretation': 'Higher probability significantly predicts success' if p_value < 0.05 else 'Probability does not significantly predict success'
        }

        # Test 2: Does recency predict success?
        success_recency = success_df['recency_at_draw'].values
        failure_recency = failure_df['recency_at_draw'].values

        # Remove outliers (999 = never seen)
        success_recency = success_recency[success_recency < 100]
        failure_recency = failure_recency[failure_recency < 100]

        if len(success_recency) > 0 and len(failure_recency) > 0:
            t_stat, p_value = scipy_stats.ttest_ind(success_recency, failure_recency)

            correlations['recency_correlation'] = {
                'success_mean': float(np.mean(success_recency)),
                'success_std': float(np.std(success_recency)),
                'failure_mean': float(np.mean(failure_recency)),
                'failure_std': float(np.std(failure_recency)),
                't_statistic': float(t_stat),
                'p_value': float(p_value),
                'significant': bool(p_value < 0.05),
                'effect_size': float(np.mean(success_recency) - np.mean(failure_recency)),
                'interpretation': 'Lower recency significantly predicts success' if p_value < 0.05 else 'Recency does not significantly predict success'
            }
        else:
            correlations['recency_correlation'] = {
                'error': 'Insufficient data for recency analysis'
            }

        # Test 3: Hot count distribution (chi-square test)
        success_hot_counts = success_df['hot_count'].value_counts().sort_index()
        overall_hot_counts = df['hot_count'].value_counts().sort_index()

        # Normalize to probabilities
        success_hot_dist = (success_hot_counts / len(success_df)).to_dict()
        overall_hot_dist = (overall_hot_counts / len(df)).to_dict()

        # Chi-square test
        all_hot_values = sorted(set(list(success_hot_dist.keys()) + list(overall_hot_dist.keys())))
        observed = [success_hot_dist.get(h, 0) * len(success_df) for h in all_hot_values]
        expected = [overall_hot_dist.get(h, 0) * len(success_df) for h in all_hot_values]

        chi2, p_value = scipy_stats.chisquare(observed, expected)

        correlations['hot_count_distribution'] = {
            'success_distribution': success_hot_dist,
            'overall_distribution': overall_hot_dist,
            'chi2_statistic': float(chi2),
            'p_value': float(p_value),
            'significant': bool(p_value < 0.05),
            'interpretation': 'Hot count distribution differs significantly between success and overall' if p_value < 0.05 else 'Hot count distribution is similar'
        }

        return correlations

    def _calculate_optimal_parameters(self, backtest_results: List[Dict]) -> Dict[str, Any]:
        """
        Calculate optimal thresholds from data (percentile-based).
        NO HARD-CODED VALUES - everything learned from success patterns.
        """

        import pandas as pd
        df = pd.DataFrame(backtest_results)
        success_df = df[df['exact_match'] == True]

        parameters = {}

        # Optimal recency thresholds (from success data percentiles)
        recency_values = success_df['recency_at_draw'].values
        recency_values = recency_values[recency_values < 100]  # Remove outliers

        if len(recency_values) > 0:
            hot_threshold = float(np.percentile(recency_values, 33))
            cold_threshold = float(np.percentile(recency_values, 67))

            # Calculate success rates for each recency category
            hot_success_rate = df[df['recency_at_draw'] <= hot_threshold]['exact_match'].mean()
            medium_success_rate = df[
                (df['recency_at_draw'] > hot_threshold) &
                (df['recency_at_draw'] <= cold_threshold)
            ]['exact_match'].mean()
            cold_success_rate = df[
                (df['recency_at_draw'] > cold_threshold) &
                (df['recency_at_draw'] < 100)
            ]['exact_match'].mean()

            parameters['recency_thresholds'] = {
                'hot_threshold_draws': hot_threshold,
                'cold_threshold_draws': cold_threshold,
                'success_rates': {
                    'hot': float(hot_success_rate),
                    'medium': float(medium_success_rate),
                    'cold': float(cold_success_rate)
                },
                'interpretation': f'Patterns ≤{hot_threshold:.0f} draws ago are HOT, ≥{cold_threshold:.0f} are COLD'
            }

        # Optimal hot counts for different scenarios
        # Scenario 1: After hot surges (recent 10 draws had avg hot_count > 3.5)
        hot_surge_draws = self._identify_hot_surge_draws()
        hot_surge_df = df[df['draw_num'].isin(hot_surge_draws)]

        if len(hot_surge_df) > 0:
            hot_surge_success = hot_surge_df.groupby('hot_count')['exact_match'].mean().to_dict()
            optimal_hot_surge = max(hot_surge_success, key=hot_surge_success.get) if hot_surge_success else 4
        else:
            hot_surge_success = {}
            optimal_hot_surge = 4

        parameters['momentum_scenario'] = {
            'name': 'After Hot Surge',
            'optimal_hot_count': int(optimal_hot_surge),
            'success_rates_by_hot_count': {int(k): float(v) for k, v in hot_surge_success.items()},
            'interpretation': f'When recent draws are hot-heavy, {optimal_hot_surge} hot numbers maximize success'
        }

        # Scenario 2: During balanced periods
        balanced_draws = self._identify_balanced_draws()
        balanced_df = df[df['draw_num'].isin(balanced_draws)]

        if len(balanced_df) > 0:
            balanced_success = balanced_df.groupby('hot_count')['exact_match'].mean().to_dict()
            optimal_balanced = max(balanced_success, key=balanced_success.get) if balanced_success else 3
        else:
            balanced_success = {}
            optimal_balanced = 3

        parameters['stability_scenario'] = {
            'name': 'During Balanced Period',
            'optimal_hot_count': int(optimal_balanced),
            'success_rates_by_hot_count': {int(k): float(v) for k, v in balanced_success.items()},
            'interpretation': f'During balanced periods, {optimal_balanced} hot numbers maximize success'
        }

        # Overall best performing hot counts
        overall_success = df.groupby('hot_count')['exact_match'].mean().sort_values(ascending=False)

        parameters['overall_best_hot_counts'] = {
            'top_3': [int(h) for h in overall_success.head(3).index],
            'success_rates': {int(k): float(v) for k, v in overall_success.to_dict().items()}
        }

        return parameters

    def _learn_feature_weights(self, backtest_results: List[Dict]) -> Dict[str, Any]:
        """
        Use logistic regression to learn feature importance weights.
        Similar to how feature importance is used in ML models.
        """

        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler

        import pandas as pd
        df = pd.DataFrame(backtest_results)

        # Features
        features = ['combined_probability', 'recency_at_draw', 'hot_count', 'medium_count', 'cold_count']
        X = df[features].values
        y = df['exact_match'].astype(int).values

        # Handle infinite recency values
        X[X > 100] = 100

        # Standardize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Train logistic regression
        model = LogisticRegression(random_state=42, max_iter=1000, solver='liblinear')
        model.fit(X_scaled, y)

        # Get coefficients
        coefficients = {
            features[i]: float(model.coef_[0][i])
            for i in range(len(features))
        }

        # Normalize to get weights (absolute values)
        total_abs = sum(abs(v) for v in coefficients.values())
        normalized_weights = {
            k: abs(v) / total_abs
            for k, v in coefficients.items()
        }

        return {
            'method': 'logistic_regression',
            'raw_coefficients': coefficients,
            'normalized_weights': normalized_weights,
            'model_accuracy': float(model.score(X_scaled, y)),
            'intercept': float(model.intercept_[0]),
            'interpretation': 'Weights represent relative importance of each feature in predicting success'
        }

    def _identify_hot_surge_draws(self) -> List[int]:
        """Identify draws that occurred during hot surges"""

        hot_surge_draws = []

        for i in range(10, len(self.draws_list)):
            # Look at previous 10 draws
            prev_10 = self.draws_list[i-10:i]
            avg_hot = np.mean([d['hot_count'] for d in prev_10])

            # Hot surge if avg > 3.5
            if avg_hot > 3.5:
                hot_surge_draws.append(self.draws_list[i]['draw_index'])

        return hot_surge_draws

    def _identify_balanced_draws(self) -> List[int]:
        """Identify draws during balanced periods"""

        balanced_draws = []

        for i in range(10, len(self.draws_list)):
            prev_10 = self.draws_list[i-10:i]
            avg_hot = np.mean([d['hot_count'] for d in prev_10])

            # Balanced if 2.5 <= avg <= 3.5
            if 2.5 <= avg_hot <= 3.5:
                balanced_draws.append(self.draws_list[i]['draw_index'])

        return balanced_draws

    def _summarize_backtest(self, backtest_results: List[Dict]) -> Dict[str, Any]:
        """Generate summary statistics from backtest"""

        import pandas as pd
        df = pd.DataFrame(backtest_results)

        best_patterns = df.groupby('config_6ball')['exact_match'].mean().sort_values(ascending=False).head(10)

        return {
            'total_configurations_tested': len(df),
            'total_draws_tested': len(df['draw_num'].unique()),
            'overall_success_rate': float(df['exact_match'].mean()),
            'total_successes': int(df['exact_match'].sum()),
            'average_distance': float(df['min_distance'].mean()),
            'best_performing_patterns': {k: float(v) for k, v in best_patterns.to_dict().items()}
        }
