# Window Saturation Feature - Version 2.0 Improvements

## Overview

The window saturation feature has been completely redesigned to replace hardcoded penalty values with a **JSON-driven, data-based configuration system**. This allows for dynamic, category-aware penalty calculations that can be easily tuned and validated.

## What Changed

### Version 1.0 (Old - Hardcoded)
```python
# HARDCODED VALUES - NO FLEXIBILITY
rarity_factor = 1.0 - odds

if recent_count >= target_count:
    saturation = 1.0 * rarity_factor      # ❌ Hardcoded 1.0
elif recent_count == target_count - 1:
    saturation = 0.6 * rarity_factor      # ❌ Hardcoded 0.6
elif recent_count == target_count - 2:
    saturation = 0.3 * rarity_factor      # ❌ Hardcoded 0.3
else:
    saturation = 0.0
```

**Problems:**
- Fixed penalty multipliers (1.0, 0.6, 0.3) - no tuning possible
- Ignores number category (hot/medium/cold)
- No window size weighting
- No configuration flexibility
- Difficult to validate or optimize

### Version 2.0 (New - JSON-Driven)

```python
# JSON-CONFIGURED - FULLY FLEXIBLE
config = load_saturation_config('data/lotto_window_saturation_config.json')

# Category-aware penalty
penalty_multiplier = get_penalty_multiplier(distance, category, config)

# Window-weighted scoring
window_weight = get_window_weight(window_size, config)

# Dynamic calculation
scenario_penalty = rarity_factor * penalty_multiplier * window_weight
```

**Improvements:**
- ✅ All parameters defined in JSON configuration file
- ✅ Category-aware penalties (hot numbers penalized more than cold)
- ✅ Window size weighting (emphasize more predictive windows)
- ✅ Easily tunable without code changes
- ✅ Supports multiple combining methods (max/avg/sum)
- ✅ Statistical validation-ready

## New Files

### 1. `/data/lotto_window_saturation_config.json`
**Main configuration file** containing all penalty parameters

**Key Sections:**

#### Penalty Thresholds
```json
{
    "penalty_thresholds": {
        "at_or_exceeding": {
            "base_multiplier": 1.0,
            "category_adjustments": {
                "hot": 1.2,      // Hot numbers: 20% higher penalty
                "medium": 1.0,   // Medium: baseline
                "cold": 0.8      // Cold numbers: 20% lower penalty
            }
        },
        "one_away": {
            "base_multiplier": 0.6,
            "category_adjustments": {
                "hot": 1.15,
                "medium": 1.0,
                "cold": 0.85
            }
        },
        "two_away": {
            "base_multiplier": 0.3,
            "category_adjustments": {
                "hot": 1.1,
                "medium": 1.0,
                "cold": 0.9
            }
        }
    }
}
```

**Rationale:**
- **Hot numbers** (appear frequently) should be penalized MORE when approaching saturation
- **Cold numbers** (appear rarely) should be penalized LESS (natural low frequency)
- **Medium numbers** use baseline multipliers

#### Window Weights
```json
{
    "window_weights": {
        "5": 0.8,    // Short window: lower weight
        "6": 0.9,
        "10": 1.0,   // Optimal window: full weight
        "25": 0.7    // Long window: lower weight
    }
}
```

**Rationale:**
- Window size 10 is most predictive based on historical odds (24.3%)
- Shorter windows (5, 6) have less predictive power
- Longer windows (25) are too diluted

#### Advanced Settings
```json
{
    "advanced_settings": {
        "enable_dynamic_scaling": true,
        "use_category_adjustments": true,
        "apply_window_weights": true,
        "combine_multiple_scenarios": "max",  // How to combine: max, avg, sum
        "penalty_cap": 1.0,                   // Maximum penalty
        "minimum_penalty_threshold": 0.05     // Ignore penalties below this
    }
}
```

### 2. `/ml_lotto/features/window_saturation.py` (Updated)

**New Functions:**

#### `load_saturation_config(config_path)`
Loads penalty configuration from JSON file

```python
config = load_saturation_config('data/lotto_window_saturation_config.json')
```

#### `calculate_rarity_factor(odds, config)`
Calculates rarity factor using configurable scaling

```python
# Old: rarity_factor = 1.0 - odds
# New: Uses config with scaling and bounds
rarity_factor = calculate_rarity_factor(odds=0.243, config=config)
# Returns: 0.757
```

#### `get_penalty_multiplier(distance, category, config)`
Gets category-aware penalty multiplier

```python
# Hot number, one away from threshold
penalty = get_penalty_multiplier(distance=1, category='hot', config=config)
# Returns: 0.6 * 1.15 = 0.69

# Cold number, one away from threshold
penalty = get_penalty_multiplier(distance=1, category='cold', config=config)
# Returns: 0.6 * 0.85 = 0.51
```

#### `get_window_weight(window_size, config)`
Gets weight for specific window size

```python
weight = get_window_weight(window_size=10, config=config)
# Returns: 1.0 (highest weight)

weight = get_window_weight(window_size=5, config=config)
# Returns: 0.8 (lower weight)
```

#### `get_saturation_statistics(saturation_scores, hmc_data)`
NEW: Generates statistics about saturation scores

```python
stats = get_saturation_statistics(saturation_scores, hmc_data)
```

Returns:
```json
{
    "total_numbers": 47,
    "avg_saturation": 0.15,
    "max_saturation": 0.85,
    "saturated_count": 5,
    "by_category": {
        "hot": {
            "count": 15,
            "avg_saturation": 0.22,
            "saturated_count": 3
        },
        "medium": {...},
        "cold": {...}
    }
}
```

