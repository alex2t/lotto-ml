# Pairwise & Triple Interaction Features Implementation

## Overview

This document describes the implementation of pairwise and triple interaction features for Model 1, as outlined in `FEATURE_INTERACTION_IMPLEMENTATION_GUIDE.md`.

**Implementation Date**: 2025-11-17
**Version**: 3.16
**Status**: ✅ Complete

---

## Key Objectives Achieved

✅ **Dynamic Data Loading** - No hard-coded values; all interaction data loaded from JSON files
✅ **Generated Every Draw** - Interaction files regenerated automatically when `drawpick.py` runs
✅ **Model 1 Only** - Only Model 1 uses interaction features; Models 2 & 3 unchanged
✅ **Maintains Parameters** - Model 1 still uses `hot_count`, `medium_count`, `cold_count`, `generic_count`
✅ **Full Output** - Model 1 still outputs 6 main numbers + 1 bonus number

---

## What Was Implemented

### 1. Dynamic Interaction Analysis (Phase 15 in `drawpick.py`)

**File Modified**: `drawpick.py` (lines 581-605)
**File Created**: `lotto_analysis/analyzers/feature_interaction_analyzer.py`

Added Phase 15 that runs the feature interaction analyzer:
- Analyzes pairwise feature interactions
- Detects threshold effects
- Identifies triple interactions (category × freshness × recency)
- Generates composite feature recommendations
- Saves to `data/analysis/` directory

**Architecture**:
- Follows proper separation of concerns
- `analysis/` folder: For exploratory testing and discovering patterns
- `lotto_analysis/analyzers/`: For production data generation (NEW analyzer added here)
- `ml_lotto/`: For ML models

**Output Files**:
- `data/analysis/lotto_feature_interactions.json` - Full analysis with all interactions
- `data/analysis/lotto_interaction_summary.csv` - Top 50 interactions (Excel-ready)
- `data/analysis/lotto_composite_features.json` - Recommended composite features for ML

**Key Point**: These files are regenerated **every time** you run `drawpick.py`, ensuring no stale data.

---

### 2. Interaction Feature Calculator Module

**File Created**: `ml_lotto/features/interactions.py`

New module that:
- Loads interaction data from JSON files dynamically
- Calculates binary pairwise interaction features (1 if both features ≥ median, 0 otherwise)
- Calculates triple interaction features (1 if combination matches high-lift pattern, 0 otherwise)
- **No hard-coded medians or thresholds** - everything loaded from JSON
- Gracefully handles missing files with safe defaults

**Key Classes**:
- `InteractionFeatureCalculator` - Main calculator class
- `calculate_all_interaction_features()` - Convenience function
- `get_interaction_feature_names()` - Get list of feature names

**Example Usage**:
```python
from ml_lotto.features.interactions import calculate_all_interaction_features

# Calculate interactions for a number
interactions = calculate_all_interaction_features(
    features_dict[num],
    include_triples=True  # Include both pairwise and triple
)
# Returns dict like: {'total_count_x_recent_4_interaction': 1, ...}
```

---

### 3. Integration into Feature Extractor

**File Modified**: `ml_lotto/features/extractor.py`

**Changes**:
1. **Import** (line 28): Added `from ml_lotto.features.interactions import ...`
2. **Feature Calculation** (lines 351-362): Added interaction feature calculation for each number
3. **Feature Keywords** (lines 412-438): Added three new keywords:
   - `PAIRWISE_INTERACTIONS` - Top 10 pairwise synergistic interactions
   - `TRIPLE_INTERACTIONS` - Top 3 triple interactions with highest lift
   - `ALL_INTERACTIONS` - All interaction features combined

**Version Updated**: 3.16 (Pairwise & Triple Interaction Features - Dynamic JSON Loading)

**How It Works**:
```python
# After all base features are extracted for a number
features[num] = {
    'total_count': ...,
    'recent_4': ...,
    # ... all other features
}

# NEW: Calculate and add interaction features
interaction_features = calculate_all_interaction_features(
    features[num],
    include_triples=True
)
features[num].update(interaction_features)
```

