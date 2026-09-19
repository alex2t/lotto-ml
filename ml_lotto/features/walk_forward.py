"""
walk_forward.py
===============
Point-in-Time Walk-Forward Feature Extraction Engine.

Eliminates future data lookahead bias and static feature vectors during ML training.
For each historical draw t in [start_index, end_index), extracts feature
vectors for numbers 1-47 using ONLY data from draws 0 to t-1.

VERSION: 1.0 (Leak-Free Dynamic Panel Edition)
- Vectorized cumulative appearances and rolling frequency counts
- True point-in-time recency (days_since_last, days_since_bonus)
- Historical gap statistics (volatility, consistency, max gap ratio)
- Dynamic HMC classification and recency zone scoring per draw
- Dynamic freshness bins, weights, and momentum per draw
- Dynamic bonus ball indicators and bonus-to-main window status
- Dynamic pairwise and triple feature interactions
"""

import copy
import time
from collections import defaultdict, deque
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np

from ml_lotto.config import MAX_NUMBER, TRAINING_START_DRAW
from lotto_analysis.config.config import HMC_HOT_THRESHOLD, HMC_COLD_THRESHOLD
from ml_lotto.features.timing import calculate_recency_zone_score, load_recency_zones
from ml_lotto.features.interactions import InteractionFeatureCalculator

# Two weeks of a three-draws-a-week schedule: enough to see every current draw day.
SCHEDULE_DRAWS = 6


def next_draw_date(draw_dates: List[pd.Timestamp]) -> pd.Timestamp:
    """
    The first day after the last draw that falls on a current draw weekday.

    The schedule is read from the weekdays of the latest SCHEDULE_DRAWS draws, so a change
    such as the 2026 move from Wed/Sat to Mon/Wed/Sat is picked up from the data.
    """
    weekdays = {d.weekday() for d in draw_dates[-SCHEDULE_DRAWS:]}
    day = draw_dates[-1] + pd.Timedelta(days=1)
    while day.weekday() not in weekdays:
        day += pd.Timedelta(days=1)
    return day


def hmc_category(days_since: int) -> str:
    """Hot/medium/cold from days since last drawn. Training and serving must both use this."""
    if days_since <= HMC_HOT_THRESHOLD:
        return 'hot'
    if days_since >= HMC_COLD_THRESHOLD:
        return 'cold'
    return 'medium'


