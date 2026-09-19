# view/pages/prediction_validator.py
import streamlit as st
import pandas as pd
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from view.utils.anomaly_detector import detect_anomalies
from view.utils.data_loader import load_high_number_distribution


def load_validation_data() -> Tuple[Dict, Dict, Dict, Dict, Dict]:
    """Load all necessary validation data files."""
    try:
        with open('data/lotto_odd_even_validated.json', 'r') as f:
            odd_even_data = json.load(f)
        with open('data/lotto_sum_contribution_validated.json', 'r') as f:
            sum_data = json.load(f)
        with open('data/lotto_odds_results.json', 'r') as f:
            odds_data = json.load(f)
        with open('data/lotto_bonus_to_main_patterns.json', 'r') as f:
            bonus_data = json.load(f)
        with open('data/lotto_trigger_periods.json', 'r') as f:
            trigger_data = json.load(f)

        return odd_even_data, sum_data, odds_data, bonus_data, trigger_data
    except FileNotFoundError as e:
        st.error(f"Required data file not found: {e}")
        return None, None, None, None, None


def validate_odd_even(numbers: List[int]) -> Tuple[str, str, float]:
    """
    Validate odd/even ratio.
    Returns: (status, message, score)
    """
    odd_count = sum(1 for n in numbers if n % 2 == 1)
    even_count = 6 - odd_count

    if 2 <= odd_count <= 4:
        return "✅", f"Realistic ratio: {odd_count} odd, {even_count} even", 100.0
    elif odd_count == 1 or odd_count == 5:
        return "⚠️", f"Uncommon ratio: {odd_count} odd, {even_count} even", 60.0
    else:
        return "❌", f"Very rare ratio: {odd_count} odd, {even_count} even", 20.0


def validate_sum(numbers: List[int], sum_data: Dict) -> Tuple[str, str, float]:
    """
    Validate sum of numbers.
    Returns: (status, message, score)
    """
    selected_sum = sum(numbers)
    sum_dist = sum_data.get('overall_distribution', {})
    sum_mean = sum_dist.get('mean', 144.87)
    sum_std = sum_dist.get('std', 30.4)
    sum_min = sum_dist.get('min', 46)
    sum_max = sum_dist.get('max', 238)

    realistic_min = max(21, sum_mean - 2 * sum_std)
    realistic_max = min(267, sum_mean + 2 * sum_std)

    if realistic_min <= selected_sum <= realistic_max:
        return "✅", f"Realistic sum: {selected_sum} (expected: {realistic_min:.0f}-{realistic_max:.0f})", 100.0
    elif sum_min <= selected_sum <= sum_max:
        return "⚠️", f"Uncommon sum: {selected_sum} (historical: {sum_min}-{sum_max})", 60.0
    else:
        return "❌", f"Unrealistic sum: {selected_sum} (outside {sum_min}-{sum_max})", 20.0


def validate_hmc_pattern(numbers: List[int], trigger_data: Dict, odds_data: Dict) -> Tuple[str, str, float]:
    """
    Validate HMC pattern distribution.
    Returns: (status, message, score)
    """
    # Count HMC distribution
    hot_count = 0
    medium_count = 0
    cold_count = 0

    for num in numbers:
        category = trigger_data.get(str(num), {}).get('category', 'unknown')
        if category == 'hot':
            hot_count += 1
        elif category == 'medium':
            medium_count += 1
        elif category == 'cold':
            cold_count += 1

    pattern = f"{hot_count}-{medium_count}-{cold_count}"

    # Check against historical HMC data
    hmc_data = odds_data.get('hmc', {})
    pattern_info = hmc_data.get(pattern, {})
    percentage = pattern_info.get('percentage', 0)

    # Get top 10 patterns
    top_10_patterns = sorted(hmc_data.items(), key=lambda x: x[1].get('count', 0), reverse=True)[:10]
    top_10_names = [p[0] for p in top_10_patterns]

    if pattern in top_10_names:
        return "✅", f"Common pattern: {pattern} ({percentage:.2f}% of draws)", 100.0
    elif percentage > 0:
        return "⚠️", f"Uncommon pattern: {pattern} ({percentage:.2f}% of draws)", 60.0
    else:
        return "❌", f"Very rare pattern: {pattern} (never observed)", 20.0