---

### 4. Model 1 Configuration Update

**File Modified**: `ml_lotto/config.py`

**Changes**:
1. **Version Updated**: 3.16 (Pairwise & Triple Interaction Features for Model 1)
2. **Description Updated**: Added "pairwise interactions" to Model 1 description
3. **Features Added**: Added `'PAIRWISE_INTERACTIONS'` to Model 1 feature list

**Model 1 Configuration**:
```python
MODEL_1_CONFIG = {
    'name': 'Short-Term Momentum + Pre-Assignment Specialist',
    'description': 'Captures immediate patterns with bonus and recent-bonus pre-assignment + pairwise interactions',

    # Parameters (unchanged)
    'hot_count': 1,
    'medium_count': 2,
    'cold_count': 1,
    'generic_count': 0,

    'features': [
        # ... existing features ...
        'PAIRWISE_INTERACTIONS',  # NEW: Synergistic feature interactions
    ]
}
```

**Models 2 & 3**: Unchanged (as requested)

---

## Interaction Features Discovered

Based on the analysis in `data/analysis/lotto_feature_interactions.json`:

### Top Pairwise Interactions

All interactions are **synergistic** (strength = 3.0, win rate = 0.857 when both high):

| Feature 1 | Feature 2 | Median 1 | Median 2 | Win Rate (Both High) |
|-----------|-----------|----------|----------|----------------------|
| total_count | recent_4 | 0 | 0 | 0.8571 |
| total_count | recent_14 | 0 | 0 | 0.8571 |
| total_count | freshness_bin | 0 | 0 | 0.8571 |
| total_count | bonus_hit_contribution | 0 | 0 | 0.8571 |
| recent_4 | recent_14 | 0 | 0 | 0.8571 |
| recent_4 | freshness_bin | 0 | 0 | 0.8571 |
| recent_4 | bonus_hit_contribution | 0 | 0 | 0.8571 |
| recent_14 | freshness_bin | 0 | 0 | 0.8571 |
| recent_14 | bonus_hit_contribution | 0 | 0 | 0.8571 |
| freshness_bin | bonus_hit_contribution | 0 | 0 | 0.8571 |

### Feature Names Generated

Pairwise features (10):
- `total_count_x_recent_4_interaction`
- `total_count_x_recent_14_interaction`
- `total_count_x_freshness_bin_interaction`
- `total_count_x_bonus_hit_contribution_interaction`
- `recent_4_x_recent_14_interaction`
- `recent_4_x_freshness_bin_interaction`
- `recent_4_x_bonus_hit_contribution_interaction`
- `recent_14_x_freshness_bin_interaction`
- `recent_14_x_bonus_hit_contribution_interaction`
- `freshness_bin_x_bonus_hit_contribution_interaction`

Triple features (3):
- `triple_medium_1_recent` (lift: 1.041x, win rate: 0.8925)
- `triple_hot_2_very_recent` (lift: 1.033x, win rate: 0.8853)
- `triple_hot_0_recent` (lift: 1.016x, win rate: 0.8710)

---

## How to Use

### Step 1: Regenerate Data Files

```bash
python drawpick.py
```

This will:
- Run all 15 analysis phases
- Generate interaction files in `data/analysis/`
- Validate all files are created

**Expected Output**:
```
======================================================================
Phase 15: Feature Interaction Analysis (Pairwise + Triple)
======================================================================
Discovering non-linear feature interactions for ML prediction...
This generates interaction features for Model 1 enhancement

  Loading draw history for interaction analysis...
  ✓ Loaded 412 draws
  Building feature matrix...
  ✓ Built matrix with 19364 records
  Analyzing pairwise interactions...
  ✓ Analyzed 21 feature pairs
  ...
  ✓ Interaction analysis complete
```

### Step 2: Run Predictions

```bash
python quickpick.py
```

Model 1 will now use the interaction features automatically.

**What Happens**:
1. `quickpick.py` loads features (including interactions)
2. Model 1's `PAIRWISE_INTERACTIONS` keyword expands to the 10 interaction features
3. Model 1 trains with base features + interaction features
4. Model 1 generates 6 main numbers + 1 bonus number (as before)

