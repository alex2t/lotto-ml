# Analysis Scripts Reference

This document explains each script in the `analysis/` folder, their purpose, usage, and dependencies.

---

## Table of Contents

1. [Overview](#overview)
2. [Scripts Reference](#scripts-reference)
   - [ensemble.py](#ensemblepy)
   - [validate_bonus.py](#validate_bonuspy)
   - [trend_analyzer.py](#trend_analyzerpy)
   - [generate_bonus_to_main_json.py](#generate_bonus_to_main_jsonpy)
   - [bonus_to_main_analysis.py](#bonus_to_main_analysispy)
   - [bonus_analysis.py](#bonus_analysispy)
   - [correlation_matrix_analyzer.py](#correlation_matrix_analyzerpy)
3. [Running Scripts from Different Locations](#running-scripts-from-different-locations)
4. [Dependencies](#dependencies)

---

## Overview

The `analysis/` folder contains scripts used for testing, pattern discovery, and data generation. These scripts were originally located in the project root but have been moved to the `analysis/` folder for better organization. All scripts have been updated to work correctly from their new location.

### Script Categories:

- **Testing & Validation**: Scripts that validate ML features and patterns
- **Pattern Discovery**: Scripts that analyze historical data to find trends
- **Data Generation**: Scripts that generate JSON files used by the ML models

---

## Scripts Reference

### ensemble.py

**Category**: Testing & Validation

**Purpose**: Implements an ensemble voting system that runs the main lottery prediction (`quickpick.py`) multiple times with different random seeds and aggregates the results to identify numbers that are consistently predicted.

**Key Features**:
- Runs `quickpick.py` multiple times (default: 15 runs)
- Changes the random seed for each run
- Aggregates results using frequency analysis
- Identifies high-confidence predictions (numbers appearing in 80%+ of runs)
- Provides confidence ratings (★★★ Very High, ★★☆ High, ★☆☆ Medium, ☆☆☆ Low)

**Usage**:
```bash
# Must be run from project root
python analysis/ensemble.py --runs 15
```

**Output**:
- Console display showing:
  - Frequency of each number across all runs
  - Recommended line (top 6 numbers)
  - Confidence breakdown for each number
  - Bonus ball recommendation

**Technical Details**:
- Temporarily modifies `ml_lotto/config.py` to change random seeds
- Restores original config after completion
- Parses results from `lottery_picks.txt`
- Each run has a 120-second timeout

**Example Output**:
```
ENSEMBLE VOTING RESULTS
Model 1: Short-Term Momentum (15 runs)
----------------------------------------------------------------------

Rank    Number   Frequency    Confidence
----------------------------------------------------------------------
1       #12      93.3%       ★★★ Very High
2       #23      86.7%       ★★★ Very High
3       #35      73.3%       ★★☆ High
...
```

**Dependencies**:
- Requires `quickpick.py` in project root
- Requires `ml_lotto/config.py` to be writable
- Generates/reads `lottery_picks.txt`

---

### validate_bonus.py

**Category**: Testing & Validation

**Purpose**: Validates that the `was_recent_bonus` feature is working correctly by checking if recent bonus numbers are being favored in predictions.

**Key Features**:
- Shows which numbers have `was_recent_bonus = 1`
- Displays prediction probabilities for bonus vs non-bonus numbers
- Compares actual patterns with expected patterns
- Historical validation using bonus-to-winner transition analysis

**Usage**:
```bash
# Can be run from project root or analysis folder
python analysis/validate_bonus.py
```

**Prerequisites**:
- Must run `quickpick.py` at least once to generate `lottery_picks.txt`
- Requires `data/lotto_draw_history.json`

**Output**:
- Console display showing:
  1. Recent bonus numbers (last 10 draws)
  2. Bonus ball history
  3. Analysis of latest predictions
  4. Historical validation (bonus → winner pattern)

**Validation Metrics**:
- Expected lift: ~3.42x over random
- Historical win rate vs baseline rate
- Percentage of picks that are recent bonus numbers

**Example Output**:
```
BONUS FEATURE VALIDATION
================================================================================

1. FEATURE STATUS
   Recent bonus numbers (last 10 draws): [3, 7, 12, 19, 23, 31, 35, 42, 44, 47]
   Count: 10/47

2. BONUS BALL HISTORY (Last 10 Draws)
   Draw 1 (2024-11-10): Bonus = 12
   ...

3. CHECKING LATEST PREDICTIONS (lottery_picks.txt)
   Line 1: [3, 12, 23, 31, 35, 42]
   → Contains 5 recent bonus numbers: [3, 12, 23, 31, 35]
   → Bonus representation: 5/6 = 83.3%

   OVERALL STATISTICS:
   - % of picks that are recent bonus: 82.5%
   - Expected if random: 21.3%
   - Expected with 3.42x lift: ~72.8%
   ✓ FEATURE IS WORKING! Models favor recent bonus numbers.
```

**Dependencies**:
- `ml_lotto.data.loader`
- `ml_lotto.features.bonus`
- `ml_lotto.config`

---

### trend_analyzer.py

**Category**: Pattern Discovery

**Purpose**: Detects long-term trends and regime shifts in lottery data to identify potential new ML features. This is a comprehensive analysis tool for discovering statistical patterns.

**Key Features**:
- HMC (Hot/Medium/Cold) category imbalance analysis over time
- Total count performance by frequency range
- Days-since-last optimal window detection
- Freshness pattern evolution tracking
- Bonus ball predictive power analysis
- Regime shift detection (identifies 10%+ changes)
- Automatic feature recommendation generation

**Usage**:
```bash
# Best run from analysis folder
cd analysis
python trend_analyzer.py
```

**Analysis Windows**:
- 50, 100, 150, 200 draw lookback windows
- Multiple time bins for recency (0-14, 14-30, 30-60, 60-120, 120+ days)
- Freshness bins (C0, C1, C2, C3+)

**Output Files**:
- `trend_analysis_hmc_imbalance_<window>draws.csv` (for each window)
- `feature_recommendations.csv` (recommended ML features)

**Console Output**:
```
LOTTERY TREND DISCOVERY ANALYZER
================================================================================
Loading draw history...
✓ Loaded 600 draws

✓ Historical HMC Baseline (from 600 draws):
  Hot:    2.15 avg
  Medium: 2.95 avg
  Cold:   1.90 avg

RUNNING TREND ANALYSES
================================================================================

1. HMC Category Imbalance Over Time
Window: Last 100 draws (as of 2024-11-16)
  Hot:    2.32 avg (+7.9% vs expected 2.15)
  Medium: 2.88 avg (-2.4% vs expected 2.95)
  Cold:   1.80 avg (-5.3% vs expected 1.90)

...

FEATURE RECOMMENDATIONS
================================================================================

1. was_recent_bonus [High Impact]
   Type: bonus_indicator
   Description: Binary indicator if number was bonus in last 10 draws
   Current Signal: Lift: 3.42x over baseline
   Implementation: For each number: 1 if appeared as bonus in last 10 draws, 0 otherwise
```

**Dependencies**:
- Uses hardcoded path: `../data/lotto_draw_history.json`
- Requires `pandas`, `numpy`, `matplotlib`

---

### generate_bonus_to_main_json.py

**Category**: Data Generation

**Purpose**: Generates `lotto_bonus_to_main_patterns.json` with comprehensive bonus-to-main transition features for ML models.

**Key Features**:
- Per-number transition profiles
- Category transition weights (hot/medium/cold)
- Freshness transition weights
- Timing decay weights for 10-draw window
- Current bonus window tracking
- Composite transition scores

**Usage**:
```bash
# Can be run from project root or analysis folder
python analysis/generate_bonus_to_main_json.py
```

**Generated Data Structure**:
```json
{
  "metadata": {
    "total_bonus_appearances": 585,
    "overall_transition_rate": 0.7436,
    "numbers_with_transitions": 47
  },
  "per_number_transition_profile": {
    "1": {
      "total_bonus_appearances": 12,
      "transitioned_to_main": 9,
      "transition_rate": 0.75,
      "avg_draws_to_transition": 3.2,
      "most_common_category": "medium",
      "most_common_freshness": 1
    },
    ...
  },
  "category_transition_weights": {
    "hot": {"rate": 0.7821, "weight": 1.05},
    "medium": {"rate": 0.7456, "weight": 1.00},
    "cold": {"rate": 0.6923, "weight": 0.93}
  },
  "timing_decay_weights": {
    "draw_1": 0.185,
    "draw_2": 0.172,
    "draw_3": 0.145,
    ...
  }
}
```

**Output File**:
- `data/lotto_bonus_to_main_patterns.json`

**Console Output**:
```
======================================================================
GENERATING BONUS-TO-MAIN PATTERNS JSON
======================================================================

Loaded 600 draws

1. Calculating per-number transition profiles...
   ✓ Generated profiles for 47 numbers

2. Calculating category transition weights...
   ✓ Generated weights for 3 categories

3. Calculating freshness transition weights...
   ✓ Generated weights for 3 freshness bins

4. Calculating timing decay weights...
   ✓ Generated weights for 10 draw positions

5. Getting current bonus window...
   ✓ Tracked last 10 bonus numbers

======================================================================
GENERATION COMPLETE
======================================================================
Output saved to: data/lotto_bonus_to_main_patterns.json

Summary:
  - Total bonus appearances: 585
  - Overall transition rate: 74.36%
  - Numbers with transitions: 47
  - Boost over random: 3.49x
```

**Dependencies**:
- Requires `data/lotto_draw_history.json`

---

### bonus_to_main_analysis.py

**Category**: Pattern Discovery & Validation

**Purpose**: Analyzes the pattern where bonus numbers from recent draws appear as main numbers in future draws. Validates the ~80% transition rate claim.

**Key Features**:
- Validates transition rate (bonus → main within 10 draws)
- Timing distribution analysis (which draw in the 10-draw window)
- Category preference analysis (hot/medium/cold)
- Freshness pattern analysis
- Feature correlation analysis (identifies predictive features)
- Generates ML feature recommendations

**Usage**:
```bash
# Can be run from project root or analysis folder
python analysis/bonus_to_main_analysis.py
```

**Analysis Components**:

1. **Overall Statistics**: Validates the ~80% transition pattern
2. **Timing Distribution**: Shows when transitions typically occur
3. **Category Analysis**: Which categories are more likely to transition
4. **Freshness Analysis**: Relationship between freshness bins and transitions
5. **Feature Correlation**: Compares features for transitioned vs non-transitioned numbers

**Output File**:
- `data/bonus_to_main_analysis.json`

**Console Output**:
```
======================================================================
BONUS-TO-MAIN NUMBER ANALYSIS
======================================================================
Analyzing pattern: Bonus numbers appearing as main within 10 draws

Loaded 600 draws

======================================================================
OVERALL STATISTICS
======================================================================
Total bonus numbers analyzed:  590
Appeared as main within 10:    474
Transition rate:               80.34%

✓ VALIDATION: 80% ≈ 80% claimed rate

======================================================================
TIMING DISTRIBUTION (Which draw in 10-draw window)
======================================================================

Draw  1:   88 (18.6%) ██████████
Draw  2:   81 (17.1%) █████████
Draw  3:   68 (14.4%) ███████
Draw  4:   61 (12.9%) ██████
Draw  5:   52 (11.0%) █████
  → Cumulative (1-5): 73.9%
Draw  6:   44 ( 9.3%) ████
...

======================================================================
CATEGORY PREFERENCE ANALYSIS
======================================================================

HOT     :
  Total bonus appearances:  195
  Became main within 10:    158
  Transition rate:          81.03%

MEDIUM  :
  Total bonus appearances:  245
  Became main within 10:    197
  Transition rate:          80.41%

COLD    :
  Total bonus appearances:  150
  Became main within 10:    119
  Transition rate:          79.33%

======================================================================
FEATURE CORRELATION ANALYSIS
======================================================================

Average feature values:
Feature              Transitioned   No Transition    Difference
----------------------------------------------------------------------
days_since_last            23.45           27.32        -3.87
recent_4                    0.85            0.62         0.23
recent_9                    1.52            1.18         0.34
freshness_bin               0.98            1.15        -0.17

======================================================================
RECOMMENDED ML MODEL FEATURES
======================================================================

Core Features:
  - was_bonus_in_last_10
  - draws_since_bonus
  - bonus_category
  - bonus_freshness_bin

Historical Features:
  - days_since_last_main_hit
  - total_main_appearances
  - total_bonus_appearances
  - bonus_to_main_ratio

Recent Activity:
  - recent_4_count
  - recent_9_count
  - recent_14_count
  - recent_activity_trend

Pattern Features:
  - current_hmc_category
  - freshness_weight
  - win_bias_ratio
  - consecutive_partner_exists

Bonus-Specific:
  - bonus_hit_contribution
  - bonus_timing_zone_weight
  - recent_bonus_exclusion_factor
```

**Dependencies**:
- Requires `data/lotto_draw_history.json`

---

### bonus_analysis.py

**Category**: Pattern Discovery

**Purpose**: Comprehensive analysis of bonus ball patterns and statistics from historical draw data. Generates detailed statistical breakdowns by category, timing, and freshness.

**Key Features**:
- HMC distribution analysis (hot/medium/cold patterns)
- Days-since-last-hit distribution by category
- Recent counts distribution analysis
- Freshness bin distribution
- Bonus-specific pattern detection
- Main numbers that were recent bonus analysis

**Usage**:
```bash
# Can be run from project root or analysis folder
python analysis/bonus_analysis.py
```

**Analysis Categories**:

1. **HMC Pattern Distribution**
   - Top HMC patterns (e.g., "2-3-2", "1-4-2")
   - Main numbers by category percentage
   - Bonus numbers by category percentage

2. **Days Since Last Hit**
   - Distribution bins: 0-7, 8-14, 15-21, 22-30, 31-45, 46-60, 61-90, 91-120, 121+ days
   - Breakdown by category (hot/medium/cold)
   - Separate analysis for main vs bonus numbers

3. **Recent Counts**
   - Analyzes multiple windows (last_4, last_9, last_14, etc.)
   - Shows distribution of appearance counts
   - By category breakdown

4. **Freshness Patterns**
   - Freshness bin distribution (C0, C1, C2, C3+)
   - Main vs bonus comparison
   - Category-specific patterns

5. **Bonus-Specific Patterns**
   - Bonus category preference
   - Bonus numbers that were recent bonus
   - Main numbers that were recent bonus
   - Bonus hit contribution statistics

**Output File**:
- `data/lotto_statistics_analysis.json`

**Console Output**:
```
Loading draw history...
Loaded 600 draws

Detecting recent count parameters...
Found 4 recent count windows: ['last_4', 'last_9', 'last_14', 'last_25']

Analyzing HMC distribution...
Analyzing days since last hit...
Analyzing recent counts...
Analyzing freshness patterns...
Analyzing bonus-specific patterns...

================================================================================
LOTTERY DRAW HISTORY ANALYSIS
================================================================================

--------------------------------------------------------------------------------
1. HMC PATTERN DISTRIBUTION
--------------------------------------------------------------------------------

Total Draws Analyzed: 600

Top HMC Patterns:
       2-3-2 :  18.67%
       1-4-2 :  15.33%
       2-2-3 :  12.50%
       3-2-2 :  10.83%
       1-3-3 :   9.17%
       ...

Main Numbers by Category:
      Hot :  30.56%
   Medium :  42.22%
     Cold :  27.22%

Bonus Numbers by Category:
      Hot :  32.50%
   Medium :  40.83%
     Cold :  26.67%

--------------------------------------------------------------------------------
2. DAYS SINCE LAST HIT DISTRIBUTION
--------------------------------------------------------------------------------

MAIN NUMBERS:

  HOT (1100 numbers):
         0-7 days :  68.18%
        8-14 days :  22.73%
       15-21 days :   6.36%
       22-30 days :   2.27%
       31-45 days :   0.45%

  MEDIUM (1520 numbers):
         0-7 days :  15.13%
        8-14 days :  18.42%
       15-21 days :  22.37%
       22-30 days :  25.66%
       31-45 days :  13.16%
       46-60 days :   4.08%

  COLD (980 numbers):
       22-30 days :   8.16%
       31-45 days :  22.45%
       46-60 days :  28.57%
       61-90 days :  26.53%
      91-120 days :   9.18%
      121+ days   :   5.10%

...

--------------------------------------------------------------------------------
5. BONUS-SPECIFIC PATTERNS
--------------------------------------------------------------------------------

Bonus Ball Category Preference:
      Hot :  32.50%
   Medium :  40.83%
     Cold :  26.67%

Bonus Ball Was Recent Bonus:
  was_not_recent_bonus :  87.50%
      was_recent_bonus :  12.50%

Main Numbers That Were Recent Bonus:
  Count     : 256
  Total     : 3600
  Percentage: 7.11%

Bonus Hit Contribution Stats:
  Average: 0.4523
  Min    : 0.0000
  Max    : 1.0000

✓ Results saved to data/lotto_statistics_analysis.json
```

**Dependencies**:
- Requires `data/lotto_draw_history.json`
- Uses dynamic detection for recent count keys

---

### correlation_matrix_analyzer.py

**Category**: Pattern Discovery

**Purpose**: Discovers which lottery numbers frequently appear together (positive correlation) or avoid each other (negative correlation). This is a comprehensive correlation analysis tool using multiple statistical methods.

**Key Features**:
- Number co-occurrence matrix (all pairs analyzed)
- Positive correlations (numbers that "attract" each other)
- Negative correlations (numbers that "repel" each other)
- HMC category correlations (hot-hot, hot-cold, etc.)
- Temporal autocorrelations (does appearing in draw N predict N+1?)
- Multiple correlation metrics:
  - **Lift**: observed/expected ratio
  - **PMI**: Pointwise Mutual Information
  - **Phi coefficient**: correlation coefficient for binary variables
  - **Chi-square**: statistical significance testing

**Usage**:
```bash
# Can be run from project root or analysis folder
python analysis/correlation_matrix_analyzer.py
```

**Analysis Methods**:

1. **Co-occurrence Matrix**
   - Analyzes all possible number pairs (1,081 pairs from 47 numbers)
   - Counts how often each pair appears together in the same draw
   - Compares to expected random frequency

2. **Correlation Metrics**
   - **Lift**: How much more/less likely pairs appear together vs random
   - **Phi Coefficient**: Correlation strength (-1 to +1)
   - **Chi-Square**: Statistical significance (p < 0.05 threshold)

3. **HMC Category Analysis**
   - Hot-Hot, Hot-Medium, Hot-Cold pairs
   - Medium-Medium, Medium-Cold pairs
   - Cold-Cold pairs
   - Reveals category interaction patterns

4. **Temporal Autocorrelation**
   - For each number: P(appear in draw N+1 | appeared in draw N)
   - Identifies "hot streak" numbers vs "cool down" numbers
   - Autocorrelation coefficient calculation

**Output Files**:
- `data/lotto_correlation_matrix.json` (full correlation data with all metrics)
- `data/lotto_correlation_summary.csv` (top 100 correlations, importable to Excel)

**Console Output**:
```
================================================================================
LOTTERY NUMBER CORRELATION ANALYSIS
================================================================================

OVERALL STATISTICS:
  Total number pairs analyzed: 1080
  Statistically significant: 52 (4.81%)
  Attraction pairs (lift > 1): 334
  Repulsion pairs (lift < 1): 745
  Neutral pairs: 1

--------------------------------------------------------------------------------
TOP 10 NUMBER PAIRS THAT ATTRACT (appear together more than expected)
--------------------------------------------------------------------------------
Pair         Observed   Expected   Lift     Phi      Sig?
--------------------------------------------------------------------------------
19-32        18         8.0        1.811    0.149    ✓
3-43         15         8.0        1.663    0.115    ✓
7-10         14         8.0        1.632    0.107    ✓
20-31        13         8.0        1.631    0.102    ✓
11-19        15         8.0        1.582    0.104    ✓
2-5          16         8.0        1.566    0.106    ✓
28-32        15         8.0        1.559    0.101    ✓
28-29        15         8.0        1.559    0.101    ✓

--------------------------------------------------------------------------------
TOP 10 NUMBER PAIRS THAT REPEL (appear together less than expected)
--------------------------------------------------------------------------------
Pair         Observed   Expected   Lift     Phi      Sig?
--------------------------------------------------------------------------------
5-28         1          8.0        0.111    -0.155   ✓
2-31         1          8.0        0.122    -0.145   ✓
15-16        1          8.0        0.163    -0.116   ✓
2-4          2          8.0        0.225    -0.134   ✓
24-43        2          8.0        0.226    -0.133   ✓
16-32        2          8.0        0.230    -0.131   ✓

--------------------------------------------------------------------------------
HMC CATEGORY CORRELATIONS
--------------------------------------------------------------------------------
  cold-hot             :  27.00% (2336 occurrences)
  hot-medium           :  23.32% (2018 occurrences)
  hot-hot              :  22.31% (1930 occurrences)
  cold-medium          :  14.05% (1216 occurrences)
  cold-cold            :   7.70% (666 occurrences)
  medium-medium        :   5.62% (486 occurrences)

--------------------------------------------------------------------------------
TEMPORAL AUTOCORRELATION (Top 10 numbers)
--------------------------------------------------------------------------------
Number   Autocorr     P(appear|appeared)   P(appear|not)
--------------------------------------------------------------------------------
22       -0.0948      0.0781               0.1729
20       -0.0878      0.0896               0.1773
13       -0.0867      0.0986               0.1853
37       -0.0780      0.0820               0.1600
33       0.0732       0.1837               0.1105

================================================================================
INTERPRETATION GUIDE
================================================================================
Lift > 1.0:  Numbers appear together MORE than random chance
Lift < 1.0:  Numbers appear together LESS than random chance
Lift ≈ 1.0:  Numbers appear together at random chance

Phi coefficient: Ranges from -1 (perfect negative) to +1 (perfect positive)
Chi-square > 3.84: Statistically significant at p < 0.05

Autocorrelation > 0: Number more likely to appear again in next draw
Autocorrelation < 0: Number less likely to appear again in next draw
================================================================================
```

**Key Insights**:

- **Attraction Pairs**: Numbers that appear together more than random chance (lift > 1.0)
  - Example: 19-32 appears together 1.81x more than expected
  - Could indicate physical or algorithmic biases in lottery drawing

- **Repulsion Pairs**: Numbers that avoid each other (lift < 1.0)
  - Example: 5-28 appears together only 0.11x as often as expected
  - Statistically significant anti-correlation

- **Category Patterns**:
  - Cold-Hot pairs are most common (27%)
  - Hot-Hot pairs are second (22.31%)
  - Medium-Medium pairs are rare (5.62%)
  - Suggests draws tend to mix categories rather than cluster

- **Temporal Patterns**:
  - Negative autocorrelation: Numbers that appeared are LESS likely to appear next draw
  - Positive autocorrelation: Numbers that appeared are MORE likely to appear next draw
  - Most numbers show weak temporal correlation (near 0)

**Use Cases**:

1. **Feature Engineering**: Create "companion number" features
   - Add "has_strong_companion" binary feature
   - Add "companion_count" numeric feature

2. **Number Selection**: Prefer high-correlation pairs when building combinations

3. **Validation**: Test if correlations are stable over time or change

4. **Pattern Detection**: Identify unusual correlation patterns that may indicate non-randomness

**Statistical Methods**:

- **Lift Ratio**: Simple, intuitive measure of association
- **PMI (Pointwise Mutual Information)**: Information-theoretic measure
- **Phi Coefficient**: Pearson correlation for binary variables
- **Chi-Square Test**: Statistical significance at α = 0.05 (chi² > 3.84)

**Dependencies**:
- Requires `data/lotto_draw_history.json`
- Uses standard library only (no external dependencies)

---

## Running Scripts from Different Locations

Most scripts in the `analysis/` folder have been updated to support running from multiple locations:

### Scripts that work from both root and analysis folder:
- `validate_bonus.py`
- `generate_bonus_to_main_json.py`
- `bonus_to_main_analysis.py`
- `bonus_analysis.py`
- `trend_analyzer.py`
- `correlation_matrix_analyzer.py`

### Scripts that must run from project root:
- `ensemble.py` (requires `quickpick.py` in current directory)

### Running from project root:
```bash
python analysis/<script_name>.py
```

### Running from analysis folder:
```bash
cd analysis
python <script_name>.py
```

---

## Dependencies

### Python Standard Library:
- `json` - JSON file handling
- `sys` - System operations
- `os` - Operating system interface
- `re` - Regular expressions
- `argparse` - Command-line argument parsing
- `subprocess` - Process management
- `pathlib` - Path handling
- `collections` (Counter, defaultdict) - Data structures
- `datetime` - Date/time operations
- `typing` - Type hints

### Third-party Libraries:
- `pandas` - Data analysis (trend_analyzer.py)
- `numpy` - Numerical operations (trend_analyzer.py)
- `matplotlib` - Plotting (trend_analyzer.py)

### Project Modules:
- `ml_lotto.data.loader` - Data loading utilities
- `ml_lotto.features.bonus` - Bonus feature calculations
- `ml_lotto.config` - Configuration settings

### Data Files Required:
- `data/lotto_draw_history.json` - Historical draw data (required by all scripts)
- `lottery_picks.txt` - Prediction results (required by validate_bonus.py, generated by quickpick.py)
- `ml_lotto/config.py` - Configuration file (modified by ensemble.py)

---

## Summary

The `analysis/` folder contains 7 specialized scripts:

| Script | Category | Purpose | Run Location |
|--------|----------|---------|--------------|
| `ensemble.py` | Testing | Ensemble voting system | Root only |
| `validate_bonus.py` | Testing | Validate bonus features | Root or analysis |
| `trend_analyzer.py` | Discovery | Find long-term trends | Root or analysis |
| `generate_bonus_to_main_json.py` | Generation | Create bonus-to-main JSON | Root or analysis |
| `bonus_to_main_analysis.py` | Discovery | Analyze bonus transitions | Root or analysis |
| `bonus_analysis.py` | Discovery | Comprehensive bonus analysis | Root or analysis |
| `correlation_matrix_analyzer.py` | Discovery | Number correlation analysis | Root or analysis |

All scripts have been updated to work correctly from their new location in the `analysis/` folder, with automatic path detection and fallback mechanisms.
