# Long-Term Pattern Analysis

## Overview

This document describes the new **Long-Term Pattern Analysis** feature, which complements the existing `FRESHNESS_PATTERN_WEIGHTS` (short-term patterns) by analyzing stable, long-term trends in lottery draw data.

## Motivation

While `FRESHNESS_PATTERN_WEIGHTS` excels at capturing short-term momentum (recent 4-14 draws), lottery patterns also exhibit long-term stability across hundreds of draws. This feature analyzes:

1. **HMC Distribution Patterns**: How hot/medium/cold numbers are distributed in winning draws over long periods
2. **Category-Based Recency Patterns**: Which "days since last hit" ranges are most successful for each category
3. **Historical Performance Trends**: Stable patterns that persist across many months

## How It Works

### 1. HMC Pattern Weights

Analyzes historical HMC patterns (e.g., "2-3-2", "3-2-2", "2-2-3") to determine optimal distribution:

```python
# Example pattern: "2-3-2" means:
# - 2 hot numbers
# - 3 medium numbers
# - 2 cold numbers
```

**Features Generated:**
- `lt_hot_weight`: Weight indicating hot numbers' importance (0.0-1.0)
- `lt_medium_weight`: Weight indicating medium numbers' importance
- `lt_cold_weight`: Weight indicating cold numbers' importance
- `lt_category_alignment`: Overall alignment score for number's current category

**Algorithm:**
1. Load HMC pattern distributions from `lotto_statistics_analysis.json`
2. For each category position (hot/medium/cold), calculate weighted average based on pattern success rates
3. Normalize weights to sum to 1.0
4. Assign alignment score to each number based on its current category

### 2. Long-Term Recency Weights

Analyzes "days since last hit" patterns by category to identify optimal recency ranges:

```python
# Example recency ranges:
# "0-7 days": 25.3%    # Very recent
# "8-14 days": 20.1%   # Recent
# "15-21 days": 15.4%  # Moderate
# ...
# "121+ days": 1.2%    # Very old
```

**Feature Generated:**
- `lt_recency_weight`: Weight based on number's days-since-last and historical success (0.0-1.0)

**Algorithm:**
1. Load days_since_last_hit distributions from statistics JSON
2. Calculate current days since last appearance for each number
3. Match number to its recency range
4. Assign weight based on historical success rate of that range for the number's category

## Usage

### In Model Configuration

Add `LONG_TERM_PATTERN_WEIGHTS` to your model's feature list:

```python
MODEL_EXAMPLE = {
    'name': 'Long-Term Pattern Model',
    'features': [
        'total_count',
        'days_since_last',
        FRESHNESS_PATTERN_WEIGHTS,      # Short-term patterns
        LONG_TERM_PATTERN_WEIGHTS,       # NEW: Long-term patterns
        'bonus_hit_contribution',
        # ... other features
    ],
    # ... rest of config
}
```

### Expansion in Feature Extraction

The `LONG_TERM_PATTERN_WEIGHTS` constant will expand to these features:

```python
[
    'lt_hot_weight',
    'lt_medium_weight',
    'lt_cold_weight',
    'lt_category_alignment',
    'lt_recency_weight'
]
```

### Loading Long-Term Features

In your data loading code:

```python
from ml_lotto.data.loader import load_statistics_analysis
from ml_lotto.features.long_term_patterns import expand_long_term_features

# Load statistics data
statistics_data = load_statistics_analysis(STATISTICS_ANALYSIS_JSON)

# Calculate long-term features
long_term_features = expand_long_term_features(
    hmc_data=hmc_data,
    statistics_data=statistics_data,
    all_draws=all_draws
)

# Access features for a number
number_features = long_term_features[23]  # Features for number 23
print(f"Hot weight: {number_features['lt_hot_weight']}")
print(f"Category alignment: {number_features['lt_category_alignment']}")
```

## Comparison: Short-Term vs Long-Term

