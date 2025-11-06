# Understanding Feature Data Sources

## 🎯 Overview

Your lottery prediction system uses **18 total features** that come from different data sources. This document explains which features need "specialized JSON files" and which don't.

---

## 📄 Main JSON Data Files

Your system uses **5 main JSON data files**:

1. **lotto_trigger_periods.json** (HMC data) - MOST COMMON
2. **lotto_draw_history.json** (draw history)
3. **lotto_odds_results.json** (odds/patterns)
4. **lotto_distribution_stats.json** (distribution analysis)
5. **lotto_7_number_freshness_results.json** (freshness patterns)

---

## 📊 Complete Feature Breakdown

### ✅ Features Using NO Special JSON (9 features)

These calculate from basic HMC data or pure logic:

#### Pure Calculation (1 feature)
- **`recency_zone_score`** - Just uses if/else logic on days_since_last

#### HMC JSON Only (8 features)
- **`total_count`** - Direct from HMC JSON
- **`days_since_last`** - Calculated from 'last_seen' in HMC JSON
- **`recent_4`, `recent_6`, `recent_9`, `recent_14`** - Direct from HMC JSON
- **`series_total`** - Aggregated from HMC JSON 'series' section
- **`series_recent`** - Aggregated from HMC JSON 'series' section
- **`category`** (hot/medium/cold) - Direct from HMC JSON
- **`has_consecutive_partner`** - Calculated from `recent_4` in HMC JSON

---

### ⚠️ Features Requiring SPECIALIZED JSON Files (9 features)

#### From lotto_draw_history.json (4 features)
- **`days_since_bonus`** - Needs bonus ball dates
- **`was_recent_bonus`** - Needs recent bonus numbers
- **`bonus_hit_target_alignment`** - Needs bonus data
- **`win_bias_ratio`** - Needs full history log with bias ratios

#### From lotto_odds_results.json (2 features)
- **`consecutive_pair_affinity`** - Needs 'all_pairs' data
- **`range_spread_affinity`** - Needs 'draw_range' distribution

#### From lotto_distribution_stats.json (2 features)
- **`odd_even_affinity`** - Needs odd/even pattern analysis
- **`sum_contribution_score`** - Needs sum distribution data

#### From lotto_7_number_freshness_results.json (1 feature group)
- **`freshness_c0_weight`, `freshness_c1_weight`, `freshness_c2_weight`, `freshness_c3_weight`**
- **`current_freshness_bin`**

---

## 🔍 What "Specialized" Means

**"Specialized JSON files"** = JSON files that contain **pre-calculated analysis results**, not just raw draw data.

### Example Comparison:

#### HMC JSON (lotto_trigger_periods.json)
```json
{
  "1": {
    "total_count": 85,
    "last_seen": "2025-11-01",
    "recent": {
      "last_4": 2,
      "last_6": 3
    },
    "category": "hot"
  }
}
```
☝️ This is **basic stats** - easy to extract directly

#### Distribution Stats JSON (lotto_distribution_stats.json)
```json
{
  "analysis_6_main_numbers": {
    "odd_even_patterns": {
      "2_4": {"count": 125, "percentage": 25.5},
      "3_3": {"count": 180, "percentage": 36.7}
    },
    "sum_distributions": {
      "S6_LOW (110-124)": {"count": 45}
    }
  }
}
```
☝️ This is **pre-calculated analysis** - needs special processing by drawpick.py

---

## 💡 Why This Matters

If you wanted to **remove a dependency on a specialized JSON file**, you could:

1. **Remove features that use it** from your model configs
2. **Or keep the features with default values** (like 0.5)

### Example: Remove Priority 3 Features

If you don't have `lotto_distribution_stats.json`, you can:

#### Option 1: Remove from model configs
```python
MODEL_1_CONFIG = {
    'features': [
        'days_since_last',
        'total_count',
        # DON'T include: 'odd_even_affinity', 'sum_contribution_score'
    ]
}
```

#### Option 2: System handles it automatically
The code already has fallback logic:
```python
if distribution_stats:
    odd_even_affinity_data = calculate_odd_even_affinity(distribution_stats)
else:
    print("WARNING: Using default values")
    odd_even_affinity_data = {num: 0.5 for num in range(1, 47+1)}
```

---

## 📋 Complete Feature Summary Table

