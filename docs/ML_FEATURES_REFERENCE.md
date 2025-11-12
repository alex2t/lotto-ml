# Machine Learning Features Reference Guide

**Version:** 4.0 (Complete Data Source Mapping Edition)
**Purpose:** Complete reference for all ML features with exact JSON data sources
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
9. [Advanced Features](#advanced-features)
10. [Feature Engineering Details](#feature-engineering-details)
11. [Model-Specific Feature Usage](#model-specific-feature-usage)
12. [Feature Importance & Interpretation](#feature-importance--interpretation)
13. [Data Source Summary Table](#data-source-summary-table)

---

## Feature Categories Overview

The system uses **32 distinct features** across different categories:

| Category | Count | Validation | Data Sources | Purpose |
|----------|-------|------------|--------------|---------|
| Static Features | 8 | Standard | lotto_trigger_periods.json, lotto_draw_history.json | Core number statistics |
| Freshness Features | 4 | Scipy (optional) | lotto_freshness_patterns_validated.json | Recency patterns |
| Dynamic Features | 4 | Standard | lotto_trigger_periods.json (recent.last_N) | Rolling window counts |
| Long-Term Features | 5 | Scipy | lotto_long_term_patterns.json | Historical patterns |
| Bonus Features | 3 | Standard | lotto_bonus_analysis.json | Bonus ball relationships |
| Pattern Features | 2 | Scipy (optional) | lotto_consecutive_pairs_validated.json | Number associations |
| JSON Features | 5 | Scipy (3/5) | Multiple validated JSON files | Pre-calculated scores |
| Advanced Features | 1 | Standard | lotto_odds_results.json | Saturation penalties |

**Total:** 32 features (varies by model configuration)

---

## Static Features

Features that represent core, unchanging statistics about each number.

### 1. `total_count`

**Type:** Integer
**Range:** 0 to ~60 (depends on draw history)
**Data Source:** `lotto_trigger_periods.json` → `[number].total_count`
**Validation:** Standard (no scipy)

**JSON Path:**
```json
{
  "1": {
    "total_count": 52,  ← THIS VALUE
    "last_seen": "2025-01-15",
    "category": "hot"
  }
}
```

**Description:**
Total number of times this number has appeared as a main number (not bonus) across all analyzed draws.

**Calculation:**
```python
# From drawpick.py Phase 2
total_count = sum(1 for draw in all_draws if number in draw['numbers'][:6])
```

**Interpretation:**
- **High values (50+):** "Hot" number, appears frequently
- **Medium values (35-50):** Average frequency
- **Low values (<35):** "Cold" number, appears rarely

**Used By:** All 3 models (Model 1, Model 2, Model 3)

**Feature Importance:** ⭐⭐⭐⭐ HIGH
One of the most predictive features - numbers with consistent appearance patterns tend to continue.

**Statistical Notes:**
This is a raw count, not normalized. Models apply StandardScaler during training to normalize across features.

---

### 2. `days_since_last`

**Type:** Integer
**Range:** 0 to 999 (999 = never appeared)
**Data Source:** `lotto_trigger_periods.json` → `[number].days_since_last_hit`
**Validation:** Standard

**JSON Path:**
```json
{
  "1": {
    "days_since_last_hit": 14,  ← THIS VALUE
    "last_seen": "2025-01-01"
  }
}
```

**Description:**
Number of days since this number last appeared as a main number.

**Calculation:**
```python
# From drawpick.py Phase 2
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

**Statistical Notes:**
Exhibits strong autocorrelation (r=0.95) with `recency_zone_score` by design.

---

### 3. `recency_zone_score`

**Type:** Float
**Range:** 0.0 to 1.0
**Data Source:** CALCULATED from `days_since_last`
**Validation:** Standard

**Calculation:**
```python
# From ml_lotto/features/timing.py:calculate_recency_zone_score()
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

**Description:**
Normalized score representing how "overdue" a number is, based on exponential decay.

**Interpretation:**
- **0.0-0.3:** Recently appeared
- **0.4-0.6:** Normal recency
- **0.7-0.9:** Overdue
- **1.0:** Extremely overdue (high probability)

**Used By:** All 3 models

**Feature Importance:** ⭐⭐⭐⭐ HIGH
Captures non-linear recency patterns better than raw `days_since_last`.

**Statistical Notes:**
Step function creates discrete zones. Alternative: sigmoid function for smooth transitions.

---

### 4. `series_total`

**Type:** Integer
**Range:** 0 to ~20
**Data Source:** `lotto_trigger_periods.json` → `[number].series.series.*[].count`
**Validation:** Standard

**JSON Path:**
```json
{
  "1": {
    "series": {
      "series": {
        "5_consecutives_2_times": [
          {"start_date": "2024-01-15", "end_date": "2024-02-20", "count": 3}
        ],
        "10_consecutives_3_times": [
          {"count": 2}
        ]
      }
    }
  }
}
```

**Calculation:**
```python
# Sum all 'count' values across all series categories
series_total = sum(
    series_entry['count']
    for series_data in hmc_data[str(number)]['series']['series'].values()
    for series_entry in series_data
)
```

**Description:**
Total number of "series" (consecutive draw streaks) this number has participated in across all history.

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
**Data Source:** `lotto_trigger_periods.json` → `[number].series` (filtered to recent window)
**Validation:** Standard

**Calculation:**
```python
# Filter series to recent 50 draws
recent_draws = all_draws[-50:]
series_recent = sum(
    1 for series_entry in series_data
    if series_entry['end_date'] >= recent_draws[0]['date']
)
```

**Description:**
Number of series in the most recent N draws (typically last 50-100 draws).

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
**Data Source:** CALCULATED from `lotto_draw_history.json`
**Validation:** Standard

**JSON Path (source data):**
```json
{
  "2025-01-15": {
    "winning_numbers_details": [
      {"number": 1, "is_bonus": false},
      {"number": 7, "is_bonus": true}  ← Bonus number
    ]
  }
}
```

**Calculation:**
```python
# From ml_lotto/features/timing.py:calculate_days_since_bonus()
latest_draw_date = max(draw_dates)
bonus_appearances = [
    draw['date'] for draw in draw_history.values()
    if any(d['is_bonus'] and d['number'] == num
           for d in draw['winning_numbers_details'])
]
if bonus_appearances:
    days_since_bonus = (latest_draw_date - max(bonus_appearances)).days
else:
    days_since_bonus = 999
```

**Description:**
Number of days since this number last appeared as the bonus ball.

**Interpretation:**
- **0-10 days:** Recently a bonus (74% chance to appear as main)
- **11-30 days:** Medium recency
- **31+ days:** Long time since bonus

**Used By:** Model 2, Model 3

**Feature Importance:** ⭐⭐⭐ MEDIUM
Important when combined with `was_recent_bonus` feature.

**Statistical Notes:**
Bonus-to-main transition rate: 74% (3.48x boost over random 21% baseline).

---

### 7. `win_bias_ratio`

**Type:** Float
**Range:** 0.5 to 2.0 (typically 0.8 to 1.2)
**Data Source:** `lotto_draw_history.json` → latest draw → `winning_numbers_details[].win_bias_ratio`
**Validation:** Standard

**JSON Path:**
```json
{
  "2025-01-15": {
    "winning_numbers_details": [
      {
        "number": 1,
        "is_bonus": false,
        "category": "hot",
        "win_bias_ratio": 1.087,  ← THIS VALUE
        "days_since_last": 14
      }
    ]
  }
}
```

**Description:**
Statistical bias ratio indicating if a number is appearing more or less frequently than expected based on its HMC category.

**Calculation:**
```python
# From drawpick.py bonus_hit_analysis
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
**Data Source:** CALCULATED from `lotto_draw_history.json` (last 10 draws)
**Validation:** Standard

**Calculation:**
```python
# From ml_lotto/features/bonus.py:calculate_was_recent_bonus()
recent_draws = all_draws[-10:]
recent_bonus_numbers = [
    detail['number']
    for draw in recent_draws
    for detail in draw['winning_numbers_details']
    if detail.get('is_bonus', False)
]
was_recent_bonus = 1 if number in recent_bonus_numbers else 0
```

**Description:**
Binary flag indicating if this number was a bonus ball in the last 10 draws.

**Interpretation:**
- **1 (True):** Number was bonus in last 10 draws → 74% transition rate to main
- **0 (False):** Not a recent bonus

**Used By:** All 3 models

**Feature Importance:** ⭐⭐⭐⭐⭐ VERY HIGH
Extremely predictive due to 74% transition rate (3.48x boost over random).

**Statistical Notes:**
- Transition rate measured across 406 draws
- Chi-square validation: p<0.001 (highly significant)
- Effect size (Cramér's V): 0.42 (strong association)

---

## Freshness Features

Features based on how "fresh" (new) vs "recycled" (repeated) numbers are within a sliding window.

### 9. `freshness_c0_weight`

**Type:** Float
**Range:** 0.0 to 1.0
**Data Source (Scipy):** `lotto_freshness_patterns_validated.json` → `validated_weights.C0`
**Data Source (Fallback):** `lotto_7_number_freshness_results.json` → `distribution_analysis_7_numbers[0]`
**Validation:** Scipy (chi-square test, p=1.0 → not significant)

**JSON Path (Scipy-validated):**
```json
{
  "validated_weights": {
    "C0": {
      "normalized_weight": 0.4286,  ← THIS VALUE
      "statistically_validated": false
    }
  },
  "pattern_distribution_test": {
    "p_value": 1.0,
    "significant": false
  }
}
```

**JSON Path (Fallback):**
```json
{
  "distribution_analysis_7_numbers": [
    {
      "pattern": "C0=3, C1=3, C>=3=1",
      "count": 52,
      "percentage": 12.8,
      "C0": 3,  ← 3/7 = 0.4286
      "C1": 3,
      "C_GE_3": 1
    }
  ]
}
```

**Calculation:**
```python
# From ml_lotto/features/freshness.py:calculate_freshness_category_features()
if validated_weights and validated_weights['C0']['statistically_validated']:
    # Use scipy-validated weights
    c0_weight = validated_weights['C0']['normalized_weight']
else:
    # Use standard frequency-based weights from top pattern
    top_pattern = freshness_data['distribution_analysis_7_numbers'][0]
    c0_weight = top_pattern['C0'] / 7.0
```

**Description:**
Weight for numbers in category C0 (never appeared in last W-1 draws). Represents "fresh" numbers.

**Window Configuration:**
- W = 5 (5-draw window)
- W-1 = 4 draws lookback
- C_max = 3 (threshold)

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
**Data Source:** Same as `freshness_c0_weight`
**Validation:** Scipy (not significant)

**Description:**
Weight for numbers in category C1 (appeared exactly once in last W-1 draws).

**Calculation:**
```python
# From validated or top pattern
c1_weight = top_pattern['C1'] / 7.0  # e.g., 3/7 = 0.4286
```

**Used By:** Model 1, Model 3

**Feature Importance:** ⭐⭐⭐ MEDIUM

---

### 11. `freshness_c2_weight` (or `freshness_c3_weight`)

**Type:** Float
**Range:** 0.0 to 1.0
**Data Source:** Same as above
**Validation:** Scipy (not significant)

**Description:**
Weight for numbers in category C≥2 (appeared 2+ times in last W-1 draws). Represents "recycled" numbers.

**Calculation:**
```python
c2_weight = top_pattern['C_GE_3'] / 7.0  # e.g., 1/7 = 0.1429
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
**Data Source:** CALCULATED from `lotto_trigger_periods.json` → `[number].recent.last_4`
**Validation:** Standard

**Calculation:**
```python
# From ml_lotto/features/freshness.py
recent_count = hmc_data[str(number)]['recent']['last_4']
c_max_threshold = 3

if recent_count >= c_max_threshold:
    current_freshness_bin = c_max_threshold  # 3
elif recent_count == 0:
    current_freshness_bin = 0  # C0: Fresh
elif recent_count == 1:
    current_freshness_bin = 1  # C1: Seen once
else:
    current_freshness_bin = 2  # C2: Recycled
```

**Description:**
The freshness category (C0, C1, or C≥2) that this number currently belongs to.

**Interpretation:**
- **0:** Number hasn't appeared in last 4 draws (fresh)
- **1:** Number appeared once in last 4 draws
- **2:** Number appeared 2+ times in last 4 draws (recycled)

**Used By:** Internal - not directly in models, but used to calculate weights

**Feature Importance:** ⭐⭐ LOW (derived feature)

---

## Dynamic Recent Count Features

Rolling window features that count appearances in specific recent draw windows.

### 13. `recent_4` (actually `recent_5`)

**Type:** Integer
**Range:** 0 to 5
**Data Source:** `lotto_trigger_periods.json` → `[number].recent.last_4`
**Validation:** Standard

**JSON Path:**
```json
{
  "1": {
    "recent": {
      "last_4": 2,  ← THIS VALUE (counts last 5 draws)
      "last_9": 4,
      "last_13": 6,
      "last_103": 45
    }
  }
}
```

**Note:** Key naming convention: `last_N` actually counts N+1 draws (e.g., `last_4` = 5 draws).

**Description:**
Number of times this number appeared in the last 5 draws (despite key name).

**Calculation:**
```python
# From drawpick.py Phase 3
window_size = 5
recent_draws = all_draws[-window_size:]
recent_4 = sum(1 for draw in recent_draws if number in draw['numbers'][:6])
```

**Interpretation:**
- **0:** Not seen recently (may be "due")
- **1-2:** Normal recent activity
- **3-5:** Very active recently (may be "hot streak")

**Used By:** Model 3

**Feature Importance:** ⭐⭐⭐⭐ HIGH
Captures immediate short-term momentum.

---

### 14. `recent_5`, `recent_9`, `recent_14`, `recent_103`

**Type:** Integer
**Range:** 0 to N (where N is the window size)
**Data Source:** `lotto_trigger_periods.json` → `[number].recent.last_N`
**Validation:** Standard

**Description:**
Similar to `recent_4`, but for different window sizes.

**Window Mappings:**
- `recent_5` → `last_4` (5 draws)
- `recent_9` → `last_9` (10 draws)
- `recent_14` → `last_13` (14 draws)
- `recent_103` → `last_103` (104 draws)

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
**Data Source:** `lotto_long_term_patterns.json` → `hmc_pattern_analysis.category_weights.hot`
**Validation:** Scipy (chi-square, p<0.001 → highly significant)

**JSON Path:**
```json
{
  "hmc_pattern_analysis": {
    "category_weights": {
      "hot": 0.313,     ← THIS VALUE (31.3% of winners are hot)
      "medium": 0.363,
      "cold": 0.325
    },
    "significant": true,
    "p_value": 0.000123,  ← Chi-square validated
    "overall_chi2": 145.7,
    "num_patterns": 18
  }
}
```

**Calculation:**
```python
# From ml_lotto/features/long_term_patterns.py:calculate_long_term_hmc_pattern_weights()
category_weights = long_term_analysis['hmc_pattern_analysis']['category_weights']
number_category = hmc_data[str(number)]['category']  # 'hot', 'medium', or 'cold'

if number_category == 'hot':
    lt_hot_weight = category_weights['hot']  # 0.313
    lt_medium_weight = 0.0
    lt_cold_weight = 0.0
elif number_category == 'medium':
    lt_hot_weight = 0.0
    lt_medium_weight = category_weights['medium']  # 0.363
    lt_cold_weight = 0.0
else:  # cold
    lt_hot_weight = 0.0
    lt_medium_weight = 0.0
    lt_cold_weight = category_weights['cold']  # 0.325
```

**Description:**
Scipy-validated weight for hot numbers based on long-term HMC pattern analysis across 406 draws.

**Interpretation:**
- **0.313:** Number is categorized as hot
- **0.0:** Number is not hot

**Used By:** Model 2, Model 3

**Feature Importance:** ⭐⭐⭐⭐⭐ VERY HIGH
Scipy-validated with p<0.001 (highly significant pattern).

**Statistical Notes:**
- Based on 18 HMC patterns (e.g., "2-3-2", "3-1-3")
- Chi-square statistic: 145.7
- Degrees of freedom: 17
- Cramér's V: 0.31 (medium effect size)

---

### 16. `lt_medium_weight`

**Type:** Float
**Range:** 0.0 to 1.0
**Data Source:** `lotto_long_term_patterns.json` → `hmc_pattern_analysis.category_weights.medium`
**Validation:** Scipy (significant)

**Description:**
Scipy-validated weight for medium numbers. Medium numbers are the most common (36.3%).

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
**Data Source:** `lotto_long_term_patterns.json` → `hmc_pattern_analysis.category_weights.cold`
**Validation:** Scipy (significant)

**Description:**
Scipy-validated weight for cold numbers.

**Interpretation:**
- **0.325:** Number is categorized as cold
- **0.0:** Number is not cold

**Used By:** Model 2, Model 3

**Feature Importance:** ⭐⭐⭐⭐ HIGH

---

### 18. `lt_category_alignment`

**Type:** Float
**Range:** 0.0 to 1.0
**Data Source:** CALCULATED from `lt_hot_weight + lt_medium_weight + lt_cold_weight`
**Validation:** Scipy-derived

**Calculation:**
```python
lt_category_alignment = lt_hot_weight + lt_medium_weight + lt_cold_weight
# Returns: 0.313 (hot), 0.363 (medium), or 0.325 (cold)
```

**Description:**
Composite score indicating how well a number aligns with the statistically validated HMC pattern.

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
**Data Source:** `lotto_long_term_patterns.json` → `recency_correlation_analysis.by_category`
**Validation:** Scipy (correlation analysis, not significant)

**JSON Path:**
```json
{
  "recency_correlation_analysis": {
    "by_category": {
      "hot": {
        "recency_ranges": {
          "0-7 days": {
            "wins": 260,
            "win_rate": 0.339,  ← Use for hot numbers with 0-7 days recency
            "midpoint_days": 3.5
          },
          "8-14 days": {
            "wins": 155,
            "win_rate": 0.202
          }
        },
        "correlation": -0.23,
        "p_value": 0.18,
        "significant": false
      }
    }
  }
}
```

**Calculation:**
```python
# From ml_lotto/features/long_term_patterns.py:calculate_long_term_recency_weights()
category = hmc_data[str(number)]['category']
days_since = hmc_data[str(number)]['days_since_last_hit']

# Find which recency bin
recency_bin = get_recency_bin(days_since)  # e.g., "8-14 days"

# Get win rate for this category + recency combination
recency_data = long_term_analysis['recency_correlation_analysis']['by_category'][category]
lt_recency_weight = recency_data['recency_ranges'][recency_bin]['win_rate']
```

**Description:**
Weight based on recency correlation analysis within each HMC category.

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
**Data Source:** `lotto_bonus_analysis.json` → `per_number_bonus_profile[number].contribution_score`
**Validation:** Standard

**JSON Path:**
```json
{
  "per_number_bonus_profile": {
    "1": {
      "contribution_score": 0.687,  ← THIS VALUE
      "total_appearances": 52,
      "as_bonus": 8,
      "as_main_after_bonus": 6,
      "bonus_to_main_rate": 0.75,
      "recent_bonus_count": 2
    }
  }
}
```

**Description:**
Per-number score indicating how likely this number is to appear when certain conditions are met (derived from bonus hit patterns).

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
**Data Source:** CALCULATED from `lotto_trigger_periods.json` → `[number-1].category` and `[number+1].category`
**Validation:** Standard

**Calculation:**
```python
# From ml_lotto/features/patterns.py:calculate_has_consecutive_partner()
left_neighbor = number - 1
right_neighbor = number + 1

left_is_hot = (left_neighbor >= 1 and
               hmc_data[str(left_neighbor)]['category'] == 'hot')
right_is_hot = (right_neighbor <= 47 and
                hmc_data[str(right_neighbor)]['category'] == 'hot')

has_consecutive_partner = 1 if (left_is_hot or right_is_hot) else 0
```

**Description:**
Binary flag indicating if this number has a consecutive neighbor (N-1 or N+1) that is currently "hot".

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
**Data Source (Scipy):** `lotto_consecutive_pairs_validated.json` → `number_pair_scores[number]`
**Data Source (Fallback):** `lotto_odds_results.json` → `patterns.2_consecutive.all_pairs`
**Validation:** Scipy (chi-square independence, p=0.36 → not significant)

**JSON Path (Scipy-validated):**
```json
{
  "number_pair_scores": {
    "1": 0.523,  ← THIS VALUE for number 1
    "2": 0.678,
    ...
  },
  "overall_chi_square_test": {
    "p_value": 0.36,  ← Not significant
    "significant": false,
    "chi2_stat": 42.1
  }
}
```

**JSON Path (Fallback):**
```json
{
  "patterns": {
    "2_consecutive": {
      "all_pairs": {
        "1-2": 45,  ← Count for pair (1,2)
        "2-3": 38,
        ...
      }
    }
  }
}
```

**Calculation:**
```python
# From ml_lotto/features/patterns.py:calculate_consecutive_pair_affinity()
if validated_scores and 'number_pair_scores' in validated_scores:
    # Use scipy-validated scores
    affinity = validated_scores['number_pair_scores'][str(number)]
else:
    # Fallback: frequency-based calculation
    all_pairs = consecutive_patterns['2_consecutive']['all_pairs']
    pair_counts = sum(
        count for pair_str, count in all_pairs.items()
        if str(number) in pair_str.split('-')
    )
    max_count = max(all pair counts across all numbers)
    affinity = pair_counts / max_count
```

**Description:**
Scipy-tested score for consecutive pair associations. Since pairs are independent (p>0.05), uses frequency-based fallback.

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
**Data Source (Scipy):** `lotto_odd_even_validated.json` → `validated_scores[number]`
**Data Source (Fallback):** `lotto_distribution_stats.json` → `odd_even_analysis[number].affinity_score`
**Validation:** Scipy (chi-square, p=0.97 → not significant)

**JSON Path (Scipy-validated):**
```json
{
  "validated_scores": {
    "1": 0.654,  ← THIS VALUE (odd number)
    "2": 0.487,  ← THIS VALUE (even number)
    ...
  },
  "overall_distribution_test": {
    "p_value": 0.97,  ← Not significant (perfectly balanced)
    "significant": false,
    "total_odd": 1218,
    "total_even": 1218,
    "odd_percentage": 50.0,
    "even_percentage": 50.0
  }
}
```

**JSON Path (Fallback):**
```json
{
  "odd_even_analysis": {
    "1": {
      "affinity_score": 0.654,  ← THIS VALUE
      "total_odd_draws": 203,
      "total_even_draws": 203
    }
  }
}
```

**Calculation:**
```python
# From quickpick.py:389-396
if odd_even_validated and 'validated_scores' in odd_even_validated:
    odd_even_json_data = {int(k): v for k, v in odd_even_validated['validated_scores'].items()}
else:
    odd_even_json_data = load_odd_even_analysis(DISTRIBUTION_STATS_JSON)
```

**Description:**
Scipy-validated odd/even affinity score. Since distribution is perfectly balanced (50/50), uses standard scoring.

**Interpretation:**
- **>0.5:** Odd numbers slightly preferred
- **<0.5:** Even numbers preferred
- **0.5:** Neutral

**Used By:** Model 1, Model 3

**Feature Importance:** ⭐⭐ LOW
Lottery is perfectly balanced (50/50), so minimal predictive power.

**Statistical Notes:**
Chi-square p=0.97 indicates perfect random distribution.

---

### 24. `sum_contribution_json`

**Type:** Float
**Range:** 0.0 to 1.0
**Data Source:** `lotto_sum_contribution_validated.json` → `validated_scores[number]`
**Validation:** Scipy (ANOVA, p<0.001 → highly significant)

**JSON Path:**
```json
{
  "validated_scores": {
    "1": 0.234,  ← THIS VALUE (contributes to lower sums)
    "47": 0.912, ← THIS VALUE (contributes to higher sums)
    ...
  },
  "anova_analysis": {
    "p_value": 0.000087,  ← Highly significant
    "significant": true,
    "f_statistic": 24.8,
    "degrees_of_freedom_between": 46,
    "degrees_of_freedom_within": 359
  },
  "per_number_contribution": {
    "1": {
      "contribution_score": 0.234,
      "statistically_validated": true,
      "p_value": 0.002,
      "t_statistic": -3.12,
      "cohens_d": -0.84,  ← Large negative effect
      "mean_with": 168.3,
      "mean_without": 172.1,
      "appearances": 52
    }
  }
}
```

**Calculation:**
```python
# From quickpick.py:398-405
if sum_contribution_validated and 'validated_scores' in sum_contribution_validated:
    sum_contribution_json_data = {int(k): v for k, v in sum_contribution_validated['validated_scores'].items()}
else:
    sum_contribution_json_data = load_sum_contribution_analysis(DISTRIBUTION_STATS_JSON)
```

**Description:**
**✓ SCIPY-VALIDATED** - Score indicating how this number affects the total draw sum.

**Scipy Method:**
```python
# Independent t-test for each number
draws_with_number = [draw for draw in all_draws if number in draw]
draws_without_number = [draw for draw in all_draws if number not in draw]

sums_with = [sum(draw['numbers'][:6]) for draw in draws_with_number]
sums_without = [sum(draw['numbers'][:6]) for draw in draws_without_number]

t_stat, p_value = ttest_ind(sums_with, sums_without)

# Cohen's d effect size
pooled_std = sqrt(((n1-1)*var1 + (n2-1)*var2) / (n1+n2-2))
cohens_d = (mean_with - mean_without) / pooled_std

# Normalize to 0-1 range
contribution_score = normalize(mean_with, overall_mean, overall_std)
```

**Interpretation:**
- **High values (>0.6):** Number contributes to higher draw sums
- **Low values (<0.4):** Number contributes to lower draw sums
- **0.5:** Neutral contribution

**Used By:** Model 2, Model 3

**Feature Importance:** ⭐⭐⭐⭐⭐ VERY HIGH
Scipy-validated with p<0.001 (28/47 numbers show significant contribution).

**Statistical Notes:**
- 28/47 numbers statistically significant (p<0.05)
- Effect sizes range from -0.84 to +0.91 (Cohen's d)
- ANOVA F-statistic: 24.8

---

### 25. `range_spread_json`

**Type:** Float
**Range:** 0.0 to 1.0
**Data Source:** `lotto_range_spread_validated.json` → `validated_scores[number]`
**Validation:** Scipy (Levene's test, p=0.016 → significant)

**JSON Path:**
```json
{
  "validated_scores": {
    "1": 0.245,  ← THIS VALUE (contributes to narrower ranges)
    "47": 0.923, ← THIS VALUE (contributes to wider ranges)
    ...
  },
  "levene_analysis": {
    "p_value": 0.016,  ← Significant
    "significant": true,
    "levene_statistic": 8.43,
    "position_variances": {
      "low": 45.2,
      "mid": 52.1,
      "high": 61.8
    }
  },
  "per_number_contribution": {
    "1": {
      "contribution_score": 0.245,
      "statistically_validated": true,
      "p_value": 0.008,
      "t_statistic": -2.67,
      "cohens_d": -0.67,  ← Medium negative effect
      "mean_with": 31.2,
      "mean_without": 33.8,
      "appearances": 52
    }
  }
}
```

**Calculation:**
```python
# From quickpick.py:407-414
if range_spread_validated and 'validated_scores' in range_spread_validated:
    range_spread_json_data = {int(k): v for k, v in range_spread_validated['validated_scores'].items()}
else:
    range_spread_json_data = load_range_spread_analysis(ODDS_JSON_INPUT)
```

**Description:**
**✓ SCIPY-VALIDATED** - Score indicating how this number affects the range (max - min) of the draw.

**Scipy Method:**
```python
# Calculate range for each draw
draw_ranges = [max(draw['numbers'][:6]) - min(draw['numbers'][:6]) for draw in all_draws]

# Split by whether number appeared
ranges_with = [range for draw, range in zip(all_draws, draw_ranges) if number in draw]
ranges_without = [range for draw, range in zip(all_draws, draw_ranges) if number not in draw]

# Independent t-test
t_stat, p_value = ttest_ind(ranges_with, ranges_without)

# Levene's test for variance equality
levene_stat, levene_p = levene(ranges_with, ranges_without)

# Normalize
contribution_score = normalize(mean_with, overall_mean_range, overall_std_range)
```

**Interpretation:**
- **High values (>0.6):** Number contributes to wider spreads (extreme positions)
- **Low values (<0.4):** Number contributes to narrower spreads (clustered)
- **0.5:** Neutral contribution

**Used By:** Model 2, Model 3

**Feature Importance:** ⭐⭐⭐⭐⭐ VERY HIGH
Scipy-validated with p=0.016 (19/47 numbers show significant contribution).

**Statistical Notes:**
- 19/47 numbers statistically significant (p<0.05)
- Levene's test confirms variance differences across positions
- Extreme numbers (1-5, 43-47) show strongest effects

---

### 26. `freshness_weight_score`

**Type:** Float
**Range:** 0.0 to 1.0
**Data Source:** CALCULATED from `freshness_c0_weight`, `freshness_c1_weight`, `freshness_c2_weight` + `current_freshness_bin`
**Validation:** Derived from scipy (if available)

**Calculation:**
```python
# Apply weight based on current freshness category
if current_freshness_bin == 0:
    freshness_weight_score = freshness_c0_weight  # e.g., 0.4286
elif current_freshness_bin == 1:
    freshness_weight_score = freshness_c1_weight  # e.g., 0.4286
else:
    freshness_weight_score = freshness_c2_weight  # e.g., 0.1429
```

**Description:**
Composite freshness score combining C0, C1, C≥2 weights for this specific number.

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
**Data Source:** `lotto_odds_results.json` → `patterns.2_consecutive.all_pairs`
**Validation:** Standard

**JSON Path:**
```json
{
  "patterns": {
    "2_consecutive": {
      "all_pairs": {
        "1-2": 45,
        "1-3": 12,
        "2-3": 38,
        ...
      }
    }
  }
}
```

**Calculation:**
```python
# From ml_lotto/data/loader.py:load_number_pair_frequency()
# Count all pairs involving this number
pair_counts = {}
for pair_str, count in all_pairs.items():
    nums = pair_str.split('-')
    if str(number) in nums:
        pair_counts[pair_str] = count

pair_frequency_score = max(pair_counts.values()) / total_appearances
```

**Description:**
Score based on how frequently this number appears with any other specific number (pair frequency analysis).

**Interpretation:**
- **High values (>0.3):** Number frequently appears with specific partners
- **Low values (<0.1):** Number appears with varied partners

**Used By:** Model 1, Model 3

**Feature Importance:** ⭐⭐ LOW
Captures pair associations but overlaps with `consecutive_pair_affinity`.

---

## Advanced Features

### 28. `window_saturation_penalty`

**Type:** Float
**Range:** 0.0 to 1.0
**Data Source:** CALCULATED from `lotto_trigger_periods.json` (recent counts) + `lotto_odds_results.json` (scenarios)
**Validation:** Standard
**Added:** Version 3.10

**Data Sources:**

**Source 1 - Recent Counts:**
```json
// lotto_trigger_periods.json
{
  "12": {
    "recent": {
      "last_4": 3,    ← Used for saturation check
      "last_9": 4,    ← Used for saturation check
      "last_13": 5
    }
  }
}
```

**Source 2 - Scenario Thresholds:**
```json
// lotto_odds_results.json
{
  "scenarios": [
    {
      "window_size": 10,
      "results": {
        "4_times": {
          "hit_count": 99,
          "total_windows": 406,
          "odds": 0.244  ← Low odds = rare = high penalty if approaching
        }
      }
    }
  ]
}
```

**Calculation:**
```python
# From ml_lotto/features/window_saturation.py:calculate_window_saturation_score()
def calculate_window_saturation_score(hmc_data, odds_data, max_number=47):
    """
    Calculate saturation penalty based on approaching rare thresholds.

    Logic:
    - Numbers approaching rare high-frequency thresholds get penalized
    - The rarer the threshold (lower odds), the higher the penalty
    - Example: If appearing 4+ times in 10 draws is rare (24% odds),
      and number has appeared 3 times in 9 draws, apply penalty
    """
    saturation_scores = {}
    scenarios = odds_data.get('scenarios', [])

    for num in range(1, max_number + 1):
        recent_data = hmc_data[str(num)].get('recent', {})
        max_saturation = 0.0

        for scenario in scenarios:
            window_size = scenario['window_size']
            results = scenario['results']

            for target_key, target_stats in results.items():
                target_count = int(target_key.split('_')[0])  # e.g., "4_times" -> 4
                odds = target_stats['odds']

                # Get recent count for this window
                recent_key = f'last_{window_size}'
                recent_count = recent_data.get(recent_key)

                if recent_count is None:
                    continue

                # Calculate penalty based on proximity to threshold
                rarity_factor = 1.0 - odds  # Low odds = high rarity = high penalty

                if recent_count >= target_count:
                    # Already at/exceeding threshold - STRONG penalty
                    saturation = 1.0 * rarity_factor
                elif recent_count == target_count - 1:
                    # One away from threshold - MODERATE penalty
                    saturation = 0.6 * rarity_factor
                elif recent_count == target_count - 2:
                    # Two away from threshold - LIGHT penalty
                    saturation = 0.3 * rarity_factor
                else:
                    saturation = 0.0

                max_saturation = max(max_saturation, saturation)

        saturation_scores[num] = max_saturation

    return saturation_scores
```

**Example:**

Scenario: window=10, target=4 times, odds=24.4%
- Number 12: last_9=3 (3 appearances in last 10 draws)
- Interpretation: Number is 1 away from rare threshold
- Rarity factor: 1.0 - 0.244 = 0.756 (high rarity)
- Saturation: 0.6 × 0.756 = 0.454 (moderate penalty)

**Description:**
Penalty score for numbers approaching or exceeding rare high-frequency thresholds in sliding windows.

**Purpose:**
Prevents model from selecting numbers that are "saturated" (appeared too frequently in recent windows), making them statistically unlikely to continue.

**Interpretation:**
- **0.0-0.2:** No saturation (safe to select)
- **0.3-0.5:** Moderate saturation (approaching threshold)
- **0.6-0.8:** High saturation (at threshold)
- **0.9-1.0:** Extreme saturation (exceeding rare threshold)

**Used By:** All models (Model 1, Model 2, Model 3, Model 4)

**Feature Importance:** ⭐⭐⭐ MEDIUM
Acts as a regularization feature to prevent over-selection of recently hot numbers.

**Statistical Rationale:**
Based on scenario analysis showing that certain high-frequency patterns (e.g., appearing 4+ times in 10 draws) are rare (24% odds). Numbers approaching these thresholds are penalized to reflect their decreased likelihood of continuing the pattern.

**Integration:**
```python
# From ml_lotto/features/extractor.py:157-172
window_saturation_data = calculate_window_saturation_score(
    hmc_data,
    odds_data,
    MAX_NUMBER
)

# Added to feature dict for each number
features_dict[num]['window_saturation_penalty'] = window_saturation_data.get(num, 0.0)
```

---

## Feature Engineering Details

### Normalization Techniques

**Min-Max Normalization:**
```python
def normalize_minmax(value, min_val, max_val):
    """Normalize to [0, 1] range."""
    return (value - min_val) / (max_val - min_val)
```

**Z-Score Normalization:**
```python
def normalize_zscore(value, mean, std):
    """Standardize to mean=0, std=1."""
    return (value - mean) / std
```

**Sigmoid Normalization:**
```python
def normalize_sigmoid(value, midpoint, scale):
    """Smooth S-curve normalization."""
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
    'window_saturation_penalty': 0.0,
    # All JSON features default to 0.5 (neutral)
    'odd_even_json': 0.5,
    'sum_contribution_json': 0.5,
    'range_spread_json': 0.5
}
```

### Feature Correlation Analysis

**Highly Correlated Pairs** (watch for multicollinearity):

- `total_count` ↔ `recent_14` (r=0.78)
- `days_since_last` ↔ `recency_zone_score` (r=0.95) *by design*
- `freshness_c0_weight` ↔ `freshness_c1_weight` (r=-0.65) *complementary*
- `lt_hot_weight` ↔ `lt_medium_weight` (r=-0.85) *mutually exclusive*

**Mitigation:** Logistic regression uses L2 regularization; XGBoost handles multicollinearity well.

---

## Model-Specific Feature Usage

### Model 1: Short-Term Momentum Specialist

**Algorithm:** Logistic Regression
**Total Features:** 12
**Focus:** Immediate patterns, freshness, and bonus relationships

**Feature Set:**

| Feature | Data Source | Scipy? | Importance |
|---------|-------------|--------|------------|
| `total_count` | lotto_trigger_periods.json | No | ⭐⭐⭐⭐ |
| `days_since_last` | lotto_trigger_periods.json | No | ⭐⭐⭐⭐⭐ |
| `recency_zone_score` | Calculated | No | ⭐⭐⭐⭐ |
| `was_recent_bonus` | Calculated from draw_history | No | ⭐⭐⭐⭐⭐ |
| `has_consecutive_partner` | Calculated from trigger_periods | No | ⭐⭐⭐ |
| `odd_even_json` | lotto_odd_even_validated.json | ✓ | ⭐⭐ |
| `bonus_hit_contribution` | lotto_bonus_analysis.json | No | ⭐⭐⭐ |
| `pair_frequency_score` | lotto_odds_results.json | No | ⭐⭐ |
| `freshness_c0_weight` | lotto_freshness_patterns_validated.json | ✓ | ⭐⭐⭐ |
| `freshness_c1_weight` | lotto_freshness_patterns_validated.json | ✓ | ⭐⭐⭐ |
| `freshness_c2_weight` | lotto_freshness_patterns_validated.json | ✓ | ⭐⭐⭐ |
| `window_saturation_penalty` | Calculated from odds + trigger_periods | No | ⭐⭐⭐ |

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

### Model 2: Long-Term Value Specialist

**Algorithm:** Logistic Regression
**Total Features:** 18
**Focus:** Historical patterns, statistical validation, sum/range analysis

**Feature Set:**

| Feature | Data Source | Scipy? | Importance |
|---------|-------------|--------|------------|
| `total_count` | lotto_trigger_periods.json | No | ⭐⭐⭐⭐ |
| `days_since_last` | lotto_trigger_periods.json | No | ⭐⭐⭐⭐⭐ |
| `recency_zone_score` | Calculated | No | ⭐⭐⭐⭐ |
| `days_since_bonus` | Calculated from draw_history | No | ⭐⭐⭐ |
| `was_recent_bonus` | Calculated from draw_history | No | ⭐⭐⭐⭐⭐ |
| `bonus_hit_contribution` | lotto_bonus_analysis.json | No | ⭐⭐⭐ |
| `recent_14` | lotto_trigger_periods.json (last_13) | No | ⭐⭐⭐ |
| `win_bias_ratio` | lotto_draw_history.json (latest) | No | ⭐⭐⭐ |
| `consecutive_pair_affinity` | lotto_consecutive_pairs_validated.json | ✓ | ⭐⭐ |
| `sum_contribution_json` | lotto_sum_contribution_validated.json | ✓✓✓ | ⭐⭐⭐⭐⭐ |
| `range_spread_json` | lotto_range_spread_validated.json | ✓✓✓ | ⭐⭐⭐⭐⭐ |
| `freshness_weight_score` | Calculated from freshness weights | ✓ | ⭐⭐⭐ |
| `lt_hot_weight` | lotto_long_term_patterns.json | ✓✓✓ | ⭐⭐⭐⭐⭐ |
| `lt_medium_weight` | lotto_long_term_patterns.json | ✓✓✓ | ⭐⭐⭐⭐⭐ |
| `lt_cold_weight` | lotto_long_term_patterns.json | ✓✓✓ | ⭐⭐⭐⭐ |
| `lt_category_alignment` | Calculated from lt_*_weight | ✓✓✓ | ⭐⭐⭐⭐ |
| `lt_recency_weight` | lotto_long_term_patterns.json | ✓ | ⭐⭐ |
| `window_saturation_penalty` | Calculated from odds + trigger_periods | No | ⭐⭐⭐ |

**✓✓✓** = Highly significant (p < 0.01)
**✓** = Validated but not significant

**HMC Configuration:** 0 Hot + 3 Medium + 2 Cold
**Diversity Penalty:** 15%

**Strengths:**
- **6 scipy-validated features** (highest count)
- Strong long-term pattern detection
- Best sum/range predictions

**Weaknesses:**
- Slower to adapt to recent changes
- No short-term freshness features

---

### Model 3: Complex Pattern Explorer

**Algorithm:** XGBoost
**Total Features:** 26
**Focus:** Maximum feature coverage, non-linear patterns, ensemble learning

**Feature Set:**
All features from Model 1 + Model 2, plus:
- `series_total`, `series_recent`, `recent_4`

**HMC Configuration:** 2 Hot + 2 Medium + 1 Cold + 1 Generic
**Diversity Penalty:** 25%

**Strengths:**
- **Highest feature count** (26 features)
- XGBoost captures non-linear interactions
- Best for complex pattern discovery
- **6 scipy-validated features**

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
| `sum_contribution_json` | ANOVA + t-test | p<0.001 | ✓ Validated | 28/47 numbers significant |
| `range_spread_json` | Levene + t-test | p=0.016 | ✓ Validated | 19/47 numbers significant |
| `lt_*_weight` | Chi-square | p<0.001 | ✓ Validated | HMC patterns validated |
| `lt_category_alignment` | Derived | p<0.001 | ✓ Validated | From validated weights |
| `odd_even_json` | Chi-square | p=0.97 | ✗ Not sig | Perfect 50/50 balance |
| `consecutive_pair_affinity` | Chi-square | p=0.36 | ✗ Not sig | Pairs are independent |
| `freshness_*_weight` | Chi-square | p=1.0 | ✗ Not sig | Uniform distribution |

**Validated Features:** 6 out of 32 features (19%)
**High-Impact Validated:** 4 features (sum, range, lt_medium, lt_hot)

---

## Data Source Summary Table

| JSON File | Features Sourced | Scipy Validated | P-Value | Generated By |
|-----------|------------------|-----------------|---------|--------------|
| **lotto_trigger_periods.json** | total_count, days_since_last, recent_*, series_* | No | N/A | drawpick.py Phase 2 |
| **lotto_draw_history.json** | days_since_bonus, was_recent_bonus, win_bias_ratio | No | N/A | drawpick.py Phase 2 |
| **lotto_bonus_analysis.json** | bonus_hit_contribution | No | N/A | drawpick.py Phase 8 |
| **lotto_odds_results.json** | pair_frequency_score, window_saturation_penalty (partial) | No | N/A | drawpick.py Phase 4 |
| **lotto_consecutive_pairs_validated.json** | consecutive_pair_affinity | ✓ | p=0.36 | drawpick.py Phase 10 |
| **lotto_odd_even_validated.json** | odd_even_json | ✓ | p=0.97 | drawpick.py Phase 10 |
| **lotto_sum_contribution_validated.json** | sum_contribution_json | ✓✓✓ | p<0.001 | drawpick.py Phase 10 |
| **lotto_range_spread_validated.json** | range_spread_json | ✓✓✓ | p=0.016 | drawpick.py Phase 10 |
| **lotto_freshness_patterns_validated.json** | freshness_c0/c1/c2_weight | ✓ | p=1.0 | drawpick.py Phase 10 |
| **lotto_long_term_patterns.json** | lt_hot/medium/cold_weight, lt_category_alignment, lt_recency_weight | ✓✓✓ | p<0.001 | drawpick.py Phase 10 |

**Legend:**
- ✓✓✓ = Highly significant (p < 0.01), use validated scores
- ✓ = Not significant (p > 0.05), uses fallback calculation

---

## Feature Extraction Flow

```
┌────────────────────────────────────────────────────────────┐
│ PHASE 1: Base Data Generation (drawpick.py Phases 1-9)   │
│ → lotto_trigger_periods.json                              │
│ → lotto_draw_history.json                                 │
│ → lotto_bonus_analysis.json                               │
│ → lotto_7_number_freshness_results.json                   │
│ → lotto_distribution_stats.json                           │
│ → lotto_odds_results.json                                 │
└─────────────────┬──────────────────────────────────────────┘
                  │
                  ▼
┌────────────────────────────────────────────────────────────┐
│ PHASE 2: Scipy Validation (drawpick.py Phase 10)         │
│ → lotto_consecutive_pairs_validated.json                  │
│ → lotto_odd_even_validated.json                           │
│ → lotto_sum_contribution_validated.json                   │
│ → lotto_range_spread_validated.json                       │
│ → lotto_freshness_patterns_validated.json                 │
│ → lotto_hmc_categorization_validated.json                 │
│ → lotto_long_term_patterns.json                           │
└─────────────────┬──────────────────────────────────────────┘
                  │
                  ▼
┌────────────────────────────────────────────────────────────┐
│ PHASE 3: Feature Extraction (quickpick.py)               │
│ → Load validated JSON files                               │
│ → Calculate derived features (recency_zone_score, etc.)   │
│ → Calculate window_saturation_penalty                     │
│ → Combine into feature matrix (32 features × 47 numbers)  │
└─────────────────┬──────────────────────────────────────────┘
                  │
                  ▼
┌────────────────────────────────────────────────────────────┐
│ PHASE 4: Model Training & Prediction (quickpick.py)      │
│ → Model 1: 12 features                                    │
│ → Model 2: 18 features (most scipy-validated)            │
│ → Model 3: 26 features (XGBoost)                          │
│ → Model 4: Pool generator (all features)                  │
└────────────────────────────────────────────────────────────┘
```

---

## Conclusion

### Key Insights

1. **32 Total Features** with comprehensive data source mapping
2. **6 Scipy-Validated Features** provide statistical rigor (p < 0.05)
3. **4 Highly Significant Features** drive predictions: `sum_contribution_json`, `range_spread_json`, `lt_medium_weight`, `lt_hot_weight`
4. **Model 2 has most validated features** (6 out of 18), making it the most statistically rigorous
5. **Every feature traces to a JSON file** with exact path documented above
6. **New window_saturation_penalty** prevents over-selection of recently saturated numbers

### Data Quality Checklist

✅ **Run `python drawpick.py`** to generate all base + validated files
✅ **Check Phase 10 output** for p-values and validation status
✅ **Verify file timestamps** - all should be from same run
✅ **Inspect scipy summary** in quickpick.py output for "✓ Using SCIPY-VALIDATED"

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
6. **Additional saturation metrics** for other window patterns

---

**Document Version:** 4.0
**Last Updated:** 2025-11-12
**Author:** Lotto ML System Documentation Team
**Total Features:** 32
**Scipy-Validated Features:** 6 (19%)
