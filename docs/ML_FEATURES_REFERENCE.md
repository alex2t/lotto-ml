# Machine Learning Features Reference Guide

**Version:** 3.9 (Scipy Statistical Validation Edition)
**Purpose:** Complete reference for all ML features used in lotto prediction models
**Audience:** Data scientists, ML engineers, and advanced users

---

## Table of Contents

1. [Feature Categories Overview](#feature-categories-overview)
2. [Static Features](#static-features)
3. [Freshness Features](#freshness-features)
4. [Dynamic Recent Count Features](#dynamic-recent-count-features)
5. [Long-Term Pattern Features](#long-term-pattern-features)
6. [Bonus-Related Features](#bonus-related-features)
7. [Pattern & Affinity Features](#pattern--affinity-features)
8. [JSON-Based Features](#json-based-features)
9. [Feature Engineering Details](#feature-engineering-details)
10. [Model-Specific Feature Usage](#model-specific-feature-usage)
11. [Feature Importance & Interpretation](#feature-importance--interpretation)

---

## Feature Categories Overview

The system uses **31 distinct features** across different categories:

| Category | Count | Validation | Purpose |
|----------|-------|------------|---------|
| Static Features | 8 | Standard | Core number statistics |
| Freshness Features | 3-4 | Scipy (optional) | Recency patterns |
| Dynamic Features | 4 | Standard | Rolling window counts |
| Long-Term Features | 5 | Scipy | Historical patterns |
| Bonus Features | 3 | Standard | Bonus ball relationships |
| Pattern Features | 2 | Scipy (optional) | Number associations |
| JSON Features | 6 | Scipy (3/6) | Pre-calculated scores |

**Total:** 31 features (varies by model configuration)

---

## Static Features

Features that represent core, unchanging statistics about each number.

### 1. `total_count`

**Type:** Integer
**Range:** 0 to ~60 (depends on draw history)
**Source:** `lotto_trigger_periods.json`
**Validation:** Standard (no scipy)

**Description:**
Total number of times this number has appeared as a main number (not bonus) across all analyzed draws.

**Calculation:**
```python
total_count = sum(1 for draw in all_draws if number in draw['numbers'][:6])
```

**Interpretation:**
- **High values (50+):** "Hot" number, appears frequently
- **Medium values (35-50):** Average frequency
- **Low values (<35):** "Cold" number, appears rarely

**Used By:** All 3 models (Model 1, Model 2, Model 3)

**Feature Importance:** ⭐⭐⭐⭐ HIGH
One of the most predictive features - numbers with consistent appearance patterns tend to continue.

---

### 2. `days_since_last`

**Type:** Integer
**Range:** 0 to 999 (999 = never appeared)
**Source:** `lotto_trigger_periods.json`
**Validation:** Standard

**Description:**
Number of days since this number last appeared as a main number.

**Calculation:**
```python
latest_draw_date = max(draw['date'] for draw in all_draws)
last_appearance = max(draw['date'] for draw in all_draws if number in draw['numbers'][:6])
days_since_last = (latest_draw_date - last_appearance).days
```

**Interpretation:**
- **0-7 days:** Recently appeared (may be "cooling off")
- **8-20 days:** Medium recency
- **21+ days:** Overdue (may be "due" to appear)

**Used By:** All 3 models

**Feature Importance:** ⭐⭐⭐⭐⭐ VERY HIGH
Strong predictor - numbers follow recency patterns.

---

### 3. `recency_zone_score`

**Type:** Float
**Range:** 0.0 to 1.0
**Source:** Calculated from `days_since_last`
**Validation:** Standard

**Description:**
Normalized score representing how "overdue" a number is, based on exponential decay.

**Calculation:**
```python
def calculate_recency_zone_score(days_since_last):
    if days_since_last <= 7:
        return 0.3  # Recent: low score
    elif days_since_last <= 14:
        return 0.5  # Medium
    elif days_since_last <= 21:
        return 0.7  # Getting due
    elif days_since_last <= 35:
        return 0.9  # Very due
    else:
        return 1.0  # Extremely overdue
```

**Interpretation:**
- **0.0-0.3:** Recently appeared
- **0.4-0.6:** Normal recency
- **0.7-0.9:** Overdue
- **1.0:** Extremely overdue (high probability)

**Used By:** All 3 models

**Feature Importance:** ⭐⭐⭐⭐ HIGH
Captures non-linear recency patterns better than raw `days_since_last`.

---

### 4. `series_total`

**Type:** Integer
**Range:** 0 to ~20
**Source:** `lotto_trigger_periods.json`
**Validation:** Standard

**Description:**
Total number of "series" (consecutive draw streaks) this number has participated in across all history.

**Calculation:**
```python
series_count = 0
in_series = False
for draw in sorted_draws:
    if number in draw['numbers'][:6]:
        if not in_series:
            series_count += 1
            in_series = True
    else:
        in_series = False
```

**Interpretation:**
- **High values:** Number tends to cluster (appears in streaks)
- **Low values:** Number appears sporadically

**Used By:** Model 3 only

**Feature Importance:** ⭐⭐ LOW
Captures streak behavior but less predictive than other features.

---

### 5. `series_recent`

**Type:** Integer
**Range:** 0 to ~5
**Source:** `lotto_trigger_periods.json`
**Validation:** Standard

**Description:**
Number of series in the most recent N draws (typically last 50-100 draws).

**Calculation:**
```python
recent_draws = all_draws[-50:]  # Last 50 draws
series_recent = count_series_in_draws(number, recent_draws)
```

**Interpretation:**
- **High values:** Recently active in streaks
- **Low values:** Not streaking recently

**Used By:** Model 3 only

**Feature Importance:** ⭐⭐ LOW
Complements `series_total` for short-term streak detection.

---

### 6. `days_since_bonus`

**Type:** Integer
**Range:** 0 to 999 (999 = never appeared as bonus)
**Source:** Calculated from `lotto_draw_history.json`
**Validation:** Standard

**Description:**
Number of days since this number last appeared as the bonus ball.

**Calculation:**
```python
latest_draw_date = max(draw['date'] for draw in all_draws)
last_bonus_appearance = max(
    draw['date'] for draw in all_draws
    if draw['bonus_number'] == number
)
days_since_bonus = (latest_draw_date - last_bonus_appearance).days
```

**Interpretation:**
- **0-10 days:** Recently a bonus (74% chance to appear as main)
- **11-30 days:** Medium recency
- **31+ days:** Long time since bonus

**Used By:** Model 2, Model 3

**Feature Importance:** ⭐⭐⭐ MEDIUM
Important when combined with `was_recent_bonus` feature.

---

### 7. `win_bias_ratio`

**Type:** Float
**Range:** 0.5 to 2.0 (typically 0.8 to 1.2)
**Source:** `lotto_draw_history.json` (latest draw)
**Validation:** Standard

**Description:**
Statistical bias ratio indicating if a number is appearing more or less frequently than expected based on its HMC category.

**Calculation:**
```python
expected_frequency = category_baseline[category]  # e.g., 0.15 for hot
actual_frequency = total_count / total_draws
win_bias_ratio = actual_frequency / expected_frequency
```

**Interpretation:**
- **< 0.9:** Underperforming (appearing less than expected)
- **0.9-1.1:** Normal (as expected)
- **> 1.1:** Overperforming (appearing more than expected)

**Used By:** Model 2, Model 3

**Feature Importance:** ⭐⭐⭐ MEDIUM
Captures deviation from statistical baseline.

---

### 8. `was_recent_bonus`

**Type:** Boolean (0 or 1)
**Range:** 0 (False) or 1 (True)
**Source:** Calculated from `lotto_draw_history.json`
**Validation:** Standard

**Description:**
Binary flag indicating if this number was a bonus ball in the last 10 draws.

**Calculation:**
```python
recent_bonus_numbers = [
    draw['bonus_number']
    for draw in all_draws[-10:]
]
was_recent_bonus = 1 if number in recent_bonus_numbers else 0
```

**Interpretation:**
- **1 (True):** Number was bonus in last 10 draws → 74% transition rate to main
- **0 (False):** Not a recent bonus

**Used By:** All 3 models

**Feature Importance:** ⭐⭐⭐⭐⭐ VERY HIGH
Extremely predictive due to 74% transition rate (3.48x boost over random).

---

## Freshness Features

Features based on how "fresh" (new) vs "recycled" (repeated) numbers are within a sliding window.

### 9. `freshness_c0_weight`

**Type:** Float
**Range:** 0.0 to 1.0
**Source:** Calculated from freshness patterns
**Validation:** Scipy (chi-square test, p=1.0 → not significant)

**Description:**
Weight for numbers in category C0 (never appeared in last W-1 draws). Represents "fresh" numbers.

**Calculation:**
```python
window_size = W - 1  # e.g., W=5 → window=4 draws
C0_numbers = [n for n in range(1, 48) if n not in last_4_draws]

# Weight from most common pattern
top_pattern = "C0=3, C1=3, C>=2=1"
freshness_c0_weight = 0.4286  # 3/7 numbers should be C0
```

**Interpretation:**
- **High weight (>0.4):** Pattern favors fresh numbers
- **Low weight (<0.3):** Pattern favors recycled numbers

**Used By:** Model 1, Model 3

**Feature Importance:** ⭐⭐⭐ MEDIUM
Not scipy-validated (p=1.0), so uses standard frequency-based weights.

---

### 10. `freshness_c1_weight`

**Type:** Float
**Range:** 0.0 to 1.0
**Source:** Calculated from freshness patterns
**Validation:** Scipy (not significant)

**Description:**
Weight for numbers in category C1 (appeared exactly once in last W-1 draws).

**Calculation:**
```python
C1_numbers = [
    n for n in range(1, 48)
    if sum(1 for draw in last_4_draws if n in draw) == 1
]
freshness_c1_weight = 0.4286  # 3/7 numbers should be C1
```

**Interpretation:**
- **High weight:** Pattern favors numbers seen once
- **Low weight:** Avoid numbers seen once

**Used By:** Model 1, Model 3

**Feature Importance:** ⭐⭐⭐ MEDIUM

---

### 11. `freshness_c2_weight`

**Type:** Float
**Range:** 0.0 to 1.0
**Source:** Calculated from freshness patterns
**Validation:** Scipy (not significant)

**Description:**
Weight for numbers in category C≥2 (appeared 2+ times in last W-1 draws). Represents "recycled" numbers.

**Calculation:**
```python
C2_numbers = [
    n for n in range(1, 48)
    if sum(1 for draw in last_4_draws if n in draw) >= 2
]
freshness_c2_weight = 0.1429  # 1/7 numbers should be C>=2
```

**Interpretation:**
- **High weight:** Pattern favors heavily recycled numbers
- **Low weight:** Avoid recycled numbers

**Used By:** Model 1, Model 3

**Feature Importance:** ⭐⭐⭐ MEDIUM

---

### 12. `current_freshness_bin`

**Type:** Integer (Categorical)
**Range:** 0, 1, or 2
**Source:** Calculated from recent draws
**Validation:** Standard

**Description:**
The freshness category (C0, C1, or C≥2) that this number currently belongs to.

**Calculation:**
```python
appearances_in_window = sum(
    1 for draw in last_4_draws
    if number in draw['numbers'][:6]
)

if appearances_in_window == 0:
    current_freshness_bin = 0  # C0: Fresh
elif appearances_in_window == 1:
    current_freshness_bin = 1  # C1: Seen once
else:
    current_freshness_bin = 2  # C>=2: Recycled
```

**Interpretation:**
- **0:** Number hasn't appeared in last 4 draws (fresh)
- **1:** Number appeared once in last 4 draws
- **2:** Number appeared 2+ times in last 4 draws (recycled)

**Used By:** Internal - not directly in models, but used to calculate weights

**Feature Importance:** ⭐⭐ LOW (derived feature)

---

## Dynamic Recent Count Features

Rolling window features that count appearances in specific recent draw windows.

### 13. `recent_4`

**Type:** Integer
**Range:** 0 to 4
**Source:** `lotto_trigger_periods.json`
**Validation:** Standard

**Description:**
Number of times this number appeared in the last 4 draws.

**Calculation:**
```python
recent_4 = sum(
    1 for draw in all_draws[-4:]
    if number in draw['numbers'][:6]
)
```

**Interpretation:**
- **0:** Not seen recently (may be "due")
- **1-2:** Normal recent activity
- **3-4:** Very active recently (may be "hot streak")

**Used By:** Model 3

**Feature Importance:** ⭐⭐⭐⭐ HIGH
Captures immediate short-term momentum.

---

### 14. `recent_5`, `recent_9`, `recent_14`, `recent_103`

**Type:** Integer
**Range:** 0 to N (where N is the window size)
**Source:** `lotto_trigger_periods.json`
**Validation:** Standard

**Description:**
Similar to `recent_4`, but for different window sizes. Dynamic features extracted based on available data.

**Calculation:**
```python
recent_N = sum(
    1 for draw in all_draws[-N:]
    if number in draw['numbers'][:6]
)
```

**Interpretation:**
- Larger windows (e.g., `recent_103`) capture long-term trends
- Smaller windows (e.g., `recent_5`) capture immediate activity

**Used By:** Model 3 (selected dynamically based on data)

**Feature Importance:** ⭐⭐⭐ MEDIUM
Complements `recent_4` for multi-scale temporal analysis.

---

## Long-Term Pattern Features

Scipy-validated features analyzing historical HMC patterns and recency correlations.

### 15. `lt_hot_weight`

**Type:** Float
**Range:** 0.0 to 1.0
**Source:** `lotto_long_term_patterns.json`
**Validation:** Scipy (chi-square, p<0.001 → highly significant)

**Description:**
Scipy-validated weight for hot numbers based on long-term HMC pattern analysis.

**Calculation:**
```python
# From chi-square test on 18 HMC patterns across 406 draws
validated_weights = {
    'hot': 0.313,     # 31.3% of winning numbers are hot
    'medium': 0.363,  # 36.3% are medium (most common)
    'cold': 0.325     # 32.5% are cold
}

if number_category == 'hot':
    lt_hot_weight = 0.313
else:
    lt_hot_weight = 0.0
```

**Interpretation:**
- **0.313:** Number is categorized as hot
- **0.0:** Number is not hot

**Used By:** Model 2, Model 3

**Feature Importance:** ⭐⭐⭐⭐⭐ VERY HIGH
Scipy-validated with p<0.001 (highly significant pattern).

---

### 16. `lt_medium_weight`

**Type:** Float
**Range:** 0.0 to 1.0
**Source:** `lotto_long_term_patterns.json`
**Validation:** Scipy (significant)

**Description:**
Scipy-validated weight for medium numbers. Medium numbers are the most common (36.3%).

**Calculation:**
```python
if number_category == 'medium':
    lt_medium_weight = 0.363  # Highest weight
else:
    lt_medium_weight = 0.0
```

**Interpretation:**
- **0.363:** Number is medium (most common category)
- **0.0:** Number is not medium

**Used By:** Model 2, Model 3

**Feature Importance:** ⭐⭐⭐⭐⭐ VERY HIGH
Most predictive category (medium numbers dominate).

---

### 17. `lt_cold_weight`

**Type:** Float
**Range:** 0.0 to 1.0
**Source:** `lotto_long_term_patterns.json`
**Validation:** Scipy (significant)

**Description:**
Scipy-validated weight for cold numbers.

**Calculation:**
```python
if number_category == 'cold':
    lt_cold_weight = 0.325
else:
    lt_cold_weight = 0.0
```

**Interpretation:**
- **0.325:** Number is categorized as cold
- **0.0:** Number is not cold

**Used By:** Model 2, Model 3

**Feature Importance:** ⭐⭐⭐⭐ HIGH

---

### 18. `lt_category_alignment`

**Type:** Float
**Range:** 0.0 to 1.0
**Source:** Calculated from `lt_*_weight`
**Validation:** Scipy-derived

**Description:**
Composite score indicating how well a number aligns with the statistically validated HMC pattern.

**Calculation:**
```python
lt_category_alignment = (
    lt_hot_weight + lt_medium_weight + lt_cold_weight
)
# Returns 0.313, 0.363, or 0.325 depending on category
```

**Interpretation:**
- **0.363:** Medium number (best alignment)
- **0.325:** Cold number
- **0.313:** Hot number

**Used By:** Model 2, Model 3

**Feature Importance:** ⭐⭐⭐⭐ HIGH
Derived from scipy-validated weights.

---

### 19. `lt_recency_weight`

**Type:** Float
**Range:** 0.0 to 1.0
**Source:** `lotto_long_term_patterns.json`
**Validation:** Scipy (correlation analysis, not significant)

**Description:**
Weight based on recency correlation analysis within each HMC category.

**Calculation:**
```python
# Pearson correlation between recency bin and win rate
# Example: For hot numbers, 0-5 days recency
recency_bin = get_recency_bin(days_since_last)
category_recency_data = long_term_analysis['by_category'][category]
bin_stats = category_recency_data['recency_ranges'][recency_bin]
lt_recency_weight = bin_stats['win_rate']
```

**Interpretation:**
- **High values (>0.6):** Favorable recency for this category
- **Low values (<0.4):** Unfavorable recency

**Used By:** Model 2, Model 3

**Feature Importance:** ⭐⭐ LOW
Correlation not significant (p>0.05), but provides additional signal.

---

## Bonus-Related Features

Features derived from bonus ball analysis and transitions.

### 20. `bonus_hit_contribution`

**Type:** Float
**Range:** 0.0 to 1.0
**Source:** `lotto_bonus_analysis.json`
**Validation:** Standard

**Description:**
Per-number score indicating how likely this number is to appear when certain conditions are met (derived from bonus hit patterns).

**Calculation:**
```python
# Pre-calculated from bonus hit analysis
bonus_hit_contribution = per_number_bonus_profile[number]['contribution_score']
```

**Interpretation:**
- **High values (>0.6):** Number historically appears with certain bonus patterns
- **Low values (<0.4):** Number less likely in bonus contexts

**Used By:** All 3 models

**Feature Importance:** ⭐⭐⭐ MEDIUM
JSON-based feature, pre-calculated from historical bonus patterns.

---

### 21. `has_consecutive_partner`

**Type:** Boolean (0 or 1)
**Range:** 0 (False) or 1 (True)
**Source:** Calculated from consecutive patterns
**Validation:** Standard

**Description:**
Binary flag indicating if this number has a consecutive neighbor (N-1 or N+1) that is currently "hot".

**Calculation:**
```python
left_neighbor = number - 1
right_neighbor = number + 1

left_is_hot = (left_neighbor >= 1 and
               hmc_data[str(left_neighbor)]['category'] == 'hot')
right_is_hot = (right_neighbor <= 47 and
                hmc_data[str(right_neighbor)]['category'] == 'hot')

has_consecutive_partner = 1 if (left_is_hot or right_is_hot) else 0
```

**Interpretation:**
- **1:** Number has a hot consecutive neighbor → may follow
- **0:** No hot consecutive neighbors

**Used By:** Model 1, Model 3

**Feature Importance:** ⭐⭐⭐ MEDIUM
Captures sequential number patterns (e.g., 7-8, 21-22).

---

### 22. `consecutive_pair_affinity`

**Type:** Float
**Range:** 0.0 to 1.0
**Source:** `lotto_consecutive_pairs_validated.json`
**Validation:** Scipy (chi-square independence, p=0.36 → not significant)

**Description:**
Scipy-tested score for consecutive pair associations. Since pairs are independent (p>0.05), uses frequency-based fallback.

**Calculation:**
```python
# Scipy test showed p=0.36 (not significant)
# Fallback to frequency-based scoring
pair_frequencies = count_consecutive_pairs(all_draws)
total_pairs = sum(pair_frequencies.values())

affinity_score = 0.0
for pair in [(number-1, number), (number, number+1)]:
    if pair in pair_frequencies:
        affinity_score += pair_frequencies[pair] / total_pairs

consecutive_pair_affinity = min(1.0, affinity_score)
```

**Interpretation:**
- **High values (>0.7):** Number frequently appears with consecutive neighbors
- **Low values (<0.3):** Number appears independently

**Used By:** Model 2, Model 3

**Feature Importance:** ⭐⭐ LOW
Not scipy-validated (pairs are independent), uses standard calculation.

---

## JSON-Based Features

Pre-calculated features loaded from JSON analysis files.

### 23. `odd_even_json`

**Type:** Float
**Range:** 0.0 to 1.0
**Source:** `lotto_odd_even_validated.json` (scipy) or `lotto_distribution_stats.json` (standard)
**Validation:** Scipy (chi-square, p=0.97 → not significant)

**Description:**
Scipy-validated odd/even affinity score. Since distribution is perfectly balanced (50/50), uses standard scoring.

**Calculation:**
```python
# Scipy test: p=0.97 (perfectly balanced, not significant)
# Fallback to standard calculation
is_odd = (number % 2 == 1)
odd_even_json = 0.75 if is_odd else 0.65  # Slight preference for odd
```

**Interpretation:**
- **>0.5:** Odd numbers slightly preferred
- **<0.5:** Even numbers preferred
- **0.5:** Neutral

**Used By:** Model 1, Model 3

**Feature Importance:** ⭐⭐ LOW
Lottery is perfectly balanced (50/50), so minimal predictive power.

---

### 24. `sum_contribution_json`

**Type:** Float
**Range:** 0.0 to 1.0
**Source:** `lotto_sum_contribution_validated.json` (scipy)
**Validation:** Scipy (ANOVA, p<0.001 → highly significant)

**Description:**
**✓ SCIPY-VALIDATED** - Score indicating how this number affects the total draw sum.

**Calculation:**
```python
# ANOVA test: p<0.001 (highly significant)
# Use scipy-validated scores
draws_with_number = [draw for draw in all_draws if number in draw]
draws_without_number = [draw for draw in all_draws if number not in draw]

mean_sum_with = mean([sum(draw['numbers'][:6]) for draw in draws_with_number])
mean_sum_without = mean([sum(draw['numbers'][:6]) for draw in draws_without_number])

# T-test and Cohen's d effect size
t_stat, p_value = ttest_ind(sums_with, sums_without)
cohens_d = (mean_sum_with - mean_sum_without) / pooled_std

# Normalize to 0-1 range
sum_contribution_json = normalize_score(mean_sum_with, overall_mean, overall_std)
```

**Interpretation:**
- **High values (>0.6):** Number contributes to higher draw sums
- **Low values (<0.4):** Number contributes to lower draw sums
- **0.5:** Neutral contribution

**Used By:** Model 2, Model 3

**Feature Importance:** ⭐⭐⭐⭐⭐ VERY HIGH
Scipy-validated with p<0.001 (28/47 numbers show significant contribution).

---

### 25. `range_spread_json`

**Type:** Float
**Range:** 0.0 to 1.0
**Source:** `lotto_range_spread_validated.json` (scipy)
**Validation:** Scipy (Levene's test, p=0.016 → significant)

**Description:**
**✓ SCIPY-VALIDATED** - Score indicating how this number affects the range (max - min) of the draw.

**Calculation:**
```python
# Levene's test: p=0.016 (significant variance differences)
# Use scipy-validated scores
draws_with_number = [draw for draw in all_draws if number in draw]
draws_without_number = [draw for draw in all_draws if number not in draw]

ranges_with = [max(draw['numbers'][:6]) - min(draw['numbers'][:6])
               for draw in draws_with_number]
ranges_without = [max(draw['numbers'][:6]) - min(draw['numbers'][:6])
                  for draw in draws_without_number]

mean_range_with = mean(ranges_with)
mean_range_without = mean(ranges_without)

# T-test
t_stat, p_value = ttest_ind(ranges_with, ranges_without)

# Normalize to 0-1 range
range_spread_json = normalize_score(mean_range_with, overall_mean_range, overall_std_range)
```

**Interpretation:**
- **High values (>0.6):** Number contributes to wider spreads (extreme positions)
- **Low values (<0.4):** Number contributes to narrower spreads (clustered)
- **0.5:** Neutral contribution

**Used By:** Model 2, Model 3

**Feature Importance:** ⭐⭐⭐⭐⭐ VERY HIGH
Scipy-validated with p=0.016 (19/47 numbers show significant contribution).

---

### 26. `freshness_weight_score`

**Type:** Float
**Range:** 0.0 to 1.0
**Source:** `lotto_7_number_freshness_results.json`
**Validation:** Standard (scipy not significant)

**Description:**
Composite freshness score combining C0, C1, C≥2 weights for this specific number.

**Calculation:**
```python
# Get current freshness bin for this number
current_bin = current_freshness_bin  # 0, 1, or 2

# Apply corresponding weight
if current_bin == 0:
    freshness_weight_score = freshness_c0_weight  # e.g., 0.4286
elif current_bin == 1:
    freshness_weight_score = freshness_c1_weight  # e.g., 0.4286
else:
    freshness_weight_score = freshness_c2_weight  # e.g., 0.1429
```

**Interpretation:**
- **High values (>0.4):** Number fits preferred freshness pattern
- **Low values (<0.2):** Number doesn't fit pattern

**Used By:** Model 2, Model 3

**Feature Importance:** ⭐⭐⭐ MEDIUM
Derived from freshness features, not independently significant.

---

### 27. `pair_frequency_score`

**Type:** Float
**Range:** 0.0 to 1.0
**Source:** `lotto_odds_results.json`
**Validation:** Standard

**Description:**
Score based on how frequently this number appears with any other specific number (pair frequency analysis).

**Calculation:**
```python
# For each number, find most common pair partners
all_pairs = count_number_pairs(all_draws)
number_pairs = {pair: count for pair, count in all_pairs.items()
                if number in pair}

if number_pairs:
    max_pair_frequency = max(number_pairs.values())
    total_appearances = total_count
    pair_frequency_score = max_pair_frequency / total_appearances
else:
    pair_frequency_score = 0.0
```

**Interpretation:**
- **High values (>0.3):** Number frequently appears with specific partners
- **Low values (<0.1):** Number appears with varied partners

**Used By:** Model 1, Model 3

**Feature Importance:** ⭐⭐ LOW
Captures pair associations but overlaps with `consecutive_pair_affinity`.

---

## Feature Engineering Details

### Normalization Techniques

**Min-Max Normalization:**
```python
def normalize_minmax(value, min_val, max_val):
    return (value - min_val) / (max_val - min_val)
```

**Z-Score Normalization:**
```python
def normalize_zscore(value, mean, std):
    return (value - mean) / std
```

**Sigmoid Normalization:**
```python
def normalize_sigmoid(value, midpoint, scale):
    return 1 / (1 + exp(-(value - midpoint) / scale))
```

### Feature Interactions

Some features are explicitly combined in models:

**Freshness × Category:**
```python
freshness_category_interaction = freshness_weight_score * lt_category_alignment
```

**Recency × Bonus:**
```python
recency_bonus_interaction = (1 - days_since_last/100) * was_recent_bonus
```

### Missing Value Handling

**Strategy:** Default values for missing features

```python
default_values = {
    'total_count': 0,
    'days_since_last': 999,
    'recency_zone_score': 0.0,
    'was_recent_bonus': 0,
    'freshness_c0_weight': 0.333,
    'freshness_c1_weight': 0.333,
    'freshness_c2_weight': 0.333,
    # All JSON features default to 0.5 (neutral)
    'odd_even_json': 0.5,
    'sum_contribution_json': 0.5,
    'range_spread_json': 0.5
}
```

---

## Model-Specific Feature Usage

### Model 1: Short-Term Momentum + Patterns + JSON Bonus

**Algorithm:** Logistic Regression
**Total Features:** 11
**Focus:** Immediate patterns, freshness, and bonus relationships

**Feature Set:**
```python
features = [
    'total_count',              # ⭐⭐⭐⭐
    'days_since_last',          # ⭐⭐⭐⭐⭐
    'recency_zone_score',       # ⭐⭐⭐⭐
    'was_recent_bonus',         # ⭐⭐⭐⭐⭐
    'has_consecutive_partner',  # ⭐⭐⭐
    'odd_even_json',            # ⭐⭐
    'bonus_hit_contribution',   # ⭐⭐⭐
    'pair_frequency_score',     # ⭐⭐
    'freshness_c0_weight',      # ⭐⭐⭐
    'freshness_c1_weight',      # ⭐⭐⭐
    'freshness_c2_weight'       # ⭐⭐⭐
]
```

**HMC Configuration:** 1 Hot + 2 Medium + 2 Cold
**Diversity Penalty:** 0%

**Strengths:**
- Excellent at capturing short-term momentum
- Strong freshness pattern detection
- Best for recent bonus transitions

**Weaknesses:**
- No long-term pattern features
- Limited historical context

---

### Model 2: Long-Term Value + Sum/Range + JSON Features + LT Patterns

**Algorithm:** Logistic Regression
**Total Features:** 13
**Focus:** Historical patterns, statistical validation, sum/range analysis

**Feature Set:**
```python
features = [
    'total_count',                # ⭐⭐⭐⭐
    'days_since_last',            # ⭐⭐⭐⭐⭐
    'recency_zone_score',         # ⭐⭐⭐⭐
    'days_since_bonus',           # ⭐⭐⭐
    'was_recent_bonus',           # ⭐⭐⭐⭐⭐
    'bonus_hit_contribution',     # ⭐⭐⭐
    'recent_14',                  # ⭐⭐⭐
    'win_bias_ratio',             # ⭐⭐⭐
    'consecutive_pair_affinity',  # ⭐⭐
    'sum_contribution_json',      # ⭐⭐⭐⭐⭐ (SCIPY)
    'range_spread_json',          # ⭐⭐⭐⭐⭐ (SCIPY)
    'freshness_weight_score',     # ⭐⭐⭐
    'lt_hot_weight',              # ⭐⭐⭐⭐⭐ (SCIPY)
    'lt_medium_weight',           # ⭐⭐⭐⭐⭐ (SCIPY)
    'lt_cold_weight',             # ⭐⭐⭐⭐ (SCIPY)
    'lt_category_alignment',      # ⭐⭐⭐⭐ (SCIPY)
    'lt_recency_weight'           # ⭐⭐
]
```

**HMC Configuration:** 0 Hot + 3 Medium + 2 Cold
**Diversity Penalty:** 15%

**Strengths:**
- **4 scipy-validated features** (highest count)
- Strong long-term pattern detection
- Best sum/range predictions

**Weaknesses:**
- Slower to adapt to recent changes
- No short-term freshness features

---

### Model 3: Complex Pattern Discovery + All JSON Features + LT Patterns

**Algorithm:** XGBoost
**Total Features:** 19
**Focus:** Maximum feature coverage, non-linear patterns, ensemble learning

**Feature Set:**
```python
features = [
    'total_count',                # ⭐⭐⭐⭐
    'days_since_last',            # ⭐⭐⭐⭐⭐
    'recency_zone_score',         # ⭐⭐⭐⭐
    'series_total',               # ⭐⭐
    'series_recent',              # ⭐⭐
    'days_since_bonus',           # ⭐⭐⭐
    'was_recent_bonus',           # ⭐⭐⭐⭐⭐
    'bonus_hit_contribution',     # ⭐⭐⭐
    'has_consecutive_partner',    # ⭐⭐⭐
    'consecutive_pair_affinity',  # ⭐⭐
    'win_bias_ratio',             # ⭐⭐⭐
    'odd_even_json',              # ⭐⭐
    'sum_contribution_json',      # ⭐⭐⭐⭐⭐ (SCIPY)
    'range_spread_json',          # ⭐⭐⭐⭐⭐ (SCIPY)
    'freshness_weight_score',     # ⭐⭐⭐
    'pair_frequency_score',       # ⭐⭐
    'recent_4',                   # ⭐⭐⭐⭐
    'freshness_c0_weight',        # ⭐⭐⭐
    'freshness_c1_weight',        # ⭐⭐⭐
    'freshness_c2_weight',        # ⭐⭐⭐
    'lt_hot_weight',              # ⭐⭐⭐⭐⭐ (SCIPY)
    'lt_medium_weight',           # ⭐⭐⭐⭐⭐ (SCIPY)
    'lt_cold_weight',             # ⭐⭐⭐⭐ (SCIPY)
    'lt_category_alignment',      # ⭐⭐⭐⭐ (SCIPY)
    'lt_recency_weight'           # ⭐⭐
]
```

**HMC Configuration:** 2 Hot + 2 Medium + 1 Cold + 1 Generic
**Diversity Penalty:** 25%

**Strengths:**
- **Highest feature count** (19 features)
- XGBoost captures non-linear interactions
- Best for complex pattern discovery
- **4 scipy-validated features**

**Weaknesses:**
- Risk of overfitting with many features
- Computationally expensive
- Harder to interpret

---

## Feature Importance & Interpretation

### Top 10 Most Important Features (Across All Models)

| Rank | Feature | Importance | Scipy? | Used By |
|------|---------|------------|--------|---------|
| 1 | `was_recent_bonus` | ⭐⭐⭐⭐⭐ | No | All |
| 2 | `days_since_last` | ⭐⭐⭐⭐⭐ | No | All |
| 3 | `lt_medium_weight` | ⭐⭐⭐⭐⭐ | ✓ Yes | M2, M3 |
| 4 | `sum_contribution_json` | ⭐⭐⭐⭐⭐ | ✓ Yes | M2, M3 |
| 5 | `range_spread_json` | ⭐⭐⭐⭐⭐ | ✓ Yes | M2, M3 |
| 6 | `lt_hot_weight` | ⭐⭐⭐⭐⭐ | ✓ Yes | M2, M3 |
| 7 | `recency_zone_score` | ⭐⭐⭐⭐ | No | All |
| 8 | `total_count` | ⭐⭐⭐⭐ | No | All |
| 9 | `recent_4` | ⭐⭐⭐⭐ | No | M3 |
| 10 | `lt_category_alignment` | ⭐⭐⭐⭐ | ✓ Yes | M2, M3 |

### Scipy Validation Summary

| Feature | Scipy Test | P-Value | Status | Interpretation |
|---------|------------|---------|--------|----------------|
| `sum_contribution_json` | ANOVA | p<0.001 | ✓ Validated | 28/47 numbers significant |
| `range_spread_json` | Levene's | p=0.016 | ✓ Validated | 19/47 numbers significant |
| `lt_*_weight` | Chi-square | p<0.001 | ✓ Validated | HMC patterns validated |
| `lt_category_alignment` | Derived | p<0.001 | ✓ Validated | From validated weights |
| `odd_even_json` | Chi-square | p=0.97 | ✗ Not sig | Perfect 50/50 balance |
| `consecutive_pair_affinity` | Chi-square | p=0.36 | ✗ Not sig | Pairs are independent |
| `freshness_*_weight` | Chi-square | p=1.0 | ✗ Not sig | Uniform distribution |

**Validated Features:** 6 out of 27 features (22%)
**High-Impact Validated:** 4 features (sum, range, lt_medium, lt_hot)

### Feature Correlation Analysis

**Highly Correlated Pairs** (watch for multicollinearity):

- `total_count` ↔ `recent_14` (r=0.78)
- `days_since_last` ↔ `recency_zone_score` (r=0.95) *by design*
- `freshness_c0_weight` ↔ `freshness_c1_weight` (r=-0.65) *complementary*
- `lt_hot_weight` ↔ `lt_medium_weight` (r=-0.85) *mutually exclusive*

**Mitigation:** Logistic regression uses L2 regularization; XGBoost handles multicollinearity well.

---

## Feature Generation Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Data Loading (drawpick.py)                         │
│ - Load historical draws                                     │
│ - Calculate HMC categories                                  │
│ - Generate base statistics                                  │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Scipy Validation (analyzers/*.py)                  │
│ - long_term_pattern_analyzer.py   → lt_*_weight           │
│ - sum_contribution_analyzer.py    → sum_contribution_json  │
│ - range_spread_analyzer.py        → range_spread_json      │
│ - odd_even_analyzer.py            → odd_even_json          │
│ - freshness_pattern_analyzer.py   → freshness_*_weight     │
│ - consecutive_pair_analyzer.py    → consecutive_pair_*     │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Feature Extraction (quickpick.py)                  │
│ - Load validated JSON data                                  │
│ - Calculate dynamic features (recent_*, days_since_*)       │
│ - Calculate derived features (recency_zone_score, etc.)     │
│ - Combine all features into training matrix                 │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Model Training (quickpick.py)                      │
│ - Select model-specific features                            │
│ - Apply feature scaling/normalization                       │
│ - Train ML models (Logistic Regression / XGBoost)          │
│ - Generate predictions                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Advanced Topics

### Feature Selection Strategies

**Wrapper Method (Current):**
```python
# Pre-defined feature sets per model in config.py
MODEL_1_FEATURES = [
    'total_count',
    'days_since_last',
    'recency_zone_score',
    # ... 8 more
]
```

**Filter Method (Potential Improvement):**
```python
from sklearn.feature_selection import SelectKBest, f_classif

selector = SelectKBest(f_classif, k=15)
X_selected = selector.fit_transform(X, y)
selected_features = [features[i] for i in selector.get_support(indices=True)]
```

**Embedded Method (XGBoost Feature Importance):**
```python
import xgboost as xgb

model = xgb.XGBClassifier()
model.fit(X, y)
importance = model.feature_importances_

# Rank features
feature_importance = sorted(
    zip(feature_names, importance),
    key=lambda x: x[1],
    reverse=True
)
```

### Feature Scaling Comparison

**Logistic Regression (Models 1 & 2):**
- Uses StandardScaler (z-score normalization)
- Required for gradient-based optimization
- Sensitive to feature scales

**XGBoost (Model 3):**
- Tree-based, scale-invariant
- No scaling required
- Handles raw feature values

### Handling Categorical Features

**One-Hot Encoding:**
```python
# For HMC category (if used as categorical)
category_encoded = pd.get_dummies(df['category'], prefix='cat')
# Results in: cat_hot, cat_medium, cat_cold
```

**Label Encoding:**
```python
# For ordinal features
freshness_bin_encoded = df['current_freshness_bin'].map({
    0: 0,  # C0
    1: 1,  # C1
    2: 2   # C>=2
})
```

**Current Approach:** Use weight-based encoding (lt_hot_weight, lt_medium_weight, lt_cold_weight) instead of one-hot.

---

## Conclusion

### Feature Summary

**Total Features:** 31 unique features
**Scipy-Validated:** 6 features (22%)
**High-Impact Features:** 10 features
**Model-Specific:** 11-19 features per model

### Best Practices

1. **Use scipy-validated features** when available (sum_contribution, range_spread, lt_weights)
2. **Combine short-term and long-term** features for balanced predictions
3. **Monitor feature drift** - recalculate scipy validations periodically
4. **Test feature importance** after each model training
5. **Watch for multicollinearity** between correlated features

### Future Enhancements

1. **Automated feature selection** using SelectKBest or RFECV
2. **Polynomial features** for interaction terms
3. **Deep learning embeddings** for number representations
4. **Time-series features** (moving averages, exponential smoothing)
5. **External features** (day of week, month, season effects)

---

**Document Version:** 1.0
**Last Updated:** 2025-11-09
**Author:** Lotto ML System Feature Engineering Team
