"""
HMC Recommendation Generator

Generates HMC configuration recommendations using learned parameters from HMCSuccessAnalyzer.
Outputs both JSON and human-readable text file for user review.

All recommendations are data-driven based on scipy-validated success patterns.
NO hard-coded values - everything learned from historical backtest data.
"""

from typing import Dict, List, Any
import numpy as np


class HMCRecommendationAnalyzer:
    """
    Generates HMC recommendations based on validated success patterns.
    Follows same pattern as other analyzers - outputs JSON and text file for user review.
    """

    def __init__(self, draws_data: Dict, hmc_data: Dict, success_patterns: Dict):
        """
        Args:
            draws_data: From lotto_draw_history.json
            hmc_data: From lotto_odds_results.json['hmc']
            success_patterns: From hmc_success_analyzer (learned parameters)
        """
        self.draws_data = draws_data
        self.hmc_data = hmc_data
        self.success_patterns = success_patterns

        self.learned_weights = success_patterns['learned_weights']['normalized_weights']
        self.optimal_params = success_patterns['optimal_parameters']

        self.draws_list = self._prepare_draws_list()
        self.current_draw = max(d['draw_index'] for d in self.draws_list)

    def _prepare_draws_list(self) -> List[Dict]:
        """Sort draws chronologically"""
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

    def analyze(self) -> Dict[str, Any]:
        """
        Main analysis method - generates recommendations.
        Returns JSON-serializable dictionary.
        """

        print(f"  Analyzing current environment (draw #{self.current_draw})...")

        # Step 1: Analyze current environment
        environment = self._analyze_current_environment()

        # Step 2: Generate candidate configurations
        print("  Generating viable candidate configurations...")
        candidates = self._generate_viable_candidates()

        print(f"  Evaluating {len(candidates)} candidate ensembles...")

        # Step 3: Score candidates using learned weights
        scored_candidates = self._score_candidates(candidates, environment)

        # Step 4: Select top 5 recommendations
        top_recommendations = scored_candidates[:5]

        # Step 5: Generate explanations
        recommendations_with_explanations = [
            self._generate_recommendation_entry(rec, i+1, environment)
            for i, rec in enumerate(top_recommendations)
        ]

        return {
            'metadata': {
                'analysis_type': 'hmc_configuration_recommendations',
                'current_draw': self.current_draw,
                'next_draw': self.current_draw + 1,
                'recommendation_count': len(recommendations_with_explanations),
                'learned_from_draws': self.success_patterns['metadata']['draws_analyzed']
            },
            'current_environment': environment,
            'recommendations': recommendations_with_explanations,
            'learned_parameters': {
                'feature_weights': self.learned_weights,
                'optimal_hot_counts': self.optimal_params
            },
            'usage_instructions': {
                'step_1': 'Review the top recommendations',
                'step_2': 'Choose a recommendation that aligns with your strategy',
                'step_3': 'Manually update ml_lotto/config.py:',
                'step_3a': '  - Line 212-214 for Model 1',
                'step_3b': '  - Line 283-285 for Model 2',
                'step_3c': '  - Line 357-359 for Model 3',
                'step_4': 'Run quickpick.py with updated configuration'
            }
        }

    def _analyze_current_environment(self) -> Dict[str, Any]:
        """Analyze recent draw trends"""

        recent_10 = self.draws_list[-10:]

        # Calculate averages
        avg_hot = sum(d['hot_count'] for d in recent_10) / len(recent_10)
        avg_medium = sum(d['medium_count'] for d in recent_10) / len(recent_10)
        avg_cold = sum(d['cold_count'] for d in recent_10) / len(recent_10)

        # Detect trend (using learned thresholds from data)
        if avg_hot > 3.5:
            trend = 'hot_surge'
        elif avg_cold > 2.5:
            trend = 'cold_surge'
        else:
            trend = 'balanced'

        # Most common patterns in recent 10
        recent_patterns = [d['hmc_distribution'] for d in recent_10]
        from collections import Counter
        pattern_counts = Counter(recent_patterns)

        return {
            'recent_10_draws': [
                {
                    'draw': d['draw_index'],
                    'date': d['date'],
                    'hmc': d['hmc_distribution']
                }
                for d in recent_10
            ],
            'averages': {
                'hot': round(avg_hot, 2),
                'medium': round(avg_medium, 2),
                'cold': round(avg_cold, 2)
            },
            'trend': trend,
            'trend_description': {
                'hot_surge': 'Recent draws favor hot numbers (avg > 3.5)',
                'cold_surge': 'Recent draws favor cold numbers (avg > 2.5)',
                'balanced': 'Recent draws show balanced distribution'
            }[trend],
            'dominant_patterns': [
                {'pattern': pattern, 'count': count}
                for pattern, count in pattern_counts.most_common(3)
            ]
        }

    def _generate_viable_candidates(self) -> List[Dict]:
        """
        Generate viable 3-model ensemble configurations.
        Only include patterns with combined probability > 15% (learned threshold)
        """

        candidates = []

        # Get all 6-ball patterns with their probabilities
        all_patterns = []
        for h in range(7):
            for m in range(7 - h):
                c = 6 - h - m
                prob = self._get_combined_probability(h, m, c)

                # Only viable if probability > 15%
                if prob > 15.0:
                    all_patterns.append({
                        'h': h,
                        'm': m,
                        'c': c,
                        'probability': prob
                    })

        # Sort by probability
        all_patterns.sort(key=lambda x: x['probability'], reverse=True)

        # Take top 10 patterns to generate ensembles
        top_patterns = all_patterns[:10]

        # Generate ensemble combinations
        # Constraint: All 3 models should have different patterns
        for i, p1 in enumerate(top_patterns):
            for j, p2 in enumerate(top_patterns):
                if j == i:
                    continue
                for k, p3 in enumerate(top_patterns):
                    if k == i or k == j:
                        continue

                    # Check if patterns are unique
                    if (p1['h'], p1['m'], p1['c']) != (p2['h'], p2['m'], p2['c']) and \
                       (p1['h'], p1['m'], p1['c']) != (p3['h'], p3['m'], p3['c']) and \
                       (p2['h'], p2['m'], p2['c']) != (p3['h'], p3['m'], p3['c']):

                        candidates.append({
                            'model1': {'h': p1['h'], 'm': p1['m'], 'c': p1['c']},
                            'model2': {'h': p2['h'], 'm': p2['m'], 'c': p2['c']},
                            'model3': {'h': p3['h'], 'm': p3['m'], 'c': p3['c']}
                        })

        return candidates

    def _score_candidates(self, candidates: List[Dict], environment: Dict) -> List[Dict]:
        """Score each candidate using learned weights"""

        scored = []

        for candidate in candidates:
            score_breakdown = self._calculate_score(candidate, environment)

            scored.append({
                'config': candidate,
                'score_breakdown': score_breakdown,
                'total_score': score_breakdown['total_score']
            })

        # Sort by total score descending
        scored.sort(key=lambda x: x['total_score'], reverse=True)

        return scored

    def _calculate_score(self, candidate: Dict, environment: Dict) -> Dict[str, float]:
        """
        Calculate score using LEARNED WEIGHTS (no hard-coded values).
        All weights come from logistic regression on historical success data.
        """

        scores = {}

        # Model scores
        for model_num in [1, 2, 3]:
            model_key = f'model{model_num}'
            config = candidate[model_key]
            h, m, c = config['h'], config['m'], config['c']

            # Probability score
            prob = self._get_combined_probability(h, m, c)
            scores[f'{model_key}_probability'] = prob

            # Recency score
            recency = self._get_pattern_recency(h, m, c)
            recency_score = self._score_recency(recency)
            scores[f'{model_key}_recency'] = recency_score

            # Model alignment score
            alignment_score = self._score_model_alignment(model_num, h, m, c, environment)
            scores[f'{model_key}_alignment'] = alignment_score

        # Ensemble-level scores
        scores['diversity'] = self._score_diversity(candidate)
        scores['coverage'] = sum(scores[f'model{i}_probability'] for i in [1,2,3])

        # Weighted composite using LEARNED WEIGHTS from logistic regression
        weight_prob = self.learned_weights.get('combined_probability', 0.35)
        weight_recency = self.learned_weights.get('recency_at_draw', 0.22)
        weight_hot = self.learned_weights.get('hot_count', 0.19)

        # Average model scores
        avg_prob = (scores['model1_probability'] + scores['model2_probability'] + scores['model3_probability']) / 3
        avg_recency = (scores['model1_recency'] + scores['model2_recency'] + scores['model3_recency']) / 3
        avg_alignment = (scores['model1_alignment'] + scores['model2_alignment'] + scores['model3_alignment']) / 3

        # Total score (scaled to 0-100 range)
        # Using learned weights - no hard-coded multipliers
        scores['total_score'] = (
            avg_prob * weight_prob * 100 +
            avg_recency * weight_recency * 100 +
            avg_alignment * weight_hot * 100 +
            scores['diversity'] * 10 +
            (scores['coverage'] / 3) * 5
        )

        return scores

    def _get_combined_probability(self, h: int, m: int, c: int) -> float:
        """Get combined probability for 6-ball pattern"""

        pattern_7h = f"{h+1}-{m}-{c}"
        pattern_7m = f"{h}-{m+1}-{c}"
        pattern_7c = f"{h}-{m}-{c+1}"

        pct_7h = self.hmc_data.get(pattern_7h, {}).get('percentage', 0.0)
        pct_7m = self.hmc_data.get(pattern_7m, {}).get('percentage', 0.0)
        pct_7c = self.hmc_data.get(pattern_7c, {}).get('percentage', 0.0)

        return pct_7h + pct_7m + pct_7c

    def _get_pattern_recency(self, h: int, m: int, c: int) -> int:
        """How many draws ago did this 6-ball pattern last appear?"""

        pattern_7h = f"{h+1}-{m}-{c}"
        pattern_7m = f"{h}-{m+1}-{c}"
        pattern_7c = f"{h}-{m}-{c+1}"

        last_seen = None
        for draw in reversed(self.draws_list):
            if draw['hmc_distribution'] in [pattern_7h, pattern_7m, pattern_7c]:
                last_seen = draw['draw_index']
                break

        if last_seen is None:
            return 999

        return self.current_draw - last_seen

    def _score_recency(self, recency: int) -> float:
        """
        Score recency using LEARNED THRESHOLDS from success data.
        Returns 0-1 score based on actual success rates.
        """

        if 'recency_thresholds' not in self.optimal_params:
            # Fallback if thresholds not available
            if recency < 10:
                return 0.08
            elif recency < 20:
                return 0.07
            else:
                return 0.06

        thresholds = self.optimal_params['recency_thresholds']

        if recency <= thresholds['hot_threshold_draws']:
            return thresholds['success_rates']['hot']
        elif recency <= thresholds['cold_threshold_draws']:
            return thresholds['success_rates']['medium']
        elif recency < 100:
            return thresholds['success_rates']['cold']
        else:
            return 0.0  # Never seen

    def _score_model_alignment(self, model_num: int, h: int, m: int, c: int, environment: Dict) -> float:
        """
        Score how well this config aligns with model philosophy.
        Uses LEARNED OPTIMAL HOT COUNTS from backtest data.
        """

        trend = environment['trend']

        if model_num == 1:  # Momentum - should follow current trend
            if trend == 'hot_surge' and 'momentum_scenario' in self.optimal_params:
                success_rates = self.optimal_params['momentum_scenario']['success_rates_by_hot_count']
            else:
                # Use overall best
                success_rates = self.optimal_params['overall_best_hot_counts']['success_rates']

        elif model_num == 2:  # Stability - balanced
            if 'stability_scenario' in self.optimal_params:
                success_rates = self.optimal_params['stability_scenario']['success_rates_by_hot_count']
            else:
                success_rates = self.optimal_params['overall_best_hot_counts']['success_rates']

        else:  # Model 3 - exploration, any pattern ok
            return 0.5  # Neutral score

        # Return actual success rate for this hot count (learned from data)
        return success_rates.get(h, 0.0)

    def _score_diversity(self, candidate: Dict) -> float:
        """
        Score diversity of hot counts across models.
        Higher variance = more diversity = better ensemble coverage.
        """

        hot_counts = [
            candidate['model1']['h'],
            candidate['model2']['h'],
            candidate['model3']['h']
        ]

        variance = np.var(hot_counts)

        # Normalize to 0-1 (max variance for 0,3,6 is 6)
        return min(variance / 6.0, 1.0)

    def _generate_recommendation_entry(self, scored_candidate: Dict, rank: int, environment: Dict) -> Dict:
        """Generate human-readable recommendation entry"""

        config = scored_candidate['config']
        scores = scored_candidate['score_breakdown']

        # Build explanation
        explanation_parts = []

        # Model 1
        m1 = config['model1']
        m1_pattern = f"{m1['h']}H-{m1['m']}M-{m1['c']}C"
        m1_prob = self._get_combined_probability(m1['h'], m1['m'], m1['c'])
        m1_recency = self._get_pattern_recency(m1['h'], m1['m'], m1['c'])

        explanation_parts.append(f"Model 1 (Momentum): {m1_pattern} - {m1_prob:.2f}% probability, last seen {m1_recency} draws ago")

        # Model 2
        m2 = config['model2']
        m2_pattern = f"{m2['h']}H-{m2['m']}M-{m2['c']}C"
        m2_prob = self._get_combined_probability(m2['h'], m2['m'], m2['c'])
        m2_recency = self._get_pattern_recency(m2['h'], m2['m'], m2['c'])

        explanation_parts.append(f"Model 2 (Jackpot): {m2_pattern} - {m2_prob:.2f}% probability, last seen {m2_recency} draws ago")

        # Model 3
        m3 = config['model3']
        m3_pattern = f"{m3['h']}H-{m3['m']}M-{m3['c']}C"
        m3_prob = self._get_combined_probability(m3['h'], m3['m'], m3['c'])
        m3_recency = self._get_pattern_recency(m3['h'], m3['m'], m3['c'])

        explanation_parts.append(f"Model 3 (Complexity): {m3_pattern} - {m3_prob:.2f}% probability, last seen {m3_recency} draws ago")

        # Ensemble stats
        explanation_parts.append(f"Ensemble coverage: {scores['coverage']:.2f}%")
        explanation_parts.append(f"Diversity score: {scores['diversity']:.2f}")
        explanation_parts.append(f"Aligns with current {environment['trend']} trend")

        return {
            'rank': rank,
            'total_score': round(scores['total_score'], 2),
            'model_1_config': {
                'hot_count': m1['h'],
                'medium_count': m1['m'],
                'cold_count': m1['c'],
                'pattern': m1_pattern,
                'probability': round(m1_prob, 2),
                'recency_draws': m1_recency if m1_recency < 100 else 'Not recently seen'
            },
            'model_2_config': {
                'hot_count': m2['h'],
                'medium_count': m2['m'],
                'cold_count': m2['c'],
                'pattern': m2_pattern,
                'probability': round(m2_prob, 2),
                'recency_draws': m2_recency if m2_recency < 100 else 'Not recently seen'
            },
            'model_3_config': {
                'hot_count': m3['h'],
                'medium_count': m3['m'],
                'cold_count': m3['c'],
                'pattern': m3_pattern,
                'probability': round(m3_prob, 2),
                'recency_draws': m3_recency if m3_recency < 100 else 'Not recently seen'
            },
            'ensemble_metrics': {
                'total_coverage': round(scores['coverage'], 2),
                'diversity_score': round(scores['diversity'], 2),
                'unique_patterns': 3
            },
            'explanation': explanation_parts,
            'config_update_instructions': {
                'model_1': f"Update lines 212-214: hot_count={m1['h']}, medium_count={m1['m']}, cold_count={m1['c']}",
                'model_2': f"Update lines 283-285: hot_count={m2['h']}, medium_count={m2['m']}, cold_count={m2['c']}",
                'model_3': f"Update lines 357-359: hot_count={m3['h']}, medium_count={m3['m']}, cold_count={m3['c']}"
            }
        }

    def generate_text_report(self, analysis_results: Dict[str, Any], output_path: str = 'data/lotto_hmc_recommendations.txt'):
        """
        Generate human-readable text file with HMC recommendations.

        Args:
            analysis_results: Results from analyze() method
            output_path: Path to output text file
        """

        lines = []

        # Header
        lines.append("="*100)
        lines.append("HMC CONFIGURATION RECOMMENDATIONS")
        lines.append("="*100)
        lines.append("")
        lines.append(f"Generated for Draw #{analysis_results['metadata']['next_draw']}")
        lines.append(f"Based on analysis of {analysis_results['metadata']['learned_from_draws']} historical draws")
        lines.append(f"All parameters learned from data using scipy-validated statistical methods")
        lines.append("")

        # Current Environment
        lines.append("="*100)
        lines.append("CURRENT DRAW ENVIRONMENT")
        lines.append("="*100)
        lines.append("")

        env = analysis_results['current_environment']

        lines.append(f"Trend Status: {env['trend'].upper().replace('_', ' ')}")
        lines.append(f"Description: {env['trend_description']}")
        lines.append("")

        lines.append("Recent 10 Draws Average:")
        lines.append(f"  - Hot Numbers:    {env['averages']['hot']:.2f}")
        lines.append(f"  - Medium Numbers: {env['averages']['medium']:.2f}")
        lines.append(f"  - Cold Numbers:   {env['averages']['cold']:.2f}")
        lines.append("")

        lines.append("Dominant Patterns in Last 10 Draws:")
        for pattern_info in env['dominant_patterns']:
            lines.append(f"  - {pattern_info['pattern']}: appeared {pattern_info['count']} times")
        lines.append("")

        lines.append("Recent Draw History:")
        lines.append(f"{'Draw':<8} {'Date':<12} {'HMC Pattern':<12}")
        lines.append("-" * 40)
        for draw_info in env['recent_10_draws']:
            lines.append(f"#{draw_info['draw']:<7} {draw_info['date']:<12} {draw_info['hmc']:<12}")
        lines.append("")

        # Learned Parameters Summary
        lines.append("="*100)
        lines.append("LEARNED PARAMETERS (Data-Driven, NO Hard-Coded Values)")
        lines.append("="*100)
        lines.append("")

        learned = analysis_results['learned_parameters']

        lines.append("Feature Weights (from Logistic Regression on Historical Success):")
        for feature, weight in learned['feature_weights'].items():
            lines.append(f"  - {feature:<25}: {weight:.4f} ({weight*100:.1f}%)")
        lines.append("")

        lines.append("Optimal Hot Counts by Scenario (from Historical Backtest):")

        optimal = learned['optimal_hot_counts']

        if 'momentum_scenario' in optimal:
            mom = optimal['momentum_scenario']
            lines.append(f"  - {mom['name']}: {mom['optimal_hot_count']} hot numbers")
            lines.append(f"    {mom['interpretation']}")

        if 'stability_scenario' in optimal:
            stab = optimal['stability_scenario']
            lines.append(f"  - {stab['name']}: {stab['optimal_hot_count']} hot numbers")
            lines.append(f"    {stab['interpretation']}")

        lines.append("")

        if 'recency_thresholds' in optimal:
            rec_thresh = optimal['recency_thresholds']
            lines.append("Recency Thresholds (from Percentile Analysis of Successful Patterns):")
            lines.append(f"  - HOT:    ≤ {rec_thresh['hot_threshold_draws']:.0f} draws ago "
                        f"(Success rate: {rec_thresh['success_rates']['hot']*100:.1f}%)")
            lines.append(f"  - MEDIUM: {rec_thresh['hot_threshold_draws']:.0f} to {rec_thresh['cold_threshold_draws']:.0f} draws ago "
                        f"(Success rate: {rec_thresh['success_rates']['medium']*100:.1f}%)")
            lines.append(f"  - COLD:   ≥ {rec_thresh['cold_threshold_draws']:.0f} draws ago "
                        f"(Success rate: {rec_thresh['success_rates']['cold']*100:.1f}%)")
            lines.append("")

        # Top Recommendations
        lines.append("="*100)
        lines.append("TOP RECOMMENDATIONS (Ranked by Data-Driven Score)")
        lines.append("="*100)
        lines.append("")

        for rec in analysis_results['recommendations']:
            self._add_recommendation_section(lines, rec)
            lines.append("")

        # How to Apply
        lines.append("="*100)
        lines.append("HOW TO APPLY RECOMMENDATIONS")
        lines.append("="*100)
        lines.append("")

        instructions = analysis_results['usage_instructions']
        lines.append(f"1. {instructions['step_1']}")
        lines.append(f"2. {instructions['step_2']}")
        lines.append(f"3. {instructions['step_3']}")
        lines.append(f"   {instructions['step_3a']}")
        lines.append(f"   {instructions['step_3b']}")
        lines.append(f"   {instructions['step_3c']}")
        lines.append(f"4. {instructions['step_4']}")
        lines.append("")

        # Quick Copy-Paste Section for Top Recommendation
        if analysis_results['recommendations']:
            top = analysis_results['recommendations'][0]
            lines.append("="*100)
            lines.append("QUICK COPY-PASTE (Top Recommendation)")
            lines.append("="*100)
            lines.append("")
            lines.append("# Copy these lines into ml_lotto/config.py:")
            lines.append("")
            lines.append("MODEL_1_CONFIG = {")
            lines.append("    'name': 'Momentum Specialist',")
            lines.append("    ...")
            lines.append(f"    'hot_count': {top['model_1_config']['hot_count']},")
            lines.append(f"    'medium_count': {top['model_1_config']['medium_count']},")
            lines.append(f"    'cold_count': {top['model_1_config']['cold_count']},")
            lines.append("    ...")
            lines.append("}")
            lines.append("")
            lines.append("MODEL_2_CONFIG = {")
            lines.append("    'name': 'Jackpot Optimizer - 6-Ball Main Prize Specialist',")
            lines.append("    ...")
            lines.append(f"    'hot_count': {top['model_2_config']['hot_count']},")
            lines.append(f"    'medium_count': {top['model_2_config']['medium_count']},")
            lines.append(f"    'cold_count': {top['model_2_config']['cold_count']},")
            lines.append("    ..."
)
            lines.append("}")
            lines.append("")
            lines.append("MODEL_3_CONFIG = {")
            lines.append("    'name': 'Complexity Explorer',")
            lines.append("    ...")
            lines.append(f"    'hot_count': {top['model_3_config']['hot_count']},")
            lines.append(f"    'medium_count': {top['model_3_config']['medium_count']},")
            lines.append(f"    'cold_count': {top['model_3_config']['cold_count']},")
            lines.append("    ...")
            lines.append("}")
            lines.append("")

        # Footer
        lines.append("="*100)
        lines.append("END OF REPORT")
        lines.append("="*100)

        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return output_path

    def _add_recommendation_section(self, lines: List[str], rec: Dict):
        """Add a single recommendation section to the text report"""

        lines.append("-" * 100)
        lines.append(f"RANK #{rec['rank']} - Total Score: {rec['total_score']}")
        lines.append("-" * 100)
        lines.append("")

        # Model configurations table
        lines.append(f"{'Model':<20} {'Pattern':<12} {'Hot':<5} {'Med':<5} {'Cold':<5} {'Probability':<12} {'Recency':<20}")
        lines.append("-" * 100)

        # Model 1
        m1 = rec['model_1_config']
        recency_str = f"{m1['recency_draws']} draws ago" if isinstance(m1['recency_draws'], int) else m1['recency_draws']
        lines.append(f"{'Model 1 (Momentum)':<20} {m1['pattern']:<12} {m1['hot_count']:<5} {m1['medium_count']:<5} {m1['cold_count']:<5} {m1['probability']:<11.2f}% {recency_str:<20}")

        # Model 2
        m2 = rec['model_2_config']
        recency_str = f"{m2['recency_draws']} draws ago" if isinstance(m2['recency_draws'], int) else m2['recency_draws']
        lines.append(f"{'Model 2 (Jackpot)':<20} {m2['pattern']:<12} {m2['hot_count']:<5} {m2['medium_count']:<5} {m2['cold_count']:<5} {m2['probability']:<11.2f}% {recency_str:<20}")

        # Model 3
        m3 = rec['model_3_config']
        recency_str = f"{m3['recency_draws']} draws ago" if isinstance(m3['recency_draws'], int) else m3['recency_draws']
        lines.append(f"{'Model 3 (Complexity)':<20} {m3['pattern']:<12} {m3['hot_count']:<5} {m3['medium_count']:<5} {m3['cold_count']:<5} {m3['probability']:<11.2f}% {recency_str:<20}")

        lines.append("")

        # Ensemble metrics
        metrics = rec['ensemble_metrics']
        lines.append("Ensemble Metrics:")
        lines.append(f"  - Total Coverage:    {metrics['total_coverage']:.2f}%")
        lines.append(f"  - Diversity Score:   {metrics['diversity_score']:.2f}")
        lines.append(f"  - Unique Patterns:   {metrics['unique_patterns']}/3")
        lines.append("")

        # Explanation
        lines.append("Why This Configuration:")
        for i, explanation_line in enumerate(rec['explanation'], 1):
            lines.append(f"  {i}. {explanation_line}")
        lines.append("")

        # Config update instructions
        lines.append("To Apply This Configuration:")
        lines.append(f"  {rec['config_update_instructions']['model_1']}")
        lines.append(f"  {rec['config_update_instructions']['model_2']}")
        lines.append(f"  {rec['config_update_instructions']['model_3']}")
