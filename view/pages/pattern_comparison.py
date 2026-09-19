# view/pages/pattern_comparison.py
import streamlit as st
import pandas as pd
import json
from typing import Dict, Any, List, Tuple
from datetime import datetime


def load_comparison_data():
    """Load all necessary data for pattern comparison."""
    data = {}

    # Load draw history
    try:
        with open('data/lotto_draw_history.json', 'r') as f:
            data['draw_history'] = json.load(f)
    except FileNotFoundError:
        data['draw_history'] = {}

    # Load HMC data
    try:
        with open('data/lotto_hmc_categorization_validated.json', 'r') as f:
            data['hmc'] = json.load(f)
    except FileNotFoundError:
        data['hmc'] = {}

    # Load trigger data for category
    try:
        with open('data/lotto_trigger_periods.json', 'r') as f:
            data['trigger'] = json.load(f)
    except FileNotFoundError:
        data['trigger'] = {}

    # Load odd/even data
    try:
        with open('data/lotto_odd_even_validated.json', 'r') as f:
            data['odd_even'] = json.load(f)
    except FileNotFoundError:
        data['odd_even'] = {}

    # Load sum data
    try:
        with open('data/lotto_sum_contribution_validated.json', 'r') as f:
            data['sum'] = json.load(f)
    except FileNotFoundError:
        data['sum'] = {}

    return data


def get_hmc_pattern(numbers: List[int], trigger_data: Dict) -> Tuple[int, int, int]:
    """Get HMC pattern for a set of numbers."""
    hot_count = 0
    medium_count = 0
    cold_count = 0

    for num in numbers:
        category = trigger_data.get(str(num), {}).get('category', 'medium')
        if category == 'hot':
            hot_count += 1
        elif category == 'cold':
            cold_count += 1
        else:
            medium_count += 1

    return hot_count, medium_count, cold_count


def get_odd_even_pattern(numbers: List[int]) -> Tuple[int, int]:
    """Get odd/even count for a set of numbers."""
    odd_count = sum(1 for n in numbers if n % 2 == 1)
    even_count = len(numbers) - odd_count
    return odd_count, even_count


def get_range_pattern(numbers: List[int]) -> Dict[str, int]:
    """Get distribution across ranges."""
    return {
        "1-10": sum(1 for n in numbers if 1 <= n <= 10),
        "11-20": sum(1 for n in numbers if 11 <= n <= 20),
        "21-30": sum(1 for n in numbers if 21 <= n <= 30),
        "31-40": sum(1 for n in numbers if 31 <= n <= 40),
        "41-47": sum(1 for n in numbers if 41 <= n <= 47),
    }


def has_consecutive_numbers(numbers: List[int]) -> Tuple[bool, List[List[int]]]:
    """Check if there are consecutive numbers."""
    sorted_nums = sorted(numbers)
    consecutives = []
    current_seq = [sorted_nums[0]]

    for i in range(1, len(sorted_nums)):
        if sorted_nums[i] == sorted_nums[i-1] + 1:
            current_seq.append(sorted_nums[i])
        else:
            if len(current_seq) >= 2:
                consecutives.append(current_seq.copy())
            current_seq = [sorted_nums[i]]

    if len(current_seq) >= 2:
        consecutives.append(current_seq)

    return len(consecutives) > 0, consecutives