## Calculation Example

### Scenario
- **Number**: 12
- **Category**: hot
- **Window**: 10 draws
- **Target**: 4 appearances
- **Odds**: 24.3%
- **Recent count** (last_9): 3 appearances

### Old Calculation (V1.0)
```python
rarity_factor = 1.0 - 0.243 = 0.757
# Number is 1 away from threshold (3 vs target 4)
saturation = 0.6 * 0.757 = 0.454
```

### New Calculation (V2.0)
```python
rarity_factor = calculate_rarity_factor(0.243, config) = 0.757

# Category-aware multiplier (hot number)
penalty_multiplier = get_penalty_multiplier(distance=1, category='hot', config)
# = 0.6 (base) * 1.15 (hot adjustment) = 0.69

# Window weight
window_weight = get_window_weight(10, config) = 1.0

# Final penalty
saturation = 0.757 * 0.69 * 1.0 = 0.522
```

**Result**: Hot number gets 15% higher penalty (0.522 vs 0.454) reflecting higher saturation risk

## Configuration Tuning Guide

### Increasing Penalties for Hot Numbers

Edit `data/lotto_window_saturation_config.json`:

```json
{
    "penalty_thresholds": {
        "at_or_exceeding": {
            "category_adjustments": {
                "hot": 1.3    // Increase from 1.2 to 1.3 (30% higher)
            }
        }
    }
}
```

### Emphasizing Shorter Windows

```json
{
    "window_weights": {
        "5": 1.0,    // Increase from 0.8 to 1.0
        "10": 0.8    // Decrease from 1.0 to 0.8
    }
}
```

### Combining Scenarios Differently

```json
{
    "advanced_settings": {
        "combine_multiple_scenarios": "avg"  // Change from "max" to "avg"
    }
}
```

Options:
- **"max"** (default): Use highest penalty across all scenarios
- **"avg"**: Average penalties across scenarios
- **"sum"**: Sum all penalties (may exceed cap)

## Integration with Existing Code

The updated `window_saturation.py` maintains **backward compatibility**:

```python
# Existing code works unchanged
window_saturation_data = calculate_window_saturation_score(
    hmc_data,
    odds_data,
    MAX_NUMBER
)

# Optional: specify custom config
window_saturation_data = calculate_window_saturation_score(
    hmc_data,
    odds_data,
    MAX_NUMBER,
    config_path='custom_config.json'
)
```

## Testing and Validation

### Quick Test

```python
from ml_lotto.features.window_saturation import (
    calculate_window_saturation_score,
    get_saturation_statistics
)
import json

# Load data
with open('data/lotto_trigger_periods.json') as f:
    hmc_data = json.load(f)

with open('data/lotto_odds_results.json') as f:
    odds_data = json.load(f)

# Calculate scores
scores = calculate_window_saturation_score(hmc_data, odds_data)

# Get statistics
stats = get_saturation_statistics(scores, hmc_data)
print(json.dumps(stats, indent=2))
```

### Comparing V1.0 vs V2.0

Create two configs:
1. `v1_compat_config.json` - mimics old hardcoded values
2. `v2_optimized_config.json` - new optimized values

Run both and compare results.

## Migration Notes

### For Users
- No code changes required
- Feature works with default configuration
- Customize `data/lotto_window_saturation_config.json` to tune behavior

### For Developers
- Configuration is loaded once per calculation (efficient)
- Falls back to defaults if JSON file missing
- All parameters are type-safe with defaults
- Error handling for malformed JSON

## Statistical Validation

The new system supports validation through:

1. **A/B Testing**: Compare config variations
2. **Backtesting**: Measure prediction accuracy with different configs
3. **Category Analysis**: Validate category adjustments match historical data
4. **Window Analysis**: Validate window weights match predictive power

## Summary of Improvements

| Feature | V1.0 (Old) | V2.0 (New) |
|---------|-----------|-----------|
| Penalty values | Hardcoded | JSON configured |
| Category awareness | No | Yes (hot/medium/cold) |
| Window weighting | No | Yes (configurable) |
| Tuning | Code changes | JSON edits |
| Flexibility | Fixed | Highly flexible |
| Validation | Difficult | Easy to test |
| Statistics | None | Built-in stats function |
| Documentation | Minimal | Comprehensive |

## Files Modified/Created

### Created
1. ✅ `data/lotto_window_saturation_config.json` - Configuration file
2. ✅ `docs/WINDOW_SATURATION_IMPROVEMENTS.md` - This documentation

### Modified
1. ✅ `ml_lotto/features/window_saturation.py` - Complete rewrite with JSON support
2. ✅ `ml_lotto/config.py` - Added WINDOW_SATURATION_CONFIG_JSON constant

### No Changes Required
- `ml_lotto/features/extractor.py` - Uses same function signature (backward compatible)
- All model configs - No changes needed
- Training scripts - No changes needed

## Future Enhancements

Possible future improvements:

1. **Auto-tuning**: Script to optimize config values based on backtest results
2. **Machine learning**: Learn optimal penalties from historical data
3. **Dynamic thresholds**: Adjust penalties based on recent draw patterns
4. **Multi-tier categories**: More granular than hot/medium/cold
5. **Time-based adjustments**: Different penalties by time of year/season

## Support

For questions or issues:
- Check this documentation
- Review example config: `data/lotto_window_saturation_config.json`
- See function docstrings in `ml_lotto/features/window_saturation.py`
