# view/pages/number_insights.py
import streamlit as st
import pandas as pd
import json
from typing import Dict, Any, List
from datetime import datetime


def load_number_data(number: int) -> Dict[str, Any]:
    """Load all available data for a specific number."""
    data = {"number": number}

    # Load trigger data
    try:
        with open('data/lotto_trigger_periods.json', 'r') as f:
            trigger_data = json.load(f)
            data['trigger'] = trigger_data.get(str(number), {})
    except FileNotFoundError:
        data['trigger'] = {}

    # Load advanced patterns (volatility/trend)
    try:
        with open('data/lotto_advanced_patterns.json', 'r') as f:
            advanced_data = json.load(f)
            per_number = advanced_data.get('per_number_features', {})
            data['advanced'] = per_number.get(str(number), {})
    except FileNotFoundError:
        data['advanced'] = {}

    # Load bonus transition data
    try:
        with open('data/lotto_bonus_to_main_patterns.json', 'r') as f:
            bonus_data = json.load(f)
            per_number = bonus_data.get('per_number_analysis', {})
            data['bonus_transition'] = per_number.get(str(number), {})
    except FileNotFoundError:
        data['bonus_transition'] = {}

    # Load bonus profile
    try:
        with open('data/lotto_bonus_analysis.json', 'r') as f:
            bonus_profile_data = json.load(f)
            per_number = bonus_profile_data.get('per_number_bonus_profile', {})
            data['bonus_profile'] = per_number.get(str(number), {})
    except FileNotFoundError:
        data['bonus_profile'] = {}

    # Load draw history to get appearance timeline
    try:
        with open('data/lotto_draw_history.json', 'r') as f:
            draw_history = json.load(f)
            data['draw_history'] = draw_history
    except FileNotFoundError:
        data['draw_history'] = {}

    # Load odd/even data
    try:
        with open('data/lotto_odd_even_validated.json', 'r') as f:
            odd_even_data = json.load(f)
            per_number = odd_even_data.get('per_number_affinity', {})
            data['odd_even'] = per_number.get(str(number), {})
    except FileNotFoundError:
        data['odd_even'] = {}

    return data


def get_appearance_timeline(number: int, draw_history: Dict) -> List[Dict]:
    """Extract all appearances of a number from draw history."""
    appearances = []

    for date_str, draw_data in sorted(draw_history.items()):
        main_numbers = draw_data.get('main_numbers', [])
        bonus_number = draw_data.get('bonus_number')

        if number in main_numbers:
            appearances.append({
                'date': date_str,
                'type': 'Main',
                'position': main_numbers.index(number) + 1 if number in main_numbers else None
            })
        elif number == bonus_number:
            appearances.append({
                'date': date_str,
                'type': 'Bonus',
                'position': None
            })

    return appearances


def calculate_gap_stats(appearances: List[Dict]) -> Dict[str, Any]:
    """Calculate gap statistics between appearances."""
    if len(appearances) < 2:
        return {
            'min_gap': 0,
            'max_gap': 0,
            'avg_gap': 0,
            'current_gap': 0
        }

    gaps = []
    for i in range(1, len(appearances)):
        date1 = datetime.strptime(appearances[i-1]['date'], '%Y-%m-%d')
        date2 = datetime.strptime(appearances[i]['date'], '%Y-%m-%d')
        gap_days = (date2 - date1).days
        gaps.append(gap_days)

    # Calculate current gap (days since last appearance)
    last_appearance = datetime.strptime(appearances[-1]['date'], '%Y-%m-%d')
    current_date = datetime(2025, 11, 23)  # Current date
    current_gap = (current_date - last_appearance).days

    return {
        'min_gap': min(gaps) if gaps else 0,
        'max_gap': max(gaps) if gaps else 0,
        'avg_gap': sum(gaps) / len(gaps) if gaps else 0,
        'current_gap': current_gap,
        'gap_list': gaps
    }