def calculate_similarity_score(pattern1: Dict, pattern2: Dict) -> float:
    """Calculate similarity score between two patterns."""
    score = 0
    max_score = 0

    # HMC pattern similarity (weight: 30)
    max_score += 30
    hmc1 = pattern1.get('hmc', (0, 0, 0))
    hmc2 = pattern2.get('hmc', (0, 0, 0))
    hmc_diff = sum(abs(a - b) for a, b in zip(hmc1, hmc2))
    score += max(0, 30 - hmc_diff * 5)

    # Odd/Even similarity (weight: 20)
    max_score += 20
    oe1 = pattern1.get('odd_even', (0, 0))
    oe2 = pattern2.get('odd_even', (0, 0))
    oe_diff = sum(abs(a - b) for a, b in zip(oe1, oe2))
    score += max(0, 20 - oe_diff * 5)

    # Sum similarity (weight: 25)
    max_score += 25
    sum1 = pattern1.get('sum', 0)
    sum2 = pattern2.get('sum', 0)
    sum_diff_pct = abs(sum1 - sum2) / max(sum1, sum2, 1) if sum1 and sum2 else 1
    score += max(0, 25 - sum_diff_pct * 100)

    # Range distribution similarity (weight: 15)
    max_score += 15
    range1 = pattern1.get('range_dist', {})
    range2 = pattern2.get('range_dist', {})
    range_diff = sum(abs(range1.get(k, 0) - range2.get(k, 0)) for k in range1.keys())
    score += max(0, 15 - range_diff * 2)

    # Consecutive numbers (weight: 10)
    max_score += 10
    cons1 = pattern1.get('has_consecutive', False)
    cons2 = pattern2.get('has_consecutive', False)
    if cons1 == cons2:
        score += 10

    return (score / max_score) * 100 if max_score > 0 else 0


def find_similar_draws(prediction_pattern: Dict, draw_history: Dict, trigger_data: Dict, top_n: int = 10) -> List[Dict]:
    """Find the most similar historical draws."""
    similarities = []

    for date_str, draw_data in draw_history.items():
        main_numbers = draw_data['main_numbers']  # direct access: a .get default hid F-25
        if len(main_numbers) != 6:
            continue

        # Calculate pattern for this historical draw
        draw_pattern = {
            'hmc': get_hmc_pattern(main_numbers, trigger_data),
            'odd_even': get_odd_even_pattern(main_numbers),
            'sum': sum(main_numbers),
            'range_dist': get_range_pattern(main_numbers),
            'has_consecutive': has_consecutive_numbers(main_numbers)[0]
        }

        # Calculate similarity
        similarity = calculate_similarity_score(prediction_pattern, draw_pattern)

        similarities.append({
            'date': date_str,
            'numbers': main_numbers,
            'bonus': draw_data['bonus_number'],
            'similarity': similarity,
            'pattern': draw_pattern
        })

    # Sort by similarity and return top N
    similarities.sort(key=lambda x: x['similarity'], reverse=True)
    return similarities[:top_n]