def validate_bonus_transition(numbers: List[int], bonus_data: Dict) -> Tuple[str, str, float]:
    """
    Check if selection includes recent bonus numbers.
    Returns: (status, message, score)
    """
    per_number_data = bonus_data.get('per_number_transition_profile', {})

    candidates = []
    for num in numbers:
        stats = per_number_data.get(str(num), {})
        transition_rate = stats.get('transition_rate', 0)
        days_since = stats.get('days_since_last_bonus', 999)

        if transition_rate > 0.65 and days_since < 150:
            candidates.append(num)

    if len(candidates) >= 1:
        return "✅", f"Includes {len(candidates)} high-probability bonus transition candidate(s): {candidates}", 100.0
    else:
        return "⚠️", "No recent bonus transition candidates included", 70.0


def validate_range_spread(numbers: List[int]) -> Tuple[str, str, float]:
    """
    Validate range spread across 1-47.
    Returns: (status, message, score)
    """
    number_range = max(numbers) - min(numbers)

    # Count distribution across bins
    bins = {
        "1-10": sum(1 for n in numbers if 1 <= n <= 10),
        "11-20": sum(1 for n in numbers if 11 <= n <= 20),
        "21-30": sum(1 for n in numbers if 21 <= n <= 30),
        "31-40": sum(1 for n in numbers if 31 <= n <= 40),
        "41-47": sum(1 for n in numbers if 41 <= n <= 47),
    }

    # Good spread: numbers in at least 3 different bins
    non_empty_bins = sum(1 for count in bins.values() if count > 0)

    # Check for clusters (>3 numbers in one bin)
    max_in_bin = max(bins.values())

    if non_empty_bins >= 4 and max_in_bin <= 3:
        return "✅", f"Good spread: {non_empty_bins} bins covered, range={number_range}", 100.0
    elif non_empty_bins >= 3:
        return "⚠️", f"Fair spread: {non_empty_bins} bins covered, range={number_range}", 70.0
    else:
        return "❌", f"Poor spread: {non_empty_bins} bins covered, range={number_range}", 30.0


def calculate_overall_score(scores: List[float]) -> Tuple[int, str, str]:
    """
    Calculate overall confidence score.
    Returns: (score, grade, color)
    """
    avg_score = sum(scores) / len(scores)

    if avg_score >= 90:
        return int(avg_score), "A+ Excellent", "green"
    elif avg_score >= 80:
        return int(avg_score), "A Good", "lightgreen"
    elif avg_score >= 70:
        return int(avg_score), "B Fair", "yellow"
    elif avg_score >= 60:
        return int(avg_score), "C Risky", "orange"
    else:
        return int(avg_score), "D Poor", "red"


def show_high_number_check(numbers: List[int]):
    """
    Show how many of the line's numbers are >= 32 next to how often past draws had each count.

    Information only - it is not scored. Every line is equally likely to win; numbers in the
    1-31 birthday range are only more likely to be shared with other players' tickets.
    """
    distribution = load_high_number_distribution()
    high_from = distribution['high_from']
    by_count = distribution['by_count']
    line_count = sum(1 for n in numbers if n >= high_from)
    line_stats = by_count[str(line_count)]

    st.subheader(f"6. High Numbers ({high_from} and above)")
    st.write(
        f"Your line has **{line_count}** number(s) of {high_from} or above. "
        f"{line_stats['percentage']:.1f}% of past draws had exactly that many "
        f"(a fair draw gives {line_stats['fair_percentage']:.1f}%)."
    )
    st.dataframe(
        pd.DataFrame([
            {
                f"Numbers >= {high_from}": int(k),
                "Past draws": v['count'],
                "Share of draws (%)": v['percentage'],
                "Fair draw (%)": v['fair_percentage'],
                "Your line": "<-" if int(k) == line_count else "",
            }
            for k, v in by_count.items()
        ]),
        hide_index=True,
    )
    st.caption(
        "Not scored. Every line has the same chance of winning; lines drawn mostly from 1-31 "
        "(birthday numbers) are more likely to share a prize with other players."
    )


