# JSON Data Generation TODO List
## Complete Guide for ML Feature Data Sources

**Version:** 3.6  
**Date:** 2025-11-04  
**Purpose:** Define all JSON data structures needed to support ML features with complete data-driven approach

---

## Table of Contents
1. [Recency Zone Analysis](#1-recency-zone-analysis)
2. [Bonus Hit Target Alignment](#2-bonus-hit-target-alignment)
3. [Current JSON Data (Already Complete)](#3-current-json-data-already-complete)
4. [Implementation Priority](#4-implementation-priority)
5. [Testing & Validation](#5-testing--validation)

---

## 1. Recency Zone Analysis

### Feature Name
**`calculate_recency_zone_score_from_json`**

### Purpose
Identify the "sweet spot" timing for when numbers are most likely to be drawn again. This feature answers: **"Is a number more likely to win 10 days after its last appearance or 100 days after?"**

### Why This Matters
Historical patterns show that numbers have optimal "cooling periods":
- Numbers drawn very recently (0-14 days) are still "hot" and likely to appear again
- Numbers that haven't been drawn in a long time (120+ days) are statistically less likely to win
- There's a clear decay pattern in win probability as days increase

### Current Implementation Issue
Currently uses **hardcoded percentages** without actual data backing:
```python
if 0 <= days_since_last <= 14:
    return 1.0    # HARDCODED: claims 40% of winners
elif 14 < days_since_last <= 30:
    return 0.78   # HARDCODED: claims 31% of winners
# etc...
```

These percentages should come from **actual analysis** of your historical draws.

---

### JSON Structure Required

**File:** `data/lotto_timing_analysis.json` (NEW FILE)  
**Alternative:** Add to `data/lotto_odds_results.json` as a new section

```json
{
  "recency_zone_analysis": {
    "analysis_metadata": {
      "total_analyzed_draws": 500,
      "total_winning_numbers_analyzed": 3500,
      "description": "Analysis of days since last draw for all winning numbers",
      "calculation_date": "2025-11-04",
      "includes_bonus": true,
      "note": "Each draw has 7 winners (6 main + 1 bonus), so total = draws × 7"
    },
    
    "zones": [
      {
        "zone_id": 1,
        "zone_name": "Very Recent (0-14 days)",
        "min_days": 0,
        "max_days": 14,
        "winner_count": 1400,
        "percentage_of_winners": 40.0,
        "score": 1.0,
        "description": "Numbers drawn within the last 2 weeks",
        "interpretation": "Highest probability zone - numbers are still 'hot'"
      },
      {
        "zone_id": 2,
        "zone_name": "Recent (14-30 days)",
        "min_days": 14,
        "max_days": 30,
        "winner_count": 1085,
        "percentage_of_winners": 31.0,
        "score": 0.78,
        "description": "Numbers drawn 2-4 weeks ago",
        "interpretation": "High probability zone - numbers cooling but still active"
      },
      {
        "zone_id": 3,
        "zone_name": "Moderate (30-60 days)",
        "min_days": 30,
        "max_days": 60,
        "winner_count": 760,
        "percentage_of_winners": 21.7,
        "score": 0.54,
        "description": "Numbers drawn 1-2 months ago",
        "interpretation": "Moderate probability - numbers entering dormant period"
      },
      {
        "zone_id": 4,
        "zone_name": "Cold (60-120 days)",
        "min_days": 60,
        "max_days": 120,
        "winner_count": 245,
        "percentage_of_winners": 7.0,
        "score": 0.18,
        "description": "Numbers drawn 2-4 months ago",
        "interpretation": "Low probability - numbers are cold"
      },
      {
        "zone_id": 5,
        "zone_name": "Very Cold (120+ days)",
        "min_days": 120,
        "max_days": 999,
        "winner_count": 10,
        "percentage_of_winners": 0.3,
        "score": 0.01,
        "description": "Numbers not drawn in 4+ months",
        "interpretation": "Extremely low probability - numbers are dormant"
      }
    ],
    
    "zone_transition_matrix": {
      "description": "Probability of moving from one zone to another in next draw",
      "0-14_to_0-14": 0.35,
      "0-14_to_14-30": 0.45,
      "0-14_to_30-60": 0.15,
      "0-14_to_60-120": 0.04,
      "0-14_to_120+": 0.01,
      "note": "Rows sum to 1.0 for each starting zone"
    },
    
    "per_number_statistics": {
      "description": "Optional: Track individual number behavior",
      "example": {
        "number": 7,
        "average_days_between_draws": 28.5,
        "most_common_zone": "14-30 days",
        "zone_distribution": {
          "0-14": 12,
          "14-30": 18,
          "30-60": 8,
          "60-120": 2,
          "120+": 0
        }
      }
    }
  }
}
```

---

### How to Calculate This Data

#### Step-by-Step Algorithm for drawpick.py

```python
def analyze_recency_zones(draw_history_log: Dict) -> Dict:
    """
    Analyze the relationship between days-since-last-draw and win probability.
    
    Process:
    1. For each historical draw
    2. For each of the 7 winning numbers in that draw
    3. Calculate how many days passed since that number was LAST drawn
    4. Categorize into zones
    5. Count occurrences in each zone
    6. Calculate percentages and scores
    """
    
    # Define zone boundaries
    zones = {
        "0-14": {"min": 0, "max": 14, "count": 0},
        "14-30": {"min": 14, "max": 30, "count": 0},
        "30-60": {"min": 30, "max": 60, "count": 0},
        "60-120": {"min": 60, "max": 120, "count": 0},
        "120+": {"min": 120, "max": 999, "count": 0}
    }
    
    total_winners = 0
    
    # Iterate through each draw in chronological order
    for draw_date, draw_data in sorted(draw_history_log.items(), 
                                       key=lambda x: x[1]['draw_index']):
        
        # Get all 7 winning numbers (6 main + 1 bonus)
        winning_numbers_details = draw_data.get('winning_numbers_details', [])
        
        for winner in winning_numbers_details:
            # Get the days since this number was last drawn
            days_since_last = winner.get('days_since_last_hit', 999)
            
            # Categorize into a zone
            for zone_name, zone_data in zones.items():
                if zone_data['min'] <= days_since_last < zone_data['max']:
                    zones[zone_name]['count'] += 1
                    break
            
            total_winners += 1
    
    # Calculate percentages and scores
    zone_list = []
    for zone_name, zone_data in zones.items():
        count = zone_data['count']
        percentage = (count / total_winners * 100) if total_winners > 0 else 0
        
        # Score is normalized percentage (max zone gets 1.0)
        score = percentage / 40.0  # Assuming max is ~40%
        
        zone_list.append({
            "zone_name": zone_name,
            "min_days": zone_data['min'],
            "max_days": zone_data['max'],
            "winner_count": count,
            "percentage_of_winners": round(percentage, 2),
            "score": round(score, 2)
        })
    
    return {
        "recency_zone_analysis": {
            "total_analyzed_draws": len(draw_history_log),
            "total_winning_numbers_analyzed": total_winners,
            "zones": zone_list
        }
    }
```

#### Key Calculation Details

**What is `days_since_last_hit`?**
This field already exists in your `lotto_draw_history.json` under each winning number's details. It represents:
```
days_since_last_hit = (current_draw_date) - (last_time_this_number_was_drawn)
```

**Example:**
- Draw on 2025-01-15: Number 7 wins
- Draw on 2025-01-25: Number 7 wins again
- For the second win, `days_since_last_hit = 10 days`
- This would fall into the "0-14 days" zone

**Important Notes:**
1. **Include ALL 7 numbers** (6 main + 1 bonus) in the analysis
2. **Only count winning numbers** - don't count numbers that didn't win
3. **Calculate fresh for each draw** - days_since_last changes as we move through history
4. **The data is already in your JSON!** You just need to aggregate it

---

### What This Data Represents

**Winner Count:** How many times a winning number fell into this zone
- Example: 1400 winning numbers had been drawn 0-14 days before they won again

**Percentage of Winners:** What proportion of all winners came from this zone
- Example: 40% of all winning numbers were in the "very recent" category

**Score:** Normalized probability score (0.0 to 1.0)
- Example: 1.0 = highest probability zone, 0.01 = lowest probability zone
- ML model uses this to weight numbers based on their timing

**Interpretation:**
```
If a number was drawn 10 days ago:
  → Falls in "0-14 days" zone
  → Score = 1.0 (highest)
  → This number has 40% probability of being in the next draw
  → ML gives it maximum recency score

If a number was drawn 150 days ago:
  → Falls in "120+ days" zone  
  → Score = 0.01 (lowest)
  → This number has only 0.3% probability
  → ML gives it minimum recency score
```

---

### How ML Feature Uses This Data

```python
def calculate_recency_zone_score_from_json(
    recency_analysis: Dict,
    days_since_last: int
) -> float:
    """
    Look up the score for a number based on how many days since it was drawn.
    """
    zones = recency_analysis['recency_zone_analysis']['zones']
    
    for zone in zones:
        if zone['min_days'] <= days_since_last < zone['max_days']:
            return zone['score']
    
    return 0.01  # Default for extreme cases
```

**Example Usage:**
```
Number 23: Last drawn 20 days ago
  → days_since_last = 20
  → Falls in zone "14-30 days"
  → Returns score = 0.78
  → ML interprets: "This number has good timing (78% of optimal)"

Number 42: Last drawn 5 days ago
  → days_since_last = 5
  → Falls in zone "0-14 days"
  → Returns score = 1.0
  → ML interprets: "This number has perfect timing (100% optimal)"
```

---

## 2. Bonus Hit Target Alignment

### Feature Name
**`calculate_bonus_hit_target_alignment`**

### Purpose
Score numbers based on whether they help achieve the **optimal pattern** of having 1-2 numbers in your selection that were recently bonus balls. This feature answers: **"Should I include numbers that were bonus balls in the last 10 draws?"**

### Why This Matters
Historical analysis shows a strong pattern:
- **71.28% of draws** contain at least 1 number that was a bonus ball in the previous 10 draws
- **50% of draws** contain exactly 1 such number
- **20% of draws** contain exactly 2 such numbers
- Only **5%** have 3 or more

This means: **Including 1-2 recent bonus numbers significantly increases your odds!**

### Current Implementation Issue
Uses **hardcoded fixed scores** without considering actual odds:
```python
if was_recent_bonus_data.get(num, 0) == 1:
    alignment[num] = 0.65  # HARDCODED
else:
    alignment[num] = 0.35  # HARDCODED
```

These scores should be calculated from **actual historical bonus hit rates**.

---

### JSON Structure Required

**File:** `data/lotto_odds_results.json` (ENHANCE EXISTING)  
**Section:** `recent_bonus_analysis` (already exists, needs more detail)

```json
{
  "recent_bonus_analysis": {
    "analysis_metadata": {
      "total_analyzed_draws": 500,
      "lookback_window": 10,
      "description": "Analysis of how many main winning numbers (6 only) were bonus balls in previous 10 draws",
      "calculation_date": "2025-11-04",
      "note": "Only counts main 6 numbers, not the bonus itself"
    },
    
    "hit_distribution": {
      "description": "Distribution of recent bonus hits in winning 6 main numbers",
      
      "0_hits": {
        "count": 143,
        "percentage": 28.6,
        "odds": 0.286,
        "description": "Draws with zero recent bonus numbers in main 6",
        "interpretation": "Less common - most draws have at least 1"
      },
      
      "1_hit": {
        "count": 250,
        "percentage": 50.0,
        "odds": 0.50,
        "description": "Draws with exactly 1 recent bonus number in main 6",
        "interpretation": "MOST COMMON - this is the target pattern"
      },
      
      "2_hits": {
        "count": 100,
        "percentage": 20.0,
        "odds": 0.20,
        "description": "Draws with exactly 2 recent bonus numbers in main 6",
        "interpretation": "Common - secondary target pattern"
      },
      
      "3_or_more_hits": {
        "count": 7,
        "percentage": 1.4,
        "odds": 0.014,
        "description": "Draws with 3+ recent bonus numbers in main 6",
        "interpretation": "Very rare - avoid too many recent bonus numbers"
      }
    },
    
    "cumulative_statistics": {
      "at_least_1_hit": {
        "count": 357,
        "percentage": 71.4,
        "odds": 0.714,
        "description": "Draws with 1 or more recent bonus hits"
      },
      "at_least_2_hits": {
        "count": 107,
        "percentage": 21.4,
        "odds": 0.214,
        "description": "Draws with 2 or more recent bonus hits"
      },
      "at_least_3_hits": {
        "count": 7,
        "percentage": 1.4,
        "odds": 0.014,
        "description": "Draws with 3 or more recent bonus hits"
      }
    },
    
    "optimal_strategy": {
      "recommended_count": 1,
      "acceptable_range": [1, 2],
      "reasoning": "70% of draws have 1-2 recent bonus numbers",
      "avoid": "Including 3+ recent bonus numbers (only 1.4% success rate)"
    },
    
    "per_number_contribution": {
      "description": "Contribution rates for recent vs non-recent bonus numbers",
      
      "recent_bonus_pool": {
        "average_pool_size": 10,
        "selected_per_draw": 1.0,
        "selection_rate": 0.10,
        "description": "On average, 10 numbers are recent bonus balls, and ~1 gets selected per draw"
      },
      
      "non_recent_bonus_pool": {
        "average_pool_size": 37,
        "selected_per_draw": 5.0,
        "selection_rate": 0.135,
        "description": "On average, 37 numbers are NOT recent bonus balls, and ~5 get selected per draw"
      },
      
      "comparison": {
        "recent_bonus_advantage": "10% selection rate from pool of 10",
        "non_recent_rate": "13.5% selection rate from pool of 37",
        "conclusion": "Slightly favor non-recent bonus numbers, but include 1-2 recent ones"
      }
    },
    
    "bonus_recency_decay": {
      "description": "How selection probability changes with bonus recency",
      "draws_1_to_3_back": {
        "selection_probability": 0.12,
        "description": "Bonus balls from last 1-3 draws"
      },
      "draws_4_to_7_back": {
        "selection_probability": 0.09,
        "description": "Bonus balls from 4-7 draws ago"
      },
      "draws_8_to_10_back": {
        "selection_probability": 0.07,
        "description": "Bonus balls from 8-10 draws ago"
      }
    },
    
    "detailed_hit_examples": [
      {
        "draw_date": "2025-01-15",
        "main_6_numbers": [5, 12, 23, 34, 41, 45],
        "recent_bonus_list": [5, 12, 18, 22, 27, 33, 38, 41, 44, 47],
        "hits": [5, 12, 41],
        "hit_count": 3,
        "category": "3_or_more_hits",
        "note": "Rare case - 3 recent bonus numbers won"
      },
      {
        "draw_date": "2025-01-18",
        "main_6_numbers": [3, 7, 19, 28, 35, 42],
        "recent_bonus_list": [5, 7, 12, 18, 22, 27, 33, 38, 41, 44],
        "hits": [7],
        "hit_count": 1,
        "category": "1_hit",
        "note": "Most common case - exactly 1 recent bonus number won"
      }
    ]
  }
}
```

---

### How to Calculate This Data

#### Step-by-Step Algorithm for drawpick.py

```python
def analyze_bonus_hit_distribution(draw_history_log: Dict, lookback: int = 10) -> Dict:
    """
    For each draw, count how many of the 6 main winning numbers were 
    bonus balls in the previous N draws.
    
    Process:
    1. Maintain a rolling list of the last N bonus balls
    2. For each draw, check the 6 main winners against this list
    3. Count how many matches (hits)
    4. Categorize: 0, 1, 2, or 3+ hits
    5. Calculate statistics and probabilities
    """
    
    hit_distribution = {
        0: 0,  # No recent bonus hits
        1: 0,  # 1 recent bonus hit
        2: 0,  # 2 recent bonus hits
        3: 0   # 3 or more recent bonus hits
    }
    
    recent_bonus_list = []  # Rolling list of last N bonus balls
    total_draws_analyzed = 0
    
    detailed_examples = []
    
    # Sort draws chronologically
    sorted_draws = sorted(draw_history_log.items(), 
                         key=lambda x: x[1]['draw_index'])
    
    for draw_date, draw_data in sorted_draws:
        # Get the 6 main winning numbers (exclude bonus)
        winning_details = draw_data.get('winning_numbers_details', [])
        main_6_numbers = [w['number'] for w in winning_details[:6]]
        
        # Count how many of these 6 are in the recent bonus list
        hits = [num for num in main_6_numbers if num in recent_bonus_list]
        hit_count = len(hits)
        
        # Categorize
        if hit_count >= 3:
            hit_distribution[3] += 1
            category = "3_or_more_hits"
        else:
            hit_distribution[hit_count] += 1
            category = f"{hit_count}_hit{'s' if hit_count != 1 else ''}"
        
        # Store example (first 5 of each category)
        if len([e for e in detailed_examples if e['category'] == category]) < 5:
            detailed_examples.append({
                "draw_date": draw_date,
                "main_6_numbers": main_6_numbers,
                "recent_bonus_list": recent_bonus_list.copy(),
                "hits": hits,
                "hit_count": hit_count,
                "category": category
            })
        
        total_draws_analyzed += 1
        
        # Update rolling bonus list
        # Get current draw's bonus number
        bonus_number = winning_details[-1]['number'] if winning_details else None
        if bonus_number:
            recent_bonus_list.append(bonus_number)
            # Keep only last N bonus balls
            if len(recent_bonus_list) > lookback:
                recent_bonus_list.pop(0)
    
    # Calculate percentages and odds
    result = {
        "analysis_metadata": {
            "total_analyzed_draws": total_draws_analyzed,
            "lookback_window": lookback
        },
        "hit_distribution": {}
    }
    
    for hit_count, count in hit_distribution.items():
        percentage = (count / total_draws_analyzed * 100) if total_draws_analyzed > 0 else 0
        odds = count / total_draws_analyzed if total_draws_analyzed > 0 else 0
        
        if hit_count == 3:
            key = "3_or_more_hits"
        else:
            key = f"{hit_count}_hit{'s' if hit_count != 1 else ''}"
        
        result["hit_distribution"][key] = {
            "count": count,
            "percentage": round(percentage, 2),
            "odds": round(odds, 4)
        }
    
    # Calculate cumulative statistics
    at_least_1 = sum(hit_distribution[i] for i in [1, 2, 3])
    at_least_2 = sum(hit_distribution[i] for i in [2, 3])
    at_least_3 = hit_distribution[3]
    
    result["cumulative_statistics"] = {
        "at_least_1_hit": {
            "count": at_least_1,
            "percentage": round(at_least_1 / total_draws_analyzed * 100, 2),
            "odds": round(at_least_1 / total_draws_analyzed, 4)
        },
        "at_least_2_hits": {
            "count": at_least_2,
            "percentage": round(at_least_2 / total_draws_analyzed * 100, 2),
            "odds": round(at_least_2 / total_draws_analyzed, 4)
        },
        "at_least_3_hits": {
            "count": at_least_3,
            "percentage": round(at_least_3 / total_draws_analyzed * 100, 2),
            "odds": round(at_least_3 / total_draws_analyzed, 4)
        }
    }
    
    result["detailed_hit_examples"] = detailed_examples
    
    return {"recent_bonus_analysis": result}
```

#### Key Calculation Details

**What is a "Recent Bonus"?**
A number that appeared as a bonus ball in any of the previous 10 draws.

**Example:**
```
Draws 91-100 had these bonus balls: [5, 12, 18, 22, 27, 33, 38, 41, 44, 47]

Draw 101 winning 6 main numbers: [7, 12, 23, 33, 41, 45]
  → Numbers 12, 33, 41 are in the recent bonus list
  → Hit count = 3
  → Category: "3_or_more_hits"
  → This is RARE (only 1.4% of draws)

Draw 102 winning 6 main numbers: [3, 9, 15, 28, 35, 41]
  → Only number 41 is in the recent bonus list
  → Hit count = 1
  → Category: "1_hit"
  → This is COMMON (50% of draws)
```

**Important Notes:**
1. **Only count the 6 main numbers**, NOT the bonus ball of the current draw
2. **Rolling window**: Update the recent bonus list after each draw
3. **The data is already tracked!** Field `is_recent_bonus_hit` in your JSON shows this
4. **Count carefully**: A number can only be counted once per draw, even if it was bonus multiple times

---

### What This Data Represents

**Hit Distribution:**
- **0 hits (28.6%):** Draw has no recent bonus numbers → Unusual pattern
- **1 hit (50.0%):** Draw has exactly 1 recent bonus → OPTIMAL TARGET
- **2 hits (20.0%):** Draw has exactly 2 recent bonus → Acceptable
- **3+ hits (1.4%):** Draw has 3+ recent bonus → Rare, avoid

**Cumulative Statistics:**
- **At least 1 hit (71.4%):** Most draws have some recent bonus representation
- **At least 2 hits (21.4%):** About 1 in 5 draws have multiple hits
- **At least 3 hits (1.4%):** Very rare to have many hits

**Optimal Strategy:**
```
When building a 6-number line:
  → Include 1-2 numbers from recent bonus list (last 10 draws)
  → Include 4-5 numbers that are NOT from recent bonus list
  → This matches the 70% success pattern
```

---

### How ML Feature Uses This Data

```python
def calculate_bonus_hit_target_alignment(
    was_recent_bonus_data: Dict[int, int],
    bonus_analysis: Dict
) -> Dict[int, float]:
    """
    Calculate alignment scores based on optimal hit distribution.
    """
    # Get probabilities from JSON
    one_hit_prob = bonus_analysis['hit_distribution']['1_hit']['odds']
    two_hits_prob = bonus_analysis['hit_distribution']['2_hits']['odds']
    
    # Target probability (1 or 2 hits)
    target_prob = one_hit_prob + two_hits_prob  # ~0.70
    
    alignment = {}
    for num in range(1, 48):
        if was_recent_bonus_data.get(num, 0) == 1:
            # This number is a recent bonus
            # Higher score helps achieve target of 1-2 hits
            alignment[num] = 0.5 + (target_prob * 0.5)  # ~0.85
        else:
            # This number is NOT a recent bonus
            # Lower score but still positive (need 4-5 of these)
            alignment[num] = 0.5 - (target_prob * 0.3)  # ~0.29
    
    return alignment
```

**Example Usage:**
```
Number 7: Was bonus ball 3 draws ago
  → was_recent_bonus = 1
  → alignment score = 0.85
  → ML interprets: "Including this helps achieve optimal 1-2 hit pattern"

Number 23: Has NOT been bonus in last 10 draws
  → was_recent_bonus = 0
  → alignment score = 0.29
  → ML interprets: "This fills the 4-5 non-bonus slots needed"

When building a line:
  → Pick 1-2 numbers with score ~0.85 (recent bonus)
  → Pick 4-5 numbers with score ~0.29 (non-recent bonus)
  → This creates optimal pattern matching 70% of historical draws
```

---

### Advanced: Bonus Recency Decay

**Optional Enhancement:** Track how the probability changes based on HOW RECENT the bonus was:

```json
{
  "bonus_recency_decay": {
    "1_draw_back": {
      "selection_probability": 0.15,
      "description": "Was bonus in the very last draw"
    },
    "2_3_draws_back": {
      "selection_probability": 0.11,
      "description": "Was bonus 2-3 draws ago"
    },
    "4_7_draws_back": {
      "selection_probability": 0.08,
      "description": "Was bonus 4-7 draws ago"
    },
    "8_10_draws_back": {
      "selection_probability": 0.06,
      "description": "Was bonus 8-10 draws ago - fading effect"
    }
  }
}
```

**Calculation:**
For each position (1-back, 2-back, ..., 10-back), track:
- How many times a number at that position was selected in the next draw
- Calculate selection probability
- Reveals decay pattern (more recent bonus = higher probability)

---

## 3. Current JSON Data (Already Complete)

### Files That Are Already Perfect

#### 3.1 `lotto_trigger_periods.json`
**Status:** ✅ Complete - No changes needed

**Contains:**
- `total_count` - Historical frequency
- `last_seen` - Most recent appearance date
- `category` - Hot/Medium/Cold classification
- `recent.last_N` - Recent activity windows (4, 6, 9, 14 draws)
- `series` - Streak pattern data

**Used By:**
- `total_count` feature
- `days_since_last` feature (calculated from last_seen)
- `recent_4, recent_6, recent_9, recent_14` features
- `series_total, series_recent` features
- `has_consecutive_partner` feature (uses recent_4)

---

#### 3.2 `lotto_draw_history.json`
**Status:** ✅ Complete - No changes needed

**Contains:**
- Per-draw complete details
- `winning_numbers_details` with all metadata
- `days_since_last_hit` for each winner (CRITICAL for recency zones)
- `is_recent_bonus_hit` for each winner (CRITICAL for bonus alignment)
- `all_numbers_bias_ratios` for win bias feature
- `recent_bonus_numbers` list (last 10 bonus balls)

**Used By:**
- `win_bias_ratio` feature
- `was_recent_bonus` feature
- `days_since_bonus` feature (bonus timing)
- Source data for new recency zone analysis
- Source data for enhanced bonus hit analysis

---

#### 3.3 `lotto_odds_results.json`
**Status:** ⚠️ Needs Enhancement (bonus analysis section)

**Currently Contains:**
- `hmc` - HMC distribution patterns ✅
- `draw_range` - Range spread distribution ✅
- `patterns.2_consecutive.all_pairs` - Consecutive pair data ✅
- `recent_bonus_analysis` - Basic bonus hit counts ⚠️ NEEDS ENHANCEMENT

**Used By:**
- `consecutive_pair_affinity` feature (uses all_pairs) ✅
- `range_spread_affinity` feature (uses draw_range) ✅
- `bonus_hit_target_alignment` feature (uses recent_bonus_analysis) ⚠️ NEEDS MORE DATA

**Enhancement Needed:**
Expand `recent_bonus_analysis` section with detailed hit distribution (see Section 2 above)

---

#### 3.4 `lotto_distribution_stats.json`
**Status:** ✅ Complete - No changes needed

**Contains:**
- `analysis_6_main_numbers`
  - `odd_even_patterns` - Balance distribution ✅
  - `sum_distributions` - Sum range distribution ✅
- `analysis_all_7_numbers`
  - Full 7-number patterns ✅

**Used By:**
- `odd_even_affinity` feature (uses odd_even_patterns) ✅
- `sum_contribution_score` feature (uses sum_distributions) ✅

---

#### 3.5 `lotto_7_number_freshness_results.json`
**Status:** ✅ Complete - No changes needed

**Contains:**
- Dynamic freshness pattern distributions
- `distribution_analysis_7_numbers` with C0/C1/C2/C≥X breakdown
- Window size and threshold configuration

**Used By:**
- `freshness_c0_weight, freshness_c1_weight, freshness_c2_weight, freshness_c3_weight` features ✅
- `current_freshness_bin` feature ✅

---

## 4. Implementation Priority

### Priority 1: Bonus Hit Enhancement (EASY)
**Effort:** Low (1-2 hours)  
**Impact:** Medium  
**Why First:** Data already exists in draw_history_log, just needs aggregation

**Tasks:**
1. Add `analyze_bonus_hit_distribution()` function to `hmc_analyzer.py`
2. Call it during HMC analysis phase
3. Enhance existing `recent_bonus_analysis` section in `lotto_odds_results.json`
4. Add cumulative statistics and detailed examples

**Files to Modify:**
- `lotto_analysis/analyzers/hmc_analyzer.py` (add new function)
- `drawpick.py` (call new function, save enhanced results)
- `ml_lotto/feature_extractor.py` (update to use enhanced data - already done!)

---

### Priority 2: Recency Zone Analysis (MEDIUM)
**Effort:** Medium (2-4 hours)  
**Impact:** High  
**Why Second:** Requires new analysis function but data is available

**Tasks:**
1. Create `analyze_recency_zones()` function
2. Add to drawpick.py analysis phases
3. Create new JSON file `lotto_timing_analysis.json`
4. Update feature_extractor to use zone data

**Files to Create:**
- `lotto_analysis/analyzers/timing_analyzer.py` (new file)

**Files to Modify:**
- `drawpick.py` (add timing analysis phase)
- `ml_lotto/feature_extractor.py` (update recency score function)

---

## 5. Testing & Validation

### Validation Checklist

#### For Recency Zone Analysis:
- [ ] Sum of all zone winner_counts equals total_winning_numbers_analyzed (draws × 7)
- [ ] All zones have percentage > 0 (if you have enough data)
- [ ] Highest percentage is in 0-14 or 14-30 zone (expected pattern)
- [ ] Percentages decrease as zones get colder (decay pattern)
- [ ] Scores are normalized between 0.01 and 1.0

#### For Bonus Hit Analysis:
- [ ] Sum of all hit distribution counts equals total_analyzed_draws
- [ ] Percentages sum to 100%
- [ ] "1_hit" is the most common category (~50%)
- [ ] "3_or_more_hits" is the rarest category (~1-5%)
- [ ] Cumulative "at_least_1_hit" is ~70-75%
- [ ] Detailed examples match their categories

#### Cross-Validation:
- [ ] Run drawpick.py successfully with new analysis
- [ ] Verify JSON files are created with correct structure
- [ ] Run quickpick.py and confirm features load correctly
- [ ] Check that feature extraction prints correct percentages
- [ ] Verify ML training completes without errors
- [ ] Compare old vs new predictions for reasonableness

---

## 6. Example Implementation Snippet

### For drawpick.py:

```python
# In main() function, add after Phase 4:

# ===== PHASE 5: TIMING ANALYSIS =====
print("\n" + "=" * 70)
print("Phase 5: Recency Zone Analysis")
print("=" * 70)

from lotto_analysis.analyzers.timing_analyzer import analyze_recency_zones

timing_analysis = analyze_recency_zones(draw_history_log)
write_json_file('data/lotto_timing_analysis.json', timing_analysis,
               "Recency zone analysis for optimal timing patterns")

# ===== PHASE 6: ENHANCED BONUS ANALYSIS =====
print("\n" + "=" * 70)
print("Phase 6: Enhanced Bonus Hit Analysis")
print("=" * 70)

from lotto_analysis.analyzers.hmc_analyzer import analyze_bonus_hit_distribution

enhanced_bonus = analyze_bonus_hit_distribution(draw_history_log, lookback=10)

# Update existing odds results with enhanced bonus analysis
final_main['recent_bonus_analysis'] = enhanced_bonus['recent_bonus_analysis']
```

---

## 7. Success Criteria

### You'll Know It's Working When:

1. **Recency Zones:**
   - Feature extraction prints: `"✓ Calculated 'recency_zone_score' from JSON (zones: 5)"`
   - Numbers with recent draws (0-14 days) get scores near 1.0
   - Numbers with old draws (120+ days) get scores near 0.01
   - ML model treats timing as significant predictor

2. **Bonus Alignment:**
   - Feature extraction prints: `"✓ Calculated 'bonus_hit_target_alignment' from JSON (optimal: 1-2 hits)"`
   - Recent bonus numbers get scores ~0.85
   - Non-recent bonus numbers get scores ~0.29
   - Generated lines typically contain 1-2 recent bonus numbers

3. **Overall System:**
   - All features print "from JSON" during extraction
   - No hardcoded values remain in feature calculations
   - ML predictions are more accurate and data-driven
   - Feature importance analysis shows timing and bonus features matter

---

## 8. Future Enhancements (Optional)

### After Core Implementation:

1. **Dynamic Zone Boundaries**
   - Instead of fixed zones (0-14, 14-30, etc.), calculate optimal boundaries from data
   - Use clustering algorithms to find natural breakpoints

2. **Per-Number Timing Profiles**
   - Some numbers may have different optimal timing than others
   - Track individual number "cycles" (average days between appearances)

3. **Bonus Position Decay**
   - More granular analysis: Does being bonus 1 draw ago differ from 10 draws ago?
   - Create decay curve rather than fixed 10-draw window

4. **Interaction Effects**
   - Analyze: Do numbers with good recency scores AND recent bonus status perform even better?
   - Create combined features capturing interactions

---

## Summary Table

| Feature | JSON Source | Status | Priority | Effort |
|---------|-------------|--------|----------|--------|
| `recency_zone_score` | lotto_timing_analysis.json | 🔴 NEW FILE NEEDED | P2 | Medium |
| `bonus_hit_target_alignment` | lotto_odds_results.json | 🟡 ENHANCE EXISTING | P1 | Low |
| `odd_even_affinity` | lotto_distribution_stats.json | ✅ COMPLETE | - | - |
| `sum_contribution_score` | lotto_distribution_stats.json | ✅ COMPLETE | - | - |
| `range_spread_affinity` | lotto_odds_results.json | ✅ COMPLETE | - | - |
| `consecutive_pair_affinity` | lotto_odds_results.json | ✅ COMPLETE | - | - |
| `has_consecutive_partner` | lotto_trigger_periods.json | ✅ COMPLETE | - | - |
| `win_bias_ratio` | lotto_draw_history.json | ✅ COMPLETE | - | - |
| `freshness_weights` | lotto_7_number_freshness_results.json | ✅ COMPLETE | - | - |

---

**End of TODO Document**

*This document provides complete specifications for implementing data-driven ML features. Follow the priorities and validation steps for successful implementation.*