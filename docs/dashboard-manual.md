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

- **Validate predictions** before playing
- **Analyze historical patterns** to inform selections
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

- **What to look for:**
  - Hot numbers for consistent selections
  - Cold numbers for contrarian picks
  - Mix of categories for balanced selection (e.g., 3 hot, 2 medium, 1 cold)

#### **Freshness Weight**
- **What it is:** How many times a number appeared in the last 5 draws
- **Options:**
  - **All:** No filter
  - **C0:** Number did NOT appear in last 5 draws (fresh)
  - **C1:** Appeared exactly ONCE in last 5 draws
  - **C≥2:** Appeared TWO or more times in last 5 draws (very recent)

- **What to look for:**
  - **C0 numbers:** Fresh picks that haven't been drawn recently (contrarian strategy)
  - **C1 numbers:** Balanced - not too fresh, not too saturated
  - **C≥2 numbers:** Very hot - appeared multiple times recently (momentum strategy)

- **Strategy tip:** Historical data shows balanced selections perform best. Mix C0 and C1 numbers rather than all C≥2.

#### **Volatility Level** ⚡
- **What it is:** Measures consistency of appearance patterns
- **Options:**
  - **All:** No filter
  - **High:** Unpredictable patterns (volatility ≥ 1.15)
  - **Med:** Moderate predictability (0.85-1.15)
  - **Low:** Consistent, predictable patterns (<0.85)

- **What to look for:**
  - **Low volatility:** Numbers with predictable timing (safer picks)
  - **High volatility:** Numbers with erratic patterns (risky but potentially rewarding)
  - **Medium volatility:** Balanced choice

- **How to use:**
  - Conservative strategy: Focus on low volatility numbers
  - Aggressive strategy: Mix some high volatility numbers for surprise wins

#### **Trend Direction** 📈
- **What it is:** Statistical direction of appearance frequency over time
- **Options:**
  - **All:** No filter
  - **↑ Trending Up:** Statistically increasing in frequency (p < 0.05)
  - **→ Stable:** No significant trend
  - **↓ Trending Down:** Statistically decreasing in frequency (p < 0.05)

- **What to look for:**
  - **↑ Trending Up:** Numbers gaining momentum - appearing more frequently
  - **↓ Trending Down:** Numbers losing steam - appearing less frequently
  - **→ Stable:** Consistent behavior

- **Strategy:**
  - **Momentum strategy:** Select trending up numbers (riding the wave)
  - **Mean reversion:** Select trending down numbers (expecting bounce back)
  - **Statistical significance:** Only shown if p < 0.05 (95% confidence)

#### **Momentum** 🔥
- **What it is:** Recent activity compared to historical baseline
- **Options:**
  - **All:** No filter
  - **🔥 Heating Up:** Appearing >20% more than baseline
  - **— Stable:** Within ±20% of baseline
  - **❄️ Cooling Down:** Appearing >20% less than baseline

- **What to look for:**
  - **🔥 Heating Up:** Numbers on a hot streak (short-term burst)
  - **❄️ Cooling Down:** Numbers that may be "due" (contrarian play)

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

- **How to use:** Regime shift numbers can indicate:
  - Transition from cold to hot (good opportunity)
  - Transition from hot to cold (proceed with caution)

### 📊 Main Display

#### **Historical Scenario Results Table**
Shows probability of a number appearing X times within a specific window:
- **Window Size:** Last N draws (e.g., Last 10 Draws)
- **Appearance:** Number of times (e.g., "1 Time", "2 Times")
- **Percentage:** Historical probability
- **Count:** How many times this scenario occurred

**How to use:** Check if your selected numbers have appeared 2-3 times in last 10 draws (common pattern).

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

### 💡 Sum/Range Validation Panel

Appears when you have exactly 6 numbers filtered:

- **Sum:** Total of your 6 numbers
  - **Realistic Range:** 84-206 (mean ± 2 standard deviations)
  - **Historical Mean:** 144.87

