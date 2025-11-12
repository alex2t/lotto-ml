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
9. [Model-Specific Feature Usage](#model-specific-feature-usage)
10. [Data Source Summary Table](#data-source-summary-table)

---

## Feature Categories Overview

The system uses **31 distinct features** across different categories:

| Category | Count | Validation | Data Sources |
|----------|-------|------------|--------------|
| Static Features | 8 | Standard | lotto_trigger_periods.json, lotto_draw_history.json |
| Freshness Features | 4 | Scipy (optional) | lotto_freshness_patterns_validated.json |
| Dynamic Features | 4 | Standard | lotto_trigger_periods.json (recent.last_N) |
| Long-Term Features | 5 | Scipy | lotto_long_term_patterns.json |
| Bonus Features | 3 | Standard | lotto_bonus_analysis.json |
| Pattern Features | 2 | Scipy (optional) | lotto_consecutive_pairs_validated.json |
| JSON Features | 5 | Scipy (3/5) | Multiple validated JSON files |

**Total:** 31 features (varies by model configuration)

---

## Static Features

### 1. `total_count`

**Type:** Integer
**Range:** 0 to ~60
**Data Source:** `lotto_trigger_periods.json` → `[number].total_count`

**JSON Path:**
```json
{
  "1": {
    "total_count": 52  ← THIS VALUE
  }
}
```

**Description:** Total appearances as main number (not bonus) across all analyzed draws.

**Feature Importance:** ⭐⭐⭐⭐ HIGH

---

### 2. `days_since_last`

**Type:** Integer
**Range:** 0 to 999
**Data Source:** `lotto_trigger_periods.json` → `[number].days_since_last_hit`

**JSON Path:**
```json
{
  "1": {
    "days_since_last_hit": 14  ← THIS VALUE
  }
}
```

**Description:** Days since last appearance as main number.

**Feature Importance:** ⭐⭐⭐⭐⭐ VERY HIGH

---

### 3. `recency_zone_score`

**Type:** Float
**Range:** 0.0 to 1.0
**Data Source:** CALCULATED from `days_since_last`

**Calculation:**
```python
# From ml_lotto/features/timing.py:calculate_recency_zone_score()
if days_since_last <= 7:
    return 0.3
elif days_since_last <= 14:
    return 0.5
elif days_since_last <= 21:
    return 0.7
elif days_since_last <= 35:
    return 0.9
else:
    return 1.0
```

**Feature Importance:** ⭐⭐⭐⭐ HIGH

---

### 4. `series_total`

**Type:** Integer
**Range:** 0 to ~20
**Data Source:** `lotto_trigger_periods.json` → `[number].series.series.*[].count`

**JSON Path:**
```json
{
  "1": {
    "series": {
      "series": {
        "5_consecutives_2_times": [
          {"count": 3}  ← Sum all counts
        ]
      }
    }
  }
}
```

**Feature Importance:** ⭐⭐ LOW

---

### 5. `series_recent`

**Type:** Integer
**Range:** 0 to ~5
**Data Source:** `lotto_trigger_periods.json` → `[number].series` (filtered to recent window)

**Feature Importance:** ⭐⭐ LOW

---

### 6. `days_since_bonus`

**Type:** Integer
**Range:** 0 to 999
**Data Source:** CALCULATED from `lotto_draw_history.json`

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

**Feature Importance:** ⭐⭐⭐ MEDIUM

---

### 7. `win_bias_ratio`

**Type:** Float
**Range:** 0.5 to 2.0
**Data Source:** `lotto_draw_history.json` → latest draw → `winning_numbers_details[].win_bias_ratio`

**JSON Path:**
```json
{
  "2025-01-15": {
    "winning_numbers_details": [
      {
        "number": 1,
        "win_bias_ratio": 1.087  ← THIS VALUE
      }
    ]
  }
}
```

**Feature Importance:** ⭐⭐⭐ MEDIUM

---

### 8. `was_recent_bonus`

**Type:** Boolean (0 or 1)
**Range:** 0 or 1
**Data Source:** CALCULATED from `lotto_draw_history.json` (last 10 draws)

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

**Feature Importance:** ⭐⭐⭐⭐⭐ VERY HIGH (74% transition rate)

---

## Freshness Features

### 9-11. `freshness_c0_weight`, `freshness_c1_weight`, `freshness_c2_weight`

**Type:** Float
**Range:** 0.0 to 1.0
**Data Source (Scipy):** `lotto_freshness_patterns_validated.json` → `validated_weights`
**Data Source (Fallback):** `lotto_7_number_freshness_results.json` → `distribution_analysis_7_numbers[0]`

**JSON Path (Scipy-validated):**
```json
{
  "validated_weights": {
    "C0": {
      "normalized_weight": 0.4286,  ← freshness_c0_weight
      "statistically_validated": true
    },
    "C1": {
      "normalized_weight": 0.4286,  ← freshness_c1_weight
      "statistically_validated": true
    },
    "C_GE_3": {
      "normalized_weight": 0.1429,  ← freshness_c2_weight
      "statistically_validated": true
    }
  }
}
```

**JSON Path (Fallback):**
```json
{
  "distribution_analysis_7_numbers": [
    {
      "pattern": "C0=3, C1=3, C>=3=1",
      "C0": 3,  ← 3/7 = 0.4286
      "C1": 3,  ← 3/7 = 0.4286
      "C_GE_3": 1  ← 1/7 = 0.1429
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
    c0_weight = top_pattern['C0'] / 7.0
```

**Feature Importance:** ⭐⭐⭐ MEDIUM

---

### 12. `current_freshness_bin`

**Type:** Integer (0, 1, or 2)
**Data Source:** CALCULATED from `lotto_trigger_periods.json` → `[number].recent.last_4`

**Calculation:**
```python
# From ml_lotto/features/freshness.py
recent_count = hmc_data[str(number)]['recent']['last_4']
if recent_count >= c_max_threshold:
    current_freshness_bin = c_max_threshold  # e.g., 2
else:
    current_freshness_bin = recent_count  # 0, 1, or 2
```

**Feature Importance:** ⭐⭐ LOW (derived feature)

---

## Dynamic Recent Count Features

### 13-16. `recent_4`, `recent_5`, `recent_9`, `recent_14`, `recent_103`

**Type:** Integer
**Range:** 0 to N (window size)
**Data Source:** `lotto_trigger_periods.json` → `[number].recent.last_N`

**JSON Path:**
```json
{
  "1": {
    "recent": {
      "last_4": 2,    ← recent_5 (actually last_4)
      "last_9": 4,    ← recent_9
      "last_13": 6,   ← recent_14 (actually last_13)
      "last_103": 45  ← recent_103
    }
  }
}
```

**Note:** The key naming is `last_N-1` (so `last_4` = 5 draws).

**Calculation:**
```python
# From ml_lotto/features/base.py:get_dynamic_recent_keys()
# Dynamically detect all recent_* keys from data
for num_data in hmc_data.values():
    recent_keys = num_data.get('recent', {}).keys()
    # Returns: ['last_4', 'last_9', 'last_13', 'last_103']
```

**Feature Importance:** ⭐⭐⭐⭐ HIGH (`recent_4`), ⭐⭐⭐ MEDIUM (others)

---

## Long-Term Pattern Features

### 17-19. `lt_hot_weight`, `lt_medium_weight`, `lt_cold_weight`

**Type:** Float
**Range:** 0.0 to 1.0
**Data Source:** `lotto_long_term_patterns.json` → `hmc_pattern_analysis.category_weights`

**JSON Path:**
```json
{
  "hmc_pattern_analysis": {
    "category_weights": {
      "hot": 0.313,     ← lt_hot_weight (if number is hot)
      "medium": 0.363,  ← lt_medium_weight (if number is medium)
      "cold": 0.325     ← lt_cold_weight (if number is cold)
    },
    "significant": true,
    "p_value": 0.000123  ← Chi-square validated (p < 0.001)
  }
}
```

**Calculation:**
```python
# From ml_lotto/features/long_term_patterns.py:calculate_long_term_hmc_pattern_weights()
category_weights = long_term_analysis['hmc_pattern_analysis']['category_weights']
number_category = hmc_data[str(number)]['category']  # 'hot', 'medium', or 'cold'

if number_category == 'hot':
    lt_hot_weight = category_weights['hot']
    lt_medium_weight = 0.0
    lt_cold_weight = 0.0
elif number_category == 'medium':
    lt_hot_weight = 0.0
    lt_medium_weight = category_weights['medium']
    lt_cold_weight = 0.0
else:  # cold
    lt_hot_weight = 0.0
    lt_medium_weight = 0.0
    lt_cold_weight = category_weights['cold']
```

**Feature Importance:** ⭐⭐⭐⭐⭐ VERY HIGH (Scipy-validated, p<0.001)

---

### 20. `lt_category_alignment`

**Type:** Float
**Range:** 0.0 to 1.0
**Data Source:** CALCULATED from `lt_hot_weight + lt_medium_weight + lt_cold_weight`

**Calculation:**
```python
lt_category_alignment = lt_hot_weight + lt_medium_weight + lt_cold_weight
# Returns: 0.313 (hot), 0.363 (medium), or 0.325 (cold)
```

**Feature Importance:** ⭐⭐⭐⭐ HIGH (Scipy-derived)

---

### 21. `lt_recency_weight`

**Type:** Float
**Range:** 0.0 to 1.0
**Data Source:** `lotto_long_term_patterns.json` → `recency_correlation_analysis.by_category`

**JSON Path:**
```json
{
  "recency_correlation_analysis": {
    "by_category": {
      "hot": {
        "recency_ranges": {
          "0-7 days": {
            "wins": 260,
            "win_rate": 0.339  ← Use this for numbers with 0-7 days recency
          },
          "8-14 days": {
            "win_rate": 0.202
          }
        }
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

**Feature Importance:** ⭐⭐ LOW (correlation not significant, p>0.05)

---

## Bonus-Related Features

### 22. `bonus_hit_contribution`

**Type:** Float
**Range:** 0.0 to 1.0
**Data Source:** `lotto_bonus_analysis.json` → `per_number_bonus_profile[number].contribution_score`

**JSON Path:**
```json
{
  "per_number_bonus_profile": {
    "1": {
      "contribution_score": 0.687,  ← THIS VALUE
      "total_appearances": 52,
      "as_bonus": 8,
      "as_main_after_bonus": 6
    }
  }
}
```

**Feature Importance:** ⭐⭐⭐ MEDIUM

---

### 23. `has_consecutive_partner`

**Type:** Boolean (0 or 1)
**Data Source:** CALCULATED from `lotto_trigger_periods.json` → `[number-1].category` and `[number+1].category`

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

**Feature Importance:** ⭐⭐⭐ MEDIUM

---

### 24. `consecutive_pair_affinity`

**Type:** Float
**Range:** 0.0 to 1.0
**Data Source (Scipy):** `lotto_consecutive_pairs_validated.json` → `number_pair_scores[number]`
**Data Source (Fallback):** `lotto_odds_results.json` → `patterns.2_consecutive.all_pairs`

**JSON Path (Scipy-validated):**
```json
{
  "number_pair_scores": {
    "1": 0.523,  ← THIS VALUE for number 1
    "2": 0.678,  ← THIS VALUE for number 2
    ...
  },
  "overall_chi_square_test": {
    "p_value": 0.36,  ← Not significant
    "significant": false
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
    affinity = pair_counts / max_count
```

**Feature Importance:** ⭐⭐ LOW (not scipy-validated, p=0.36)

---

## JSON-Based Features

### 25. `odd_even_json`

**Type:** Float
**Range:** 0.0 to 1.0
**Data Source (Scipy):** `lotto_odd_even_validated.json` → `validated_scores[number]`
**Data Source (Fallback):** `lotto_distribution_stats.json` → `odd_even_analysis[number].affinity_score`

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
    "significant": false
  }
}
```

**JSON Path (Fallback):**
```json
{
  "odd_even_analysis": {
    "1": {
      "affinity_score": 0.654  ← THIS VALUE
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

**Feature Importance:** ⭐⭐ LOW (p=0.97, perfectly balanced 50/50)

---

### 26. `sum_contribution_json`

**Type:** Float
**Range:** 0.0 to 1.0
**Data Source:** `lotto_sum_contribution_validated.json` → `validated_scores[number]`

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
    "significant": true
  },
  "per_number_contribution": {
    "1": {
      "contribution_score": 0.234,
      "statistically_validated": true,
      "p_value": 0.002,
      "cohens_d": -0.84,  ← Large negative effect
      "mean_with": 168.3,
      "mean_without": 172.1
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

**Feature Importance:** ⭐⭐⭐⭐⭐ VERY HIGH (Scipy-validated, p<0.001, 28/47 numbers significant)

---

### 27. `range_spread_json`

**Type:** Float
**Range:** 0.0 to 1.0
**Data Source:** `lotto_range_spread_validated.json` → `validated_scores[number]`

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
    "significant": true
  },
  "per_number_contribution": {
    "1": {
      "contribution_score": 0.245,
      "statistically_validated": true,
      "p_value": 0.008,
      "cohens_d": -0.67,  ← Medium negative effect
      "mean_with": 31.2,
      "mean_without": 33.8
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

**Feature Importance:** ⭐⭐⭐⭐⭐ VERY HIGH (Scipy-validated, p=0.016, 19/47 numbers significant)

---

### 28. `freshness_weight_score`

**Type:** Float
**Range:** 0.0 to 1.0
**Data Source:** CALCULATED from `freshness_c0_weight`, `freshness_c1_weight`, `freshness_c2_weight` + `current_freshness_bin`

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

**Feature Importance:** ⭐⭐⭐ MEDIUM

---

### 29. `pair_frequency_score`

**Type:** Float
**Range:** 0.0 to 1.0
**Data Source:** `lotto_odds_results.json` → `patterns.2_consecutive.all_pairs` (same as consecutive_pair_affinity)

**JSON Path:**
```json
{
  "patterns": {
    "2_consecutive": {
      "all_pairs": {
        "1-2": 45,
        "1-3": 12,
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

**Feature Importance:** ⭐⭐ LOW

---

## Model-Specific Feature Usage

### Model 1: Short-Term Momentum Specialist

**Algorithm:** Logistic Regression
**Total Features:** 11

| Feature | Data Source | Scipy? |
|---------|-------------|--------|
| `total_count` | lotto_trigger_periods.json | No |
| `days_since_last` | lotto_trigger_periods.json | No |
| `recency_zone_score` | Calculated | No |
| `was_recent_bonus` | Calculated from draw_history | No |
| `has_consecutive_partner` | Calculated from trigger_periods | No |
| `odd_even_json` | lotto_odd_even_validated.json | ✓ |
| `bonus_hit_contribution` | lotto_bonus_analysis.json | No |
| `pair_frequency_score` | lotto_odds_results.json | No |
| `freshness_c0_weight` | lotto_freshness_patterns_validated.json | ✓ |
| `freshness_c1_weight` | lotto_freshness_patterns_validated.json | ✓ |
| `freshness_c2_weight` | lotto_freshness_patterns_validated.json | ✓ |

---

### Model 2: Long-Term Value Specialist

**Algorithm:** Logistic Regression
**Total Features:** 17

| Feature | Data Source | Scipy? |
|---------|-------------|--------|
| `total_count` | lotto_trigger_periods.json | No |
| `days_since_last` | lotto_trigger_periods.json | No |
| `recency_zone_score` | Calculated | No |
| `days_since_bonus` | Calculated from draw_history | No |
| `was_recent_bonus` | Calculated from draw_history | No |
| `bonus_hit_contribution` | lotto_bonus_analysis.json | No |
| `recent_14` | lotto_trigger_periods.json (recent.last_13) | No |
| `win_bias_ratio` | lotto_draw_history.json (latest) | No |
| `consecutive_pair_affinity` | lotto_consecutive_pairs_validated.json | ✓ |
| `sum_contribution_json` | lotto_sum_contribution_validated.json | ✓✓✓ |
| `range_spread_json` | lotto_range_spread_validated.json | ✓✓✓ |
| `freshness_weight_score` | Calculated from freshness weights | ✓ |
| `lt_hot_weight` | lotto_long_term_patterns.json | ✓✓✓ |
| `lt_medium_weight` | lotto_long_term_patterns.json | ✓✓✓ |
| `lt_cold_weight` | lotto_long_term_patterns.json | ✓✓✓ |
| `lt_category_alignment` | Calculated from lt_*_weight | ✓✓✓ |
| `lt_recency_weight` | lotto_long_term_patterns.json | ✓ |

**✓✓✓** = Highly significant (p < 0.001)
**✓** = Validated but not significant

---

### Model 3: Complex Pattern Explorer

**Algorithm:** XGBoost
**Total Features:** 25

All features from Model 1 + Model 2, plus:
- `series_total`, `series_recent`, `recent_4`

---

## Data Source Summary Table

| JSON File | Features Sourced | Scipy Validated | P-Value | Generated By |
|-----------|------------------|-----------------|---------|--------------|
| **lotto_trigger_periods.json** | total_count, days_since_last, recent_*, series_* | No | N/A | drawpick.py Phase 2 |
| **lotto_draw_history.json** | days_since_bonus, was_recent_bonus, win_bias_ratio | No | N/A | drawpick.py Phase 2 |
| **lotto_bonus_analysis.json** | bonus_hit_contribution | No | N/A | drawpick.py Phase 8 |
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
│ → Combine into feature matrix (31 features × 47 numbers)  │
└─────────────────┬──────────────────────────────────────────┘
                  │
                  ▼
┌────────────────────────────────────────────────────────────┐
│ PHASE 4: Model Training & Prediction (quickpick.py)      │
│ → Model 1: 11 features                                    │
│ → Model 2: 17 features (most scipy-validated)            │
│ → Model 3: 25 features (XGBoost)                          │
└────────────────────────────────────────────────────────────┘
```

---

## Conclusion

### Key Insights

1. **6 Scipy-Validated Features** provide statistical rigor (p < 0.05)
2. **4 Highly Significant Features** drive predictions: `sum_contribution_json`, `range_spread_json`, `lt_medium_weight`, `lt_hot_weight`
3. **Model 2 has most validated features** (6 out of 17), making it the most statistically rigorous
4. **Every feature traces to a JSON file** with exact path documented above

### Data Quality Checklist

✅ **Run `python drawpick.py`** to generate all base + validated files
✅ **Check Phase 10 output** for p-values and validation status
✅ **Verify file timestamps** - all should be from same run
✅ **Inspect scipy summary** in quickpick.py output for "✓ Using SCIPY-VALIDATED"

---

**Document Version:** 2.0
**Last Updated:** 2025-11-12
**Author:** Lotto ML System Documentation Team
