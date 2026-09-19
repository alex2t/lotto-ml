# ml_lotto/prediction/predictor.py
"""
predictor.py
============
Main prediction orchestration: generates predictions and picks from trained models.

UPDATED: v3.6 - Modified for 5 main numbers (bonus assigned separately)
"""

import numpy as np
from typing import Dict, Any, List
from ml_lotto.config import MAX_NUMBER
from lotto_analysis.config.config import HIGH_NUMBER_FROM
from ml_lotto.prediction.constraints import (
    get_optimal_pattern_distribution,
    categorize_numbers_by_freshness,
    build_dual_categorized_pools,
    display_available_numbers,
    reachable_pattern
)
from ml_lotto.prediction.ilp_selection import solve_line, pattern_string
from ml_lotto.prediction.filters import (
    FILTERS_AVAILABLE,
    get_filter_statistics
)


def generate_predictions(
    models: Dict[str, Any],
    model_features: Dict[str, List[str]],
    features_dict: Dict[int, Dict[str, Any]]
) -> Dict[str, np.ndarray]:
    """
    Generate predictions from all trained models.
    
    Args:
        models: Dictionary of trained model pipelines and configs
        model_features: Feature names used by each model
        features_dict: Current feature values for all numbers
        
    Returns:
        Dictionary mapping model_name -> probability_array
    """
    print("\n" + "="*70)
    print("GENERATING MAIN NUMBER PREDICTIONS")
    print("="*70)
    
    all_probabilities = {}
    
    for model_name, model_data in models.items():
        pipeline = model_data['pipeline']
        features_for_model = model_features[model_name]
        
        # Every consumer indexes this array positionally as probabilities[num - 1],
        # so row i must be number i+1. Build one row per number unconditionally and
        # let a missing number raise here rather than shifting every number above the
        # gap onto another number's probability (F-4).
        # feat[col], never feat.get(col, 0): features_for_model is the exact column list the
        # pipeline was fitted on. A silent 0 for a missing column would apply a coefficient
        # fitted on real values to a constant, breaking train/serve parity with no error (F-9).
        X_pred_list = []
        for num in range(1, MAX_NUMBER + 1):
            feat = features_dict[num]
            X_pred_list.append([feat[col] for col in features_for_model])

        X_pred = np.array(X_pred_list)

        probabilities = pipeline.predict_proba(X_pred)[:, 1]
        all_probabilities[model_name] = probabilities
        print(f"  ✓ {model_name} predictions generated")
    
    return all_probabilities