- **Range Distribution:** Numbers spread across:
  - 1-10, 11-20, 21-30, 31-40, 41-47
  - **Ideal:** At least 1 number in each range, max 3 per range

- **Confidence Level:**
  - **HIGH:** Both sum and range are realistic
  - **MEDIUM:** One criterion is slightly off
  - **LOW:** Both criteria are problematic

---

## 2. Draw History

**Purpose:** Review historical draws and identify bonus-to-main transition candidates.

### 📊 Display Format

Each draw shows:
- **Draw #:** Sequential draw number
- **Date:** Draw date
- **HMC Distribution:** Pattern for that draw (e.g., 4H-2M-1C)
- **Draw Range:** Days between first and last number
- **Last 10 Bonus Numbers:** The 10 most recent bonus numbers at time of draw
  - **Highlighted in green:** If that number appeared in the current draw
- **Winning Numbers Table:** All 7 numbers with details:
  - **Number:** The drawn number
  - **Bonus?:** ⭐ if bonus number
  - **Category:** HMC status at time of draw
  - **Days Since:** Days since previous appearance
  - **Recent columns (L4, L5, L9, L24):** Appearance counts

### 🎯 Bonus-to-Main Transition Candidates

**Key Finding:** 74.25% of bonus numbers appear in main draw within 10 draws!

**What this section shows:**
- Numbers that recently appeared as **bonus** and have high probability of appearing in **main draw** soon
- **Filter criteria:**
  - Transition Rate > 65%
  - Days Since Last Bonus < 150 days

**Table columns:**
- **Number:** The candidate number
- **Transition Rate:** Historical % of transitioning from bonus to main
- **Days Since Bonus:** Days since it last appeared as bonus
- **Avg Draws to Transit:** Average number of draws before transitioning
- **Last Bonus:** Date of last bonus appearance
- **HMC When Transitioning:** Most common HMC category when it transitions
- **Freshness:** Most common freshness level when it transitions

**Copyable List:** Click to select the comma-separated list of candidates for easy filtering.

**Strategy:** Include 1-2 transition candidates in your 6-number selection for statistically-backed picks.

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

**Strategy:** Pick a 6-ball pattern from the top 10 for statistically optimal selection.

### ⚖️ Odd/Even Pattern Analysis

**Overall Distribution:** ~50% odd, ~50% even (balanced)

**Realistic Ratios:**
- **2, 3, or 4 odd numbers:** 90%+ of historical draws
- **1 or 5 odd numbers:** ~5% of draws (uncommon)
- **0 or 6 odd numbers:** <0.5% of draws (extremely rare)

**Per-Number Affinity Table:**
Shows if specific numbers prefer to appear with odd or even neighbors.

**Filters:**
- **Affinity:** Strong Odd / Balanced / Strong Even
- **Significance:** Show only statistically significant results (p < 0.05)

**Validation Helper:**
Enter 6 numbers to check odd/even ratio against historical patterns.

**Strategy:** Aim for 2-4 odd numbers (historically most common).

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

**Strategy:** Balanced freshness (mix of C0, C1, C2) tends to perform better than extremes.

---

## 5. Prediction Validator

**Purpose:** Comprehensive validation of your 6-number selection before playing.

### 📝 Input Section

Enter your 6 numbers (from quickpick.py or manual selection).

### Validation Results (5 scored checks + 1 informational)

#### 1️⃣ **Odd/Even Ratio**
- **Realistic:** 2-4 odd numbers (Score: 100)
- **Uncommon:** 1 or 5 odd numbers (Score: 60)
- **Very Rare:** 0 or 6 odd numbers (Score: 20)

#### 2️⃣ **Sum Validation**
- **Realistic:** Sum between 84-206 (Score: 100)
- **Uncommon:** Sum between historical min-max (Score: 60)
- **Unrealistic:** Sum outside historical range (Score: 20)

#### 3️⃣ **HMC Pattern**
- **Good:** Matches top 10 historical patterns (Score: 80-100)
- **Fair:** Matches top 20 patterns (Score: 60-79)
- **Poor:** Rare or never occurred pattern (Score: 20-59)