| Feature | FRESHNESS_PATTERN_WEIGHTS | LONG_TERM_PATTERN_WEIGHTS |
|---------|---------------------------|---------------------------|
| **Time Range** | Recent 4-14 draws | 100+ historical draws |
| **Focus** | Momentum, recent trends | Stable, persistent patterns |
| **Volatility** | High (changes frequently) | Low (stable over time) |
| **Best For** | Capturing hot streaks | Identifying reliable trends |
| **Data Source** | `lotto_7_number_freshness_results.json` | `lotto_statistics_analysis.json` |

**Recommendation**: Use **both** features together:
- `FRESHNESS_PATTERN_WEIGHTS` captures immediate momentum
- `LONG_TERM_PATTERN_WEIGHTS` provides stable baseline

## Example Analysis Output

When running feature extraction, you'll see:

```
============================================================
LONG-TERM PATTERN ANALYSIS
============================================================

✓ Long-Term HMC Pattern Analysis:
  Analyzed 31 historical HMC patterns
  Hot weight: 32.4%
  Medium weight: 35.8%
  Cold weight: 31.8%

  Current number distribution:
    Hot: 15 numbers
    Medium: 17 numbers
    Cold: 15 numbers

✓ Long-Term Recency Weights calculated
  Based on 9 historical recency ranges

✓ Long-term pattern features calculated for all 47 numbers
============================================================
```

## Integration with Extractor

To integrate with the main feature extractor, update `extractor.py`:

```python
# Import the long-term features module
from ml_lotto.features.long_term_patterns import expand_long_term_features
from ml_lotto.data.loader import load_statistics_analysis

# In extract_features_from_hmc_json, add parameters:
def extract_features_from_hmc_json(
    # ... existing parameters ...
    statistics_data: Dict[str, Any] = None,
    long_term_features: Dict[int, Dict[str, float]] = None
):
    # Add long-term features to feature dictionary
    for num in range(1, MAX_NUMBER + 1):
        lt_features = long_term_features.get(num, {}) if long_term_features else {}

        features[num] = {
            # ... existing features ...
            **lt_features,  # Add long-term features
        }

# In expand_feature_selection, add:
custom_keywords = {
    # ... existing keywords ...
    LONG_TERM_PATTERN_WEIGHTS: ['lt_hot_weight', 'lt_medium_weight',
                                  'lt_cold_weight', 'lt_category_alignment',
                                  'lt_recency_weight']
}
```

## Files Modified/Created

### New Files:
- `ml_lotto/features/long_term_patterns.py` - Core implementation
- `LONG_TERM_PATTERN_ANALYSIS.md` - This documentation

### Modified Files:
- `ml_lotto/config.py` - Added `LONG_TERM_PATTERN_WEIGHTS` constant and `STATISTICS_ANALYSIS_JSON` path
- `ml_lotto/data/loader.py` - Added `load_statistics_analysis()` function

## Future Enhancements

Potential improvements to consider:

1. **Time-Weighted HMC Patterns**: Weight recent patterns more heavily than old patterns
2. **Adaptive Thresholds**: Dynamically adjust recency range boundaries based on recent trends
3. **Category Transition Analysis**: Track when numbers transition between hot/medium/cold
4. **Multi-Draw Window Analysis**: Analyze patterns across multiple window sizes (e.g., 50, 100, 200 draws)
5. **Seasonal Pattern Detection**: Identify if patterns vary by time of year

## Performance Considerations

- **Computation**: Long-term features are calculated once per prediction (not per training instance)
- **Memory**: Minimal overhead (~5 features per number = 235 values total)
- **Training Time**: No significant impact on model training time
- **Prediction Speed**: Negligible impact on prediction speed

## Conclusion

The Long-Term Pattern Analysis feature provides a stable, data-driven complement to short-term momentum features. By analyzing patterns across hundreds of draws, it identifies reliable trends that can improve prediction accuracy when combined with other features.

**Key Benefit**: While short-term features can be noisy, long-term features provide a stable foundation that helps models avoid overfitting to temporary fluctuations.
