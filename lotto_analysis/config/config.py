"""
Configuration settings for lottery analysis
"""

# =============== ANALYSIS CONFIGURATION ===============
TOTAL_DRAWS = 600          # Total number of draws to analyze
TRAINING_DATA = 100        # Initial training window size for HMC analysis
NUM_DRAWS = TOTAL_DRAWS - TRAINING_DATA  # Draws used for pattern analysis

# =============== FILE PATHS ===============
CSV_FILE = 'data/irish500.csv'  # Path to CSV file
OUTPUT_FILE_MAIN = "data/lotto_odds_results.json"
OUTPUT_FILE_PERIODS = "data/lotto_trigger_periods.json"
OUTPUT_FILE_HISTORY = "data/lotto_draw_history.json"
OUTPUT_FILE_7_NUMBERS = "data/lotto_7_number_freshness_results.json"
OUTPUT_FILE_DISTRIBUTIONS = "data/lotto_distribution_stats.json"
OUTPUT_FILE_BONUS_TO_MAIN = "data/lotto_bonus_to_main_patterns.json"

# =============== LOTTERY PARAMETERS ===============
MAX_NUMBER = 47            # Maximum lottery number

# HMC Categorization Method
HMC_METHOD = "recency"    # Options: "frequency" (old) or "recency" (validated)

# FREQUENCY-BASED (deprecated - kept for backwards compatibility)
HOT_COUNT = 15            # Number of hot numbers (frequency-based)
COLD_COUNT = 15           # Number of cold numbers (frequency-based)

# RECENCY-BASED (VALIDATED - scipy ANOVA thresholds from statistical analysis)
HMC_HOT_THRESHOLD = 13    # Hot: appeared in last 13 days (33rd percentile)
HMC_COLD_THRESHOLD = 27   # Cold: appeared 27+ days ago (67th percentile)
                          # Medium: 13 < days < 27

# =============== ANALYSIS SCENARIOS ===============
# Window sizes and target repetition counts to detect
SCENARIOS = [
    {"window": 5,  "targets": [2]},
    {"window": 6,  "targets": [3]},
    {"window": 10, "targets": [4]},
    {"window": 25, "targets": [8]}
]

# **NEW CONFIGURATION:** Index of the SCENARIOS list to use for 7-number freshness...
FRESHNESS_WINDOW_INDEX = 0

# =============== RANGE BINS ===============
# Define the Range Bins for draw range analysis
RANGE_BINS = {
    "20-25": (20, 25),
    "25-30": (25, 30),
    "30-35": (30, 35),
    "35-40": (35, 40),
    "40-45": (40, 45)
}

# ==================== DISTRIBUTION BINS ====================

# Sum Bins for ALL 7 numbers (6 main + bonus)
# Min possible: 28 (1+2+3+4+5+6+7), Max possible: 287 (41+42+43+44+45+46+47)
# Average expected: ~157
SUM_BINS_7_NUMBERS = {
    "S_VERY_LOW (<130)": (0, 130),
    "S_LOW (130-144)": (130, 145),
    "S_MID_LOW (145-159)": (145, 160),
    "S_MID (160-174)": (160, 175),
    "S_MID_HIGH (175-189)": (175, 190),
    "S_HIGH (190-204)": (190, 205),
    "S_VERY_HIGH (>=205)": (205, 350)
}

# Sum Bins for 6 main numbers only (excluding bonus)
# Min: 21 (1+2+3+4+5+6), Max: 267 (42+43+44+45+46+47), Avg: ~144
SUM_BINS_6_NUMBERS = {
    "S6_VERY_LOW (<110)": (0, 110),
    "S6_LOW (110-124)": (110, 125),
    "S6_MID_LOW (125-139)": (125, 140),
    "S6_MID (140-154)": (140, 155),
    "S6_MID_HIGH (155-169)": (155, 170),
    "S6_HIGH (170-184)": (170, 185),
    "S6_VERY_HIGH (>=185)": (185, 300)
}

# Odd/Even Patterns for ALL 7 numbers (6 main + bonus)
# Format: "odd_even" (e.g., "7_0" means 7 odd, 0 even)
ODD_EVEN_PATTERNS_7_NUMBERS = [
    "7_0", "6_1", "5_2", "4_3", "3_4", "2_5", "1_6", "0_7"
]

# Odd/Even Patterns for 6 main numbers only (excluding bonus)
# Format: "odd_even" (e.g., "6_0" means 6 odd, 0 even)
ODD_EVEN_PATTERNS_6_NUMBERS = [
    "6_0", "5_1", "4_2", "3_3", "2_4", "1_5", "0_6"
]