#### 4️⃣ **Bonus Transition**
- **Excellent:** Includes 2+ high-probability transition candidates (Score: 100)
- **Good:** Includes 1 candidate (Score: 80)
- **Fair:** Includes candidates with lower probability (Score: 60)
- **Poor:** No transition candidates (Score: 40)

#### 5️⃣ **Range Spread**
- **Good:** Numbers in 4+ ranges, max 3 per range (Score: 80-100)
- **Fair:** Numbers in 3 ranges (Score: 60-79)
- **Poor:** Numbers clustered in 1-2 ranges (Score: 20-59)

#### 6. **High Numbers (32 and above)** - information only, not scored
- Shows how many of your numbers are 32 or above, and a table of how often past draws had 0-6
  such numbers next to what a fair draw gives (added 2026-09-19, F-19).
- It does not change your chance of winning - every line is equally likely. Numbers 1-31 are
  the birthday range many players use, so a line built mostly from them is more likely to share a
  prize. Use it to decide how your own line should look.

### ⚠️ Automated Anomaly Detection

**11 real-time checks:**

**Critical Alerts (🚨):**
- Extreme sum deviation (>3 standard deviations)
- All odd or all even numbers
- All numbers from one HMC category
- All numbers in ≤2 ranges
- 4+ consecutive numbers
- Exact duplicate of recent draw

**Warning Alerts (⚠️):**
- Unusual sum (>2.5σ)
- Severe odd/even imbalance (5-1 or 1-5)
- 5 numbers from one HMC category
- 4+ numbers in single range
- 4+ cooling down numbers
- All numbers in ≤2 decades

**Info Alerts (ℹ️):**
- 4+ highly volatile numbers

### 🏆 Overall Validation Score

**Grading:**
- **A+ (90-100):** Excellent - play with confidence
- **A (80-89):** Good - minor adjustments optional
- **B (70-79):** Fair - consider regenerating
- **C (60-69):** Moderate - improvements recommended
- **D (<60):** Poor - definitely regenerate

**Recommendations:** Specific suggestions if score < 80

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

**How to interpret:**
- **High volatility + Trending Up + Heating Up:** Strong pick (momentum play)
- **Low volatility + Stable trend:** Predictable, safe pick
- **Regime Shift = Yes:** Number changing behavior - opportunity or risk

### ⏱️ Recent Activity

Shows appearances in last 4, 5, 9, and 24 draws with freshness classification.

### 🎁 Bonus Number Analysis

- **Bonus Appearances:** Times appeared as bonus
- **Bonus→Main Rate:** Probability of transitioning
- **Avg Draws to Transit:** Typical waiting period
- **Last Bonus:** Date and days since

**Transition candidate status:** If rate > 65% and days < 150, it's a strong candidate.

### 📏 Gap Analysis

**What it shows:** Time between appearances

- **Min Gap:** Shortest time between appearances
- **Max Gap:** Longest time between appearances
- **Avg Gap:** Typical waiting time
- **Current Gap:** Days since last appearance

**Overdue Detection:**
- If current gap > 1.5× average: ⚠️ OVERDUE (strong pick)
- If current gap < 0.5× average: Recently appeared (avoid)

### 🔗 Trigger Series Patterns

Shows historical hot streaks:
- **Pattern:** E.g., "5 Consecutives 2 Times" (appeared 2 times within 5 draws)
- **Start/End Dates:** When the streak occurred
- **Count:** Number of appearances in that period

**How to use:** If number has recent trigger series, it may be entering another hot streak.

### 📅 Appearance History

Last 20 appearances with:
- **Date:** When it appeared
- **Type:** Main or Bonus
- **Gap:** Days since previous appearance

### 💡 Recommendation (0-100 Score)

**Factors considered:**
- Trend direction (+20 for significant uptrend)
- Momentum (+15 for heating up)
- Regime shift (+10 for positive shift)
- Overdue status (+25 for >1.5× average gap)
- Bonus transition (+15 for strong candidate)
- Freshness (+5 for C0)

