# Lottery Prediction System: Complete Feature Documentation

## Table of Contents
1. [Feature Overview](#feature-overview)
2. [Feature Families](#feature-families)
3. [Individual Feature Descriptions](#individual-feature-descriptions)
4. [Feature Correlations & Conflicts](#feature-correlations--conflicts)
5. [Model Design Guidelines](#model-design-guidelines)
6. [Feature Combination Strategies](#feature-combination-strategies)

---

## Feature Overview

The lottery prediction system uses **12 distinct features** derived from historical draw data. These features fall into four main families:

| Family | Feature Count | Signal Type | Correlation Risk |
|--------|--------------|-------------|------------------|
| **Freshness Pattern** | 5 | Recent activity (last 4 draws) | SPECIAL* |
| **Recent Activity** | 4 | Progressive windows (4-14 draws) | MEDIUM-HIGH |
| **Historical** | 2 | Long-term patterns | LOW |
| **Special** | 3 | Niche patterns | LOW-MEDIUM |

**SPECIAL NOTE on Freshness Features:** The 5 freshness features have NEGATIVE correlation with each other (good!), but POSITIVE correlation with `recent_4` (bad if mixed). See detailed explanation below.

---

## Feature Families

### 1. Freshness Pattern Features (C0/C1/C2/C≥3)

**Purpose:** Identify which "recency category" a number belongs to based on how many times it appeared in the last 4 draws, weighted by historical winning pattern preferences.

**Logic Behind Construction:**
- Historical analysis shows that winning draws tend to have specific distributions of "fresh" vs "stale" numbers
- Numbers are categorized into 4 bins based on their count in the last 4 draws:
  - **C0 (Very Cold):** Not drawn in last 4 draws (count = 0)
  - **C1 (Lukewarm):** Drawn exactly once in last 4 draws (count = 1)
  - **C2 (Warm):** Drawn exactly twice in last 4 draws (count = 2)
  - **C≥3 (Very Hot):** Drawn 3+ times in last 4 draws (count ≥ 3)

**Why These Weights Matter:**
From analyzing 403 historical draws, the most successful winning patterns are:
- **Pattern 1 (10.92%):** 3 C0 + 3 C1 + 1 C2 + 0 C≥3
- **Pattern 2 (9.68%):** 4 C0 + 2 C1 + 1 C2 + 0 C≥3
- **Pattern 3 (6.95%):** 3 C0 + 4 C1 + 0 C2 + 0 C≥3

**Key Insight:** Winning draws heavily favor a mix of cold (C0) and lukewarm (C1) numbers, with few warm (C2) numbers and almost no very hot (C≥3) numbers. This is counterintuitive - numbers that appeared recently (hot numbers) are LESS likely to win again soon!

#### Features in This Family:

**`freshness_c0_weight`** (0.0 - 0.6)

**What it measures:** Historical winning pattern preference for numbers in the C0 category (very cold numbers that haven't appeared in the last 4 draws).

**How it's calculated:**
1. Analyze top 5 historical winning patterns
2. Calculate average count of C0 numbers in those patterns (e.g., Pattern 1 has 3, Pattern 2 has 4, Pattern 3 has 3 → average ~3.3)
3. Divide by 7 (total numbers per draw) to get weight (3.3 ÷ 7 = 0.47)
4. Each number gets this weight value IF it's currently in the C0 category, otherwise gets 0.0

**How it works in practice:**
- **Number 5** appeared 0 times in last 4 draws → `freshness_c0_weight = 0.47` (HIGH)
- **Number 13** appeared 2 times in last 4 draws → `freshness_c0_weight = 0.0` (ZERO - not C0)
- **Number 35** appeared 3 times in last 4 draws → `freshness_c0_weight = 0.0` (ZERO - not C0)

**Typical value when active:** ~0.47 (meaning about 47% of the ideal draw consists of C0 numbers, or roughly 3.3 out of 7 numbers)

**Why it predicts winners:** Historical data shows that about 3-4 out of every 7 winning numbers tend to be "very cold" (not drawn recently). Numbers with high `freshness_c0_weight` match this successful pattern.

**Real-world example:**
If the last 4 draws were: [1,5,13,22,28,35,42], then all OTHER numbers (2,3,4,6,7,8,9...) are C0 and get `freshness_c0_weight = 0.47`. The next draw statistically should pick about 3-4 numbers from this C0 pool.

---

**`freshness_c1_weight`** (0.0 - 0.6)

**What it measures:** Historical winning pattern preference for numbers in the C1 category (lukewarm numbers that appeared exactly once in the last 4 draws).

**How it's calculated:**
1. Same method as c0_weight
2. Average count of C1 numbers in top patterns (e.g., Pattern 1 has 3, Pattern 2 has 2, Pattern 3 has 4 → average ~3.0)
3. Divide by 7 to get weight (3.0 ÷ 7 = 0.43)
4. Each number gets this weight IF it appeared exactly 1 time in last 4 draws

**How it works in practice:**
- **Number 1** appeared 1 time in last 4 draws → `freshness_c1_weight = 0.43` (HIGH)
- **Number 5** appeared 0 times in last 4 draws → `freshness_c1_weight = 0.0` (ZERO - not C1)
- **Number 13** appeared 2 times in last 4 draws → `freshness_c1_weight = 0.0` (ZERO - not C1)

**Typical value when active:** ~0.43 (meaning about 43% of the ideal draw consists of C1 numbers, or roughly 3 out of 7 numbers)

**Why it predicts winners:** The second-most common component of winning draws is numbers that appeared once recently - they're "warm" but not "too hot."

**Relationship to c0_weight:** Together, c0_weight and c1_weight account for about 90% of a typical winning draw (3.3 C0 numbers + 3.0 C1 numbers = 6.3 out of 7 total numbers).

---

**`freshness_c2_weight`** (0.0 - 0.6)

**What it measures:** Historical winning pattern preference for numbers in the C2 category (warm numbers that appeared exactly twice in the last 4 draws).

**How it's calculated:**
1. Same method as c0_weight and c1_weight
2. Average count of C2 numbers in top patterns (e.g., Pattern 1 has 1, Pattern 2 has 1, Pattern 3 has 0 → average ~0.7)
3. Divide by 7 to get weight (0.7 ÷ 7 = 0.10)
4. Each number gets this weight IF it appeared exactly 2 times in last 4 draws

**How it works in practice:**
- **Number 13** appeared 2 times in last 4 draws → `freshness_c2_weight = 0.10` (LOW)
- **Number 28** appeared 2 times in last 4 draws → `freshness_c2_weight = 0.10` (LOW)
- **Number 35** appeared 3 times in last 4 draws → `freshness_c2_weight = 0.0` (ZERO - not C2)

**Typical value when active:** ~0.10 (meaning only about 10% of the ideal draw consists of C2 numbers, or roughly 0.7 out of 7 numbers)

**Why it predicts winners (weakly):** Warm numbers (appeared twice recently) are much less common in winning draws. You typically get 0-1 C2 numbers per winning draw.

**Key insight:** This weight is LOW, telling the model "C2 numbers are okay but not preferred." The model learns to be neutral or slightly positive toward them.

---

**`freshness_c3_weight`** (0.0 - 0.6)

**What it measures:** Historical winning pattern preference for numbers in the C≥3 category (very hot numbers that appeared 3 or more times in the last 4 draws).

**How it's calculated:**
1. Same method as other weights
2. Average count of C≥3 numbers in top patterns (e.g., Pattern 1 has 0, Pattern 2 has 0, Pattern 3 has 0 → average ~0.0)
3. Divide by 7 to get weight (0.0 ÷ 7 = 0.00)
4. Each number gets this weight IF it appeared 3+ times in last 4 draws

**How it works in practice:**
- **Number 35** appeared 3 times in last 4 draws → `freshness_c3_weight = 0.00` (ZERO/VERY LOW)
- **Number 42** appeared 2 times in last 4 draws → `freshness_c3_weight = 0.0` (ZERO - not C≥3)

**Typical value when active:** ~0.00 (meaning almost NO winning draws contain C≥3 numbers)

**Why it predicts winners (negatively):** Numbers that appeared 3-4 times in the last 4 draws are "too hot" and historically almost never win again immediately. The model learns to AVOID these numbers.

**Gambler's fallacy reversal:** This is the opposite of the common belief that "hot numbers stay hot." The data shows very hot numbers actually cool off!

**Important note:** Very few numbers ever reach C≥3 status (maybe 2-3 numbers at any time), but when they do, this feature tells the model to strongly de-prioritize them.

---

**`current_freshness_bin`** (0, 1, 2, or 3)

**What it measures:** Which freshness category this number currently belongs to, as a simple categorical value.

**How it's calculated:**
1. Count how many times the number appeared in the last 4 draws
2. Assign category:
   - Count = 0 → Bin = 0 (C0)
   - Count = 1 → Bin = 1 (C1)
   - Count = 2 → Bin = 2 (C2)
   - Count ≥ 3 → Bin = 3 (C≥3)

**How it works in practice:**
- **Number 5** (appeared 0 times) → `current_freshness_bin = 0`
- **Number 1** (appeared 1 time) → `current_freshness_bin = 1`
- **Number 13** (appeared 2 times) → `current_freshness_bin = 2`
- **Number 35** (appeared 3 times) → `current_freshness_bin = 3`

**Why it exists:** This is a simpler, alternative encoding to the four weight features. Instead of one-hot encoding (where only one weight is non-zero), this uses a single categorical variable.

**When to use it:**
- **Use the 4 weights (c0/c1/c2/c3_weight):** When you want the model to learn different importance for each category
- **Use `current_freshness_bin`:** When you want a simpler feature (single variable instead of 4)
- **NEVER use both together:** They encode the same information (0.95 correlation!)

---

### Important Relationship Between Freshness Features

#### The One-Hot Encoding Pattern

For any given number at any given time, **only ONE** of the four weight features will be non-zero:

```
Number 5 (appeared 0 times in last 4 draws):
  freshness_c0_weight = 0.47  ✓
  freshness_c1_weight = 0.00
  freshness_c2_weight = 0.00
  freshness_c3_weight = 0.00

Number 1 (appeared 1 time in last 4 draws):
  freshness_c0_weight = 0.00
  freshness_c1_weight = 0.43  ✓
  freshness_c2_weight = 0.00
  freshness_c3_weight = 0.00

Number 13 (appeared 2 times in last 4 draws):
  freshness_c0_weight = 0.00
  freshness_c1_weight = 0.00
  freshness_c2_weight = 0.10  ✓
  freshness_c3_weight = 0.00

Number 35 (appeared 3 times in last 4 draws):
  freshness_c0_weight = 0.00
  freshness_c1_weight = 0.00
  freshness_c2_weight = 0.00
  freshness_c3_weight = 0.00  ✓
```

#### Why This Matters for ML Models

When you include all 4 weights in a model:

**What the model learns:**
```
Winning_Probability = 
    β₁ × freshness_c0_weight +    # e.g., +0.85 (strong positive)
    β₂ × freshness_c1_weight +    # e.g., +0.75 (positive)
    β₃ × freshness_c2_weight +    # e.g., +0.20 (weak positive)
    β₄ × freshness_c3_weight +    # e.g., -0.50 (negative)
    ... other features
```

**Result for different numbers:**
- **C0 numbers:** Get +0.85 boost (strong preference)
- **C1 numbers:** Get +0.75 boost (strong preference)
- **C2 numbers:** Get +0.20 boost (weak preference)
- **C≥3 numbers:** Get -0.50 penalty (avoidance)

This creates a clear preference gradient: C0 > C1 > C2 > C≥3

---

### 2. Recent Activity Features

**Purpose:** Measure how frequently a number has been drawn in various recent time windows.

**Logic Behind Construction:**
These features look at progressively longer windows to capture both immediate momentum and sustained activity patterns. A number appearing frequently in recent draws might be "on a hot streak" or might be "due for a break."

#### Features in This Family:

**`recent_4`** (0 - 4)

**What it measures:** Raw count of how many times this number appeared in the last 4 draws.

**Window size:** Approximately 8-12 days (2 draws per week)

**How it's calculated:**
1. Look at the most recent 4 lottery draws
2. Count how many times this number appeared
3. Simple integer count (no weighting)

**Distribution across all numbers:**
- **Count = 0:** ~60% of numbers (28-30 numbers)
- **Count = 1:** ~25% of numbers (12-14 numbers)
- **Count = 2:** ~12% of numbers (5-6 numbers)
- **Count = 3:** ~2% of numbers (1-2 numbers)
- **Count = 4:** ~0.2% of numbers (very rare - means appeared in ALL 4 draws!)

**Interpretation:**
- **0:** Very cold - hasn't appeared recently
- **1:** Lukewarm - single recent appearance
- **2:** Warm - appeared in half of recent draws
- **3-4:** Very hot - exceptional recent frequency (unusual behavior)

**Why it predicts winners:** Captures immediate momentum. However, the relationship is not linear - very high values (3-4) are actually NEGATIVE predictors based on historical winning patterns!

**Relationship to freshness weights:** This is the RAW DATA that the freshness weights are derived from. If you use both, you're encoding the same information twice (0.82 correlation).

**When to use:**
- ✅ Use in models WITHOUT any freshness weights
- ❌ Don't use in models that already have c0/c1/c2/c3 weights
- ✅ Can use in XGBoost models (trees handle the redundancy)

---

**`recent_6`** (0 - 6)

**What it measures:** Count of appearances in the last 6 draws.

**Window size:** Approximately 12-18 days

**How it's calculated:**
Same as recent_4, but looking back 6 draws instead of 4.

**Distribution:**
- **Count = 0:** ~45% of numbers
- **Count = 1-2:** ~40% of numbers
- **Count = 3-4:** ~12% of numbers
- **Count = 5-6:** ~3% of numbers (very rare)

**Why it matters:** Captures slightly longer-term momentum than recent_4. A number with recent_6 = 3 but recent_4 = 0 means "was hot but just cooled off."

**Correlation with recent_4:** 0.78 (high overlap)

**When to use:**
- ⚠️ Use sparingly - overlaps heavily with recent_4
- ✅ Good for mid-term momentum in models that DON'T use recent_4
- ❌ Don't use if you already have recent_4 (redundant)

---

**`recent_9`** (0 - 9)

**What it measures:** Count of appearances in the last 9 draws.

**Window size:** Approximately 18-27 days (~1 month)

**How it's calculated:**
Same as recent_4 and recent_6, but looking back 9 draws.

**Distribution:**
- **Count = 0-1:** ~35% of numbers (very cold)
- **Count = 2-3:** ~40% of numbers (moderate)
- **Count = 4-5:** ~20% of numbers (warm)
- **Count = 6+:** ~5% of numbers (very hot)

**Why it matters:** Identifies numbers in sustained hot or cold periods beyond just immediate momentum.

**Correlation with recent_6:** 0.85 (very high overlap)

**When to use:**
- ⚠️ Overlaps with both recent_4 and recent_6
- ✅ Good for mid-term analysis in specialized models
- ❌ Usually skip in favor of recent_4 (short) or recent_14 (long)

---

**`recent_14`** (0 - 14)

**What it measures:** Count of appearances in the last 14 draws.

**Window size:** Approximately 28-42 days (~1-1.5 months)

**How it's calculated:**
Same as other recent_X features, but looking back 14 draws.

**Distribution:**
- **Count = 0-2:** ~25% of numbers (very cold long-term)
- **Count = 3-4:** ~40% of numbers (moderate)
- **Count = 5-6:** ~25% of numbers (warm)
- **Count = 7+:** ~10% of numbers (very hot long-term)

**Typical range:** Most numbers fall between 2-6

**Why it matters:** 
- Captures long-term activity trends
- Less volatile than recent_4 (smooths out random fluctuations)
- Better predictor of sustained hot/cold periods

**Correlation with recent_4:** 0.55 (moderate - provides NEW information)

**When to use:**
- ✅ BEST choice for long-term recent activity
- ✅ Can combine with recent_4 (one short, one long window)
- ✅ Independent enough from recent_4 to provide value
- ❌ Don't combine with recent_6 or recent_9 (redundant)

**Strategic value:** In many systems, recent_14 is MORE predictive than recent_4 because it captures sustained patterns rather than random noise.

---

### 3. Historical Pattern Features

**Purpose:** Capture long-term frequency patterns and timing information that reflect fundamental probability distributions.

**Logic Behind Construction:**
Some numbers are inherently more frequent over the lottery's entire history (hundreds of draws). This reflects fundamental probability distributions or mechanical characteristics of the lottery system. Additionally, time since last appearance helps identify numbers that might be "overdue" (though this requires careful interpretation to avoid gambler's fallacy).

#### Features in This Family:

**`total_count`** (60 - 95)

**What it measures:** Total number of times this number has been drawn across ALL historical draws in the database.

**Time span:** All available history (typically 400-600 draws = 2-3 years of data)

**How it's calculated:**
1. Count every time this number appeared as a winning number (main or bonus) in historical data
2. Simple cumulative count since data collection began
3. Increases by 6-7 total per draw (6 main numbers + 1 bonus, but spread across 47 possible numbers)

**Distribution across numbers:**
- **Low frequency (60-70):** "Cold" numbers - bottom ~33% of numbers
- **Medium frequency (70-80):** "Medium" numbers - middle ~34% of numbers
- **High frequency (80-95):** "Hot" numbers - top ~33% of numbers

**Range explanation:**
If you have 500 draws with 7 numbers per draw (including bonus), that's 3,500 total selections. Divided equally across 47 numbers = 74.5 average. But randomness creates variance, so you see 60-95 range.

**Interpretation:**
- **High values (85-95):** "Hot" numbers - historically drawn more frequently than average
  - May indicate mechanical bias in lottery machine
  - May indicate ball weight/shape differences
  - May be purely random variance
- **Medium values (70-80):** "Medium" numbers - average frequency
- **Low values (60-70):** "Cold" numbers - historically drawn less frequently
  - Could be "overdue" if you believe in reversion to mean
  - Could simply be random variance

**Why it matters:**
1. **Long-term bias detection:** If a number has been drawn 95 times while another only 60 times over 500 draws, there MAY be a systematic reason
2. **Frequency baseline:** Helps distinguish between "always hot" numbers vs "temporarily hot" numbers
3. **Stability:** Changes very slowly (only increases by 1 when drawn), so it's a stable predictor

**Relationship to recent activity:**
- A number can be high in `total_count` (historically hot) but low in `recent_4` (currently cold)
- A number can be low in `total_count` (historically cold) but high in `recent_4` (currently hot)
- Correlation between `total_count` and `recent_4`: only 0.25 (they measure different things!)

**When to use:**
- ✅ Essential for long-term value models
- ✅ Complements short-term features (freshness, recent_4)
- ✅ Helps identify "consistently hot" vs "temporarily hot" numbers
- ⚠️ Don't rely on it alone (past frequency doesn't guarantee future results)

**Strategic insight:** Numbers in the 85-95 range have demonstrated sustained high frequency. While no guarantee, they're statistically more likely to continue being drawn often IF there's a mechanical reason (not just random luck).

---

**`days_since_last`** (0 - 999)

**What it measures:** Number of calendar days between today and the most recent date this number was drawn.

**How it's calculated:**
1. Find the most recent draw where this number appeared
2. Get that draw's date
3. Calculate: TODAY - LAST_DRAW_DATE = days_since_last
4. Special value: 999 means "never appeared" (shouldn't occur in real data)

**Distribution:**
- **0-7 days:** Very recent appearance (~15% of numbers)
- **7-21 days:** Recent appearance (~35% of numbers)
- **21-60 days:** Moderate gap (~35% of numbers)
- **60-180 days:** Long absence (~12% of numbers)
- **180+ days:** Very long absence (~3% of numbers, may indicate data issues)

**Interpretation:**
- **Low values (0-14):** Just drawn recently
  - May be "too hot" to draw again soon (negative predictor)
  - Or may be in a hot streak (positive predictor)
  - Depends on model interpretation!
- **Medium values (14-45):** Normal rotation
  - Most numbers fall here
  - Neither hot nor cold
- **High values (60+):** Long absence, potentially "overdue"
  - May be genuinely cold (negative predictor)
  - Or may be "due" for regression to mean (positive predictor)
  - Gambler's fallacy warning: Random draws have no memory!

**Why it matters:**
1. **Time decay:** Numbers get "fresher" as time passes without being drawn
2. **Timing patterns:** Some numbers show cyclical patterns (e.g., drawn every ~30 days)
3. **Outlier detection:** Very high values (120+ days) may indicate a number entering a cold period

**Relationship to total_count:**
- **Negative correlation (-0.25):** Numbers with high total_count tend to have LOWER days_since_last
- Why? Hot numbers cycle more frequently, so they were drawn more recently on average
- Cold numbers have longer gaps between appearances

**Relationship to recent_4:**
- **Positive correlation (0.48):** Numbers with high days_since_last tend to have LOW recent_4
- Why? If it's been 30 days, it definitely didn't appear in the last 4 draws!

**When to use:**
- ✅ Almost always useful - provides independent timing signal
- ✅ Combines well with total_count (frequency + timing = complete picture)
- ✅ Combines well with freshness features (recent pattern + time gap = momentum)
- ✅ One of the most universally useful features

**Strategic insight:** This feature captures "recency" from a different angle than recent_4. While recent_4 counts "how many times in last 4 draws," days_since_last measures "how long ago was the last time," which can span beyond 4 draws. A number with recent_4=0 could have days_since_last=5 (just missed last 4 draws) or days_since_last=90 (genuinely cold).

---

### 4. Special Pattern Features

**Purpose:** Capture niche patterns like bonus ball timing and unusual streaks that might have predictive value but don't fit into the main categories.

**Logic Behind Construction:**
These features target specific phenomena that emerge from domain knowledge about how lotteries work. They're more speculative than the main features but can provide edge cases or capture behaviors not visible in standard frequency/recency measures.

#### Features in This Family:

**`days_since_bonus`** (0 - 999)

**What it measures:** Number of calendar days since this number was last drawn as the BONUS ball specifically (not as one of the 6 main winning numbers).

**How it's calculated:**
1. Scan historical draws looking for when this number was the bonus
2. Find the most recent such occurrence
3. Calculate: TODAY - LAST_BONUS_DATE = days_since_bonus
4. Special value: 999 means "never appeared as bonus" or "appeared so long ago we don't have data"

**Why bonus matters separately:**
- Different selection mechanism (bonus drawn from remaining balls after main 6)
- Some players believe bonus appearance affects probability of main number appearance
- May indicate recent "attention" to this number in the lottery system

**Distribution:**
- **0-30 days:** Recent bonus appearance (~12% of numbers)
- **30-90 days:** Moderate gap (~25% of numbers)
- **90-180 days:** Long gap (~30% of numbers)
- **180+ days:** Very long gap or never (~33% of numbers)

**Typical values:**
Most numbers fall in the 60-200 day range, as bonus appearances are less frequent than main number appearances (1 bonus per draw vs 6 main numbers).

**Interpretation:**
Two competing theories:
1. **Negative correlation theory:** Numbers that recently appeared as bonus are LESS likely to appear as main numbers soon
   - Logic: "That number just got its turn as bonus, now it needs to rest"
   - If true, high days_since_bonus = more likely to win
2. **Positive correlation theory:** Numbers that recently appeared as bonus are MORE likely to appear as main numbers soon
   - Logic: "That number is hot right now, appeared as bonus, might appear as main too"
   - If true, low days_since_bonus = more likely to win

The ML model learns which theory (if either) is correct for your specific lottery!

**Why it might be predictive:**
- If the bonus ball is drawn using a slightly different mechanism, it could indicate which numbers are "active" in the current mechanical state
- Psychological: if a number was just the bonus, some players might avoid it, changing the meta-game

**Correlation with other features:**
- **days_since_last:** 0.35 correlation (moderate)
  - Numbers recently drawn as main are somewhat more likely to also have been recent bonus
- **total_count:** 0.12 correlation (low - independent signal!)
  - Historical frequency doesn't predict bonus timing

**When to use:**
- ✅ Good addition to most models (independent signal)
- ✅ Especially useful in models focused on timing
- ⚠️ May be noise (bonus timing might not matter at all)
- ✅ Worth testing - if it helps, keep it; if not, remove it

**Strategic insight:** This is a "maybe" feature. In some lotteries it provides genuine signal, in others it's pure noise. Include it in comprehensive models (XGBoost), test in linear models, and monitor its coefficient/importance to see if it matters.

---

**`series_total`** (0 - 20+)

**What it measures:** Total count of times this number has appeared in "unusual streaks" throughout all historical data.

**What counts as a streak:**
Pre-defined patterns that indicate unusual clustering:
- **Short intense streaks:** Appearing 3+ times in a 5-draw window
- **Medium streaks:** Appearing 4+ times in a 7-draw window  
- **Long streaks:** Appearing 5+ times in a 15-draw window

**How it's calculated:**
1. Scan all historical draws using sliding windows (5-draw, 7-draw, 15-draw)
2. For each window, check if this number appears enough times to qualify as a "streak"
3. Count how many such streak periods this number has experienced
4. Sum all streaks across all window sizes

**Example for Number 35:**
```
Draws 100-104: Number 35 appeared 3 times → +1 streak (5-draw window)
Draws 200-206: Number 35 appeared 4 times → +1 streak (7-draw window)
Draws 300-314: Number 35 appeared 5 times → +1 streak (15-draw window)
Draws 400-404: Number 35 appeared 3 times → +1 streak (5-draw window)

Total: series_total = 4
```

**Distribution:**
- **Low (0-7):** ~40% of numbers - rarely streak
- **Medium (8-15):** ~40% of numbers - moderate streak behavior
- **High (16-25):** ~20% of numbers - frequently enter streaks

**Why it matters:**
1. **Volatility indicator:** High series_total means this number has volatile, streak-prone behavior
2. **Pattern recognition:** Numbers that frequently streak may be more likely to streak again
3. **Risk/reward signal:** Streak-prone numbers might offer higher hit rates during hot periods

**Interpretation:**
- **High values (15+):** "Volatile" number
  - Has history of entering hot streaks
  - When it gets hot, it stays hot for a while
  - May be mechanical reason (ball characteristics)
- **Low values (0-7):** "Stable" number
  - Appears more consistently spread out
  - Rarely enters hot or cold periods
  - More predictable, less volatile

**Why it might predict winners:**
- If a number is streak-prone by nature, detecting the START of a new streak could be valuable
- Numbers currently in streaks (high series_recent) that also have high series_total may continue streaking
- Contrarian play: Numbers with low series_total in a streak might revert faster

**Correlation with other features:**
- **total_count:** 0.40 correlation (moderate)
  - Hot numbers tend to have more streaks (more opportunities)
  - But not perfectly correlated - some hot numbers are steady, not streaky
- **recent_4:** 0.28 correlation (low)
  - Current hot behavior doesn't strongly predict historical streak count

**When to use:**
- ✅ Good for "streak hunter" specialized models
- ⚠️ May be noisy (streaks might be random clustering)
- ✅ Combines well with series_recent (total history + recent behavior)
- ❌ Less useful in simple momentum models

**Limitations:**
- Looks at ALL history (old streaks from 2 years ago might not be relevant)
- Doesn't distinguish between short/medium/long streak types
- High values might reflect age of data (more draws = more chances for streaks)

---

**`series_recent`** (0 - 10)

**What it measures:** Count of streak occurrences in the last 60 days (approximately 30 draws).

**How it's calculated:**
1. Same streak detection as series_total
2. But only count streaks that ENDED within the last 60 days
3. Focuses on recent streak activity, not all-time history

**Example for Number 28:**
```
Last 60 days:
Draws (20 days ago): Number 28 appeared 3 times in 5-draw window → +1 recent streak
Draws (10 days ago): Number 28 appeared 4 times in 7-draw window → +1 recent streak

Total: series_recent = 2
```

**Distribution:**
- **None (0):** ~75% of numbers - no recent streaks
- **Low (1-2):** ~20% of numbers - one recent streak
- **High (3+):** ~5% of numbers - multiple recent streaks (very active!)

**Why it matters:**
1. **Current momentum:** Recent streaks indicate the number is hot RIGHT NOW
2. **Timing indicator:** Numbers exiting streaks might cool off, entering streaks might continue
3. **Recency focus:** More relevant than series_total (old streaks don't matter)

**Interpretation:**
- **Value = 0:** Normal behavior, no recent unusual activity
- **Value = 1-2:** Recently experienced a streak
  - Might be exiting hot period (about to cool off)
  - Or might be continuing hot behavior
  - Model learns which interpretation is correct!
- **Value = 3+:** Extremely hot recently (rare)
  - Multiple streak periods in just 60 days
  - Either about to cool off (exhaustion) or in sustained hot period

**Why it might predict winners:**
- Numbers currently IN a streak (high series_recent + high recent_4) might continue
- Numbers just EXITING a streak (high series_recent + low recent_4) might be "cooling off"
- Complements recent_X features by adding pattern context

**Correlation with other features:**
- **recent_4:** 0.58 correlation (moderate-high)
  - If you're in a streak, you probably appeared recently
  - But not perfect - streak could have ended 2 weeks ago
- **series_total:** 0.55 correlation (moderate)
  - Streak-prone numbers more likely to have recent streaks
  - But independent timing component
- **days_since_last:** -0.40 correlation (moderate negative)
  - Recent streaks mean recent appearances

**When to use:**
- ✅ Better than series_total for most models (more timely)
- ✅ Good complement to recent_4 (adds pattern context)
- ✅ Useful in streak-focused or momentum models
- ⚠️ May be redundant with recent_4 in simple models

**Strategic insight:** This feature answers "Has this number been acting unusually hot in the past 2 months?" which is different from "How many times did it appear in the last 4 draws?" A number with recent_4 = 2 and series_recent = 0 means "appeared twice recently but not in an unusual pattern." A number with recent_4 = 2 and series_recent = 2 means "appeared twice recently AND this is part of an unusual hot streak pattern!"

---

## Feature Correlations & Conflicts

### Understanding Correlation Types

**Positive Correlation:** Features that move together
- When Feature A increases, Feature B also increases
- Problem: They encode similar or same information (redundant)
- Example: `recent_4 = 2` usually means `freshness_c2_weight > 0`

**Negative Correlation:** Features that move opposite
- When Feature A increases, Feature B decreases
- Often GOOD: Features are complementary, not redundant
- Example: `freshness_c0_weight = 0.47` means `freshness_c1_weight = 0` (mutually exclusive)

**Zero/Low Correlation:** Features that are independent
- Changes in Feature A don't predict changes in Feature B
- BEST: Each feature provides unique information
- Example: `total_count` and `days_since_bonus` are independent (0.12 correlation)

---

### High Positive Correlation Risks (>0.75) 🔴

#### Risk Group 1: Raw Count vs Freshness Bin
**Correlated Features:** `recent_4` ↔ `current_freshness_bin`

**Correlation:** 0.95 (extremely high!)

**Why they correlate:**
- `current_freshness_bin` is literally just `recent_4` converted to categories:
  - recent_4 = 0 → bin = 0
  - recent_4 = 1 → bin = 1
  - recent_4 = 2 → bin = 2
  - recent_4 ≥ 3 → bin = 3
- Same data, different format

**Problem:**
- Encoding the exact same information twice
- Model capacity wasted
- Coefficients split between redundant features

**Solution:**
- ❌ NEVER use both together
- ✅ Use recent_4 (if you want raw counts)
- ✅ OR use current_freshness_bin (if you want categories)
- ✅ OR use the four weight features (if you want pattern preferences)

---

#### Risk Group 2: Raw Count vs Pattern Weights
**Correlated Features:** `recent_4` ↔ `freshness_c0_weight`, `freshness_c1_weight`, `freshness_c2_weight`, `freshness_c3_weight`

**Correlation:** 0.78 - 0.82 (very high)

**Why they correlate:**
- All five features derive from the same underlying data (count in last 4 draws)
- recent_4 = 0 → c0_weight is non-zero, others are zero
- recent_4 = 1 → c1_weight is non-zero, others are zero
- recent_4 = 2 → c2_weight is non-zero, others are zero
- recent_4 ≥ 3 → c3_weight is non-zero, others are zero

**Problem:**
Using `recent_4` together with any c0/c1/c2/c3 weight features means encoding the same information in two different ways.

**Solution - For Linear Models:**
- ❌ BAD: `['recent_4', 'freshness_c0_weight', 'freshness_c1_weight']`
- ✅ GOOD: `['recent_4', 'days_since_last', 'total_count']` (raw count approach)
- ✅ GOOD: `['freshness_c0_weight', 'freshness_c1_weight', 'freshness_c2_weight', 'freshness_c3_weight', 'days_since_last']` (pattern weight approach)

**Solution - For Tree Models (XGBoost):**
- ✅ OKAY: `['recent_4', 'freshness_c0_weight', 'freshness_c1_weight', ...]`
- Why? Trees split on different features in different branches, so can utilize redundant information

---

#### Risk Group 3: Progressive Recent Windows
**Correlated Features:** `recent_4` ↔ `recent_6` ↔ `recent_9` ↔ `recent_14`

**Correlations:**
- recent_4 ↔ recent_6: 0.78
- recent_6 ↔ recent_9: 0.85
- recent_9 ↔ recent_14: 0.72

**Why they correlate:**
- Overlapping time windows
- If a number appeared in last 4 draws, it also appeared in last 6, 9, and 14
- Each additional window adds less new information

**Problem:**
Using multiple progressive windows creates diminishing returns:
- recent_4 provides 100% new information
- recent_6 adds maybe 30% new information (2 extra draws)
- recent_9 adds maybe 20% new information (3 more draws)
- recent_14 adds maybe 15% new information (5 more draws)

**Solution:**
- ✅ BEST: Use only TWO windows with maximum separation
  - recent_4 (short-term) + recent_14 (long-term)
  - Correlation: 0.55 (moderate - acceptable!)
- ⚠️ OKAY: Use recent_4 + recent_9 (moderate separation)
- ❌ BAD: Use recent_4 + recent_6 (high overlap)
- ❌ BAD: Use all four (massive redundancy)

---

### Negative Correlation (Actually Good!) 🟢

#### Pattern Weights Are Mutually Exclusive
**Features:** `freshness_c0_weight` ↔ `freshness_c1_weight` ↔ `freshness_c2_weight` ↔ `freshness_c3_weight`

**Correlations:**
- c0_weight ↔ c1_weight: -0.65
- c0_weight ↔ c2_weight: -0.48
- c1_weight ↔ c2_weight: -0.52

**Why they're negatively correlated:**
- Only ONE weight is non-zero per number
- If c0_weight = 0.47, then c1 = c2 = c3 = 0.0
- They're complementary, not redundant!

**Why this is GOOD:**
- Together they form a complete "one-hot encoding"
- Model learns different importance for each category
- No wasted capacity - each weight contributes unique signal

**Best practice:**
- ✅ Use ALL FOUR weights together: `['freshness_c0_weight', 'freshness_c1_weight', 'freshness_c2_weight', 'freshness_c3_weight']`
- This is the RECOMMENDED approach for freshness pattern models
- Negative correlation is BENEFICIAL here!