def show():
    """Display the prediction validator page."""
    st.title("🎯 Prediction Validator")

    st.markdown("""
    **Comprehensive ML Prediction Validation Tool**

    Enter your 6 numbers (from quickpick.py or manual selection) to get instant validation
    across multiple statistical dimensions. This tool helps you identify potential issues
    before playing.
    """)

    # Load validation data
    odd_even_data, sum_data, odds_data, bonus_data, trigger_data = load_validation_data()

    if not all([odd_even_data, sum_data, odds_data, bonus_data, trigger_data]):
        st.error("Unable to load validation data. Please ensure all data files are present.")
        return

    st.markdown("---")

    # Input section
    st.header("📝 Enter Your Numbers")

    col_input1, col_input2 = st.columns([3, 1])

    with col_input1:
        numbers_input = st.text_input(
            "Enter 6 numbers (comma-separated)",
            placeholder="e.g., 5, 12, 23, 31, 42, 47",
            help="Paste numbers from quickpick.py or enter manually"
        )

    with col_input2:
        validate_button = st.button("🔍 Validate", type="primary", use_container_width=True)

    if validate_button or numbers_input:
        try:
            numbers = [int(n.strip()) for n in numbers_input.split(',') if n.strip().isdigit()]

            if len(numbers) != 6:
                st.error(f"❌ Please enter exactly 6 numbers. You entered {len(numbers)}.")
                return

            if any(n < 1 or n > 47 for n in numbers):
                st.error("❌ All numbers must be between 1 and 47.")
                return

            if len(set(numbers)) != 6:
                st.error("❌ All numbers must be unique (no duplicates).")
                return

            # Display validated numbers
            st.success(f"✅ Validating: **{', '.join(str(n) for n in sorted(numbers))}**")

            st.markdown("---")
            st.header("📊 Validation Results")

            # Run all validations
            scores = []

            # 1. Odd/Even Validation
            st.subheader("1️⃣ Odd/Even Ratio")
            status1, msg1, score1 = validate_odd_even(numbers)
            scores.append(score1)

            col1a, col1b = st.columns([1, 4])
            with col1a:
                st.metric("Status", status1)
            with col1b:
                st.write(msg1)
                st.progress(score1 / 100)

            # 2. Sum Validation
            st.subheader("2️⃣ Sum Validation")
            status2, msg2, score2 = validate_sum(numbers, sum_data)
            scores.append(score2)

            col2a, col2b = st.columns([1, 4])
            with col2a:
                st.metric("Status", status2)
            with col2b:
                st.write(msg2)
                st.progress(score2 / 100)

            # 3. HMC Pattern
            st.subheader("3️⃣ HMC Pattern")
            status3, msg3, score3 = validate_hmc_pattern(numbers, trigger_data, odds_data)
            scores.append(score3)

            col3a, col3b = st.columns([1, 4])
            with col3a:
                st.metric("Status", status3)
            with col3b:
                st.write(msg3)
                st.progress(score3 / 100)

            # 4. Bonus Transition
            st.subheader("4️⃣ Bonus Transition Check")
            status4, msg4, score4 = validate_bonus_transition(numbers, bonus_data)
            scores.append(score4)

            col4a, col4b = st.columns([1, 4])
            with col4a:
                st.metric("Status", status4)
            with col4b:
                st.write(msg4)
                st.progress(score4 / 100)

            # 5. Range Spread
            st.subheader("5️⃣ Range Spread")
            status5, msg5, score5 = validate_range_spread(numbers)
            scores.append(score5)

            col5a, col5b = st.columns([1, 4])
            with col5a:
                st.metric("Status", status5)
            with col5b:
                st.write(msg5)
                st.progress(score5 / 100)

            # 6. High numbers - information only, not part of the overall score (F-19)
            show_high_number_check(numbers)

            # Automated Anomaly Detection
            st.markdown("---")
            st.header("⚠️ Automated Anomaly Detection")

            alerts, alert_summary = detect_anomalies(numbers)

            # Display alert summary
            col_alert1, col_alert2, col_alert3, col_alert4 = st.columns(4)

            with col_alert1:
                total_alerts = len(alerts)
                st.metric("Total Alerts", total_alerts)

            with col_alert2:
                critical_count = alert_summary.get('critical', 0)
                if critical_count > 0:
                    st.metric("🚨 Critical", critical_count, delta="High Risk", delta_color="inverse")
                else:
                    st.metric("🚨 Critical", critical_count)

            with col_alert3:
                warning_count = alert_summary.get('warning', 0)
                if warning_count > 0:
                    st.metric("⚠️ Warning", warning_count, delta="Review", delta_color="off")
                else:
                    st.metric("⚠️ Warning", warning_count)

            with col_alert4:
                info_count = alert_summary.get('info', 0)
                st.metric("ℹ️ Info", info_count)

            # Display individual alerts
            if alerts:
                st.markdown("**Detected Anomalies:**")

                # Group by severity
                critical_alerts = [a for a in alerts if a['severity'] == 'critical']
                warning_alerts = [a for a in alerts if a['severity'] == 'warning']
                info_alerts = [a for a in alerts if a['severity'] == 'info']

                # Show critical alerts first
                if critical_alerts:
                    for alert in critical_alerts:
                        with st.container():
                            st.error(f"**🚨 {alert['category']}: {alert['message']}**")
                            if alert.get('details'):
                                st.caption(alert['details'])

                # Show warnings
                if warning_alerts:
                    for alert in warning_alerts:
                        with st.container():
                            st.warning(f"**⚠️ {alert['category']}: {alert['message']}**")
                            if alert.get('details'):
                                st.caption(alert['details'])

                # Show info
                if info_alerts:
                    for alert in info_alerts:
                        with st.container():
                            st.info(f"**ℹ️ {alert['category']}: {alert['message']}**")
                            if alert.get('details'):
                                st.caption(alert['details'])

            else:
                st.success("✅ **No anomalies detected!** Your selection passes all automated checks.")

            # Overall Score
            st.markdown("---")
            st.header("🏆 Overall Validation Score")

            final_score, grade, color = calculate_overall_score(scores)

            col_final1, col_final2, col_final3 = st.columns(3)

            with col_final1:
                st.metric("Final Score", f"{final_score}/100", delta=grade)

            with col_final2:
                if final_score >= 80:
                    st.success("✅ **RECOMMENDED** - Play with confidence!")
                elif final_score >= 60:
                    st.warning("⚠️ **CAUTION** - Consider adjustments")
                else:
                    st.error("❌ **NOT RECOMMENDED** - Regenerate numbers")

            with col_final3:
                st.metric("Grade", grade)

            # Detailed breakdown
            with st.expander("📋 Detailed Score Breakdown"):
                breakdown_df = pd.DataFrame({
                    'Category': ['Odd/Even Ratio', 'Sum Validation', 'HMC Pattern', 'Bonus Transition', 'Range Spread'],
                    'Status': [status1, status2, status3, status4, status5],
                    'Score': scores,
                    'Weight': ['20%', '20%', '20%', '20%', '20%']
                })
                st.dataframe(breakdown_df, hide_index=True, width=800)

            # Recommendations
            st.markdown("---")
            st.subheader("💡 Recommendations")

            if final_score < 80:
                st.markdown("**Suggested Improvements:**")

                if score1 < 100:
                    st.write("- ⚖️ Adjust odd/even ratio to 2-4 odd numbers")
                if score2 < 100:
                    st.write("- 📊 Aim for sum between 84-206")
                if score3 < 100:
                    st.write("- 🎯 Try a more common HMC pattern (check Statistics page)")
                if score4 < 100:
                    st.write("- 🎲 Include 1-2 recent bonus numbers (check Draw History)")
                if score5 < 100:
                    st.write("- 📏 Spread numbers across more ranges (1-10, 11-20, etc.)")
            else:
                st.success("✅ Your selection looks statistically sound! No improvements needed.")

        except ValueError:
            st.error("❌ Invalid input. Please enter 6 numbers separated by commas.")
        except Exception as e:
            st.error(f"❌ Error during validation: {str(e)}")

    else:
        # Show example
        st.info("👆 Enter your 6 numbers above and click 'Validate' to begin comprehensive analysis.")

        with st.expander("📖 What Gets Validated?"):
            st.markdown("""
            **1. Odd/Even Ratio**
            - Checks if you have a realistic mix of odd and even numbers
            - Optimal: 2-4 odd numbers (most common historically)

            **2. Sum Validation**
            - Verifies the sum of your 6 numbers is realistic
            - Optimal: 84-206 (mean ± 2 standard deviations)

            **3. HMC Pattern**
            - Validates your Hot-Medium-Cold distribution
            - Optimal: Matches one of the top 10 historical patterns

            **4. Bonus Transition**
            - Checks if you include recent bonus numbers
            - Optimal: 1-2 numbers with high transition probability

            **5. Range Spread**
            - Ensures numbers are well-distributed across 1-47
            - Optimal: Numbers in 4+ different range bins

            **Overall Score:**
            - A (80-100): Excellent, play with confidence
            - B (70-79): Good, minor adjustments optional
            - C (60-69): Fair, consider regenerating
            - D (<60): Poor, definitely regenerate
            """)