**Assessment:**
- **75-100:** 🌟 STRONG PICK
- **60-74:** 👍 GOOD PICK
- **40-59:** ⚖️ NEUTRAL
- **0-39:** ⛔ AVOID

**Positive & Caution Indicators:** Specific reasons for the score.

---

## 7. Pattern Comparison

**Purpose:** Compare your prediction against historical winning patterns.

### 🎯 Input Section

Enter your 6 numbers to analyze.

### 📊 Your Prediction Pattern

Displays:
- **HMC Pattern:** e.g., 3H-2M-1C
- **Odd/Even:** e.g., 3 Odd / 3 Even
- **Sum:** Total value (validated against realistic range)
- **Consecutive:** Whether you have consecutive numbers
- **Range Distribution:** Count in each range (1-10, 11-20, etc.)

### 🔍 Similar Historical Draws

**Similarity Algorithm (weighted):**
- HMC pattern similarity: 30%
- Odd/Even similarity: 20%
- Sum proximity: 25%
- Range distribution: 15%
- Consecutive numbers: 10%

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

### 💡 Pattern Assessment (0-100 Score)

**Scoring factors:**
- HMC pattern frequency (25 points if ≥5%, 15 if ≥2%, 5 if >0%)
- Odd/Even frequency (25 points if ≥10%, 15 if ≥5%)
- Sum within realistic range (20 points)
- High similarity to past winners (20 points if ≥80%, 10 if ≥60%)
- Good range distribution (10 points)

**Assessment levels:**
- **75-100:** 🌟 STRONG PATTERN (excellent historical precedent)
- **50-74:** 👍 GOOD PATTERN (reasonable alignment)
- **25-49:** ⚖️ MODERATE PATTERN (some concerns)
- **0-24:** ⛔ WEAK PATTERN (limited precedent)

**Pattern Strengths & Considerations:** Specific feedback on your pattern.

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

**Strategy implications:**
- **C0 numbers:** Lower short-term probability but potentially "due"
- **C1 numbers:** Balanced - proven recent activity without saturation
- **C≥2 numbers:** Hot streak - high recent activity

**Historical finding:** Balanced selections (mix of C0, C1, C2) perform better than extremes.

### Volatility

**Definition:** Consistency of appearance patterns over time.

**How it's measured:**
- Standard deviation of gap times between appearances
- Normalized against mean gap time

**Interpretation:**
- **Low (<0.85):** Predictable, consistent timing
- **Medium (0.85-1.15):** Moderate predictability
- **High (≥1.15):** Erratic, unpredictable

**Strategy:**
- **Risk-averse:** Focus on low volatility (predictable)
- **Risk-tolerant:** Include high volatility (potential surprises)

### Trend

**Definition:** Long-term statistical direction of appearance frequency.

**How it's calculated:**
- Linear regression on appearance counts over time
- Statistical significance tested (p < 0.05 required)

**Types:**
- **↑ Trending Up:** Increasing frequency (significant)
- **→ Stable:** No significant trend
- **↓ Trending Down:** Decreasing frequency (significant)

**Difference from Momentum:**
- **Trend:** Long-term statistical direction
- **Momentum:** Short-term recent burst

**Strategy:**
- **Momentum play:** Ride trending up numbers
- **Mean reversion:** Bet on trending down numbers bouncing back

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
- **Yes:** Number entering new behavioral phase
  - Cold → Hot transition (opportunity)
  - Hot → Cold transition (caution)
- **No:** Predictable, stable behavior continuing

**Strategy:** Regime shift numbers can signal:
- Start of hot streak (good entry point)
- End of hot streak (exit signal)

### Bonus-to-Main Transition

**Key Finding:** 74.25% of bonus numbers appear in main draw within 10 draws.

**How it works:**
1. Number appears as **bonus** in draw N
2. Track next 10 draws
3. If appears in **main 6** within those 10 draws → transition occurred