def generate_all_picks(
    models: Dict[str, Any],
    all_probabilities: Dict[str, np.ndarray],
    features_dict: Dict[int, Dict[str, Any]],
    freshness_data: Dict[str, Any] = None,
    pre_assigned_numbers: Dict[int, List[int]] = None
) -> List[Dict[str, Any]]:
    """
    Generate MAIN NUMBER picks from all models with optional pre-assigned numbers.

    Args:
        models: Trained model pipelines and configs
        all_probabilities: Predicted probabilities from each model
        features_dict: Current feature values for all numbers
        freshness_data: Freshness pattern configuration from JSON
        pre_assigned_numbers: Dict mapping model_idx -> list of pre-assigned numbers
                              These numbers are EXEMPT from selection and penalties

    Returns:
        List of pick lines with metadata

    UPDATED v3.9: Support for pre-assigned numbers (bonus + bonus-to-main)
    - If pre_assigned_numbers provided: picks remaining numbers to total 6 main
    - Pre-assigned numbers are excluded from selection pool and diversity penalties
    """
    # Initialize pre-assigned numbers if not provided
    if pre_assigned_numbers is None:
        pre_assigned_numbers = {}

    print("\n" + "="*70)
    print("GENERATING MAIN NUMBER PICKS (6 Numbers Per Model)")
    print("="*70)
    print("Selection Strategy:")
    print("  - Models with pre-assigned: select remaining numbers to reach 6 total")
    print("  - Models without pre-assigned: select all 6 numbers")
    print("  - Pre-assigned numbers are EXEMPT from selection and diversity penalties")
    
    if FILTERS_AVAILABLE:
        filter_stats = get_filter_statistics()
        print("\n📋 PHASE 1 FILTERS ACTIVE:")
        print("  1️⃣  Odd/Even Balance Filter")
        print(f"     - {filter_stats['odd_even_filter']['description']}")
        print(f"     - Expected elimination: {filter_stats['odd_even_filter']['expected_elimination']}")
        
        print("  2️⃣  Sum Constraint Filter")
        print(f"     - {filter_stats['sum_constraint']['description']}")
        print(f"     - Expected elimination: {filter_stats['sum_constraint']['expected_elimination']}")
        
        print("  3️⃣  Range Distribution Filter")
        print(f"     - {filter_stats['range_distribution']['description']}")
        print(f"     - Expected elimination: {filter_stats['range_distribution']['expected_elimination']}")
        
        print(f"\n  📊 Combined Impact: {filter_stats['combined_impact']['total_elimination']}")
    else:
        print("\n⚠️  Phase 1 filters not available (running without post-generation validation)")
    
    c_max_threshold = freshness_data.get('c_max_threshold', 3) if freshness_data else 3
    
    target_pattern = get_optimal_pattern_distribution(freshness_data, c_max_threshold)
    
    pattern_display_parts = []
    for i in sorted(target_pattern.keys()):
        if i < c_max_threshold:
            pattern_display_parts.append(f"C{i}={target_pattern[i]}")
        else:
            pattern_display_parts.append(f"C>= {i}={target_pattern[i]}")
    
    print(f"\n✓ Target Freshness Pattern (6 main numbers): {', '.join(pattern_display_parts)}")
    print(f"  Source: observed freshness split of the 6 main balls (distribution_analysis_6_main)")
    
    number_categories = categorize_numbers_by_freshness(features_dict)
    
    display_available_numbers(features_dict, number_categories, c_max_threshold)
    
    lines = []
    penalty_numbers = set()
    
    for model_idx, (model_name, model_data) in enumerate(models.items(), 1):
        model_config = model_data['config']
        probabilities = all_probabilities[model_name]

        # Get pre-assigned numbers for this model (filter out None values)
        model_pre_assigned = [x for x in pre_assigned_numbers.get(model_idx, []) if x is not None]

        # Determine how many numbers THIS model needs to select
        # Model target: 6 total main numbers
        numbers_to_select = 6 - len(model_pre_assigned)

        h = model_config['hot_count']
        m = model_config['medium_count']
        c = model_config['cold_count']
        g = model_config['generic_count']

        # If pre-assigned numbers exist, adjust HMC targets
        if model_pre_assigned:
            # Determine HMC categories of pre-assigned numbers
            pre_assigned_hmc_counts = {'hot': 0, 'medium': 0, 'cold': 0}
            for num in model_pre_assigned:
                if num in features_dict:
                    cat = features_dict[num].get('category', 'medium')
                    pre_assigned_hmc_counts[cat] += 1

            # Subtract pre-assigned from target counts
            h = max(0, h - pre_assigned_hmc_counts['hot'])
            m = max(0, m - pre_assigned_hmc_counts['medium'])
            c = max(0, c - pre_assigned_hmc_counts['cold'])

            # Adjust total to match numbers_to_select
            total_adjusted = h + m + c + g
            if total_adjusted != numbers_to_select:
                diff = numbers_to_select - total_adjusted
                g = max(0, g + diff)

        total_picks = h + m + c + g
        if total_picks != numbers_to_select:
            print(f"\n⚠️  WARNING: Model {model_idx} configured for {total_picks} numbers, adjusting to {numbers_to_select}")
            if total_picks > numbers_to_select:
                while h + m + c + g > numbers_to_select:
                    if g > 0:
                        g -= 1
                    elif c > 0:
                        c -= 1
                    elif m > 0:
                        m -= 1
                    elif h > 0:
                        h -= 1
            else:
                g += (numbers_to_select - total_picks)

        print(f"\n→ Model {model_idx}: {model_config['name']}")
        if model_pre_assigned:
            print(f"  Pre-assigned: {sorted(model_pre_assigned)} (EXEMPT from penalties)")
            print(f"  Selecting {h}H + {m}M + {c}C + {g}G = {h+m+c+g} additional numbers")
        else:
            print(f"  HMC Ratio: {h}H + {m}M + {c}C + {g}G = {h+m+c+g} numbers")
        if model_config['min_high_numbers']:
            print(f"  At least {model_config['min_high_numbers']} numbers >= {HIGH_NUMBER_FROM}")
        
        # Numbers on earlier lines are avoided unless unavoidable - the solver's flat
        # penalty is the only diversity mechanism (F-16). Pre-assigned numbers are exempt.
        penalty_set_for_model = penalty_numbers - set(model_pre_assigned)
        if penalty_set_for_model:
            print(f"  Diversity: avoiding {len(penalty_set_for_model)} numbers used by earlier lines")

        # Build pools, excluding pre-assigned numbers from selection
        exclude_from_selection = set(model_pre_assigned) if model_pre_assigned else set()
        pools = build_dual_categorized_pools(
            features_dict,
            number_categories,
            probabilities,
            exclude_numbers=exclude_from_selection
        )
        
        model_config_adjusted = model_config.copy()
        model_config_adjusted['hot_count'] = h
        model_config_adjusted['medium_count'] = m
        model_config_adjusted['cold_count'] = c
        model_config_adjusted['generic_count'] = g
        
        # The global target ignores this model's HMC ratio, and the two can be mutually
        # unsatisfiable: every bin 1 and bin 2 candidate is currently hot, so a model with few
        # hot slots cannot place the non-bin-0 numbers the target asks for. Selection is given
        # the reachable pattern instead, and the shortfall is reported rather than showing up
        # as a silent miss (F-13).
        model_target = reachable_pattern(target_pattern, pools, model_config_adjusted)
        if model_target != target_pattern:
            shortfall = ', '.join(
                f"C{b}: {target_pattern[b]} -> {model_target[b]}"
                for b in sorted(target_pattern) if model_target[b] != target_pattern[b]
            )
            print(f"  Target unreachable for this HMC ratio, using {model_target} ({shortfall})")

        selected_numbers = solve_line(
            probabilities,
            {num: features_dict[num]['category'] for num in range(1, MAX_NUMBER + 1)},
            number_categories,
            {'hot': h, 'medium': m, 'cold': c},
            model_target,
            penalty_set_for_model,
            model_pre_assigned,
            model_config['min_high_numbers']
        )
        achieved_pattern = pattern_string(selected_numbers, number_categories, model_target)

        # Combine pre-assigned numbers with selected numbers
        if model_pre_assigned:
            final_numbers = sorted(model_pre_assigned + selected_numbers)
            print(f"  Selected: {selected_numbers}")
            print(f"  Pre-assigned: {sorted(model_pre_assigned)}")
            print(f"  Final: {final_numbers} ({len(final_numbers)} total)")
        else:
            final_numbers = selected_numbers
            print(f"  Selected: {selected_numbers}")

        print(f"  Achieved Pattern: {achieved_pattern}")
        reused = sorted(set(selected_numbers) & penalty_set_for_model)
        if reused:
            print(f"  Reused from earlier lines (no feasible line avoided them): {reused}")

        lines.append({
            'model_name': model_config['name'],
            'model_index': model_idx,
            'config_str': f"{h}H-{m}M-{c}C+{g}G | {achieved_pattern}",
            'numbers': final_numbers,
            'pre_assigned': model_pre_assigned if model_pre_assigned else [],
            'selected': selected_numbers,
            'description': model_config['description']
        })

        # Add ONLY selected numbers to penalty set (not pre-assigned)
        penalty_numbers.update(selected_numbers)

    return lines


def generate_pool_picks(
    models: Dict[str, Any],
    all_probabilities: Dict[str, np.ndarray],
    features_dict: Dict[int, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generate pool from Model 4 if present.

    Args:
        models: Trained model pipelines and configs
        all_probabilities: Predicted probabilities from each model
        features_dict: Current feature values for all numbers

    Returns:
        pool_data dict or None if Model 4 not present
    """
    from ml_lotto.prediction.pool_generator import generate_pool_from_model

    # Find Model 4 (Intelligent Pool Generator)
    model_4_name = None
    for model_name, model_data in models.items():
        if 'Pool Generator' in model_data['config']['name']:
            model_4_name = model_name
            break

    if model_4_name is None:
        return None

    print("\n" + "="*70)
    print("GENERATING MODEL 4: CANDIDATE POOL")
    print("="*70)

    model_config = models[model_4_name]['config']
    probabilities = all_probabilities[model_4_name]

    pool_data = generate_pool_from_model(
        model_config,
        probabilities,
        features_dict
    )

    print(f"✓ Pool generated: {pool_data['pool_config']}")
    print(f"  Total candidates: {pool_data['pool_size']}")
    print(f"  Quality score: {pool_data['quality_score']:.0f}/100")

    return pool_data