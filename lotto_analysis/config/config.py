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

# =============== LOTTERY PARAMETERS ===============
MAX_NUMBER = 47            # Maximum lottery number
HOT_COUNT = 15             # Number of hot numbers
COLD_COUNT = 15           # Number of cold numbers

# =============== ANALYSIS SCENARIOS ===============
# Window sizes and target repetition counts to detect
SCENARIOS = [
    {"window": 5,  "targets": [2]},
    {"window": 6,  "targets": [3]},
    {"window": 10, "targets": [4]},
    {"window": 15, "targets": [5]}
]

# **NEW CONFIGURATION:** Index of the SCENARIOS list to use for 7-number freshness analysis.
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