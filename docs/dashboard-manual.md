<!-- Status: current. Verified 2026-09-17 against app.py - all 8 pages match. -->
<!-- Audience: human operator of the dashboard. Not a spec for the code. -->

# Irish Lotto ML Analysis Dashboard - User Manual

## Table of Contents
1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Page-by-Page Guide](#page-by-page-guide)
   - [Trigger Periods Analysis](#1-trigger-periods-analysis)
   - [Draw History](#2-draw-history)
   - [Statistics](#3-statistics)
   - [Freshness Analysis](#4-freshness-analysis)
   - [Prediction Validator](#5-prediction-validator)
   - [Number Insights](#6-number-insights)
   - [Pattern Comparison](#7-pattern-comparison)
   - [Post Draw Analysis](#8-post-draw-analysis)
4. [Key Concepts Explained](#key-concepts-explained)
5. [Recommended Workflow](#recommended-workflow)
6. [Tips & Best Practices](#tips--best-practices)

---

## Introduction

The Irish Lotto ML Analysis Dashboard is a comprehensive validation and analysis tool designed to work alongside Machine Learning prediction models (like Model 4). It helps you:

- **See how typical a line looks** next to past draws
- **Explore historical patterns** for fun
- **Evaluate model performance** after each draw
- **Identify trends and anomalies** in real-time

**System Workflow:**
```
drawpick.py → quickpick.py → app.py (This Dashboard)
   ↓              ↓              ↓
Aggregate    Generate ML    Validate & Analyze
 Data        Predictions     Predictions
```

---

## Getting Started

### Running the Dashboard

```bash
streamlit run app.py
```

The dashboard will open in your web browser with 8 pages accessible via the top navigation menu.

### Understanding Irish Lotto Structure

- **7 numbers drawn total:** 6 main numbers + 1 bonus number
- **Players select:** 6 numbers (from 1-47)
- **Win conditions:** Match main numbers (bonus number used for secondary prizes)

---

## Page-by-Page Guide

---

## 1. Trigger Periods Analysis

**Purpose:** Identify numbers experiencing "hot streaks" (trigger periods) and analyze their volatility, trends, and momentum.

### 🔍 Sidebar Filters

#### **HMC Category**
- **What it is:** Classifies numbers by recent appearance frequency
- **Options:**
  - **All:** Show all numbers
  - **Hot:** Numbers appearing frequently in recent draws
  - **Medium:** Numbers with average appearance frequency
  - **Cold:** Numbers appearing rarely

- It does not change the chance in the next draw - every number is equally likely.

#### **Freshness Weight**
- **What it is:** How many times a number appeared in the last 5 draws
- **Options:**
  - **All:** No filter
  - **C0:** Number did NOT appear in last 5 draws (fresh)
  - **C1:** Appeared exactly ONCE in last 5 draws
  - **C≥2:** Appeared TWO or more times in last 5 draws (very recent)

- It does not change the chance in the next draw - every number is equally likely.

#### **Volatility Level** ⚡
- **What it is:** Measures consistency of appearance patterns
- **Options:**
  - **All:** No filter
  - **High:** Unpredictable patterns (volatility ≥ 1.15)
  - **Med:** Moderate predictability (0.85-1.15)
  - **Low:** Consistent, predictable patterns (<0.85)

- **What it tells you:** how regular a number's past gaps have been. It does not change the
  number's chance in the next draw - every number is equally likely.


#### **Trend Direction** 📈
- **What it is:** Whether a number came up more or less often in the last 50 draws than in the 50
  before (Fisher's exact test, p < 0.05)
- **Options:**
  - **All:** No filter
  - **↑ Trending Up:** Significantly more often
  - **→ Stable:** No significant change
  - **↓ Trending Down:** Significantly less often
- About 2 of the 47 numbers are flagged by chance even in a fair draw.

- **What to look for:**
  - **↑ Trending Up:** Numbers gaining momentum - appearing more frequently
  - **↓ Trending Down:** Numbers losing steam - appearing less frequently
  - **→ Stable:** Consistent behavior

- **Statistical significance:** Only shown if p < 0.05
- It does not change the chance in the next draw - every number is equally likely.

#### **Momentum** 🔥
- **What it is:** Recent activity compared to historical baseline
- **Options:**
  - **All:** No filter
  - **🔥 Heating Up:** Appearing >20% more than baseline
  - **— Stable:** Within ±20% of baseline
  - **❄️ Cooling Down:** Appearing >20% less than baseline

- **What to look for:**
  - **🔥 Heating Up:** came up more often recently
  - **❄️ Cooling Down:** came up less often recently
- It does not change the chance in the next draw - every number is equally likely. A number is never "due".

- **Difference from Trend:**
  - **Trend** = Long-term statistical direction
  - **Momentum** = Short-term recent activity burst

#### **Regime Shift Status** 🔄
- **What it is:** Identifies numbers experiencing significant pattern changes
- **Options:**
  - **All:** No filter
  - **Yes:** Number is in regime shift (pattern changing)
  - **No:** Number following typical pattern

- **What to look for:**
  - **Yes:** Number behavior is changing - may be entering new phase
  - **No:** Predictable behavior continuing

- It does not change the chance in the next draw - every number is equally likely.

### 📊 Main Display

#### **Historical Scenario Results Table**
Shows probability of a number appearing X times within a specific window:
- **Window Size:** Last N draws (e.g., Last 10 Draws)
- **Appearance:** Number of times (e.g., "1 Time", "2 Times")
- **Percentage:** Historical probability
- **Count:** How many times this scenario occurred

**How to use:** See how often a number has appeared a given number of times in a window.

#### **Trigger Periods Analysis Table**
Shows all 47 numbers with:
- **Category:** HMC status (Hot/Medium/Cold)
- **Freshness:** C0/C1/C≥2
- **Volatility/Trend/Momentum/Regime Shift:** As explained above
- **Total Count:** Historical appearances
- **Last Seen:** Most recent draw date
- **L4, L5, L9, L24:** Appearances in last 4/5/9/24 draws
- **Series columns:** Trigger period dates (color-coded by recency)

**Color Coding:**
- 🔴 **Red:** < 4 weeks ago (very recent)
- 🟣 **Purple:** 4-8 weeks ago (recent)
- 🟡 **Yellow:** 8-12 weeks ago (moderate)
- ⚫ **Black:** > 12 weeks ago (old)

### 🔥 Trending & Volatile Numbers Section

**Purpose:** Quick-reference copyable lists for filtering

- **📈 Trending Up Numbers:** Top 10 with strongest upward trends
- **⚡ High Volatility Numbers:** Top 10 most unpredictable
- **🔥 Heating Up:** Top 10 with strongest momentum
- **❄️ Cooling Down:** Top 10 weakest momentum
- **🔄 Numbers in Regime Shift:** All numbers changing patterns

**How to use:**
1. Copy numbers from a list
2. Paste into "Enter specific numbers" filter
3. View detailed analysis of that subset

### 💡 Sum/Range Check

Appears when you have exactly 6 numbers filtered:

- **Sum:** Total of your 6 numbers, shown as a typical sum (within mean ± 2 standard deviations of
  past draws), an uncommon sum (outside that but within past draws' range), or a sum never seen before.
- **Range Distribution:** how many of the 6 fall in 1-10, 11-20, 21-30, 31-40, 41-47.

How typical a sum is says nothing about the chance of winning. There is no confidence verdict
(removed in F-28).

---

## 2. Draw History

**Purpose:** Review historical draws and which recent bonus balls later came up as main numbers.

### 📊 Display Format

Each draw shows:
- **Draw #:** Sequential draw number
- **Date:** Draw date
- **HMC Distribution:** Pattern for that draw (e.g., 4H-2M-1C)
- **Draw Range:** Days between first and last number
- **Last 10 Bonus Balls Before This Draw:** the bonus balls of the 10 previous draws (F-33 - it
  used to include the draw's own bonus)
  - **Highlighted in red:** a ball from that list that came up in this draw
- **Winning Numbers Table:** All 7 numbers with details:
  - **Number:** The drawn number
  - **Bonus?:** ⭐ if bonus number
  - **Category:** HMC status at time of draw
  - **Days Since:** Days since previous appearance
  - **Recent columns (L4, L5, L9, L24):** Appearance counts

### 🎯 Recent Bonus Balls and the Main Draw

Shows the share of bonus balls that came up in the main draw within the next 10 draws, next to the
share any number would in a fair draw (`expected_random_rate` in `lotto_bonus_to_main_patterns.json`).
In a fair draw any number comes up in the main draw within 10 draws 74.5% of the time (1 - (41/47)^10), and bonus balls do the same - 74.6% over 488 draws, checked 2026-09-19 (F-30). A recent bonus ball is no likelier than any other number.

**Table:** every number that was a bonus ball in the last 150 days, with its past bonus-to-main rate,
days since it was a bonus ball, average draws until it came up as a main number, and the HMC category
and freshness it most often had. A copyable list lets you filter them on other pages.

### 🔍 Sidebar Filters

- **Number of draws to display:** How many recent draws to show (default: 5)
- Older draws are listed first, newest last (chronological order)

---

## 3. Statistics

**Purpose:** Understand overall probability distributions and validate patterns.

### 📊 Overall HMC Distribution in Main Numbers

Shows what percentage of ALL main numbers (across all history) are Hot, Medium, or Cold:

**Typical Distribution:**
- 🔥 **Hot:** ~47.60% (nearly half!)
- 🌡️ **Medium:** ~24.27%
- ❄️ **Cold:** ~28.13%

**Key Insight:** Hot numbers dominate historical draws. Consider weighting your selections toward hot numbers.

### 🎯 HMC Distribution (7-Ball Patterns)

**Shows:** Historical frequency of Hot-Medium-Cold patterns for all 7 drawn numbers

**Top patterns typically:**
- 4H-2M-1C
- 3H-2M-2C
- 4H-1M-2C

**How to use:** Check if your selection's HMC pattern matches common historical patterns.

### 🎯 6-Ball HMC Pattern Analysis

**Why this matters:** You select 6 numbers, but 7 are drawn. This shows combined probability.

**Example:** If you pick 2H-2M-2C, the 7th ball could be:
- Hot → becomes 3H-2M-2C
- Medium → becomes 2H-3M-2C
- Cold → becomes 2H-2M-3C

**Combined Probability:** Sum of all three scenarios

**Top 10 Best 6-Ball Patterns table:** Shows which 6-ball selections have highest probability

**Custom Pattern Analyzer:**
- Enter your Hot/Medium/Cold counts (must total 6)
- See detailed breakdown of possible 7-ball outcomes
- View probability distribution chart

**Note:** a common pattern is not likelier to win; every line is equally likely.

### ⚖️ Odd/Even Pattern Analysis

**Overall Distribution:** ~50% odd, ~50% even (balanced)

**Past draws (498, checked 2026-09-19):**
- **2, 3, or 4 odd numbers:** 79%
- **1 or 5 odd numbers:** 19%
- **0 or 6 odd numbers:** 2%

**Per-Number Affinity Table:**
Shows if specific numbers prefer to appear with odd or even neighbors.

**Filters:**
- **Affinity:** Strong Odd / Balanced / Strong Even
- **Significance:** Show only statistically significant results (p < 0.05)

**Validation Helper:**
Enter 6 numbers to check odd/even ratio against historical patterns.

**Note:** 2-4 odd is the most common shape; it is not likelier to win.

### High Numbers (32 and above) per Draw

How many of each past draw's 6 main numbers were 32 or above: headline shares for 1, 2 and 3
such numbers, and a table for 0-6 next to what a fair draw gives (added 2026-09-19, F-19). About
a quarter of draws have 1, a third have 2, a quarter have 3. Numbers 1-31 are the birthday range
many players use; the breakdown shows what real draws look like when you build your own line.

---

## 4. Freshness Analysis

**Purpose:** Analyze numbers by recency (freshness weight).

### 🎯 Mode Selection

**6 Balls vs 7 Balls:**
- **6 Balls:** For your selections (what you pick)
- **7 Balls:** For analyzing actual draws (6 main + bonus)

### 📊 Filter by Freshness Pattern

**What it shows:** Historical frequency of freshness combinations

**Freshness Bins:**
- **C0:** Number did NOT appear in last 5 draws
- **C1:** Appeared once in last 5 draws
- **C≥2:** Appeared 2 or more times in last 5 draws

**For 6-Ball mode:**
Select C0/C1/C2 counts (must total 6) to see combined probability.

**Example:** 3×C0, 2×C1, 1×C2 means:
- 3 numbers not in last 5 draws
- 2 numbers appeared once in last 5 draws
- 1 number appeared 2+ times in last 5 draws

**Top patterns table:** Shows most common freshness combinations historically.

**Note:** no freshness mix is likelier to win; every line is equally likely.

---

## 5. Prediction Validator

**Purpose:** See how typical your 6 numbers look next to past draws. Every line is equally likely to win.

### 📝 Input Section

Enter your 6 numbers (from quickpick.py or manual selection).

### Validation Results (5 scored checks + 1 informational)

#### 1️⃣ **Odd/Even Ratio**
- **Common:** 2-4 odd numbers (Score: 100)
- **Uncommon:** 1 or 5 odd numbers (Score: 60)
- **Very Rare:** 0 or 6 odd numbers (Score: 20)

#### 2️⃣ **Sum Validation**
- **Typical:** Sum between 84-206 (Score: 100)
- **Uncommon:** Sum between historical min-max (Score: 60)
- **Never seen before:** Sum outside historical range (Score: 20)

#### 3️⃣ **HMC Pattern**
- **Good:** Matches top 10 historical patterns (Score: 80-100)
- **Fair:** Matches top 20 patterns (Score: 60-79)
- **Poor:** Rare or never occurred pattern (Score: 20-59)

#### 4️⃣ **Bonus Transition**
- **Typical:** Includes a number that was a bonus ball in the last 150 days (Score: 100) - 99.6% of
  past draws did (F-30, 2026-09-19)
- **Unusual:** No such number (Score: 70)

#### 5️⃣ **Range Spread**
- **Wide:** Numbers in 4+ ranges, max 3 per range (Score: 80-100)
- **Moderate:** Numbers in 3 ranges (Score: 60-79)
- **Narrow:** Numbers clustered in 1-2 ranges (Score: 20-59)

#### 6. **High Numbers (32 and above)** - information only, not scored
- Shows how many of your numbers are 32 or above, and a table of how often past draws had 0-6
  such numbers next to what a fair draw gives (added 2026-09-19, F-19).
- It does not change your chance of winning - every line is equally likely. Numbers 1-31 are
  the birthday range many players use, so a line built mostly from them is more likely to share a
  prize. Use it to decide how your own line should look.

### ⚠️ Automated Anomaly Detection

**Each alert describes how unusual the line looks next to past draws:**

**Very unusual:**
- Sum more than 3 standard deviations from the mean of past draws (mean and standard deviation read
  from `lotto_sum_contribution_validated.json`, F-29)
- All odd or all even numbers
- All numbers from one HMC category
- All numbers in ≤2 ranges
- 4+ consecutive numbers
- Exact duplicate of recent draw

**Unusual:**
- Sum more than 2.5 standard deviations from the mean
- Severe odd/even imbalance (5-1 or 1-5)
- 5 numbers from one HMC category
- 4+ numbers in single range
- 4+ cooling down numbers
- All numbers in ≤2 decades

The volatility alert was removed in F-29: it needed 4 numbers at volatility ≥ 1.5, and no number has
reached 1.2, so it never fired.

### 🏆 Overall Validation Score

The score measures how typical a line looks next to past draws, **not its chance of winning** -
every line is equally likely to win (F-26, 2026-09-19).

**Grading:**
- **A+ (90-100):** Very typical
- **A (80-89):** Typical of past draws
- **B (70-79):** Fairly typical
- **C (60-69):** Less typical
- **D (<60):** Unusual next to past draws

**What Makes It Less Typical:** below 80, the checks that pulled the score down, for a player who
wants a more typical-looking line. No advice to play or regenerate.

---

## 6. Number Insights

**Purpose:** Deep-dive analysis of any individual number (1-47).

### 📊 Overview Section

- **Total Appearances:** How many times drawn historically
- **HMC Category:** Current classification
- **Last Seen:** Most recent draw date
- **Odd/Even:** Number parity

### 📈 Volatility & Trend Analysis

- **Volatility:** High/Med/Low + numerical value
- **Trend:** ↑/→/↓ with significance
- **Momentum:** 🔥/—/❄️ with multiplier
- **Regime Shift:** Yes/No
- **Gap Consistency:** Predictability score (0-1)
- **Recent Counts:** Appearances in last 20, older periods
- **Peak/Trough Counts:** Number of cycles detected

These describe the number's past. None changes its chance in the next draw. A significant trend
is 5% likely by chance for any number, so about 2 of the 47 show one in a fair draw.

### ⏱️ Recent Activity

Shows appearances in last 4, 5, 9, and 24 draws with freshness classification.

### 🎁 Bonus Number Analysis

- **Bonus Appearances:** Times appeared as bonus
- **Bonus→Main Rate:** How often it came up as a main number within 10 draws of being a bonus ball,
  next to the 74.5% any number would in a fair draw
- **Avg Draws to Transit:** Typical waiting period
- **Last Bonus:** Date and days since


### 📏 Gap Analysis

**What it shows:** Time between appearances

- **Min Gap:** Shortest time between appearances
- **Max Gap:** Longest time between appearances
- **Avg Gap:** Typical waiting time
- **Current Gap:** Days since last appearance

**Current gap vs average:** stated as a fact - longer than usual, about usual, or came up
recently. The current gap runs to the latest draw, not today. A long gap does not make a number due.

### 🔗 Trigger Series Patterns

Shows historical hot streaks:
- **Pattern:** E.g., "5 Consecutives 2 Times" (appeared 2 times within 5 draws)
- **Start/End Dates:** When the streak occurred
- **Count:** Number of appearances in that period

**Note:** a past streak says nothing about the next draw.

### 📅 Appearance History

Last 20 appearances with:
- **Date:** When it appeared
- **Type:** Main or Bonus
- **Gap:** Days since previous appearance

### 📋 Profile

A list of what stands out in the number's past, with no score or verdict (F-30, 2026-09-19): how
often it came up recently against its history, a regime shift, a gap longer than usual or a recent
appearance, a recent bonus appearance, and its count in the last 5 draws. The old 0-100
"Recommendation" (STRONG PICK ... AVOID) is gone - it rewarded "overdue" numbers, and every number has
the same 6 in 47 (12.8%) chance of being a main number in each draw.

---

## 7. Pattern Comparison

**Purpose:** Compare your prediction against historical winning patterns.

### 🎯 Input Section

Enter your 6 numbers to analyze.

### 📊 Your Prediction Pattern

Displays:
- **HMC Pattern:** e.g., 3H-2M-1C
- **Odd/Even:** e.g., 3 Odd / 3 Even
- **Sum:** Total value (typical or unusual next to past draws)
- **Consecutive:** Whether you have consecutive numbers
- **Range Distribution:** Count in each range (1-10, 11-20, etc.)

### 🔍 Similar Historical Draws

**Similarity Algorithm (weighted):**
- HMC pattern similarity: 30%
- Odd/Even similarity: 20%
- Sum proximity: 25%
- Range distribution: 15%
- Consecutive numbers: 10%

**Which hot/medium/cold.** Your line is classified with today's categories; each past draw with the
categories in force just before it was drawn. A past draw typed in today can therefore show a
different HMC pattern from its own row, and need not rank first.

**Top 15 Similar Draws table:**
- **Rank:** 1-15
- **Date:** When the similar draw occurred
- **Numbers:** Actual winning numbers
- **Bonus:** Bonus number
- **Similarity:** Percentage match
- **HMC/O/E/Sum/Consecutive:** Pattern details

**Best Match:** Highlighted with similarity % and details.

### 📈 Pattern Frequency Analysis

**HMC Pattern Frequency:**
- Shows how many times your HMC pattern has won historically
- Example: "2H-2M-2C appeared in 8.5% of draws"

**Odd/Even Pattern Frequency:**
- Shows how common your odd/even split is
- Example: "3/3 split appeared in 35% of draws"

### 💡 How Typical Is This Shape (0-100 Score)

How much your line's shape looks like past draws - **not its chance of winning**; every line is
equally likely to win (F-28, 2026-09-19).

**Scoring factors:**
- HMC pattern frequency (25 points if ≥5%, 15 if ≥2%, 5 if >0%)
- Odd/Even frequency (25 points if ≥10%, 15 if ≥5%)
- Sum within the typical range (20 points)
- Similarity to the closest past draws (20 points if ≥80%, 10 if ≥60%)
- Numbers in all five ranges, at most 3 in one (10 points)

**Levels:** 75-100 Very typical shape, 50-74 Typical, 25-49 Less typical, 0-24 Unusual shape.

**Common / Less common in past draws:** which parts of the shape are which.

---

## 8. Post Draw Analysis

**Purpose:** Evaluate Model 4 performance after each draw.

### 📝 Input Section

**Winning Numbers:**
- Enter 6 main winning numbers
- Enter 1 bonus number

**Model 4 Predictions:**
- Set prediction count (default: 20, configurable)
- Enter all numbers Model 4 predicted

### 🏆 Performance Summary

**Accuracy:** Percentage of correct predictions (e.g., 3/6 = 50%)

**Performance Levels:**
- **EXCELLENT:** 5-6 correct (≥83%)
- **GOOD:** 3-4 correct (50-83%)
- **FAIR:** 2 correct (33-50%)
- **POOR:** 0-1 correct (<33%)

**Metrics:**
- Correct Predictions count
- Missed Numbers count
- Bonus Predicted (Yes/No)

### ✅ Correct Predictions

Shows numbers you predicted correctly with:
- **HMC:** Category at time of draw
- **Freshness:** C0/C1/C≥2
- **Volatility/Trend/Momentum:** As explained in Trigger Analysis
- **Recent Activity:** L4, L5, L9 counts
- **Last Seen:** Previous appearance date
- **Total Hits:** Historical appearances

**HMC Breakdown:** How many hot/medium/cold were correctly predicted.

**How to use:** Identify characteristics of successful predictions to refine model.

### ❌ Missed Numbers

Shows winning numbers you didn't predict with same detailed characteristics.

**HMC Breakdown:** Identifies if you missed specific categories (e.g., "3 hot numbers missed").

**Insight:** Review these to understand model blind spots.

### 🎁 Bonus Number Analysis

- Shows if bonus was in your predictions
- Complete profile of bonus number
- Recent activity metrics

### 📋 Wrong Predictions (Expandable)

Numbers you predicted that didn't win (excluding bonus).

**How to use:** Understand over-predicted characteristics.

### 💡 Recommendations for Model Improvement

**Pattern-Based:**
- "Hot numbers were missed" → Increase hot number weighting
- "Cold numbers were missed" → Include more cold numbers
- "Hot number strategy working" → Continue current approach

**Freshness-Based:**
- "Fresh C0 numbers missed" → Include more non-recent numbers

**Model Performance:**
- "Low accuracy" → Consider retraining with recent data
- "Too many predictions" → Reduce count for better precision
- "Too few predictions" → Increase count for better coverage

---

## Key Concepts Explained

### HMC (Hot-Medium-Cold) Classification

**Definition:** Numbers are classified based on recent appearance frequency.

**How it's calculated:**
- Analyzes appearances in recent draws (typically last 20-30 draws)
- Compares against overall historical average
- Uses statistical thresholds to classify

**Categories:**
- **Hot (🔥):** Appearing significantly more than average
- **Medium (🌡️):** Appearing at average rate
- **Cold (❄️):** Appearing significantly less than average

**Why it matters:** Historical data shows hot numbers appear in ~47.6% of main draws.

### Freshness Weight (C0, C1, C≥2)

**Definition:** How many times a number appeared in the last 5 draws.

**Categories:**
- **C0:** 0 appearances (fresh, not recently drawn)
- **C1:** 1 appearance (moderate recency)
- **C≥2:** 2+ appearances (very recent, saturated)

**What it means:** a description of the recent past. No number is "due" and no mix performs better;
every line is equally likely to win. (F-18 found bin-2 numbers drawn ~11% more often at p = 0.031 -
weak, and re-checked as draws accumulate.)

### Volatility

**Definition:** Consistency of appearance patterns over time.

**How it's measured:**
- Standard deviation of gap times between appearances
- Normalized against mean gap time

**Interpretation:**
- **Low (<0.85):** Predictable, consistent timing
- **Medium (0.85-1.15):** Moderate predictability
- **High (≥1.15):** Erratic, unpredictable

**Note:** It does not change the chance in the next draw - every number is equally likely.

### Trend

**Definition:** Change in how often a number came up: the last 50 draws against the 50 before.

**How it's calculated (checked against the code 2026-09-19, F-31):**
- Value: the change between the two windows, on a smoothed series
- Significance: Fisher's exact test on the raw counts of the two windows, p < 0.05. On simulated
  fair draws it flags 3.3% of numbers; the earlier test on the smoothed series flagged 61%.

**Types:**
- **↑ Trending Up:** Increasing frequency (significant)
- **→ Stable:** No significant trend
- **↓ Trending Down:** Decreasing frequency (significant)

**Difference from Momentum:**
- **Trend:** Long-term statistical direction
- **Momentum:** Short-term recent burst

**Note:** It does not change the chance in the next draw - every number is equally likely.

### Momentum

**Definition:** Recent activity compared to historical baseline.

**How it's calculated:**
- Recent count (typically last 20 draws) / Older count (previous period)
- Ratio > 1.2 = heating up
- Ratio < 0.8 = cooling down

**Types:**
- **🔥 Heating Up (>1.2):** Appearing more than historical rate
- **— Stable (0.8-1.2):** Consistent with historical rate
- **❄️ Cooling Down (<0.8):** Appearing less than historical rate

**Use case:** Identifies short-term bursts that may not be long-term trends.

### Regime Shift

**Definition:** Significant change in a number's behavior pattern.

**How it's detected:**
- Analyzes peaks and troughs in appearance frequency
- Detects when pattern deviates from historical norm
- Uses statistical tests for significance

**Interpretation:**
- **Yes:** the number's past frequency changed noticeably
- **No:** no such change

**Note:** It does not change the chance in the next draw - every number is equally likely.

### Bonus-to-Main Transition

**Finding:** In a fair draw any number comes up in the main draw within 10 draws 74.5% of the time (1 - (41/47)^10), and bonus balls do the same - 74.6% over 488 draws, checked 2026-09-19 (F-30). A recent bonus ball is no likelier than any other number.

**How it works:**
1. Number appears as **bonus** in draw N
2. Track next 10 draws
3. If appears in **main 6** within those 10 draws → transition occurred

**Transition Rate:**
- Per-number statistic
- Shown next to the fair-draw 74.5%

**Why it matters:** Provides statistically-backed candidates for main number selection.

### Trigger Periods

**Definition:** Windows of time when a number appears multiple times.

**Example:** "5 consecutives 2 times" = appeared 2 times within 5 draws

**How it's detected:**
- Scans historical draws for appearance clusters
- Records window size and frequency
- Color-coded by recency

**Use case:** If a number has recent trigger series, it may be entering another hot period.

### Pattern Similarity Algorithm

**Purpose:** Compare your selection to historical winners.

**Weighted components:**
1. **HMC pattern (30%):** How close is your H-M-C distribution?
2. **Odd/Even (20%):** How similar is your odd/even split?
3. **Sum (25%):** How close is your total sum?
4. **Range distribution (15%):** How similar is your spread across ranges?
5. **Consecutive (10%):** Do you both have/lack consecutive numbers?

**Similarity score:** 0-100% (100% = identical pattern)

**Use case:** High similarity (>80%) to historical winners indicates statistically sound selection.

---

## Recommended Workflow

### Pre-Draw Workflow (Before Playing)

**Step 1: Generate Predictions**
```bash
python3 drawpick.py    # Update data
python3 quickpick.py   # Generate Model 4 predictions
streamlit run app.py   # Open dashboard
```

**Step 2: Validate Predictions**
1. Go to **Prediction Validator**
2. Paste your 6 numbers from Model 4
3. Review all 5 validation dimensions
4. Check anomaly detection alerts
5. Read the score as how typical the line looks - it does not change the chance of winning

**Step 3: Deep Analysis (Optional)**

a) **Check Pattern Match:**
   - Go to **Pattern Comparison**
   - Enter your 6 numbers
   - See which past draws had a similar shape

b) **Review Individual Numbers:**
   - Go to **Number Insights**
   - Analyze each of your 6 numbers
   - See each number's history

c) **Verify HMC Balance:**
   - Go to **Statistics**
   - Use 6-Ball HMC Pattern Analyzer
   - See how common your pattern has been

d) **Check Freshness:**
   - Go to **Freshness Analysis**
   - See your line's C0/C1/C2 mix next to past draws

**Step 4: Review Recent Bonus Balls**
- Go to **Draw History**
- Check **Recent Bonus Balls and the Main Draw**
- See which recent bonus balls later came up as main numbers

**Step 5: Filter & Refine**
- Go to **Trigger Periods Analysis**
- Filter the 47 numbers by category, freshness, volatility or trend to explore them
- Use the Sum/Range check at the bottom

**Step 6: Final Decision**
- Every line is equally likely to win. The validation score only shows how typical your line looks;
  keep it or change it as you like.

### Post-Draw Workflow (After Results)

**Step 1: Evaluate Performance**
1. Go to **Post Draw Analysis**
2. Enter the 7 winning numbers
3. Enter your Model 4 predictions (all 20)
4. Click **Analyze Results**

**Step 2: Review Results**
- Check **Accuracy** percentage
- Identify **Correct Predictions** characteristics
- Analyze **Missed Numbers** patterns
- Review **Recommendations**

**Step 3: Model Tuning**
Based on recommendations:
- **If hot numbers missed:** Increase hot number weight in Model 4
- **If fresh numbers missed:** Include more C0 numbers
- **If accuracy < 33%:** Consider retraining model
- **If bonus predicted but low accuracy:** Good transition logic, adjust main selection

**Step 4: Update Strategy**
- Document what worked (correct predictions)
- Document what didn't (missed patterns)
- Adjust model parameters for next run

---

## Tips & Best Practices

### What the facts mean for your line

Irish Lotto is a fair draw: **every line has the same chance of winning**. Nothing on this site -
hot or cold, odd or even, sum, spread, transition candidates, volatility, momentum - changes that.
What the pages show is what past draws looked like, so you can build a line that looks like them, or
deliberately does not. Both are equally likely to win.

The one thing a line's make-up does change is how many other players might share a prize: lines
made mostly of 1-31 (birthdays) are played more often. See the High Numbers check (F-19).

### Analysis Tips

**Using Filters Effectively:**
1. **Start broad, narrow down:**
   - Begin with "All" filters
   - Apply one filter at a time
   - Observe how pool changes

2. **Use copyable lists:**
   - Copy numbers from Trending/Volatile lists
   - Paste into specific number filter
   - Analyze subset in detail

**Reading Tables:**
1. **Color-coded trigger dates:**
   - Focus on 🔴 Red and 🟣 Purple (recent activity)
   - ⚫ Black dates are historical reference only

2. **Recent activity columns (L4, L5, L9, L24):**
   - **L4 = 2-3:** Very active recently
   - **L9 = 3-4:** Sustained activity
   - **L24 = 6-8:** Consistent long-term

3. **Sorting:**
   - Click column headers to sort
   - Use for finding extremes (highest/lowest)

**Checking a line's shape:**
1. **Sum:** is it in the typical range?
2. **Pattern frequency:** compare with the Statistics page
3. **Similar draws:** Pattern Comparison page
4. **Anything unusual:** Prediction Validator

None of these changes the chance of winning.

### Performance Optimization

**For Model 4:**
1. **Track accuracy over 10+ draws:** Single draw results are noisy
2. **Adjust based on consistent patterns:** Not one-off misses
3. **Recommended prediction count:** 15-25 numbers (sweet spot)
4. **Retraining frequency:** Every 20-30 draws or when accuracy drops

**Dashboard Usage:**
1. **Pre-draw validation:** 5-10 minutes
2. **Deep analysis:** 15-20 minutes (optional, for refinement)
3. **Post-draw review:** 5 minutes

**Decision Making:**
- **High confidence (validation score ≥ 85):** Play immediately
- **Medium confidence (70-84):** Consider minor adjustments
- **Low confidence (<70):** Regenerate or skip

---

## Troubleshooting

### "No data available" errors
**Cause:** Data files not generated
**Solution:** Run `python3 drawpick.py` to generate all data files

### Validation score lower than expected
A low score means the line looks less like past draws, not that it is less likely to win.
**What lowers it:**
1. Sum is within 84-206
2. Odd/even ratio is 2-4
3. Not all same HMC category
4. Numbers spread across ranges
5. "Very unusual" alerts

### Model 4 accuracy below 20%
**Possible causes:**
1. Model needs retraining with recent data
2. Too many predictions (reduce count)
3. Chance: the models sit at chance, as a fair draw requires (F-17)

**Solutions:**
1. Review Post Draw Analysis recommendations
2. Reduce prediction count to 15-20
3. Judge accuracy over many draws, not one

### Recent bonus balls don't match "Last 10 Bonus Balls Before This Draw"
The Draw History table lists every number that was a bonus ball in the last 150 days; the "Last 10
Bonus Balls Before This Draw" line lists only the bonus balls of the 10 draws before that draw.

---

## Glossary

**Appearance:** When a number is drawn (main or bonus)

**Baseline:** Historical average appearance rate for a number

**Boost Factor:** How much better than random (e.g., 2.5x = 150% better)

**Category:** HMC classification (Hot/Medium/Cold)

**Confidence Interval:** Statistical range where true value likely falls

**Draw:** Single lottery event (7 numbers: 6 main + 1 bonus)

**Freshness:** Recency classification (C0/C1/C≥2)

**Gap:** Days between appearances of a number

**HMC:** Hot-Medium-Cold classification system

**Main Numbers:** The 6 primary winning numbers

**Momentum:** Short-term activity compared to historical baseline

**Pattern:** Specific combination characteristic (HMC, odd/even, etc.)

**Regime Shift:** Significant change in number behavior pattern

**Significance (p-value):** Statistical confidence (p < 0.05 = 95% confident)

**Transition:** Bonus number appearing in main draw within 10 draws

**Trend:** Long-term statistical direction of appearances

**Trigger Period:** Time window with multiple appearances

**Validation:** Checking selection against historical patterns

**Volatility:** Consistency/predictability of appearance patterns

---

## Support & Updates

**Data Updates:**
Run `python3 drawpick.py` after each draw to update all analysis data.

**Model Retraining:**
Run `python3 quickpick.py` periodically to retrain Model 4 with latest data.

**Dashboard Access:**
```bash
streamlit run app.py
```

**Version:** 1.0 (Phase 3 Complete)

**Last Updated:** November 2025

---

## Quick Reference Card

### Pre-Draw Checklist
- [ ] Run drawpick.py (data updated?)
- [ ] Generate predictions (quickpick.py)
- [ ] Check your line on the Prediction Validator if you are curious how typical it looks

### Post-Draw Checklist
- [ ] Enter actual results in Post Draw Analysis
- [ ] Review accuracy (target: ≥33%)
- [ ] Check correct predictions characteristics
- [ ] Analyze missed numbers patterns
- [ ] Apply recommendations
- [ ] Document learnings

### Typical Line Profile
What most past draws looked like - not a recipe for winning, since every line is equally likely:
- **Odd/Even:** 2-4 odd numbers
- **Sum:** 84-206
- **Ranges:** 4-5 ranges covered, at most 3 in one

---

**End of User Manual**

For questions or issues, review the Troubleshooting section or consult the specific page documentation above.

Good luck with your predictions! 🍀