**Transition Rate:**
- Per-number statistic
- Example: Number 46 has 69.2% transition rate
- Only includes numbers with rate > 65% and days since < 150

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
5. **If score < 80:** Regenerate or manually adjust

**Step 3: Deep Analysis (Optional)**

a) **Check Pattern Match:**
   - Go to **Pattern Comparison**
   - Enter your 6 numbers
   - Review similarity to historical winners
   - **Target:** >60% similarity to top matches

b) **Review Individual Numbers:**
   - Go to **Number Insights**
   - Analyze each of your 6 numbers
   - Check for overdue numbers (strong picks)
   - Verify momentum and trends

c) **Verify HMC Balance:**
   - Go to **Statistics**
   - Use 6-Ball HMC Pattern Analyzer
   - Ensure your pattern is in top 10

d) **Check Freshness:**
   - Go to **Freshness Analysis**
   - Verify balanced C0/C1/C2 distribution
   - Avoid all C0 or all C≥2

**Step 4: Review Transition Candidates**
- Go to **Draw History**
- Check **Bonus-to-Main Transition Candidates**
- **Ensure 1-2 candidates are in your selection**

**Step 5: Filter & Refine**
- Go to **Trigger Periods Analysis**
- Apply filters for your selection criteria:
  - Volatility: Low or Medium (safer)
  - Trend: Trending Up (momentum play)
  - Freshness: Mix of C0 and C1
- Use Sum/Range validation at bottom

**Step 6: Final Decision**
- If validation score ≥ 80 and no critical anomalies → **Play**
- If score < 80 → Adjust or regenerate

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

### Selection Strategy Tips

**1. Balanced HMC Distribution**
- ✅ **Good:** 3H-2M-1C, 3H-3M-0C, 4H-1M-1C
- ❌ **Avoid:** 6H-0M-0C, 0H-0M-6C (extreme concentrations)
- **Why:** Historical data shows balanced selections perform better

**2. Optimal Odd/Even Ratio**
- ✅ **Target:** 2-4 odd numbers (covers 90%+ of historical draws)
- ⚠️ **Risky:** 1 or 5 odd (~5% of draws)
- ❌ **Avoid:** 0 or 6 odd (<0.5% of draws)

**3. Sum Validation**
- ✅ **Target:** 84-206 (realistic range)
- **Sweet spot:** 120-170 (highest concentration)
- ❌ **Avoid:** <84 or >206 (outside 95% confidence interval)

**4. Range Spread**
- ✅ **Good:** At least 4 of 5 ranges covered
- ✅ **Good:** Max 3 numbers per range
- ❌ **Avoid:** All numbers in 1-2 ranges
- ❌ **Avoid:** 4+ numbers in single range

**5. Freshness Balance**
- ✅ **Recommended:** Mix of C0 and C1 (e.g., 3×C0, 2×C1, 1×C2)
- ⚠️ **Risky:** All C0 (completely fresh)
- ⚠️ **Risky:** All C≥2 (over-saturated)

**6. Include Transition Candidates**
- ✅ **Strategy:** Include 1-2 bonus-to-main transition candidates
- **Success rate:** 74.25% transition within 10 draws
- **How to find:** Draw History page → Transition Candidates section

**7. Volatility Mix**
- ✅ **Conservative:** Mostly low volatility (4-5 low, 1-2 medium)
- ✅ **Balanced:** Mix of low and medium (3 low, 2 medium, 1 high)
- ⚠️ **Aggressive:** Include high volatility for surprise wins

**8. Momentum Strategy**
- **Momentum play:** Select mostly 🔥 Heating Up numbers (ride the wave)
- **Contrarian play:** Select ❄️ Cooling Down numbers (expecting bounce)
- **Balanced:** Mix of both

### Analysis Tips

**Using Filters Effectively:**
1. **Start broad, narrow down:**
   - Begin with "All" filters
   - Apply one filter at a time
   - Observe how pool changes