def show():
    """Display the Number Insights page."""
    st.title("🔍 Number Insights - Deep Dive Analysis")

    st.markdown("""
    Select any number (1-47) to view comprehensive historical analysis, trends, and patterns.
    This tool helps identify the best numbers for your next prediction.
    """)

    # Number selector
    col1, col2 = st.columns([1, 3])

    with col1:
        selected_number = st.number_input(
            "Select Number",
            min_value=1,
            max_value=47,
            value=1,
            step=1,
            help="Choose a number between 1 and 47 to analyze"
        )

    with col2:
        st.markdown(f"### Analyzing Number: **{selected_number}**")

    st.markdown("---")

    # Load all data for the selected number
    number_data = load_number_data(selected_number)

    # === OVERVIEW SECTION ===
    st.header("📊 Overview")

    col_ov1, col_ov2, col_ov3, col_ov4 = st.columns(4)

    trigger = number_data.get('trigger', {})
    advanced = number_data.get('advanced', {})

    with col_ov1:
        total_count = trigger.get('total_count', 0)
        st.metric("Total Appearances", total_count)

    with col_ov2:
        category = trigger.get('category', 'N/A').upper()
        category_emoji = {"HOT": "🔥", "MEDIUM": "🌡️", "COLD": "❄️"}.get(category, "❓")
        st.metric("HMC Category", f"{category_emoji} {category}")

    with col_ov3:
        last_seen = trigger.get('last_seen', 'N/A')
        st.metric("Last Seen", last_seen)

    with col_ov4:
        is_odd = selected_number % 2 == 1
        st.metric("Odd/Even", "Odd" if is_odd else "Even")

    st.markdown("---")

    # === VOLATILITY & TREND SECTION ===
    if advanced:
        st.header("📈 Volatility & Trend Analysis")

        col_vt1, col_vt2, col_vt3, col_vt4 = st.columns(4)

        with col_vt1:
            volatility = advanced.get('appearance_volatility', 0)
            volatility_label = "High" if volatility >= 1.15 else "Med" if volatility >= 0.85 else "Low"
            st.metric("Volatility", volatility_label, f"{volatility:.3f}")

        with col_vt2:
            trend = advanced.get('appearance_trend', 0)
            is_significant = advanced.get('trend_is_significant', False)
            trend_label = "↑ Up" if (is_significant and trend > 0.2) else "↓ Down" if (is_significant and trend < -0.2) else "→ Stable"
            st.metric("Trend", trend_label, f"{trend:.3f}")

        with col_vt3:
            recent_vs_baseline = advanced.get('recent_vs_baseline', 1.0)
            momentum_label = "🔥 Heating" if recent_vs_baseline > 1.2 else "❄️ Cooling" if recent_vs_baseline < 0.8 else "— Stable"
            st.metric("Momentum", momentum_label, f"{recent_vs_baseline:.2f}x")

        with col_vt4:
            in_regime_shift = advanced.get('in_regime_shift', False)
            st.metric("Regime Shift", "Yes" if in_regime_shift else "No")

        # Additional advanced metrics
        col_adv1, col_adv2, col_adv3 = st.columns(3)

        with col_adv1:
            st.metric("Gap Consistency", f"{advanced.get('gap_consistency_score', 0):.2f}")
            st.caption("Higher = more predictable timing")

        with col_adv2:
            st.metric("Recent Count (Last 20)", advanced.get('recent_count', 0))
            st.caption(f"vs Older: {advanced.get('older_count', 0)}")

        with col_adv3:
            st.metric("Regime Shifts Detected", advanced.get('regime_shifts_detected', 0))
            st.caption(f"Peaks: {advanced.get('peak_count', 0)} | Troughs: {advanced.get('trough_count', 0)}")

        st.markdown("---")

    # === RECENT ACTIVITY SECTION ===
    st.header("⏱️ Recent Activity")

    recent = trigger.get('recent', {})

    col_r1, col_r2, col_r3, col_r4 = st.columns(4)

    with col_r1:
        st.metric("Last 4 Draws", recent.get('last_4', 0))

    with col_r2:
        st.metric("Last 5 Draws", recent.get('last_5', 0))

    with col_r3:
        st.metric("Last 9 Draws", recent.get('last_9', 0))

    with col_r4:
        st.metric("Last 24 Draws", recent.get('last_24', 0))

    # Freshness bin
    last_5 = recent.get('last_5', 0)
    if last_5 == 0:
        freshness = "C0 (Not in last 5)"
        freshness_color = "🟢"
    elif last_5 == 1:
        freshness = "C1 (Once in last 5)"
        freshness_color = "🟡"
    else:
        freshness = f"C≥2 ({last_5} times in last 5)"
        freshness_color = "🔴"

    st.info(f"{freshness_color} **Freshness Weight:** {freshness}")

    st.markdown("---")

    # === BONUS NUMBER ANALYSIS ===
    bonus_transition = number_data.get('bonus_transition', {})
    bonus_profile = number_data.get('bonus_profile', {})

    if bonus_transition or bonus_profile:
        st.header("🎁 Bonus Number Analysis")

        col_b1, col_b2, col_b3 = st.columns(3)

        with col_b1:
            bonus_count = bonus_profile.get('total_bonus_appearances', 0)
            main_count = bonus_profile.get('total_main_appearances', 0)
            st.metric("Bonus Appearances", bonus_count)
            st.caption(f"Main: {main_count}")

        with col_b2:
            transition_rate = bonus_transition.get('transition_rate', 0)
            st.metric("Bonus→Main Rate", f"{transition_rate*100:.1f}%")

        with col_b3:
            avg_draws = bonus_transition.get('stats', {}).get('avg_draws_to_main', 0)
            st.metric("Avg Draws to Transit", f"{avg_draws:.1f}")

        # Last bonus appearance
        last_bonus = bonus_transition.get('last_bonus_date')
        if last_bonus:
            days_since = bonus_transition.get('days_since_bonus', 0)
            st.info(f"📅 Last Bonus: {last_bonus} ({days_since} days ago)")

            if transition_rate > 0.65 and days_since < 150:
                st.success("✅ This number is a STRONG candidate for transitioning from bonus to main draw!")

        st.markdown("---")

    # === GAP ANALYSIS ===
    st.header("📏 Gap Analysis")

    appearances = get_appearance_timeline(selected_number, number_data.get('draw_history', {}))
    gap_stats = calculate_gap_stats(appearances)

    col_g1, col_g2, col_g3, col_g4 = st.columns(4)

    with col_g1:
        st.metric("Min Gap", f"{gap_stats['min_gap']} days")

    with col_g2:
        st.metric("Max Gap", f"{gap_stats['max_gap']} days")

    with col_g3:
        st.metric("Avg Gap", f"{gap_stats['avg_gap']:.1f} days")

    with col_g4:
        current_gap = gap_stats['current_gap']
        avg_gap = gap_stats['avg_gap']
        gap_delta = f"+{current_gap - avg_gap:.0f}" if current_gap > avg_gap else f"{current_gap - avg_gap:.0f}"
        st.metric("Current Gap", f"{current_gap} days", gap_delta)

    # Gap interpretation
    if avg_gap > 0:
        gap_ratio = current_gap / avg_gap
        if gap_ratio > 1.5:
            st.warning(f"⚠️ Current gap is {gap_ratio:.1f}x the average - this number is OVERDUE!")
        elif gap_ratio > 1.2:
            st.info(f"ℹ️ Current gap is {gap_ratio:.1f}x the average - slightly overdue")
        elif gap_ratio < 0.5:
            st.success(f"✅ Current gap is only {gap_ratio:.1f}x the average - recently appeared")
        else:
            st.info(f"ℹ️ Current gap is {gap_ratio:.1f}x the average - within normal range")

    st.markdown("---")

    # === TRIGGER SERIES SECTION ===
    series_data = trigger.get('series', {}).get('series', {})

    if series_data:
        st.header("🔗 Trigger Series Patterns")
        st.markdown("""
        Shows historical periods where this number appeared multiple times within a specific window.
        Useful for identifying hot streaks and pattern repetitions.
        """)

        series_records = []
        for series_name, occurrences in series_data.items():
            for occurrence in occurrences:
                series_records.append({
                    "Pattern": series_name.replace('_', ' ').title(),
                    "Start Date": occurrence.get('start_date', 'N/A'),
                    "End Date": occurrence.get('end_date', 'N/A'),
                    "Count": occurrence.get('count', 0)
                })

        if series_records:
            series_df = pd.DataFrame(series_records)
            series_df = series_df.sort_values(by='End Date', ascending=False)
            st.dataframe(series_df, width='stretch')
        else:
            st.info("No trigger series patterns detected for this number.")

    st.markdown("---")

    # === APPEARANCE HISTORY ===
    st.header("📅 Appearance History")

    st.markdown(f"""
    **Total Appearances:** {len(appearances)} (Main + Bonus)
    """)

    if appearances:
        # Recent 20 appearances
        recent_appearances = appearances[-20:][::-1]  # Last 20, reversed

        appearance_df = pd.DataFrame(recent_appearances)

        # Add gap column
        if len(appearances) >= 2:
            gaps_for_display = []
            for i in range(len(recent_appearances)):
                actual_index = len(appearances) - 1 - i
                if actual_index > 0:
                    date1 = datetime.strptime(appearances[actual_index - 1]['date'], '%Y-%m-%d')
                    date2 = datetime.strptime(appearances[actual_index]['date'], '%Y-%m-%d')
                    gap = (date2 - date1).days
                    gaps_for_display.append(gap)
                else:
                    gaps_for_display.append(None)

            appearance_df['Gap (days)'] = gaps_for_display

        appearance_df = appearance_df[['date', 'type', 'Gap (days)']].copy()
        appearance_df.columns = ['Date', 'Type', 'Gap (days)']

        st.dataframe(appearance_df, width='stretch')

        st.caption(f"Showing last 20 appearances (Total: {len(appearances)})")
    else:
        st.info("No appearance history found for this number.")

    st.markdown("---")

    # === RECOMMENDATION SECTION ===
    st.header("💡 Recommendation")

    recommendation_score = 0
    reasons = []
    warnings = []

    # Score based on various factors
    if advanced:
        # Positive factors
        if advanced.get('trend_is_significant') and advanced.get('appearance_trend', 0) > 0.2:
            recommendation_score += 20
            reasons.append("✅ Statistically significant upward trend")

        if advanced.get('recent_vs_baseline', 0) > 1.2:
            recommendation_score += 15
            reasons.append("✅ Heating up - appearing more than baseline")

        if advanced.get('in_regime_shift'):
            recommendation_score += 10
            reasons.append("✅ In regime shift - pattern changing")

        # Negative factors
        if advanced.get('appearance_trend', 0) < -0.2 and advanced.get('trend_is_significant'):
            recommendation_score -= 15
            warnings.append("⚠️ Trending down significantly")

        if advanced.get('recent_vs_baseline', 1) < 0.8:
            recommendation_score -= 10
            warnings.append("⚠️ Cooling down - appearing less than baseline")

    # Gap analysis
    if avg_gap > 0 and gap_ratio > 1.5:
        recommendation_score += 25
        reasons.append(f"✅ Overdue - current gap is {gap_ratio:.1f}x average")
    elif avg_gap > 0 and gap_ratio < 0.5:
        recommendation_score -= 20
        warnings.append(f"⚠️ Recently appeared - gap only {gap_ratio:.1f}x average")

    # Bonus transition
    if bonus_transition.get('transition_rate', 0) > 0.65 and bonus_transition.get('days_since_bonus', 999) < 150:
        recommendation_score += 15
        reasons.append("✅ Strong bonus-to-main transition candidate")

    # Freshness
    if last_5 == 0:
        recommendation_score += 5
        reasons.append("✅ Fresh - not in last 5 draws")
    elif last_5 >= 2:
        recommendation_score -= 10
        warnings.append(f"⚠️ Appeared {last_5} times in last 5 draws")

    # Final recommendation
    recommendation_score = max(0, min(100, recommendation_score + 50))  # Normalize to 0-100

    if recommendation_score >= 75:
        st.success(f"🌟 **STRONG PICK** (Score: {recommendation_score}/100)")
    elif recommendation_score >= 60:
        st.info(f"👍 **GOOD PICK** (Score: {recommendation_score}/100)")
    elif recommendation_score >= 40:
        st.warning(f"⚖️ **NEUTRAL** (Score: {recommendation_score}/100)")
    else:
        st.error(f"⛔ **AVOID** (Score: {recommendation_score}/100)")

    # Show reasons
    if reasons:
        st.markdown("**Positive Indicators:**")
        for reason in reasons:
            st.markdown(f"- {reason}")

    if warnings:
        st.markdown("**Caution Indicators:**")
        for warning in warnings:
            st.markdown(f"- {warning}")

    if not reasons and not warnings:
        st.info("No strong indicators detected. This number shows neutral characteristics.")
