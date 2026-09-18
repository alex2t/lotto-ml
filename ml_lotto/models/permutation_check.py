"""
permutation_check.py
====================
Label-permutation check: does any main model find an edge, or is its AUC what noise gives?

Each model is trained once on the real labels and then `n_permutations` times with the
training labels shuffled within each draw - every draw keeps its hit count, but which
numbers hit is random, so there is nothing to learn. Validation labels are never
shuffled. The shuffled runs give each model's null distribution of validation AUC,
produced by the exact production pipeline (features, selection, tuning, calibration).

Decision rule, fixed before running: a model shows an edge only if p < 0.05, where
p = (1 + #null >= real) / (n + 1). That needs at least 19 permutations; with 20 the
real AUC must beat every permuted one (p = 1/21 = 0.048). Across four models one false
pass is expected about one time in five, so a single pass needs confirming with more
permutations.
"""

import json
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from ml_lotto.config import MAX_NUMBER
from ml_lotto.features.walk_forward import PointInTimeFeatureEngine
from ml_lotto.models.trainer import build_main_datasets, excludes_bonus, train_model

EDGE_P = 0.05


def shuffle_within_draws(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Return a copy with `hit` permuted independently inside each block of MAX_NUMBER rows."""
    hits = df['hit'].to_numpy().reshape(-1, MAX_NUMBER)
    shuffled = df.copy()
    shuffled['hit'] = rng.permuted(hits, axis=1).ravel()
    return shuffled


def empirical_p(real: float, null: List[float]) -> float:
    """Share of the null at or above the real value, counting the real run itself."""
    return (1 + sum(v >= real for v in null)) / (len(null) + 1)


def run_permutation_check(
    model_configs: List[Dict[str, Any]],
    base_engine: PointInTimeFeatureEngine,
    features_dict: Dict[int, Dict[str, Any]],
    n_draws: int,
    n_permutations: int,
    tuning: Dict[str, Any],
    seed: int = 0,
    output_path: str = 'model_metrics/permutation_check.json'
) -> Dict[str, Dict[str, Any]]:
    """Train every main model on real and permuted labels; write and return the comparison."""
    datasets, all_feature_names = build_main_datasets(model_configs, base_engine, features_dict, n_draws)
    rng = np.random.default_rng(seed)
    results = {}

    for idx, config in enumerate(model_configs, 1):
        exclude_bonus = excludes_bonus(idx)
        train_df, val_df = datasets[exclude_bonus]

        def val_auc(labels_df: pd.DataFrame) -> float:
            metrics = train_model(config, labels_df, all_feature_names, idx, exclude_bonus=exclude_bonus,
                                  val_df=val_df, output_dir=None, **tuning)[3]
            return float(metrics['auc_val'])

        real = val_auc(train_df)
        null = [val_auc(shuffle_within_draws(train_df, rng)) for _ in range(n_permutations)]
        p = empirical_p(real, null)
        results[config['name']] = {
            'real_auc': real,
            'null_mean': float(np.mean(null)),
            'null_std': float(np.std(null)),
            'null_max': float(np.max(null)),
            'p_value': p,
            'edge': p < EDGE_P,
            'null_aucs': null,
        }
        print(f"PERMUTATION {config['name']}: real {real:.4f} | null {np.mean(null):.4f} "
              f"+/- {np.std(null):.4f} (max {np.max(null):.4f}) | p = {p:.3f}")

    report = {'n_permutations': n_permutations, 'seed': seed, 'models': results}
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    return results