### Step 3: Verify

Check that Model 1 is using interaction features:

```bash
grep -A 5 "Model 1.*features" lottery_picks.txt
```

You should see interaction features in the feature count.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        drawpick.py                          │
│  Phase 15: Feature Interaction Analysis                    │
│                                                             │
│  1. Load draw history                                      │
│  2. Build feature matrix                                   │
│  3. Analyze pairwise interactions                          │
│  4. Analyze triple interactions                            │
│  5. Save to data/analysis/*.json                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              data/analysis/lotto_feature_interactions.json  │
│                                                             │
│  {                                                          │
│    "pairwise_interactions": [                              │
│      {                                                      │
│        "feature_1": "total_count",                         │
│        "feature_2": "recent_4",                            │
│        "median_1": 0,                                      │
│        "median_2": 0,                                      │
│        "win_rate_high_high": 0.8571,                       │
│        "interaction_strength": 3.0                         │
│      },                                                     │
│      ...                                                    │
│    ],                                                       │
│    "triple_interactions": [...]                            │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│         ml_lotto/features/interactions.py                   │
│                                                             │
│  class InteractionFeatureCalculator:                       │
│    def __init__(self, json_path):                          │
│      # Load medians and thresholds from JSON              │
│      self.pairwise_interactions = load_json(...)           │
│      self.feature_medians = extract_medians(...)           │
│                                                             │
│    def calculate_pairwise_interactions(self, features):    │
│      # For each interaction pair:                          │
│      #   if val1 >= median1 and val2 >= median2:          │
│      #     interaction = 1                                 │
│      #   else:                                             │
│      #     interaction = 0                                 │
│      return interaction_dict                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│           ml_lotto/features/extractor.py                    │
│                                                             │
│  for num in range(1, 48):                                  │
│    features[num] = {                                        │
│      'total_count': ...,                                   │
│      'recent_4': ...,                                      │
│      ...                                                    │
│    }                                                        │
│                                                             │
│    # NEW: Add interaction features                         │
│    interactions = calculate_all_interaction_features(      │
│      features[num],                                        │
│      include_triples=True                                  │
│    )                                                        │
│    features[num].update(interactions)                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│               ml_lotto/config.py                            │
│                                                             │
│  MODEL_1_CONFIG = {                                         │
│    'features': [                                            │
│      'total_count',                                        │
│      'recent_4',                                           │
│      ...                                                    │
│      'PAIRWISE_INTERACTIONS',  ← Expands to 10 features   │
│    ]                                                        │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     quickpick.py                            │
│                                                             │
│  Model 1 trains with:                                      │
│    - Base features (total_count, recent_4, ...)           │
│    - 10 pairwise interaction features                      │
│    - 3 triple interaction features (optional)              │
│                                                             │
│  Outputs: 6 main numbers + 1 bonus number                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow

1. **Data Generation** (`drawpick.py`)
   - Analyzes 412 historical draws
   - Calculates medians for each feature pair
   - Identifies synergistic interactions
   - Saves to `data/analysis/lotto_feature_interactions.json`

2. **Feature Extraction** (`quickpick.py` → `extractor.py`)
   - Loads interaction data from JSON
   - For each number (1-47):
     - Extracts base features
     - Calculates interaction features
     - Adds to feature dictionary

3. **Model Training** (`MODEL_1_CONFIG`)
   - Expands `PAIRWISE_INTERACTIONS` keyword to 10 feature names
   - Trains logistic regression with base + interaction features
   - Outputs predictions for 6 main + 1 bonus

---

## Expected Impact

Based on the implementation guide:

| Model Type | Expected Improvement | Confidence |
|------------|---------------------|------------|
| Logistic Regression (Model 1) | +2-5% accuracy | High |

**Why**: Linear models benefit most because they cannot discover interactions automatically. The explicit interaction features help the model capture non-linear relationships.

---

## Testing

### Manual Verification

1. **Check interaction files exist**:
   ```bash
   ls -lh data/analysis/lotto_feature_interactions.json
   ls -lh data/analysis/lotto_interaction_summary.csv
   ls -lh data/analysis/lotto_composite_features.json
   ```

2. **Verify feature count**:
   ```python
   from ml_lotto.features.interactions import get_interaction_feature_names

   pairwise = get_interaction_feature_names(include_triples=False)
   all_features = get_interaction_feature_names(include_triples=True)

   print(f"Pairwise: {len(pairwise)} features")  # Should be 10
   print(f"All: {len(all_features)} features")    # Should be 13
   ```

3. **Run test script**:
   ```bash
   python test_interactions.py
   ```

### Automated Test

A test script `test_interactions.py` has been created that validates:
- ✓ Interactions module imports correctly
- ✓ Calculator loads data from JSON dynamically
- ✓ Feature names are extracted correctly
- ✓ Interaction features calculate correctly
- ✓ Extractor keywords work as expected
- ✓ MODEL_1_CONFIG is properly configured

---

## Troubleshooting

### Issue: Interaction files not found

**Solution**: Run `python drawpick.py` to generate the files.

### Issue: Interaction features not appearing

**Solution**:
1. Check that `drawpick.py` completed Phase 15 successfully
2. Verify JSON files exist in `data/analysis/`
3. Check `quickpick.py` output for feature count

### Issue: Model 1 performance unchanged

**Possible Causes**:
- Interaction data hasn't changed (expected if draw history is same)
- Need more draws to see effect
- Interactions are working but effect is subtle

**Solution**: Compare feature importance before/after to see if interaction features rank high.

---

## Files Modified/Created

### Modified Files
1. `drawpick.py` - Added Phase 15 for interaction analysis (fixed Path import, proper analyzer integration)
2. `ml_lotto/features/extractor.py` - Added interaction feature calculation
3. `ml_lotto/config.py` - Added PAIRWISE_INTERACTIONS to Model 1

### Created Files
1. `lotto_analysis/analyzers/feature_interaction_analyzer.py` - **NEW production analyzer** (follows proper architecture)
2. `ml_lotto/features/interactions.py` - Interaction calculator module (loads from JSON)
3. `test_interactions.py` - Test script for validation
4. `docs/INTERACTION_FEATURES_IMPLEMENTATION.md` - This document

### Generated Files (by `drawpick.py`)
1. `data/analysis/lotto_feature_interactions.json` - Full interaction analysis
2. `data/analysis/lotto_interaction_summary.csv` - Top 50 interactions
3. `data/analysis/lotto_composite_features.json` - Composite feature recommendations

### Architecture Note
- **Proper Separation of Concerns**:
  - `analysis/` folder: Exploratory testing only
  - `lotto_analysis/analyzers/`: Production data generation ← **NEW analyzer here**
  - `ml_lotto/`: ML models and feature loading

---

## Version History

- **v3.16** (2025-11-17): Initial implementation of pairwise & triple interaction features
  - Dynamic JSON loading (no hard-coded data)
  - Integrated into Model 1 only
  - Maintains all Model 1 parameters and outputs

---

## Notes

1. **No Hard-Coded Data**: All medians and thresholds are loaded from JSON files generated by `drawpick.py`
2. **Dynamic Updates**: Interaction data is regenerated every time you run `drawpick.py`
3. **Model 1 Only**: Only Model 1 uses interaction features; Models 2 & 3 are unchanged
4. **Graceful Degradation**: If interaction files are missing, features are safely skipped
5. **Backward Compatible**: System works with or without interaction features

---

## References

- **Analysis Script**: `analysis/feature_interaction_explorer.py`
- **Implementation Guide**: `docs/FEATURE_INTERACTION_IMPLEMENTATION_GUIDE.md`
- **Interaction Data**: `data/analysis/lotto_feature_interactions.json`
- **Model Config**: `ml_lotto/config.py` → `MODEL_1_CONFIG`

---

**Implementation Complete** ✅

All objectives have been achieved. The system now generates interaction features dynamically without any hard-coded data, and Model 1 uses these features to capture synergistic relationships between features.