| Feature | Data Source | Type | Can Remove? | Priority |
|---------|-------------|------|-------------|----------|
| `total_count` | HMC JSON | Direct | ❌ Core | 1 |
| `days_since_last` | HMC JSON | Calculated | ❌ Core | 1 |
| `recent_4/6/9/14` | HMC JSON | Direct | ✅ Yes | 1 |
| `series_total` | HMC JSON | Aggregated | ✅ Yes | 1 |
| `series_recent` | HMC JSON | Aggregated | ✅ Yes | 1 |
| `category` | HMC JSON | Direct | ❌ Core | 1 |
| `has_consecutive_partner` | HMC JSON | Calculated | ✅ Yes | 2 |
| `recency_zone_score` | Pure calculation | Calculated | ✅ Yes | 1 |
| | | | | |
| `days_since_bonus` | draw_history.json | Calculated | ✅ Yes | 2 |
| `was_recent_bonus` | draw_history.json | Calculated | ✅ Yes | 2 |
| `bonus_hit_target_alignment` | draw_history.json | Calculated | ✅ Yes | 2 |
| `win_bias_ratio` | draw_history.json | Extracted | ✅ Yes | 2 |
| | | | | |
| `consecutive_pair_affinity` | odds_results.json | Calculated | ✅ Yes | 2 |
| `range_spread_affinity` | odds_results.json | Calculated | ✅ Yes | 3 |
| | | | | |
| `odd_even_affinity` | distribution_stats.json | Calculated | ✅ Yes | 3 |
| `sum_contribution_score` | distribution_stats.json | Calculated | ✅ Yes | 3 |
| | | | | |
| `freshness_c0/c1/c2/c3_weight` | freshness.json + HMC | Calculated | ⚠️ Important | 1 |
| `current_freshness_bin` | freshness.json + HMC | Calculated | ⚠️ Important | 1 |

---

## 🎯 Feature Categories by Independence

### Category 1: Fully Independent (No external files needed)
```
✓ recency_zone_score
```

### Category 2: HMC JSON Only
```
✓ total_count
✓ days_since_last
✓ recent_4, recent_6, recent_9, recent_14
✓ series_total
✓ series_recent
✓ category
✓ has_consecutive_partner
```

### Category 3: Requires Draw History JSON
```
⚠ days_since_bonus
⚠ was_recent_bonus
⚠ bonus_hit_target_alignment
⚠ win_bias_ratio
```

### Category 4: Requires Odds Results JSON
```
⚠ consecutive_pair_affinity
⚠ range_spread_affinity
```

### Category 5: Requires Distribution Stats JSON
```
⚠ odd_even_affinity
⚠ sum_contribution_score
```

### Category 6: Requires Multiple Files
```
⚠ freshness_c0/c1/c2/c3_weight (HMC + freshness JSON)
⚠ current_freshness_bin (HMC + freshness JSON)
```

---

## 🔧 How to Check Which Files You Need

Based on your model configuration, here's what you need:

### Minimum Requirements (Always needed)
- ✅ `lotto_trigger_periods.json` (HMC data)

### If Using Priority 2 Features
- ✅ `lotto_draw_history.json` (for bonus features)
- ✅ `lotto_odds_results.json` (for consecutive pairs)

### If Using Priority 3 Features
- ✅ `lotto_distribution_stats.json` (for realism features)

### If Using Freshness Features
- ✅ `lotto_7_number_freshness_results.json` (for pattern weights)

---

## 📝 Example: Checking Your Model
```python
MODEL_1_CONFIG = {
    'features': [
        'FRESHNESS_PATTERN_WEIGHTS',    # ← Needs freshness.json + HMC
        'days_since_last',                # ← Needs HMC only
        'recency_zone_score',            # ← No JSON needed
        'total_count',                    # ← Needs HMC only
        'was_recent_bonus',              # ← Needs draw_history.json
        'has_consecutive_partner',        # ← Needs HMC only
        'odd_even_affinity'               # ← Needs distribution_stats.json
    ]
}
```

**Files Required:**
1. ✅ lotto_trigger_periods.json (HMC)
2. ✅ lotto_draw_history.json (bonus features)
3. ✅ lotto_7_number_freshness_results.json (freshness)
4. ✅ lotto_distribution_stats.json (odd/even)

---

## ✅ Bottom Line

**"All others require specialized JSON files"** means:

- **9 features** work with just basic HMC data or pure calculation
- **9 features** need additional pre-calculated analysis files
- If you're missing a specialized JSON file, those features will use default values (0.5) or can be removed from models
- All specialized JSON files are generated by running `python drawpick.py`

---

## 🚀 Quick Reference

### Want to use ONLY basic features?
Use these features (no specialized JSON needed):
```python
features = [
    'total_count',
    'days_since_last', 
    'recent_4',
    'recent_14',
    'recency_zone_score',
    'series_total',
    'category'
]
```

### Want the full feature set?
Ensure all 5 JSON files exist:
```bash
python drawpick.py  # Generates all JSON files
```

Then use any features you want!

---

## 📞 Need Help?

If a feature is missing data, the system will show:
```
⚠️  WARNING: distribution_stats not provided. Using default values.
```

This means the feature will work but with neutral scores (0.5) instead of data-driven scores.