2. **Combine complementary filters:**
   - ✅ Hot + C1 + Trending Up = Strong momentum plays
   - ✅ Cold + C0 + Cooling Down = Contrarian value picks
   - ✅ Medium + C1 + Stable = Safe, predictable picks

3. **Use copyable lists:**
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

**Pattern Validation:**
1. **Always validate sum:** Quick check for realism
2. **Check pattern frequency:** Compare to Statistics page
3. **Review similar draws:** Pattern Comparison page
4. **Verify no critical anomalies:** Prediction Validator

### Common Mistakes to Avoid

❌ **Mistake 1: All hot numbers**
- **Why it's bad:** Lack of diversity, over-correlation
- **Fix:** Include 1-2 medium or cold numbers

❌ **Mistake 2: Ignoring transition candidates**
- **Why it's bad:** Miss 74% probability boost
- **Fix:** Always include 1-2 transition candidates

❌ **Mistake 3: Extreme odd/even ratios**
- **Why it's bad:** <6% of historical draws
- **Fix:** Stick to 2-4 odd numbers

❌ **Mistake 4: Consecutive number overload**
- **Why it's bad:** 4+ consecutive is extremely rare
- **Fix:** Maximum 2-3 consecutive numbers

❌ **Mistake 5: Ignoring sum validation**
- **Why it's bad:** Unrealistic sums have near-zero probability
- **Fix:** Always keep sum between 84-206

❌ **Mistake 6: Playing without validation**
- **Why it's bad:** May have critical anomalies
- **Fix:** Always run Prediction Validator first

❌ **Mistake 7: Not tracking performance**
- **Why it's bad:** Can't improve model without feedback
- **Fix:** Use Post Draw Analysis after every draw

❌ **Mistake 8: Over-fitting to recent data**
- **Why it's bad:** Patterns change, recent ≠ future
- **Fix:** Balance recent trends with historical statistics

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

### Validation score unexpectedly low
**Check:**
1. Sum is within 84-206
2. Odd/even ratio is 2-4
3. Not all same HMC category
4. Numbers spread across ranges
5. No critical anomalies

### Model 4 accuracy below 20%
**Possible causes:**
1. Model needs retraining with recent data
2. Too many predictions (reduce count)
3. Ignoring transition candidates
4. Over-emphasis on single strategy (e.g., all hot)

**Solutions:**
1. Review Post Draw Analysis recommendations
2. Reduce prediction count to 15-20
3. Always include 1-2 transition candidates
4. Balance HMC categories

### Transition candidates don't match last 10 bonus
**Cause:** This is actually correct behavior!
- **Last 10 Bonus:** Simple historical record
- **Transition Candidates:** Predictive analysis with filters

**Requirements for transition candidate:**
- Transition rate > 65% (from ALL historical bonus appearances)
- Days since last bonus < 150 days

**Note:** After recent fix, overlap should be much higher (6-8 of 10).

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
- [ ] Validation score ≥ 80?
- [ ] No critical anomalies?
- [ ] Sum between 84-206?
- [ ] 2-4 odd numbers?
- [ ] Include 1-2 transition candidates?
- [ ] HMC pattern in top 10?

### Post-Draw Checklist
- [ ] Enter actual results in Post Draw Analysis
- [ ] Review accuracy (target: ≥33%)
- [ ] Check correct predictions characteristics
- [ ] Analyze missed numbers patterns
- [ ] Apply recommendations
- [ ] Document learnings

### Optimal Selection Profile
- **HMC:** 3H-2M-1C or 3H-3M-0C
- **Odd/Even:** 2-4 odd numbers
- **Sum:** 120-170 (sweet spot)
- **Freshness:** Mix of C0 and C1
- **Ranges:** 4-5 ranges covered, max 3 per range
- **Transition:** 1-2 candidates included
- **Volatility:** Mostly low/medium
- **Validation:** Score ≥ 80

---

**End of User Manual**

For questions or issues, review the Troubleshooting section or consult the specific page documentation above.

Good luck with your predictions! 🍀