def show():
    """Display the Pattern Comparison page."""
    st.title("🔎 Pattern Comparison - Historical Match Finder")

    st.markdown("""
    Enter your 6-number prediction to compare it against historical winning patterns.
    This tool identifies similar past draws and helps validate your selection.
    """)

    # Input section
    st.header("🎯 Enter Your Prediction")

    numbers_input = st.text_input(
        "Enter 6 numbers (comma-separated, e.g., 5, 12, 23, 31, 42, 47)",
        help="Enter exactly 6 numbers between 1 and 47"
    )

    if not numbers_input:
        st.info("👆 Enter your 6 numbers above to start the comparison")
        return

    # Parse and validate input
    try:
        numbers = [int(n.strip()) for n in numbers_input.split(',')]
        numbers = sorted(list(set(numbers)))  # Remove duplicates and sort

        if len(numbers) != 6:
            st.error(f"❌ Please enter exactly 6 unique numbers. You entered {len(numbers)}.")
            return

        if any(n < 1 or n > 47 for n in numbers):
            st.error("❌ All numbers must be between 1 and 47.")
            return

    except ValueError:
        st.error("❌ Invalid input. Please enter numbers only, separated by commas.")
        return

    st.success(f"✅ Analyzing: **{', '.join(str(n) for n in numbers)}**")

    st.markdown("---")

    # Load data
    data = load_comparison_data()
    trigger_data = data.get('trigger', {})
    draw_history = data.get('draw_history', {})
    sum_data = data.get('sum', {})

    # Analyze prediction pattern
    st.header("📊 Your Prediction Pattern")

    hmc = get_hmc_pattern(numbers, trigger_data)
    odd_even = get_odd_even_pattern(numbers)
    total_sum = sum(numbers)
    range_dist = get_range_pattern(numbers)
    has_cons, consecutives = has_consecutive_numbers(numbers)

    prediction_pattern = {
        'hmc': hmc,
        'odd_even': odd_even,
        'sum': total_sum,
        'range_dist': range_dist,
        'has_consecutive': has_cons
    }

    # Display pattern details
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("HMC Pattern", f"{hmc[0]}H-{hmc[1]}M-{hmc[2]}C")

    with col2:
        st.metric("Odd/Even", f"{odd_even[0]} Odd / {odd_even[1]} Even")

    with col3:
        st.metric("Sum", total_sum)
        # Validate against historical mean
        sum_mean = sum_data.get('summary_statistics', {}).get('mean', 144.87)
        sum_std = sum_data.get('summary_statistics', {}).get('std', 30.4)
        realistic_min = max(21, sum_mean - 2 * sum_std)
        realistic_max = min(267, sum_mean + 2 * sum_std)
        if realistic_min <= total_sum <= realistic_max:
            st.caption("✅ Realistic")
        else:
            st.caption("⚠️ Unusual")

    with col4:
        st.metric("Consecutive", "Yes" if has_cons else "No")
        if consecutives:
            st.caption(f"{', '.join(str(c) for seq in consecutives for c in seq)}")

    # Range distribution
    st.markdown("**Range Distribution:**")
    col_r1, col_r2, col_r3, col_r4, col_r5 = st.columns(5)
    for col, (range_label, count) in zip([col_r1, col_r2, col_r3, col_r4, col_r5], range_dist.items()):
        with col:
            st.metric(range_label, count)

    st.markdown("---")

    # Find similar historical draws
    st.header("🔍 Similar Historical Draws")

    st.markdown("""
    These are the most similar historical winning draws based on pattern matching.
    Similarity is calculated using HMC pattern, odd/even ratio, sum, range distribution, and consecutive numbers.
    """)

    similar_draws = find_similar_draws(prediction_pattern, draw_history, trigger_data, top_n=15)

    if similar_draws:
        # Display top matches
        match_records = []
        for idx, match in enumerate(similar_draws):
            pattern = match['pattern']
            hmc_str = f"{pattern['hmc'][0]}H-{pattern['hmc'][1]}M-{pattern['hmc'][2]}C"
            oe_str = f"{pattern['odd_even'][0]}/{pattern['odd_even'][1]}"

            match_records.append({
                "Rank": idx + 1,
                "Date": match['date'],
                "Numbers": ', '.join(str(n) for n in match['numbers']),
                "Bonus": match['bonus'],
                "Similarity": f"{match['similarity']:.1f}%",
                "HMC": hmc_str,
                "O/E": oe_str,
                "Sum": pattern['sum'],
                "Consecutive": "Yes" if pattern['has_consecutive'] else "No"
            })

        match_df = pd.DataFrame(match_records)
        st.dataframe(match_df, width='stretch')

        # Highlight best match
        best_match = similar_draws[0]
        st.success(f"""
        🏆 **Best Match:** {best_match['date']} ({best_match['similarity']:.1f}% similar)
        **Numbers:** {', '.join(str(n) for n in best_match['numbers'])} + Bonus: {best_match['bonus']}
        """)

        # Pattern frequency analysis
        st.markdown("---")
        st.header("📈 Pattern Frequency in Historical Wins")

        # Count how often this pattern has won
        hmc_matches = sum(1 for draw in draw_history.values()
                          if get_hmc_pattern(draw['main_numbers'], trigger_data) == hmc)

        oe_matches = sum(1 for draw in draw_history.values()
                         if get_odd_even_pattern(draw['main_numbers']) == odd_even)

        total_draws = len(draw_history)

        col_freq1, col_freq2 = st.columns(2)

        with col_freq1:
            st.metric(
                "HMC Pattern Frequency",
                f"{hmc_matches}/{total_draws}",
                f"{(hmc_matches/total_draws*100):.2f}%"
            )
            st.caption(f"Pattern: {hmc[0]}H-{hmc[1]}M-{hmc[2]}C")

        with col_freq2:
            st.metric(
                "Odd/Even Pattern Frequency",
                f"{oe_matches}/{total_draws}",
                f"{(oe_matches/total_draws*100):.2f}%"
            )
            st.caption(f"Pattern: {odd_even[0]} Odd / {odd_even[1]} Even")

        # Pattern strength assessment
        st.markdown("---")
        st.header("💡 Pattern Assessment")

        assessment_score = 0
        strengths = []
        weaknesses = []

        # Assess HMC frequency
        hmc_freq_pct = (hmc_matches / total_draws * 100) if total_draws > 0 else 0
        if hmc_freq_pct >= 5:
            assessment_score += 25
            strengths.append(f"✅ HMC pattern {hmc[0]}H-{hmc[1]}M-{hmc[2]}C appears in {hmc_freq_pct:.1f}% of wins (Common)")
        elif hmc_freq_pct >= 2:
            assessment_score += 15
            strengths.append(f"✅ HMC pattern {hmc[0]}H-{hmc[1]}M-{hmc[2]}C appears in {hmc_freq_pct:.1f}% of wins (Moderate)")
        elif hmc_freq_pct > 0:
            assessment_score += 5
            weaknesses.append(f"⚠️ HMC pattern {hmc[0]}H-{hmc[1]}M-{hmc[2]}C is rare ({hmc_freq_pct:.1f}% of wins)")
        else:
            weaknesses.append(f"❌ HMC pattern {hmc[0]}H-{hmc[1]}M-{hmc[2]}C has NEVER won")

        # Assess Odd/Even
        oe_freq_pct = (oe_matches / total_draws * 100) if total_draws > 0 else 0
        if oe_freq_pct >= 10:
            assessment_score += 25
            strengths.append(f"✅ Odd/Even {odd_even[0]}/{odd_even[1]} is common ({oe_freq_pct:.1f}% of wins)")
        elif oe_freq_pct >= 5:
            assessment_score += 15
            strengths.append(f"✅ Odd/Even {odd_even[0]}/{odd_even[1]} is moderate ({oe_freq_pct:.1f}% of wins)")
        else:
            weaknesses.append(f"⚠️ Odd/Even {odd_even[0]}/{odd_even[1]} is uncommon ({oe_freq_pct:.1f}% of wins)")

        # Assess sum
        if realistic_min <= total_sum <= realistic_max:
            assessment_score += 20
            strengths.append(f"✅ Sum ({total_sum}) is within realistic range ({realistic_min:.0f}-{realistic_max:.0f})")
        else:
            weaknesses.append(f"⚠️ Sum ({total_sum}) is outside realistic range ({realistic_min:.0f}-{realistic_max:.0f})")

        # Assess top similarity
        if best_match['similarity'] >= 80:
            assessment_score += 20
            strengths.append(f"✅ Very strong match with historical win on {best_match['date']} ({best_match['similarity']:.1f}% similar)")
        elif best_match['similarity'] >= 60:
            assessment_score += 10
            strengths.append(f"✅ Good match with historical wins (best: {best_match['similarity']:.1f}% similar)")
        else:
            weaknesses.append(f"⚠️ Limited similarity to historical wins (best: {best_match['similarity']:.1f}%)")

        # Assess range distribution
        range_values = list(range_dist.values())
        if 0 not in range_values and max(range_values) <= 3:
            assessment_score += 10
            strengths.append("✅ Good range distribution across all segments")
        elif 0 in range_values:
            weaknesses.append("⚠️ Some number ranges are not covered")

        # Final verdict
        if assessment_score >= 75:
            st.success(f"🌟 **STRONG PATTERN** (Score: {assessment_score}/100)")
            st.markdown("This pattern has excellent historical precedent!")
        elif assessment_score >= 50:
            st.info(f"👍 **GOOD PATTERN** (Score: {assessment_score}/100)")
            st.markdown("This pattern shows reasonable historical alignment.")
        elif assessment_score >= 25:
            st.warning(f"⚖️ **MODERATE PATTERN** (Score: {assessment_score}/100)")
            st.markdown("This pattern has some historical support but also concerns.")
        else:
            st.error(f"⛔ **WEAK PATTERN** (Score: {assessment_score}/100)")
            st.markdown("This pattern has limited historical precedent.")

        # Show details
        if strengths:
            st.markdown("**Pattern Strengths:**")
            for strength in strengths:
                st.markdown(f"- {strength}")

        if weaknesses:
            st.markdown("**Pattern Considerations:**")
            for weakness in weaknesses:
                st.markdown(f"- {weakness}")

    else:
        st.warning("No similar historical draws found. This might indicate an unusual pattern.")
