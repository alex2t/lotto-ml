#!/usr/bin/env python3
"""
feature_interaction_explorer.py
===============================
Standalone runner for the feature interaction analysis.

    python analysis/feature_interaction_explorer.py

This used to carry its own copy of the analysis, which drifted from the copy
drawpick.py runs. Both wrote to data/analysis/lotto_feature_interactions.json, so
running this script silently replaced the pipeline's output with results computed by
older, different rules - different thresholds, different recency bands and a different
recent_* convention.

It is now a thin wrapper over the single implementation in
lotto_analysis/analyzers/feature_interaction_analyzer.py, which is the same code
drawpick.py Phase 15 calls. Running this script and running drawpick.py now produce
identical output.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lotto_analysis.analyzers.feature_interaction_analyzer import (  # noqa: E402
    generate_feature_interaction_analysis,
    save_feature_interaction_outputs,
)

DRAW_HISTORY = REPO_ROOT / 'data' / 'lotto_draw_history.json'
OUTPUT_DIR = REPO_ROOT / 'data' / 'analysis'


def main() -> int:
    if not DRAW_HISTORY.exists():
        print(f"Draw history not found: {DRAW_HISTORY}")
        print("Run drawpick.py first to generate it.")
        return 1

    print(f"Loading draw history from {DRAW_HISTORY}...")
    with open(DRAW_HISTORY, encoding='utf-8') as f:
        draw_history_log = json.load(f)
    print(f"Loaded {len(draw_history_log)} draws")

    analysis = generate_feature_interaction_analysis(draw_history_log)
    save_feature_interaction_outputs(analysis, output_dir=str(OUTPUT_DIR))

    pairwise = analysis['pairwise_interactions']
    triples = analysis['triple_interactions']
    print(f"\nPairwise interactions: {len(pairwise)}")
    print(f"Triple interactions:   {len(triples)}")
    print(f"Written to {OUTPUT_DIR}")

    if pairwise:
        print(f"\n{'Feature 1':<24}{'Feature 2':<24}{'Thr 1':>8}{'Thr 2':>8}{'Strength':>10}")
        for inter in pairwise[:10]:
            print(f"{inter['feature_1']:<24}{inter['feature_2']:<24}"
                  f"{inter['threshold_1']:>8}{inter['threshold_2']:>8}"
                  f"{inter['interaction_strength']:>10.4f}")

    if triples:
        print(f"\n{'Triple':<34}{'Lift':>8}{'Samples':>9}")
        for triple in triples[:10]:
            name = f"triple_{triple['category']}_{triple['freshness_bin']}_{triple['recency']}"
            print(f"{name:<34}{triple['lift_over_baseline']:>8}{triple['sample_size']:>9}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
