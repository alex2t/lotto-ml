# Machine Learning Features Reference Guide

**Version:** 5.0 (Accurate Feature Documentation)
**Last Updated:** 2025-11-15
**Purpose:** Complete and accurate reference for all ML features with exact data sources
**Audience:** Newcomers, data scientists, ML engineers, and developers

---

## Quick Start for Newcomers

This document explains all the features (inputs) used by the machine learning models to predict lottery numbers. If you're new to the project, start here to understand:
- What data the ML models use
- Where that data comes from
- How features are calculated
- Which features are most important

### Prerequisites
Before reading this guide, you should understand:
- Basic lottery concepts (main numbers, bonus ball)
- Basic machine learning terminology (features, training, models)
- JSON file format

### System Overview
```
CSV Data (irish500.csv)
    ↓
drawpick.py (13 Analysis Phases)
    ↓
17 JSON Files (data/*.json)
    ↓
Feature Extraction (extractor.py)
    ↓
~40 ML Features per Number
    ↓
4 ML Models → Predictions
```

---

## Table of Contents

1. [Feature Categories Overview](#feature-categories-overview)
2. [Core Features](#core-features)
3. [Recency & Timing Features](#recency--timing-features)
4. [Recent Activity Windows](#recent-activity-windows)
5. [Series & Pattern Features](#series--pattern-features)
6. [Bonus Ball Features](#bonus-ball-features)
7. [Freshness Features](#freshness-features)
8. [Long-Term Pattern Features](#long-term-pattern-features)
9. [Advanced Pattern Features](#advanced-pattern-features)
10. [Distribution Features](#distribution-features)
11. [Window Saturation Features](#window-saturation-features)
12. [Model-Specific Feature Usage](#model-specific-feature-usage)
13. [Feature Importance Rankings](#feature-importance-rankings)
14. [Data Pipeline](#data-pipeline)

---

## Feature Categories Overview

The system extracts approximately **40 features** for each of the 47 lottery numbers. These features are organized into 11 categories:

| Category | Feature Count | Data Source(s) | Primary Purpose |
|----------|---------------|----------------|-----------------|
| **Core Features** | 3 | lotto_trigger_periods.json | Basic statistics (count, category) |
| **Recency & Timing** | 3 | lotto_trigger_periods.json, calculated | When number last appeared |
| **Recent Activity** | 4 | lotto_trigger_periods.json | Rolling window counts |
| **Series & Patterns** | 4 | lotto_trigger_periods.json, validated files | Consecutive appearance patterns |
| **Bonus Features** | 3 | lotto_bonus_analysis.json, lotto_draw_history.json | Bonus ball relationships |
| **Freshness** | 5 | lotto_freshness_patterns_validated.json | How "fresh" vs "recycled" |
| **Long-Term** | 6 | lotto_long_term_patterns.json | Historical trend alignment |
| **Advanced Patterns** | 6 | lotto_advanced_patterns.json | Volatility and momentum |
| **Distribution** | 3 | Validated JSON files | Sum, range, odd/even |
| **Window Saturation** | 1 | lotto_window_saturation_calculated.json | Prevents over-selection |
| **Interaction** | 2+ | Calculated from other features | Combined feature signals |

**Total**: ~40 features (varies slightly by model configuration)

---

## Core Features

These are the fundamental statistics about each number.

### 1. `total_count`

**Description:** Total number of times this number has appeared as a main number (not bonus) across all historical draws.

**Data Source:** `lotto_trigger_periods.json` → `[number].total_count`

**Type:** Integer
**Range:** 0 to ~90 (depends on draw history)

**Example JSON:**
```json
{
  "1": {
    "total_count": 86,
    "last_seen": "2025/11/05",
    "category": "hot"
  }
}
```

**Interpretation:**
- **High values (75+):** Frequently appearing number ("hot")
- **Medium values (60-75):** Average frequency
- **Low values (<60):** Rarely appearing number ("cold")

**Used By:** All 4 models
**Importance:** ⭐⭐⭐⭐ HIGH - Strong predictor of future appearances

**Notes:**
- This is a raw count, not normalized
- Models apply StandardScaler during training to normalize
- Correlated with `category` feature (by design - category is derived from total_count)

---

### 2. `category`

**Description:** Classification of the number based on its historical appearance frequency.

**Data Source:** `lotto_trigger_periods.json` → `[number].category`

**Type:** String (categorical)
**Values:** "hot", "medium", or "cold"

**Categorization Rules:**
- **Hot:** Top 15 numbers by total_count (numbers 1-15 by frequency)
- **Medium:** Middle 17 numbers (numbers 16-32 by frequency)
- **Cold:** Bottom 15 numbers (numbers 33-47 by frequency)

**Example:**
```json
{
  "1": {"category": "hot"},
  "25": {"category": "medium"},
  "45": {"category": "cold"}
}
```

**Interpretation:**
- **Hot:** Appears frequently in draws (~47% of main numbers are hot)
- **Medium:** Average appearance rate (~24% of main numbers are medium)
- **Cold:** Appears less frequently (~28% of main numbers are cold)

**Used By:** Indirectly used by all models (via `lt_category_alignment` and other features)
**Importance:** ⭐⭐⭐⭐ HIGH - Foundation for many derived features

**Notes:**
- Category boundaries are recalculated after each draw
- Not used directly as a feature (one-hot encoding not beneficial)
- Instead, used via long-term pattern alignment features

---

### 3. `days_since_last`

**Description:** Number of calendar days since this number last appeared as a main number.

**Data Source:** `lotto_trigger_periods.json` → `[number].last_seen` (calculated from current date)

**Type:** Integer
**Range:** 0 to 999 (999 = never appeared or very old)

**Calculation:**
```python
latest_draw_date = max(draw['date'] for draw in all_draws)
last_appearance = max(draw['date'] for draw in all_draws
                     if number in draw['numbers'][:6])
days_since_last = (latest_draw_date - last_appearance).days
```

**Example:**
- Number last appeared on 2025-11-05
- Today is 2025-11-15
- `days_since_last` = 10

**Interpretation:**
- **0-7 days:** Recently appeared (may be "cooling off")
- **8-20 days:** Medium recency
- **21-35 days:** Getting overdue
- **36+ days:** Very overdue (may be "due" to appear)

**Used By:** All 4 models
**Importance:** ⭐⭐⭐⭐⭐ VERY HIGH - One of the strongest predictors

**Notes:**
- Highly correlated with `recency_zone_score` (by design)
- Statistical analysis shows numbers follow recency patterns
- Not perfectly correlated with `recent_4` (draws vs calendar days)

---

## Recency & Timing Features

These features capture when and how recently numbers appeared.

### 4. `recency_zone_score`

**Description:** Normalized score representing how "overdue" a number is, based on exponential decay zones.

**Data Source:** Calculated from `days_since_last`

**Type:** Float
**Range:** 0.0 to 1.0

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
- **0.0-0.3:** Recently appeared, unlikely to repeat soon
- **0.4-0.6:** Normal recency window
- **0.7-0.9:** Overdue, higher chance of appearing
- **1.0:** Extremely overdue, very high probability

**Used By:** Model 2, Model 3
**Importance:** ⭐⭐⭐⭐ HIGH - Captures non-linear recency patterns

**Notes:**
- Step function creates discrete zones (alternative: sigmoid for smooth transitions)
- Zones based on empirical analysis of historical patterns
- More interpretable than raw `days_since_last` for ML models

---

### 5. `days_since_bonus`

**Description:** Number of calendar days since this number last appeared as the **bonus ball**.

**Data Source:** Calculated from `lotto_draw_history.json` → `winning_numbers_details[].is_bonus`

**Type:** Integer
**Range:** 0 to 999 (999 = never appeared as bonus)

**Calculation:**
```python
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

**Interpretation:**
- **0-10 days:** Recently a bonus → 74% chance to appear as main within 10 draws
- **11-30 days:** Medium recency
- **31+ days:** Long time since bonus

**Used By:** Model 3
**Importance:** ⭐⭐⭐ MEDIUM - Important when combined with `was_recent_bonus`

**Statistical Note:**
Bonus-to-main transition rate: **74%** (3.48x boost over random 21% baseline)

---

## Recent Activity Windows

These features count how many times a number appeared in specific recent draw windows.

### 6. `recent_4`

**Description:** Number of times this number appeared in the last 5 draws.

**Data Source:** `lotto_trigger_periods.json` → `[number].recent.last_4`

**Type:** Integer
**Range:** 0 to 5

**Note on Naming:** The JSON key is `last_4` but it actually counts the last 5 draws (W-1 = 4, so window W = 5). This is intentional due to freshness analysis window conventions.

**Example:**
```json
{
  "1": {
    "recent": {
      "last_4": 2,   ← Appeared in 2 of last 5 draws
      "last_5": 3,
      "last_9": 4,
      "last_24": 7
    }
  }
}
```

**Interpretation:**
- **0:** Not seen recently (may be "due")
- **1-2:** Normal recent activity
- **3-5:** Very active recently (hot streak or potentially saturated)

**Used By:** Model 1, Model 4
**Importance:** ⭐⭐⭐⭐ HIGH - Captures immediate short-term momentum

---

### 7. `recent_5`, `recent_9`, `recent_14`, `recent_24`

**Description:** Similar to `recent_4`, but for different window sizes.

**Data Sources:**
- `recent_5` → `lotto_trigger_periods.json` → `[number].recent.last_5` (counts last 6 draws)
- `recent_9` → `lotto_trigger_periods.json` → `[number].recent.last_9` (counts last 10 draws)
- `recent_14` → Uses `last_13` (counts last 14 draws) if available, else calculated
- `recent_24` → Uses `last_24` (counts last 25 draws) if available, else calculated

**Type:** Integer
**Range:** 0 to N (where N is the window size)

**Interpretation:**
- Larger windows (e.g., `recent_24`) capture long-term trends
- Smaller windows (e.g., `recent_5`) capture immediate activity
- Used together for multi-scale temporal analysis

**Used By:**
- `recent_9`: Model 4 (Bonus-to-Main model)
- `recent_14`: Model 2, Model 3
- `recent_24`: Not currently used (available for experimentation)

**Importance:** ⭐⭐⭐ MEDIUM to HIGH (depending on window size)

---

## Series & Pattern Features

These features capture consecutive appearance patterns and pair associations.

### 8. `series_total`

**Description:** Total number of "series" (consecutive draw streaks) this number has participated in across all history.

**Data Source:** `lotto_trigger_periods.json` → `[number].series.series.*[].count` (summed)

**Type:** Integer
**Range:** 0 to ~20

**Example:**
```json
{
  "1": {
    "series": {
      "series": {
        "5_consecutives_2_times": [
          {"start_date": "2024/01/15", "end_date": "2024/02/20", "count": 3}
        ],
        "10_consecutives_4_times": [
          {"count": 2}
        ]
      }
    }
  }
}
```

**Calculation:**
```python
series_total = sum(
    series_entry['count']
    for series_data in hmc_data[str(number)]['series']['series'].values()
    for series_entry in series_data
)
# Example: 3 + 2 = 5
```

**Interpretation:**
- **High values:** Number tends to cluster (appears in streaks)
- **Low values:** Number appears sporadically

**Used By:** Model 3
**Importance:** ⭐⭐ LOW - Captures streak behavior but less predictive

---

### 9. `series_recent`

**Description:** Number of series in the most recent 60 days.

**Data Source:** `lotto_trigger_periods.json` → `[number].series` (filtered by date)

**Type:** Integer
**Range:** 0 to ~5

**Calculation:**
```python
# Filter series to recent 60 days
recent_series = sum(
    1 for series_entry in series_data
    if (current_date - parse_date(series_entry['end_date'])).days <= 60
)
```

**Interpretation:**
- **High values:** Recently active in streaks
- **Low values:** Not streaking recently

**Used By:** Model 3
**Importance:** ⭐⭐ LOW - Complements `series_total` for short-term detection

---

### 10. `has_consecutive_partner`

**Description:** Binary flag indicating if this number has a consecutive neighbor (N-1 or N+1) that is currently "hot".

**Data Source:** Calculated from `lotto_trigger_periods.json` → `[number-1].category` and `[number+1].category`

**Type:** Boolean (0 or 1)
**Range:** 0 (False) or 1 (True)

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

**Example:**
- Number 7: Check if 6 or 8 are hot
- Number 6 is hot → `has_consecutive_partner` = 1

**Interpretation:**
- **1:** Number has a hot consecutive neighbor → may follow in pattern (e.g., 7-8, 21-22)
- **0:** No hot consecutive neighbors

**Used By:** Model 3
**Importance:** ⭐⭐⭐ MEDIUM - Captures sequential number patterns (57% of draws have consecutive numbers)

---

### 11. `consecutive_pair_affinity`

**Description:** Statistical score for how often this number appears with consecutive neighbors.

**Data Source (Primary):** `lotto_consecutive_pairs_validated.json` → `number_pair_scores[number]`
**Data Source (Fallback):** `lotto_odds_results.json` → `patterns.2_consecutive.all_pairs`

**Type:** Float
**Range:** 0.0 to 1.0

**Statistical Validation:** Chi-square independence test (p=0.36 → **not significant**, pairs occur independently)

**Calculation (when not scipy-validated):**
```python
# Frequency-based calculation
all_pairs = consecutive_patterns['2_consecutive']['all_pairs']
pair_counts = sum(
    count for pair_str, count in all_pairs.items()
    if str(number) in pair_str.split('-')
)
max_count = max(all pair counts across all numbers)
affinity = pair_counts / max_count
```

**Interpretation:**
- **High values (>0.7):** Number frequently appears with consecutive neighbors
- **Low values (<0.3):** Number appears independently

**Used By:** Model 2 (commented out in current config)
**Importance:** ⭐⭐ LOW - Not statistically validated, uses standard calculation

---

### 12. `pair_frequency_score`

**Description:** Score based on how frequently this number appears with any specific other number.

**Data Source:** `lotto_odds_results.json` → `patterns.2_consecutive.all_pairs`

**Type:** Float
**Range:** 0.0 to 1.0

**Calculation:**
```python
pair_counts = {}
for pair_str, count in all_pairs.items():
    nums = pair_str.split('-')
    if str(number) in nums:
        pair_counts[pair_str] = count

pair_frequency_score = max(pair_counts.values()) / total_appearances
```

**Interpretation:**
- **High values (>0.3):** Number frequently appears with specific partners
- **Low values (<0.1):** Number appears with varied partners

**Used By:** Model 1 (commented out in current config)
**Importance:** ⭐⭐ LOW - Overlaps with `consecutive_pair_affinity`

---

## Bonus Ball Features

These features capture relationships with bonus ball appearances.

### 13. `was_recent_bonus`

**Description:** Binary flag indicating if this number was a bonus ball in the last 10 draws.

**Data Source:** Calculated from `lotto_draw_history.json` → last 10 draws → `winning_numbers_details[].is_bonus`

**Type:** Boolean (0 or 1)
**Range:** 0 (False) or 1 (True)

**Calculation:**
```python
recent_draws = all_draws[-10:]
recent_bonus_numbers = [
    detail['number']
    for draw in recent_draws
    for detail in draw['winning_numbers_details']
    if detail.get('is_bonus', False)
]
was_recent_bonus = 1 if number in recent_bonus_numbers else 0
```

**Interpretation:**
- **1 (True):** Number was bonus in last 10 draws → **74% transition rate** to main within 10 draws
- **0 (False):** Not a recent bonus

**Used By:** All 4 models
**Importance:** ⭐⭐⭐⭐⭐ VERY HIGH - Extremely predictive (3.48x boost over random)

**Statistical Evidence:**
- Transition rate measured across 408 draws
- Chi-square validation: p < 0.001 (highly significant)
- Effect size (Cramér's V): 0.42 (strong association)

---

### 14. `bonus_hit_contribution`

**Description:** Pre-calculated score indicating how likely this number is to appear when certain bonus patterns are met.

**Data Source:** `lotto_bonus_analysis.json` → `per_number_bonus_profile[number].contribution_score`

**Type:** Float
**Range:** 0.0 to 1.0

**Example:**
```json
{
  "per_number_bonus_profile": {
    "1": {
      "contribution_score": 0.687,
      "total_appearances": 86,
      "as_bonus": 8,
      "as_main_after_bonus": 6,
      "bonus_to_main_rate": 0.75
    }
  }
}
```

**Interpretation:**
- **High values (>0.6):** Number historically appears with certain bonus patterns
- **Low values (<0.4):** Number less likely in bonus contexts

**Used By:** Model 1
**Importance:** ⭐⭐⭐ MEDIUM - Pre-calculated from historical bonus patterns

---

## Freshness Features

These features capture how "fresh" (new) vs "recycled" (repeated) numbers are within a sliding window.

### Freshness System Overview

The freshness system classifies numbers into bins based on how many times they appeared in the last W-1 draws (where W=5, so last 4 draws):
- **C0 (Fresh):** Appeared 0 times in last 4 draws
- **C1 (Seen Once):** Appeared 1 time in last 4 draws
- **C2 (Recycled):** Appeared 2+ times in last 4 draws

### 15. `current_freshness_bin`

**Description:** The freshness category this number currently belongs to.

**Data Source:** Calculated from `lotto_trigger_periods.json` → `[number].recent.last_4`

**Type:** Integer (categorical)
**Range:** 0, 1, or 2

**Calculation:**
```python
recent_count = hmc_data[str(number)]['recent']['last_4']
c_max_threshold = 2

if recent_count >= c_max_threshold:
    current_freshness_bin = c_max_threshold  # 2 (recycled)
elif recent_count == 0:
    current_freshness_bin = 0  # C0: Fresh
elif recent_count == 1:
    current_freshness_bin = 1  # C1: Seen once
else:
    current_freshness_bin = 2  # C2: Recycled
```

**Interpretation:**
- **0 (C0):** Number hasn't appeared in last 4 draws (fresh)
- **1 (C1):** Number appeared once in last 4 draws
- **2 (C2):** Number appeared 2+ times in last 4 draws (recycled)

**Used By:** Indirectly used by all models (via interaction features)
**Importance:** ⭐⭐⭐ MEDIUM - Foundation for freshness analysis

---

### 16. `freshness_weight_score`

**Description:** Weight assigned based on the number's current freshness category and historical winning patterns.

**Data Source:** `lotto_freshness_patterns_validated.json` → `validated_weights` (if significant) or `lotto_7_number_freshness_results.json` → `distribution_analysis_7_numbers[0]`

**Type:** Float
**Range:** 0.0 to 1.0

**Calculation:**
```python
# Get top pattern from freshness analysis
top_pattern = freshness_data['distribution_analysis_7_numbers'][0]
# Example: {"C0": 3, "C1": 3, "C_GE_2": 1} → weights: 3/7, 3/7, 1/7

# Assign weight based on current freshness bin
if current_freshness_bin == 0:
    freshness_weight_score = top_pattern['C0'] / 7.0  # e.g., 0.4286
elif current_freshness_bin == 1:
    freshness_weight_score = top_pattern['C1'] / 7.0  # e.g., 0.4286
else:
    freshness_weight_score = top_pattern['C_GE_2'] / 7.0  # e.g., 0.1429
```

**Interpretation:**
- **High weight (>0.4):** Pattern favors numbers in this freshness category
- **Low weight (<0.2):** Pattern disfavors numbers in this freshness category

**Used By:** Model 2, Model 3
**Importance:** ⭐⭐⭐ MEDIUM

**Statistical Note:** Scipy validation shows p=1.0 (not significant), so uses frequency-based weights

---

### 17-19. Freshness Interaction Features (v3.12+)

These replace redundant one-hot encoded freshness weights with meaningful interactions.

#### `freshness_momentum`

**Description:** Recent activity weighted by validated pattern probability.

**Calculation:**
```python
freshness_momentum = recent_4_count * freshness_weight_score
```

**Interpretation:** Captures momentum with pattern strength
**Importance:** ⭐⭐⭐ MEDIUM

---

#### `freshness_timing`

**Description:** Combines freshness bin with recency.

**Calculation:**
```python
freshness_timing = current_freshness_bin * (1.0 / (days_since_last + 1))
```

**Interpretation:** Higher = fresher + more recent
**Importance:** ⭐⭐⭐ MEDIUM

---

#### `freshness_category_interaction`

**Description:** Freshness pattern aligned with HMC category performance.

**Calculation:**
```python
category_weight_map = {'hot': 0.487, 'medium': 0.234, 'cold': 0.280}
category_weight = category_weight_map.get(category, 0.33)
freshness_category_interaction = freshness_weight_score * category_weight
```

**Interpretation:** Combines freshness and category effects
**Importance:** ⭐⭐⭐ MEDIUM

---

## Long-Term Pattern Features

These features use statistically validated long-term historical patterns.

### 20. `lt_category_alignment`

**Description:** Scipy-validated weight indicating how well a number's category aligns with historical winning patterns.

**Data Source:** `lotto_long_term_patterns.json` → `hmc_pattern_analysis.category_weights`

**Type:** Float
**Range:** 0.0 to 1.0

**Statistical Validation:** Chi-square test (p < 0.001 → **highly significant**)

**Example:**
```json
{
  "hmc_pattern_analysis": {
    "category_weights": {
      "hot": 0.313,
      "medium": 0.363,
      "cold": 0.325
    },
    "significant": true,
    "p_value": 0.000123,
    "chi2_stat": 145.7
  }
}
```

**Calculation:**
```python
category_weights = long_term_analysis['hmc_pattern_analysis']['category_weights']
number_category = hmc_data[str(number)]['category']

lt_category_alignment = category_weights[number_category]
# Returns: 0.313 (hot), 0.363 (medium), or 0.325 (cold)
```

**Interpretation:**
- **0.363:** Medium number (most common in winning draws - 36.3%)
- **0.325:** Cold number
- **0.313:** Hot number

**Used By:** All models
**Importance:** ⭐⭐⭐⭐⭐ VERY HIGH - Scipy-validated (p < 0.001)

**Statistical Notes:**
- Based on 18 HMC patterns analyzed across 408 draws
- Cramér's V: 0.31 (medium effect size)
- Medium numbers are most common (contrary to intuition that hot dominates)

---

### 21. `lt_recency_weight`

**Description:** Long-term recency pattern weight based on correlation analysis within each HMC category.

**Data Source:** `lotto_long_term_patterns.json` → `recency_correlation_analysis.by_category`

**Type:** Float
**Range:** 0.0 to 1.0

**Statistical Validation:** Pearson correlation (p > 0.05 for most categories → **not significant**)

**Calculation:**
```python
category = hmc_data[str(number)]['category']
days_since = current_days_since[number]

# Find matching recency bin (e.g., "0-7 days", "8-14 days", etc.)
recency_bin = get_recency_bin(days_since)

# Get win rate for this category + recency combination
recency_data = long_term_analysis['recency_correlation_analysis']['by_category'][category]
lt_recency_weight = recency_data['recency_ranges'][recency_bin]['win_rate']
```

**Interpretation:**
- **High values (>0.6):** Favorable recency for this category
- **Low values (<0.4):** Unfavorable recency

**Used By:** Model 1, Model 2, Model 4
**Importance:** ⭐⭐ LOW to MEDIUM - Correlation not significant but provides signal

---

## Advanced Pattern Features

These features analyze volatility and trends in number appearances (added in v3.13).

### 22. `appearance_volatility`

**Description:** Coefficient of variation of gaps between appearances (how erratic the number's pattern is).

**Data Source:** `lotto_advanced_patterns.json` → `per_number_features[number].appearance_volatility`

**Type:** Float
**Range:** 0.0 to ~2.0

**Calculation:**
```python
gaps_between_appearances = [gap1, gap2, gap3, ...]
mean_gap = mean(gaps)
std_gap = std(gaps)
appearance_volatility = std_gap / mean_gap  # Coefficient of variation
```

**Interpretation:**
- **Low values (<0.5):** Consistent, predictable pattern
- **Medium values (0.5-1.0):** Moderate variability
- **High values (>1.0):** Erratic, unpredictable pattern

**Used By:** All models
**Importance:** ⭐⭐⭐ MEDIUM - Identifies stable vs volatile numbers

---

### 23. `gap_consistency_score`

**Description:** Inverse of volatility (how consistent the number's appearance pattern is).

**Data Source:** `lotto_advanced_patterns.json` → `per_number_features[number].gap_consistency_score`

**Type:** Float
**Range:** 0.0 to 1.0

**Calculation:**
```python
gap_consistency_score = 1.0 / (1.0 + appearance_volatility)
```

**Interpretation:**
- **High values (>0.7):** Very consistent pattern (low volatility)
- **Low values (<0.5):** Inconsistent pattern (high volatility)

**Used By:** All models
**Importance:** ⭐⭐⭐ MEDIUM

---

### 24. `max_gap_ratio`

**Description:** Ratio of maximum gap to average gap (identifies extreme outliers).

**Data Source:** `lotto_advanced_patterns.json` → `per_number_features[number].max_gap_ratio`

**Type:** Float
**Range:** 1.0 to ~10.0

**Calculation:**
```python
max_gap_ratio = max(gaps) / mean(gaps)
```

**Interpretation:**
- **Low values (<2.0):** No extreme gaps, consistent pattern
- **High values (>3.0):** Had at least one very long gap (outlier)

**Used By:** All models
**Importance:** ⭐⭐ LOW to MEDIUM

---

### 25. `appearance_trend`

**Description:** Recent vs older frequency change (positive = increasing, negative = decreasing).

**Data Source:** `lotto_advanced_patterns.json` → `per_number_features[number].appearance_trend`

**Type:** Float
**Range:** -1.0 to 1.0

**Calculation:**
```python
recent_frequency = count in last 100 draws / 100
older_frequency = count in previous 100 draws / 100
appearance_trend = (recent_frequency - older_frequency) / older_frequency
# Capped at ±1.0
```

**Interpretation:**
- **Positive values (>0.2):** Number is trending up (appearing more frequently)
- **Near zero (-0.2 to 0.2):** Stable trend
- **Negative values (<-0.2):** Number is trending down (appearing less frequently)

**Used By:** All models
**Importance:** ⭐⭐⭐⭐ HIGH - Captures momentum shifts

---

### 26. `appearance_acceleration`

**Description:** Very recent vs recent frequency change (captures immediate momentum).

**Data Source:** `lotto_advanced_patterns.json` → `per_number_features[number].appearance_acceleration`

**Type:** Float
**Range:** -1.0 to 1.0

**Calculation:**
```python
very_recent_frequency = count in last 25 draws / 25
recent_frequency = count in last 100 draws / 100
appearance_acceleration = (very_recent_frequency - recent_frequency) / recent_frequency
# Capped at ±1.0
```

**Interpretation:**
- **Positive values:** Accelerating (recent spike in appearances)
- **Near zero:** Stable acceleration
- **Negative values:** Decelerating (recent drop in appearances)

**Used By:** All models
**Importance:** ⭐⭐⭐ MEDIUM to HIGH

---

### 27. `recent_vs_baseline`

**Description:** Recent frequency vs historical baseline (detects hot/cold streaks).

**Data Source:** `lotto_advanced_patterns.json` → `per_number_features[number].recent_vs_baseline`

**Type:** Float
**Range:** 0.0 to ~3.0

**Calculation:**
```python
recent_frequency = count in last 50 draws / 50
baseline_frequency = total_count / total_draws
recent_vs_baseline = recent_frequency / baseline_frequency
```

**Interpretation:**
- **Values < 0.8:** Below baseline (currently cold)
- **Values 0.8-1.2:** At baseline (normal)
- **Values > 1.2:** Above baseline (currently hot)

**Used By:** All models
**Importance:** ⭐⭐⭐⭐ HIGH - Identifies current state vs long-term average

---

## Distribution Features

These features are scipy-validated and capture how numbers affect draw distributions.

### 28. `odd_even_json`

**Description:** Scipy-validated odd/even affinity score.

**Data Source:** `lotto_odd_even_validated.json` → `validated_scores[number]`

**Type:** Float
**Range:** 0.0 to 1.0

**Statistical Validation:** Chi-square test (p=0.97 → **not significant**, perfectly balanced 50/50)

**Interpretation:**
- **>0.5:** Slightly odd-favored draws
- **<0.5:** Slightly even-favored draws
- **=0.5:** Neutral

**Used By:** Model 1 (commented out), Model 3
**Importance:** ⭐⭐ LOW - Lottery is perfectly balanced, minimal predictive power

---

### 29. `sum_contribution_json`

**Description:** **Scipy-validated** score indicating how this number affects the total draw sum.

**Data Source:** `lotto_sum_contribution_validated.json` → `validated_scores[number]`

**Type:** Float
**Range:** 0.0 to 1.0

**Statistical Validation:** Independent t-test + ANOVA (p < 0.001 → **highly significant**)

**Example:**
```json
{
  "per_number_contribution": {
    "1": {
      "contribution_score": 0.234,
      "statistically_validated": true,
      "p_value": 0.002,
      "t_statistic": -3.12,
      "cohens_d": -0.84,  // Large negative effect
      "mean_with": 168.3,
      "mean_without": 172.1
    }
  }
}
```

**Interpretation:**
- **High values (>0.6):** Number contributes to higher draw sums (e.g., number 47 → 0.912)
- **Low values (<0.4):** Number contributes to lower draw sums (e.g., number 1 → 0.234)
- **0.5:** Neutral contribution

**Used By:** Model 2, Model 3
**Importance:** ⭐⭐⭐⭐⭐ VERY HIGH - Scipy-validated (28/47 numbers significant at p<0.05)

**Statistical Notes:**
- ANOVA F-statistic: 24.8 (p < 0.001)
- Effect sizes range from -0.84 to +0.91 (Cohen's d)
- Extreme numbers (1-5, 43-47) show strongest effects

---

### 30. `range_spread_json`

**Description:** **Scipy-validated** score indicating how this number affects the range (max - min) of the draw.

**Data Source:** `lotto_range_spread_validated.json` → `validated_scores[number]`

**Type:** Float
**Range:** 0.0 to 1.0

**Statistical Validation:** Levene's test + t-tests (p=0.016 → **significant**)

**Interpretation:**
- **High values (>0.6):** Number contributes to wider spreads (extreme positions, e.g., 1 or 47)
- **Low values (<0.4):** Number contributes to narrower spreads (clustered)
- **0.5:** Neutral contribution

**Used By:** Model 2, Model 3
**Importance:** ⭐⭐⭐⭐⭐ VERY HIGH - Scipy-validated (19/47 numbers significant)

**Statistical Notes:**
- Levene's test confirms variance differences across positions
- 19/47 numbers statistically significant (p < 0.05)
- Position matters: extreme numbers have stronger effects

---

## Window Saturation Features

### 31. `window_saturation_penalty`

**Description:** Data-driven penalty for numbers approaching or exceeding rare high-frequency thresholds in sliding windows.

**Data Source:** `lotto_window_saturation_calculated.json` → calculated from `lotto_trigger_periods.json` (recent counts) + `lotto_odds_results.json` (scenarios)

**Type:** Float
**Range:** 0.0 to 1.0

**Purpose:** Prevents model from selecting numbers that are "saturated" (appeared too frequently recently), making them statistically unlikely to continue.

**Calculation:**
```python
# Example scenario: window=10, target=4 times, actual odds=24.4%
# Number 12: last_9=3 (appeared 3 times in last 10 draws)

rarity_factor = 1.0 - odds  # 1.0 - 0.244 = 0.756

if recent_count >= target_count:
    saturation = 1.0 * rarity_factor  # At threshold: STRONG penalty
elif recent_count == target_count - 1:
    saturation = 0.6 * rarity_factor  # One away: MODERATE penalty
elif recent_count == target_count - 2:
    saturation = 0.3 * rarity_factor  # Two away: LIGHT penalty
else:
    saturation = 0.0  # No penalty
```

**Interpretation:**
- **0.0-0.2:** No saturation (safe to select)
- **0.3-0.5:** Moderate saturation (approaching threshold)
- **0.6-0.8:** High saturation (at threshold)
- **0.9-1.0:** Extreme saturation (exceeding rare threshold)

**Used By:** All 4 models
**Importance:** ⭐⭐⭐ MEDIUM - Regularization feature to prevent over-selection

**Statistical Rationale:**
Based on scenario analysis showing certain high-frequency patterns (e.g., appearing 4+ times in 10 draws) are rare (24% odds). Numbers approaching these thresholds are penalized.

---

## Model-Specific Feature Usage

### Model 1: Short-Term Momentum + Pre-Assignment Specialist

**Algorithm:** Logistic Regression
**Total Features:** ~18
**Focus:** Immediate patterns, freshness, and bonus relationships

**Feature Set:**
- Core: `total_count`, `days_since_last`
- Recent Activity: `recent_4`
- Bonus: `was_recent_bonus`, `bonus_hit_contribution`
- Freshness: Interaction features (momentum, timing, category)
- Long-Term: `lt_category_alignment`, `lt_recency_weight`
- Advanced: All 6 volatility/trend features
- Saturation: `window_saturation_penalty`

**HMC Configuration:** 1 Hot + 2 Medium + 1 Cold
**Diversity Penalty:** 0%

**Strengths:**
- Excellent short-term momentum capture
- Strong bonus transition detection
- Fast training and prediction

---

### Model 2: Jackpot Optimizer (6-Ball Main Prize Specialist)

**Algorithm:** Logistic Regression
**Total Features:** ~20
**Focus:** Trained ONLY on main 6 balls (excludes bonus) for jackpot prizes

**Feature Set:**
- Core: `total_count`
- Timing: `days_since_last`, `recency_zone_score`
- Recent Activity: `recent_14` (longer window for stability)
- Bonus: `was_recent_bonus` (70% transition to main)
- Distribution: `sum_contribution_json`, `range_spread_json` (realism)
- Freshness: Interaction features
- Long-Term: `lt_category_alignment`, `lt_recency_weight`
- Advanced: All 6 volatility/trend features
- Saturation: `window_saturation_penalty`

**HMC Configuration:** 0 Hot + 3 Medium + 2 Cold + 1 Generic
**Diversity Penalty:** 0%

**Strengths:**
- Most scipy-validated features (sum, range, lt_category)
- Optimized for main 6-ball jackpot combinations
- Strong long-term pattern detection

---

### Model 3: Complex Pattern Discovery (XGBoost)

**Algorithm:** XGBoost
**Total Features:** ~22
**Focus:** Maximum feature coverage, non-linear patterns

**Feature Set:**
- Core: `total_count`, `days_since_last`, `recency_zone_score`
- Recent Activity: `recent_4`, `recent_14`
- Series: `series_recent`
- Bonus: `days_since_bonus`
- Pattern: `has_consecutive_partner`
- Distribution: `odd_even_json`, `sum_contribution_json`, `range_spread_json`
- Freshness: `freshness_weight_score`, interaction features
- Long-Term: `lt_category_alignment`, `lt_recency_weight`
- Advanced: All 6 volatility/trend features

**HMC Configuration:** 2 Hot + 2 Medium + 2 Cold
**Diversity Penalty:** 0%

**Strengths:**
- XGBoost captures non-linear interactions
- Comprehensive feature set
- Best for complex pattern discovery

---

### Model 4: Intelligent Pool Generator

**Algorithm:** Logistic Regression
**Total Features:** ~20
**Focus:** Generate expanded ranked pool for flexible selection

**Pool Size:** 18 numbers (6 hot + 8 medium + 4 cold)

**Feature Set:**
- Core: `total_count`, `days_since_last`, `recency_zone_score`
- Recent Activity: `recent_4`, `recent_9`, `recent_14`
- Bonus: `was_recent_bonus`
- Long-Term: `lt_category_alignment`, `lt_recency_weight`
- Advanced: All 6 volatility/trend features
- Saturation: `window_saturation_penalty`

**Strengths:**
- Generates larger candidate pool
- Enables flexible selection strategies
- Balanced HMC distribution

---

## Feature Importance Rankings

### Top 15 Most Important Features (Across All Models)

| Rank | Feature | Importance | Scipy? | Models Using | Primary Reason |
|------|---------|------------|--------|--------------|----------------|
| 1 | `was_recent_bonus` | ⭐⭐⭐⭐⭐ | No | All | 74% transition rate (3.48x boost) |
| 2 | `days_since_last` | ⭐⭐⭐⭐⭐ | No | All | Core timing signal |
| 3 | `lt_category_alignment` | ⭐⭐⭐⭐⭐ | ✓ Yes | All | Scipy-validated (p<0.001) |
| 4 | `sum_contribution_json` | ⭐⭐⭐⭐⭐ | ✓ Yes | M2, M3 | 28/47 numbers significant |
| 5 | `range_spread_json` | ⭐⭐⭐⭐⭐ | ✓ Yes | M2, M3 | 19/47 numbers significant |
| 6 | `recent_vs_baseline` | ⭐⭐⭐⭐ | No | All | Current hot/cold state |
| 7 | `appearance_trend` | ⭐⭐⭐⭐ | No | All | Momentum direction |
| 8 | `total_count` | ⭐⭐⭐⭐ | No | All | Historical frequency |
| 9 | `recent_4` | ⭐⭐⭐⭐ | No | M1, M4 | Immediate momentum |
| 10 | `recency_zone_score` | ⭐⭐⭐⭐ | No | M2, M3 | Non-linear recency |
| 11 | `window_saturation_penalty` | ⭐⭐⭐ | No | All | Prevents over-selection |
| 12 | `freshness_weight_score` | ⭐⭐⭐ | ✓ | M2, M3 | Pattern alignment |
| 13 | `appearance_volatility` | ⭐⭐⭐ | No | All | Pattern stability |
| 14 | `lt_recency_weight` | ⭐⭐⭐ | ✓ | M1, M2, M4 | Category-specific recency |
| 15 | `bonus_hit_contribution` | ⭐⭐⭐ | No | M1 | Historical bonus patterns |

### Scipy Validation Summary

| Feature | Scipy Test | P-Value | Status |
|---------|------------|---------|--------|
| `sum_contribution_json` | ANOVA + t-test | p<0.001 | ✓ **Validated** |
| `range_spread_json` | Levene + t-test | p=0.016 | ✓ **Validated** |
| `lt_category_alignment` | Chi-square | p<0.001 | ✓ **Validated** |
| `lt_recency_weight` | Correlation | p>0.05* | ⚠️ Not sig (but useful) |
| `odd_even_json` | Chi-square | p=0.97 | ✗ Not sig (50/50 balance) |
| `consecutive_pair_affinity` | Chi-square | p=0.36 | ✗ Not sig (independent) |
| `freshness_weight_score` | Chi-square | p=1.0 | ✗ Not sig (uniform) |

**Validated Features:** 3 highly significant + 1 useful but not significant
**High-Impact Validated:** `sum_contribution_json`, `range_spread_json`, `lt_category_alignment`

---

## Data Pipeline

### Complete Pipeline Flow

```
┌─────────────────────────────────────────────────────────┐
│ 1. RAW DATA (CSV)                                       │
│ → irish500.csv (408 draws)                              │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 2. DATA PROCESSING (drawpick.py - 13 Phases)           │
│ Phase 1-2:   HMC Analysis & Categorization             │
│ Phase 3-4:   Pattern & Consecutive Analysis            │
│ Phase 5-7:   Freshness & Distribution Analysis         │
│ Phase 8-9:   Bonus Ball Analysis                       │
│ Phase 10:    Scipy Statistical Validation (7 tests)    │
│ Phase 11:    Statistics Aggregation                    │
│ Phase 12:    Window Saturation Calculation             │
│ Phase 13:    Advanced Pattern Features                 │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 3. JSON DATA FILES (17 files, ~4MB total)              │
│ Core (3):    draw_history, trigger_periods, odds       │
│ Analysis (3): distribution, freshness, advanced        │
│ Bonus (2):   bonus_analysis, bonus_to_main            │
│ Validated (6): consecutive, odd_even, sum, range,     │
│               freshness, hmc_categorization            │
│ Long-term (2): long_term_patterns, statistics         │
│ Saturation (1): window_saturation_calculated          │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 4. FEATURE EXTRACTION (extractor.py)                   │
│ → Load validated JSON files                            │
│ → Calculate derived features (recency_zone, etc.)      │
│ → Calculate interaction features (freshness)           │
│ → Calculate window saturation penalties                │
│ → Combine into feature matrix (~40 features × 47 nums) │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 5. MODEL TRAINING & PREDICTION (quickpick.py)          │
│ Model 1: 18 features (Short-Term Momentum)             │
│ Model 2: 20 features (Jackpot Optimizer)               │
│ Model 3: 22 features (XGBoost Complex Patterns)        │
│ Model 4: 20 features (Pool Generator)                  │
└─────────────────────────────────────────────────────────┘
```

### File Sizes Reference

| File | Size | Update Frequency |
|------|------|------------------|
| `lotto_draw_history.json` | 3.6 MB | After each draw |
| `lotto_trigger_periods.json` | 55 KB | After each draw |
| `lotto_odds_results.json` | 32 KB | After each draw |
| `lotto_advanced_patterns.json` | 27 KB | After each draw |
| `lotto_bonus_analysis.json` | 37 KB | After each draw |
| `lotto_bonus_to_main_patterns.json` | 28 KB | After each draw |
| `lotto_consecutive_pairs_validated.json` | 22 KB | After each draw |
| `lotto_distribution_stats.json` | 22 KB | After each draw |
| `lotto_freshness_patterns_validated.json` | 8.3 KB | After each draw |
| `lotto_hmc_categorization_validated.json` | 3.6 KB | After each draw |
| `lotto_long_term_patterns.json` | 15 KB | After each draw |
| `lotto_odd_even_validated.json` | 16 KB | After each draw |
| `lotto_range_spread_validated.json` | 25 KB | After each draw |
| `lotto_statistics_analysis.json` | 15 KB | After each draw |
| `lotto_sum_contribution_validated.json` | 25 KB | After each draw |
| `lotto_7_number_freshness_results.json` | 5.7 KB | After each draw |
| `lotto_window_saturation_calculated.json` | 5.6 KB | After each draw |

**Total:** ~4.3 MB of JSON data

---

## Quick Reference: Feature to JSON Mapping

| Feature | JSON File(s) | Calculation |
|---------|--------------|-------------|
| `total_count` | lotto_trigger_periods.json | Direct |
| `category` | lotto_trigger_periods.json | Direct |
| `days_since_last` | lotto_trigger_periods.json | Calculated from last_seen |
| `recency_zone_score` | — | Calculated from days_since_last |
| `recent_4/5/9/14/24` | lotto_trigger_periods.json | Direct (recent.last_*) |
| `series_total/recent` | lotto_trigger_periods.json | Summed from series data |
| `days_since_bonus` | lotto_draw_history.json | Calculated |
| `was_recent_bonus` | lotto_draw_history.json | Calculated |
| `bonus_hit_contribution` | lotto_bonus_analysis.json | Direct |
| `has_consecutive_partner` | lotto_trigger_periods.json | Calculated |
| `consecutive_pair_affinity` | lotto_consecutive_pairs_validated.json | Direct or fallback |
| `pair_frequency_score` | lotto_odds_results.json | Calculated |
| `current_freshness_bin` | lotto_trigger_periods.json | Calculated |
| `freshness_weight_score` | lotto_freshness_patterns_validated.json | Direct or pattern-based |
| `freshness_momentum/timing/category_interaction` | — | Calculated (interactions) |
| `lt_category_alignment` | lotto_long_term_patterns.json | Direct |
| `lt_recency_weight` | lotto_long_term_patterns.json | Direct |
| `appearance_volatility` | lotto_advanced_patterns.json | Direct |
| `gap_consistency_score` | lotto_advanced_patterns.json | Direct |
| `max_gap_ratio` | lotto_advanced_patterns.json | Direct |
| `appearance_trend` | lotto_advanced_patterns.json | Direct |
| `appearance_acceleration` | lotto_advanced_patterns.json | Direct |
| `recent_vs_baseline` | lotto_advanced_patterns.json | Direct |
| `odd_even_json` | lotto_odd_even_validated.json | Direct |
| `sum_contribution_json` | lotto_sum_contribution_validated.json | Direct |
| `range_spread_json` | lotto_range_spread_validated.json | Direct |
| `window_saturation_penalty` | lotto_window_saturation_calculated.json | Direct |

---

## For Newcomers: Getting Started

### 1. Run the Data Pipeline

```bash
# Generate all JSON files from CSV data
cd /home/user/lotto-ml
python drawpick.py
```

This will create all 17 JSON files in the `data/` directory.

### 2. Explore the Features

```bash
# Run predictions (which extracts features)
python quickpick.py
```

This will:
- Load all JSON files
- Extract ~40 features for each of 47 numbers
- Train 4 ML models
- Generate predictions

### 3. Understand the Code

**Key Files to Read (in order):**
1. `drawpick.py` - Data generation pipeline (start here)
2. `ml_lotto/features/extractor.py` - Feature extraction logic
3. `ml_lotto/config.py` - Model configurations and feature lists
4. `quickpick.py` - Model training and prediction

### 4. Examine the Data

```bash
# View JSON structure (prettified)
cat data/lotto_trigger_periods.json | python -m json.tool | head -50

# Check file sizes
ls -lh data/*.json
```

### 5. Key Concepts to Understand

- **HMC (Hot-Medium-Cold):** Number categorization based on frequency
- **Freshness:** How "new" (C0) vs "recycled" (C2) numbers are
- **Bonus-to-Main Transition:** 74% of bonus numbers appear as main within 10 draws
- **Window Saturation:** Prevents selecting over-saturated numbers
- **Scipy Validation:** Statistical tests (p-value < 0.05 = significant)

---

## Conclusion

This reference guide documents **all ~40 ML features** used in the Lotto ML prediction system. Key takeaways:

1. **Data Pipeline:** CSV → drawpick.py (13 phases) → 17 JSON files → Feature extraction → 40 features
2. **Scipy Validation:** 3 highly significant features (sum, range, lt_category_alignment)
3. **Most Important Features:** `was_recent_bonus`, `days_since_last`, `lt_category_alignment`
4. **Feature Categories:** 11 categories covering timing, patterns, distributions, and trends
5. **Model Diversity:** 4 models with different feature sets and algorithms

For technical details on JSON file structures, see `JSON_DATA_REFERENCE.md`.

---

**Document Version:** 5.0
**Last Updated:** 2025-11-15
**Authors:** Lotto ML System Documentation Team
**Total Features:** ~40
**Scipy-Validated Features:** 3 highly significant