class PointInTimeFeatureEngine:
    """
    Computes walk-forward point-in-time feature vectors across historical draws.
    Guarantees zero future lookahead bias by conditioning all features at draw t
    strictly on draws 0 to t-1.
    """

    def __init__(
        self,
        all_draws: List[Dict[str, Any]],
        base_features_dict: Optional[Dict[int, Dict[str, Any]]] = None
    ):
        """
        Initialize feature engine with historical draw sequence.

        Args:
            all_draws: Chronologically ordered list of draw records
            base_features_dict: Optional baseline features for static properties (odd_even, sum, etc.)
        """
        self.all_draws = all_draws
        self.base_features_dict = base_features_dict or {}
        self.N = len(all_draws)
        self.recency_zones_json = load_recency_zones()
        try:
            self.interaction_calc = InteractionFeatureCalculator()
        except Exception:
            self.interaction_calc = None

        self._reported_fallbacks = False

        self._precompute_matrices()
        self._precompute_timeline_state()

    def with_base_features(self, base_features_dict: Dict[int, Dict[str, Any]]) -> 'PointInTimeFeatureEngine':
        """
        Return a view of this engine with different static base features.

        The precomputed draw state is shared, not rebuilt, so one engine per run can serve
        the main, bonus and bonus-to-main models (C-15a).
        """
        view = copy.copy(self)
        view.base_features_dict = base_features_dict or {}
        view._reported_fallbacks = False
        return view

    def _precompute_matrices(self):
        """Vectorize draw history into binary occurrence matrices."""
        N = self.N
        self.draw_dates = []
        self.matrix_all = np.zeros((N, MAX_NUMBER + 1), dtype=np.int32)
        self.matrix_main = np.zeros((N, MAX_NUMBER + 1), dtype=np.int32)
        self.matrix_bonus = np.zeros((N, MAX_NUMBER + 1), dtype=np.int32)
        self.bonus_numbers_list = []

        for idx, d in enumerate(self.all_draws):
            d_str = d.get('date') or d.get('draw_date') or ''
            d_str = str(d_str).replace('/', '-')
            try:
                dt = pd.to_datetime(d_str)
            except Exception:
                dt = pd.Timestamp.now()
            self.draw_dates.append(dt)

            nums = d.get('numbers') or d.get('winning_numbers') or []
            valid_nums = [n for n in nums if 1 <= n <= MAX_NUMBER]
            self.matrix_all[idx, valid_nums] = 1
            main_nums = [n for n in nums[:6] if 1 <= n <= MAX_NUMBER]
            self.matrix_main[idx, main_nums] = 1

            bonus_num = d.get('bonus_number')
            if bonus_num is None and len(nums) > 6:
                bonus_num = nums[6]
            if bonus_num and 1 <= bonus_num <= MAX_NUMBER:
                self.matrix_bonus[idx, bonus_num] = 1
            self.bonus_numbers_list.append(bonus_num)

        # Cumulative appearance sums along time axis: shape (N + 1, MAX_NUMBER + 1)
        self.cum_all = np.vstack([np.zeros((1, MAX_NUMBER + 1), dtype=np.int32), np.cumsum(self.matrix_all, axis=0)])
        self.cum_main = np.vstack([np.zeros((1, MAX_NUMBER + 1), dtype=np.int32), np.cumsum(self.matrix_main, axis=0)])
        self.cum_bonus = np.vstack([np.zeros((1, MAX_NUMBER + 1), dtype=np.int32), np.cumsum(self.matrix_bonus, axis=0)])

        # Reference date for the not-yet-drawn draw at index N. Training rows at draw t use
        # date_t, so the serving row must use the next draw's date. Every serving path takes
        # its date from here (C-6b).
        self.next_draw_date = next_draw_date(self.draw_dates)

    def _precompute_timeline_state(self):
        """Precompute the historical tracking state at every draw index t."""
        self.draw_states = []
        first_date = self.draw_dates[0] if self.draw_dates else pd.Timestamp.now()

        last_seen_date = {num: first_date for num in range(1, MAX_NUMBER + 1)}
        last_seen_draw_idx = {num: None for num in range(1, MAX_NUMBER + 1)}
        last_bonus_date = {num: None for num in range(1, MAX_NUMBER + 1)}
        # Running gap moments (count, sum, sum of squares, max) instead of the gap lists:
        # snapshotting every list at every draw cost O(N^2) memory (C-15a).
        gap_stats = {num: (0, 0, 0, 0) for num in range(1, MAX_NUMBER + 1)}
        recent_bonus_deque = deque(maxlen=10)

        # One extra iteration (t == N) builds the state for the upcoming, undrawn draw.
        for t in range(self.N + 1):
            current_date = self.draw_dates[t] if t < self.N else self.next_draw_date

            # Snapshot state strictly BEFORE draw t
            state_at_t = {
                'days_since': {},
                'days_since_bonus': {},
                'bonus_window': list(recent_bonus_deque),
                'elapsed_days': max((current_date - first_date).days, 1),
                'gap_stats': dict(gap_stats)
            }
            for num in range(1, MAX_NUMBER + 1):
                if last_seen_draw_idx[num] is not None:
                    state_at_t['days_since'][num] = (current_date - last_seen_date[num]).days
                else:
                    state_at_t['days_since'][num] = 999

                if last_bonus_date[num] is not None:
                    state_at_t['days_since_bonus'][num] = (current_date - last_bonus_date[num]).days
                else:
                    state_at_t['days_since_bonus'][num] = 999

            self.draw_states.append(state_at_t)

            if t == self.N:
                break

            # Update tracking state WITH draw t (for draws > t)
            b_num = self.bonus_numbers_list[t]
            if b_num and 1 <= b_num <= MAX_NUMBER:
                recent_bonus_deque.append(b_num)
                last_bonus_date[b_num] = current_date

            for num in np.where(self.matrix_all[t] == 1)[0]:
                if last_seen_draw_idx[num] is not None:
                    gap = t - last_seen_draw_idx[num]
                    n, s, ss, mx = gap_stats[num]
                    gap_stats[num] = (n + 1, s + gap, ss + gap * gap, max(mx, gap))
                last_seen_date[num] = current_date
                last_seen_draw_idx[num] = t

    def extract_features_for_next_draw(self) -> Dict[int, Dict[str, Any]]:
        """
        Extract features for the upcoming, not-yet-drawn draw.

        This is the serving counterpart of the training rows: it conditions on ALL
        N historical draws, exactly as a training row at draw t conditions on draws
        0..t-1. Use this rather than extract_features_at_draw(N - 1), which omits
        the most recent completed draw.
        """
        return self.extract_features_at_draw(self.N)

    def extract_features_at_draw(self, t: int) -> Dict[int, Dict[str, Any]]:
        """
        Extract complete feature dictionary for all 47 numbers at draw t.
        Uses ONLY information available prior to draw t (draws 0..t-1).

        t == self.N is valid and yields the serving row for the upcoming draw.
        """
        if t < 0 or t > self.N:
            raise ValueError(f"Draw index {t} out of range [0, {self.N}]")

        state = self.draw_states[t]
        recent_bonus_set = set(state['bonus_window'])
        recent_bonus_list = state['bonus_window']

        tot_count_all = self.cum_all[t]
        tot_bonus_all = self.cum_bonus[t]

        # Align with drawpick.py SCENARIOS (MAIN 6 balls over window sizes 5, 6, 10, 15, 25).
        # Main-only matches hmc_analyzer and drawpick; the bonus signal is carried by the
        # dedicated was_recent_bonus / draws_since_bonus features instead.
        # last_4 (recent_4) = window of 5 draws
        # last_5 (recent_5) = window of 6 draws
        # last_9 (recent_9) = window of 10 draws
        # last_14 (recent_14) = window of 15 draws
        # last_24 (recent_24) = window of 25 draws
        r4_arr = self.cum_main[t] - self.cum_main[max(0, t - 5)]
        r5_arr = self.cum_main[t] - self.cum_main[max(0, t - 6)]
        r9_arr = self.cum_main[t] - self.cum_main[max(0, t - 10)]
        r14_arr = self.cum_main[t] - self.cum_main[max(0, t - 15)]
        r24_arr = self.cum_main[t] - self.cum_main[max(0, t - 25)]

        r10_all_arr = self.cum_all[t] - self.cum_all[max(0, t - 10)]
        r20_all_arr = self.cum_all[t] - self.cum_all[max(0, t - 20)]
        r50_all_arr = self.cum_all[t] - self.cum_all[max(0, t - 50)]

        r5_all_arr = self.cum_all[t] - self.cum_all[max(0, t - 5)]
        r25_all_arr = self.cum_all[t] - self.cum_all[max(0, t - 25)]

        categories = {num: hmc_category(state['days_since'][num]) for num in range(1, MAX_NUMBER + 1)}

        hot_numbers = {n for n, cat in categories.items() if cat == 'hot'}
        cat_weights = {'hot': 0.487, 'medium': 0.234, 'cold': 0.280}
        freshness_weights_table = {0: 0.33, 1: 0.33, 2: 0.34}

        features_at_draw = {}

        for num in range(1, MAX_NUMBER + 1):
            days_since = state['days_since'][num]
            cat = categories[num]
            tot_count = int(tot_count_all[num])
            tot_bonus = int(tot_bonus_all[num])

            is_in_b_win = 1 if num in recent_bonus_set else 0
            if is_in_b_win:
                try:
                    # bonus_window is chronological (oldest first), so position from the
                    # END is "draws since". The live pipeline reports the OLDEST
                    # occurrence in the window, so index() (first match) is correct here.
                    draws_since_b = len(recent_bonus_list) - 1 - recent_bonus_list.index(num)
                except ValueError:
                    draws_since_b = 10
            else:
                draws_since_b = 10

            r4 = int(r4_arr[num])
            r5 = int(r5_arr[num])
            r9 = int(r9_arr[num])
            r14 = int(r14_arr[num])
            r24 = int(r24_arr[num])

            r10_all = int(r10_all_arr[num])
            r20_all = int(r20_all_arr[num])
            r50_all = int(r50_all_arr[num])

            rate10 = r10_all / 10.0
            rate20 = r20_all / 20.0
            rate50 = r50_all / 50.0

            r5_all = int(r5_all_arr[num])
            r10_5_all = r10_all - r5_all
            trend10 = (r5_all / 5.0) - (r10_5_all / 5.0)

            r20_10_all = r20_all - r10_all
            trend20 = (r10_all / 10.0) - (r20_10_all / 10.0)

            r25_all = int(r25_all_arr[num])
            r50_25_all = r50_all - r25_all
            trend50 = (r25_all / 25.0) - (r50_25_all / 25.0)

            accel = (r10_all - r20_10_all) / 10.0

            n_gaps, g_sum, g_sumsq, g_max = state['gap_stats'][num]
            if n_gaps > 1:
                g_mean = g_sum / n_gaps
                g_var = (n_gaps * g_sumsq - g_sum * g_sum) / (n_gaps * n_gaps)
                g_std = float(np.sqrt(g_var))
                g_cv = g_std / g_mean if g_mean > 0 else 0.0
                max_g_ratio = g_max / g_mean if g_mean > 0 else 1.0
            else:
                g_mean = 0.0
                g_var = 0.0
                g_std = 0.0
                g_cv = 0.0
                max_g_ratio = 1.0

            app_volatility = g_cv
            gap_consistency = 1.0 / (1.0 + app_volatility)

            has_consec = 1 if ((num > 1 and (num - 1) in hot_numbers) or (num < MAX_NUMBER and (num + 1) in hot_numbers)) else 0

            freshness_bin = min(r4, 2)
            f_weight_score = freshness_weights_table.get(freshness_bin, 0.33)
            f_momentum = r4 * f_weight_score
            f_timing = freshness_bin * (1.0 / max(days_since + 1, 1))
            f_cat_interaction = f_weight_score * cat_weights.get(cat, 0.33)

            baseline_rate = tot_count / max(t, 1)
            recent_vs_base = (rate10 / baseline_rate) if baseline_rate > 0 else 1.0

            static_feat = self.base_features_dict.get(num, {}) if self.base_features_dict else {}

            # Point-in-time bonus/transition quantities (were per-number constants)
            elapsed_days = state['elapsed_days']
            timing_decay = (1.0 / (1.0 + draws_since_b)) if is_in_b_win else 0.0
            transition_rate = static_feat.get('historical_transition_rate', 0.74)

            rec = {
                'total_count': tot_count,
                'days_since_last': days_since,
                'recency_zone_score': calculate_recency_zone_score(days_since, category=cat, recency_zones_json=self.recency_zones_json),
                'days_since_bonus': state['days_since_bonus'][num],
                'win_bias_ratio': static_feat.get('win_bias_ratio', 1.0),
                'was_recent_bonus': is_in_b_win,
                'is_in_bonus_window': is_in_b_win,
                'draws_since_bonus': draws_since_b,
                'has_consecutive_partner': has_consec,
                'consecutive_pair_affinity': static_feat.get('consecutive_pair_affinity', 0.5),
                'bonus_hit_contribution': 1.0 if is_in_b_win else 0.0,
                'freshness_weight_score': f_weight_score,
                'pair_frequency_score': static_feat.get('pair_frequency_score', 0.5),
                'freshness_momentum': f_momentum,
                'freshness_timing': f_timing,
                'freshness_category_interaction': f_cat_interaction,
                'current_freshness_bin': freshness_bin,
                'recent_4': r4,
                'recent_5': r5,
                'recent_9': r9,
                'recent_14': r14,
                'recent_24': r24,
                'rolling_rate_10': rate10,
                'rolling_trend_10': trend10,
                'rolling_rate_20': rate20,
                'rolling_trend_20': trend20,
                'rolling_rate_50': rate50,
                'rolling_trend_50': trend50,
                'gap_variance': g_var,
                'gap_cv': g_cv,
                'appearance_acceleration': accel,
                'appearance_volatility': app_volatility,
                'gap_consistency_score': gap_consistency,
                'max_gap_ratio': max_g_ratio,
                'appearance_trend': trend10,
                'recent_vs_baseline': recent_vs_base,
                'category': cat,
                'freshness_bin': freshness_bin,
                # Bonus-specific properties
                'category_weight': cat_weights.get(cat, 1.0),
                'was_bonus_last_10': is_in_b_win,
                'freshness_weight': f_weight_score,
                'timing_zone_weight': static_feat.get('timing_zone_weight', 1.0),
                'days_since_last_bonus': state['days_since_bonus'][num],
                'bonus_frequency_ratio': tot_bonus / max(t, 1),
                'total_bonus_count': tot_bonus,
                'avg_days_between_bonus': (elapsed_days / tot_bonus) if tot_bonus > 0 else float(elapsed_days),
                # Bonus-to-main transition properties
                'historical_transition_rate': transition_rate,
                'category_multiplier': cat_weights.get(cat, 1.0),
                'freshness_multiplier': f_weight_score,
                'timing_decay_weight': timing_decay,
                'composite_transition_score': (
                    transition_rate * cat_weights.get(cat, 1.0) * f_weight_score * timing_decay
                    if is_in_b_win else 0.0
                ),
                'avg_draws_to_transition': static_feat.get('avg_draws_to_transition', 5.0)
            }

            if self.interaction_calc:
                pairwise = self.interaction_calc.calculate_pairwise_interactions(rec)
                triples = self.interaction_calc.calculate_triple_interactions(rec)
                rec.update(pairwise)
                rec.update(triples)

            features_at_draw[num] = rec

        return features_at_draw

    def report_static_fallbacks(self, all_feature_names: List[str]) -> List[str]:
        """
        Report feature names the engine does not compute point-in-time.

        Those names fall back to base_features_dict, i.e. one full-history value reused
        for every training row of that number. They carry no temporal signal and are
        estimated using data from the whole timeline, so they are the residue of the
        original lookahead problem. Printed once per engine so the list stays visible.
        """
        sample = self.extract_features_at_draw(min(self.N, max(self.N - 1, 0)))
        produced = set(sample.get(1, {}).keys())
        missing = sorted(fn for fn in all_feature_names if fn not in produced)
        if missing and not self._reported_fallbacks:
            self._reported_fallbacks = True
            print(f"  WARNING: {len(missing)} feature(s) have no point-in-time implementation "
                  f"and reuse a single full-history value per number:")
            for i in range(0, len(missing), 4):
                print("      " + ", ".join(missing[i:i + 4]))
        return missing

    def build_main_dataset(
        self,
        all_feature_names: List[str],
        start_index: int = TRAINING_START_DRAW,
        end_index: Optional[int] = None,
        exclude_bonus: bool = False
    ) -> pd.DataFrame:
        """
        Build dynamic walk-forward dataset for main models (Models 1, 2, 3, 4).

        Args:
            all_feature_names: List of feature names to extract
            start_index: Starting draw index (inclusive)
            end_index: Ending draw index (exclusive)
            exclude_bonus: If True, label main 6 only (Model 2). If False, label all 7 positions.

        Returns:
            DataFrame with all feature columns + 'hit' label
        """
        if end_index is None:
            end_index = self.N

        if start_index >= end_index:
            return pd.DataFrame(columns=all_feature_names + ['hit'])

        self.report_static_fallbacks(all_feature_names)

        records = []
        for t in range(start_index, end_index):
            feats_t = self.extract_features_at_draw(t)
            target_mask = self.matrix_main[t] if exclude_bonus else self.matrix_all[t]

            for num in range(1, MAX_NUMBER + 1):
                rec = feats_t[num]
                static_feat = self.base_features_dict.get(num, {})
                row = {fn: rec.get(fn, static_feat.get(fn, 0)) for fn in all_feature_names}
                row['hit'] = int(target_mask[num])
                records.append(row)

        return pd.DataFrame(records)

    def build_bonus_dataset(
        self,
        all_feature_names: List[str],
        start_index: int = 100,
        end_index: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Build dynamic walk-forward dataset for bonus ball prediction model.

        Args:
            all_feature_names: List of feature names to extract
            start_index: Starting draw index (inclusive)
            end_index: Ending draw index (exclusive)

        Returns:
            DataFrame with all feature columns + 'is_bonus' label
        """
        if end_index is None:
            end_index = self.N

        if start_index >= end_index:
            return pd.DataFrame(columns=all_feature_names + ['is_bonus'])

        self.report_static_fallbacks(all_feature_names)

        records = []
        for t in range(start_index, end_index):
            feats_t = self.extract_features_at_draw(t)
            bonus_num = self.bonus_numbers_list[t]

            for num in range(1, MAX_NUMBER + 1):
                rec = feats_t[num]
                static_feat = self.base_features_dict.get(num, {})
                row = {fn: rec.get(fn, static_feat.get(fn, 0)) for fn in all_feature_names}
                row['is_bonus'] = 1 if num == bonus_num else 0
                records.append(row)

        return pd.DataFrame(records)


def build_walk_forward_dataset(
    all_draws: List[Dict[str, Any]],
    features_dict: Dict[int, Dict[str, Any]],
    all_feature_names: List[str],
    exclude_bonus: bool = False,
    start_index: int = TRAINING_START_DRAW,
    end_index: Optional[int] = None
) -> pd.DataFrame:
    """
    Convenience wrapper to build a walk-forward training/validation dataset.
    """
    engine = PointInTimeFeatureEngine(all_draws, features_dict)
    return engine.build_main_dataset(
        all_feature_names=all_feature_names,
        start_index=start_index,
        end_index=end_index,
        exclude_bonus=exclude_bonus
    )


def build_walk_forward_bonus_dataset(
    base_engine: PointInTimeFeatureEngine,
    bonus_features_dict: Dict[int, Dict[str, Any]],
    training_start_draw: int = 100,
    training_end_draw: Optional[int] = None
) -> pd.DataFrame:
    """
    Convenience wrapper to build a walk-forward bonus training/validation dataset.
    """
    sample_num = next(iter(bonus_features_dict.keys())) if bonus_features_dict else 1
    feature_names = [k for k in bonus_features_dict.get(sample_num, {}).keys() if k != 'category']
    engine = base_engine.with_base_features(bonus_features_dict)
    return engine.build_bonus_dataset(
        all_feature_names=feature_names,
        start_index=training_start_draw,
        end_index=training_end_draw
    )
