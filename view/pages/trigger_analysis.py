# view/pages/trigger_analysis.py
import streamlit as st
import pandas as pd
import json
from pathlib import Path
from typing import Dict, Any, List
from view.utils.data_loader import load_trigger_data # PATH CHANGE
from view.utils.formatting import ( # PATH CHANGE
    abbreviate_series_name, expand_series_data, sort_series_names,
    THRESHOLD_RED, THRESHOLD_PURPLE, THRESHOLD_YELLOW
)


def create_html_table(display_df: pd.DataFrame, all_series_names: List[str]) -> str:
    """Create an HTML table with color-coded dates and horizontal scrolling."""
    # ... (Keep this function as is) ...
    html = """
    <div style="overflow-x: auto; max-width: 100%; border: 1px solid #ddd; border-radius: 4px;">
    <table style="border-collapse: collapse; width: 100%;">
    <thead>
        <tr style="background-color: #f0f0f0;">
    """
    
    html += "<th style='padding: 12px; text-align: left; border: 1px solid #ddd; font-weight: bold; white-space: nowrap;'>Number</th>"
    
    for col in display_df.columns:
        if col not in all_series_names:
            html += f"<th style='padding: 12px; text-align: left; border: 1px solid #ddd; font-weight: bold; white-space: nowrap;'>{col}</th>"
    
    for series_name in all_series_names:
        abbreviated = abbreviate_series_name(series_name)
        html += f"<th style='padding: 12px; text-align: center; border: 1px solid #ddd; font-weight: bold; white-space: nowrap;' title=\"{series_name}\">{abbreviated}</th>"
    
    html += "</tr>\n</thead>\n<tbody>\n"
    
    for idx, row in display_df.iterrows():
        html += "<tr style='border-bottom: 1px solid #ddd;'>\n"
        
        html += f"<td style='padding: 10px; border: 1px solid #ddd; font-weight: bold;'>{idx}</td>"
        
        for col in display_df.columns:
            if col not in all_series_names:
                value = row[col]
                html += f"<td style='padding: 10px; border: 1px solid #ddd;'>{value}</td>"
        
        for series_name in all_series_names:
            series_val = row[series_name]
            if isinstance(series_val, tuple) and len(series_val) == 2:
                date_str, color = series_val
                html += f"<td style='padding: 10px; border: 1px solid #ddd; white-space: nowrap; text-align: center;'>"
                html += f"<span style='color: {color}; font-weight: bold;'>{date_str}</span>"
                html += "</td>"
            else:
                html += f"<td style='padding: 10px; border: 1px solid #ddd; color: #999; text-align: center;'>—</td>"
        
        html += "</tr>\n"
    
    html += "</tbody>\n</table>\n</div>"
    return html


def show():
    """Display the trigger analysis page."""
    st.title("📊 Trigger Periods Analysis")

    # Load data
    trigger_df, odds_data, all_series_options, dynamic_recent_columns = load_trigger_data()

    # Load sum/range validation data
    try:
        with open('data/lotto_sum_contribution_validated.json', 'r') as f:
            sum_data = json.load(f)
        with open('data/lotto_range_spread_validated.json', 'r') as f:
            range_data = json.load(f)
    except FileNotFoundError as e:
        sum_data = None
        range_data = None

    # Load advanced patterns data (volatility/trend indicators)
    try:
        with open('data/lotto_advanced_patterns.json', 'r') as f:
            advanced_data = json.load(f)
    except FileNotFoundError:
        advanced_data = None

    # Enrich trigger_df with volatility/trend indicators
    if advanced_data:
        per_number_features = advanced_data.get('per_number_features', {})

        def get_volatility_label(volatility_value):
            """Categorize volatility into Low/Medium/High."""
            if volatility_value < 0.85:
                return "Low"
            elif volatility_value < 1.15:
                return "Med"
            else:
                return "High"

        def get_trend_label(trend_value, is_significant):
            """Categorize trend into Up/Stable/Down with significance."""
            if not is_significant:
                return "→"
            elif trend_value > 0.2:
                return "↑"
            elif trend_value < -0.2:
                return "↓"
            else:
                return "→"

        def get_momentum_label(recent_vs_baseline):
            """Categorize momentum: heating up, cooling down, stable."""
            if recent_vs_baseline > 1.2:
                return "🔥"
            elif recent_vs_baseline < 0.8:
                return "❄️"
            else:
                return "—"

        volatility_list = []
        trend_list = []
        momentum_list = []
        regime_shift_list = []

        for idx, row in trigger_df.iterrows():
            number_str = str(row['Number'])
            features = per_number_features.get(number_str, {})

            volatility = features.get('appearance_volatility', 1.0)
            trend = features.get('appearance_trend', 0.0)
            is_significant = features.get('trend_is_significant', False)
            recent_vs_baseline = features.get('recent_vs_baseline', 1.0)
            in_shift = features.get('in_regime_shift', False)

            volatility_list.append(get_volatility_label(volatility))
            trend_list.append(get_trend_label(trend, is_significant))
            momentum_list.append(get_momentum_label(recent_vs_baseline))
            regime_shift_list.append("Yes" if in_shift else "No")

        trigger_df['Volatility'] = volatility_list
        trigger_df['Trend'] = trend_list
        trigger_df['Momentum'] = momentum_list
        trigger_df['Regime Shift'] = regime_shift_list

    # Get all unique series names and sort by window size
    all_series_names = set()
    for series_data in trigger_df["Series Data"]:
        all_series_names.update(series_data.keys())
    all_series_names = sort_series_names(list(all_series_names))

    # Map freshness bin to label for display
    def freshness_bin_to_label(bin_num):
        if bin_num == 0:
            return "C0"
        elif bin_num == 1:
            return "C1"
        elif bin_num == 2:
            return "C≥2"
        else:
            return "N/A"

    # Add freshness label column
    trigger_df["Freshness"] = trigger_df["Freshness Bin"].apply(freshness_bin_to_label)

    # Define columns to display (conditionally include volatility/trend if available)
    if advanced_data:
        TRIGGER_COLUMNS = ["Category", "Freshness", "Volatility", "Trend", "Momentum", "Regime Shift", "Total Count", "Last Seen"] + dynamic_recent_columns
    else:
        TRIGGER_COLUMNS = ["Category", "Freshness", "Total Count", "Last Seen"] + dynamic_recent_columns
    
    # --- Sidebar Filters ---
    st.sidebar.header("🔍 Data Filters")

    hmc_category = st.sidebar.selectbox(
        "Select HMC Category",
        options=["All", "hot", "medium", "cold"],
        help="Filter numbers by Hot-Medium-Cold category"
    )

    freshness_weight = st.sidebar.selectbox(
        "Select Freshness Weight",
        options=["All", "C0", "C1", "C≥2"],
        help="Filter by freshness: C0 (not in last 5 draws), C1 (appeared once), C≥2 (appeared 2+ times)"
    )

    # Volatility/Trend filters (only if advanced data available)
    if advanced_data:
        volatility_filter = st.sidebar.selectbox(
            "Select Volatility Level",
            options=["All", "High", "Med", "Low"],
            help="Filter by volatility: High (unpredictable), Med (moderate), Low (consistent)"
        )

        trend_filter = st.sidebar.selectbox(
            "Select Trend Direction",
            options=["All", "↑ Trending Up", "→ Stable", "↓ Trending Down"],
            help="Filter by trend: ↑ (increasing), → (stable), ↓ (decreasing)"
        )

        momentum_filter = st.sidebar.selectbox(
            "Select Momentum",
            options=["All", "🔥 Heating Up", "— Stable", "❄️ Cooling Down"],
            help="Filter by momentum: 🔥 (appearing more), ❄️ (appearing less)"
        )

        regime_shift_filter = st.sidebar.selectbox(
            "Regime Shift Status",
            options=["All", "Yes", "No"],
            help="Filter by regime shift: numbers experiencing pattern changes"
        )
    else:
        volatility_filter = "All"
        trend_filter = "All"
        momentum_filter = "All"
        regime_shift_filter = "All"

    numbers_input = st.sidebar.text_input(
        "Enter specific numbers (e.g., 1, 12, 45)",
        value=""
    )
    entered_numbers = [num.strip() for num in numbers_input.split(",") if num.strip().isdigit()]

    series_selection = st.sidebar.selectbox(
        "Filter by Series Name",
        options=["All Series"] + all_series_options,
        help="Select a series pattern to see which numbers belong to it."
    )
    
    # --- Data Filtering Logic ---
    filtered_df = trigger_df.copy()

    # Filter by HMC category
    if hmc_category != "All":
        filtered_df = filtered_df[filtered_df["Category"] == hmc_category]

    # Filter by Freshness Weight
    if freshness_weight != "All":
        # Map freshness weight to bin number
        freshness_map = {"C0": 0, "C1": 1, "C≥2": 2}
        freshness_bin_filter = freshness_map[freshness_weight]
        filtered_df = filtered_df[filtered_df["Freshness Bin"] == freshness_bin_filter]

    # Filter by Volatility
    if advanced_data and volatility_filter != "All":
        filtered_df = filtered_df[filtered_df["Volatility"] == volatility_filter]

    # Filter by Trend
    if advanced_data and trend_filter != "All":
        trend_map = {"↑ Trending Up": "↑", "→ Stable": "→", "↓ Trending Down": "↓"}
        trend_symbol = trend_map[trend_filter]
        filtered_df = filtered_df[filtered_df["Trend"] == trend_symbol]

    # Filter by Momentum
    if advanced_data and momentum_filter != "All":
        momentum_map = {"🔥 Heating Up": "🔥", "— Stable": "—", "❄️ Cooling Down": "❄️"}
        momentum_symbol = momentum_map[momentum_filter]
        filtered_df = filtered_df[filtered_df["Momentum"] == momentum_symbol]

    # Filter by Regime Shift
    if advanced_data and regime_shift_filter != "All":
        filtered_df = filtered_df[filtered_df["Regime Shift"] == regime_shift_filter]

    # Filter by specific numbers
    if entered_numbers:
        entered_numbers_int = [int(n) for n in entered_numbers]
        filtered_df = filtered_df[filtered_df["Number"].isin(entered_numbers_int)]
    
    series_numbers = []
    if series_selection != "All Series":
        for index, row in filtered_df.iterrows():
            if series_selection in row["Series Data"]:
                series_numbers.append(row["Number"])
        
        if series_numbers:
            filtered_df = filtered_df[filtered_df["Number"].isin(series_numbers)]
        else:
            filtered_df = filtered_df[0:0]
    
    # --- Historical Scenario Results ---
    st.header("📋 Historical Scenario Results")
    st.markdown("This table shows the historical odds of a number being drawn a certain number of times within a defined window size.")
    
    scenarios_list = []
    for scenario in odds_data.get("scenarios", []):
        window = scenario.get("window_size")
        for times, result in scenario.get("results", {}).items():
            scenarios_list.append({
                "Window Size": f"Last {window} Draws",
                "Appearance": f"{times}",
                "Hit Count": result.get("hit_count", 0),
                "Total Windows": result.get("total_windows", 0),
                "Odds (Historical)": f"{result.get('odds', 0) * 100:.2f}%"
            })
    
    scenarios_df = pd.DataFrame(scenarios_list)
    if not scenarios_df.empty:
        st.dataframe(scenarios_df.set_index(["Window Size", "Appearance"]), width='stretch') # FIX: use_container_width -> width='stretch'
    else:
        st.warning("No scenario data found in lotto_odds_results.json.")
    
    st.markdown("---")

    # --- SUM/RANGE VALIDATION PANEL ---
    if sum_data and not filtered_df.empty:
        st.header("✅ Sum/Range Validation")

        sum_dist = sum_data.get('overall_distribution', {})
        sum_mean = sum_dist.get('mean', 144.87)
        sum_std = sum_dist.get('std', 30.4)
        sum_min = sum_dist.get('min', 46)
        sum_max = sum_dist.get('max', 238)

        # Calculate realistic range (mean ± 2 std deviations)
        realistic_min = max(21, sum_mean - 2 * sum_std)  # Min possible is 21 (1+2+3+4+5+6)
        realistic_max = min(267, sum_mean + 2 * sum_std)  # Max possible is 267 (42+43+44+45+46+47)

        col_sum1, col_sum2, col_sum3, col_sum4 = st.columns(4)
        with col_sum1:
            st.metric("Historical Mean Sum", f"{sum_mean:.1f}")
        with col_sum2:
            st.metric("Std Deviation", f"{sum_std:.1f}")
        with col_sum3:
            st.metric("Realistic Range", f"{realistic_min:.0f} - {realistic_max:.0f}")
        with col_sum4:
            st.metric("Actual Range", f"{sum_min} - {sum_max}")

        # If exactly 6 numbers are filtered, calculate their sum
        filtered_numbers = filtered_df['Number'].tolist()
        if len(filtered_numbers) == 6:
            selected_sum = sum(filtered_numbers)

            st.subheader(f"📊 Your Selection Sum: {selected_sum}")

            # Validate sum
            if realistic_min <= selected_sum <= realistic_max:
                st.success(f"✅ **Realistic Sum!** Your sum ({selected_sum}) falls within the expected range ({realistic_min:.0f} - {realistic_max:.0f})")
                confidence = "HIGH"
            elif sum_min <= selected_sum <= sum_max:
                st.warning(f"⚠️ **Uncommon Sum.** Your sum ({selected_sum}) is within historical bounds but outside typical range.")
                confidence = "MEDIUM"
            else:
                st.error(f"❌ **Unrealistic Sum!** Your sum ({selected_sum}) is outside all historical data ({sum_min} - {sum_max})")
                confidence = "LOW"

            # Range spread analysis
            number_range = max(filtered_numbers) - min(filtered_numbers)
            st.metric("Number Range", number_range, delta=f"From {min(filtered_numbers)} to {max(filtered_numbers)}")

            # Show distribution of numbers across 1-47
            range_bins = {
                "1-10": sum(1 for n in filtered_numbers if 1 <= n <= 10),
                "11-20": sum(1 for n in filtered_numbers if 11 <= n <= 20),
                "21-30": sum(1 for n in filtered_numbers if 21 <= n <= 30),
                "31-40": sum(1 for n in filtered_numbers if 31 <= n <= 40),
                "41-47": sum(1 for n in filtered_numbers if 41 <= n <= 47),
            }

            st.markdown("**Distribution Across Number Ranges:**")
            col_r1, col_r2, col_r3, col_r4, col_r5 = st.columns(5)
            for col, (range_label, count) in zip([col_r1, col_r2, col_r3, col_r4, col_r5], range_bins.items()):
                with col:
                    st.metric(range_label, count)

            # Overall validation summary
            st.info(f"**Validation Confidence:** {confidence}")

        elif len(filtered_numbers) > 6:
            st.info(f"📝 Select exactly 6 numbers for sum validation. Currently showing {len(filtered_numbers)} numbers.")
            if filtered_numbers:
                avg_sum = sum(filtered_numbers) / len(filtered_numbers)
                st.markdown(f"**Quick Stats:** Average value = {avg_sum:.1f}")
        else:
            st.info(f"📝 Select 6 numbers to see sum/range validation. Currently showing {len(filtered_numbers)} numbers.")

        st.markdown("---")

    # --- TRENDING/VOLATILE NUMBERS SECTION ---
    if advanced_data and not trigger_df.empty:
        st.header("🔥 Trending & Volatile Numbers")
        st.markdown("""
        **Quick Reference Lists** - Copy these numbers to use in filters or for quick analysis.
        These lists are generated from the full dataset before any filters are applied.
        """)

        per_number_features = advanced_data.get('per_number_features', {})

        # Build lists of numbers by category
        trending_up_numbers = []
        volatile_numbers = []
        regime_shift_numbers = []
        heating_up_numbers = []
        cooling_down_numbers = []

        for number_str, features in per_number_features.items():
            number = int(number_str)
            trend = features.get('appearance_trend', 0.0)
            is_significant = features.get('trend_is_significant', False)
            volatility = features.get('appearance_volatility', 1.0)
            in_shift = features.get('in_regime_shift', False)
            recent_vs_baseline = features.get('recent_vs_baseline', 1.0)

            # Trending up (significant upward trend)
            if is_significant and trend > 0.2:
                trending_up_numbers.append((number, trend))

            # High volatility
            if volatility >= 1.15:
                volatile_numbers.append((number, volatility))

            # In regime shift
            if in_shift:
                regime_shift_numbers.append(number)

            # Heating up (appearing more than baseline)
            if recent_vs_baseline > 1.2:
                heating_up_numbers.append((number, recent_vs_baseline))

            # Cooling down (appearing less than baseline)
            if recent_vs_baseline < 0.8:
                cooling_down_numbers.append((number, recent_vs_baseline))

        # Sort and display
        col_trend1, col_trend2 = st.columns(2)

        with col_trend1:
            st.subheader("📈 Trending Up Numbers")
            if trending_up_numbers:
                trending_up_numbers.sort(key=lambda x: x[1], reverse=True)
                top_trending = [num for num, _ in trending_up_numbers[:10]]
                st.markdown(f"**Top 10 (by trend strength):**")
                st.code(", ".join(str(n) for n in top_trending), language=None)
                st.caption(f"Total: {len(trending_up_numbers)} numbers trending up")
            else:
                st.info("No numbers with significant upward trends")

            st.subheader("🔥 Heating Up (Momentum)")
            if heating_up_numbers:
                heating_up_numbers.sort(key=lambda x: x[1], reverse=True)
                top_heating = [num for num, _ in heating_up_numbers[:10]]
                st.markdown(f"**Top 10 (by momentum):**")
                st.code(", ".join(str(n) for n in top_heating), language=None)
                st.caption(f"Total: {len(heating_up_numbers)} numbers heating up")
            else:
                st.info("No numbers heating up significantly")

        with col_trend2:
            st.subheader("⚡ High Volatility Numbers")
            if volatile_numbers:
                volatile_numbers.sort(key=lambda x: x[1], reverse=True)
                top_volatile = [num for num, _ in volatile_numbers[:10]]
                st.markdown(f"**Top 10 (most volatile):**")
                st.code(", ".join(str(n) for n in top_volatile), language=None)
                st.caption(f"Total: {len(volatile_numbers)} highly volatile numbers")
            else:
                st.info("No highly volatile numbers")

            st.subheader("🔄 Numbers in Regime Shift")
            if regime_shift_numbers:
                regime_shift_numbers.sort()
                st.markdown(f"**All numbers in shift:**")
                st.code(", ".join(str(n) for n in regime_shift_numbers), language=None)
                st.caption(f"Total: {len(regime_shift_numbers)} numbers in regime shift")
            else:
                st.info("No numbers in regime shift")

        # Cooling down section (full width)
        if cooling_down_numbers:
            st.subheader("❄️ Cooling Down Numbers")
            cooling_down_numbers.sort(key=lambda x: x[1])
            top_cooling = [num for num, _ in cooling_down_numbers[:10]]
            st.markdown(f"**Top 10 (coolest):**")
            st.code(", ".join(str(n) for n in top_cooling), language=None)
            st.caption(f"Total: {len(cooling_down_numbers)} numbers cooling down")

        st.markdown("---")

    # --- MAIN PAGE DISPLAY ---
    st.header("🎯 Trigger Periods Analysis Table")

    if not filtered_df.empty:
        st.markdown(f"**Displaying {len(filtered_df)} numbers.**")
        
        st.subheader("Filtered Numbers")
        st.code(", ".join(filtered_df['Number'].astype(str).tolist()))
        
        st.subheader("Detailed Trigger Statistics")
        
        display_df = filtered_df[["Number"] + TRIGGER_COLUMNS].copy()
        display_df = display_df.set_index("Number")
        
        for series_name in all_series_names:
            series_data = filtered_df["Series Data"].apply(
                lambda x: expand_series_data(x).get(series_name)
            )
            display_df[series_name] = series_data
        
        html_table = create_html_table(display_df, all_series_names)
        st.html(html_table)
        
        if series_selection != "All Series":
            st.subheader(f"Details for Series: `{series_selection}`")
            series_details = []
            for index, row in filtered_df.iterrows():
                if series_selection in row["Series Data"]:
                    for detail in row["Series Data"][series_selection]:
                        series_details.append({
                            "Number": row["Number"],
                            "Start Date": detail.get("start_date", "N/A"),
                            "End Date": detail.get("end_date", "N/A"),
                            "Count": detail.get("count", 0)
                        })
            
            series_df = pd.DataFrame(series_details)
            if not series_df.empty:
                series_df = series_df.sort_values(by="End Date", ascending=False)
                st.dataframe(series_df.set_index("Number"), width='stretch') # FIX: use_container_width -> width='stretch'
            else:
                st.info(f"No numbers matching the current filters belong to this series.")
    
    else:
        st.info("No numbers match the current selection criteria.")
    
    st.markdown("---")

    # --- Info Sections ---
    col_info1, col_info2 = st.columns(2)

    with col_info1:
        with st.expander("ℹ️ Date Color Coding Info"):
            st.markdown(f"""
            - **🔴 Red**: Less than {THRESHOLD_RED} weeks ago
            - **🟣 Purple**: {THRESHOLD_RED} to {THRESHOLD_PURPLE} weeks ago
            - **🟡 Yellow**: {THRESHOLD_PURPLE} to {THRESHOLD_YELLOW} weeks ago
            - **⚫ Black**: More than {THRESHOLD_YELLOW} weeks ago
            """)

    with col_info2:
        with st.expander("ℹ️ Freshness Weight Info"):
            st.markdown("""
            **Freshness Categories** (based on last 5 draws):
            - **C0**: Number did NOT appear in the last 5 draws
            - **C1**: Number appeared exactly ONCE in the last 5 draws
            - **C≥2**: Number appeared TWO or MORE times in the last 5 draws

            You can combine HMC and Freshness filters to find numbers that match both criteria.
            For example: Hot + C1 shows hot numbers that appeared once in the last 5 draws.
            """)

    # Additional info sections for volatility/trend
    if advanced_data:
        col_info3, col_info4 = st.columns(2)

        with col_info3:
            with st.expander("ℹ️ Volatility & Trend Info"):
                st.markdown("""
                **Volatility** (Consistency of appearance patterns):
                - **High**: Unpredictable appearance patterns (volatility ≥ 1.15)
                - **Med**: Moderate predictability (0.85 ≤ volatility < 1.15)
                - **Low**: Consistent, predictable patterns (volatility < 0.85)

                **Trend** (Direction of change over time):
                - **↑ Trending Up**: Statistically significant increase in appearances
                - **→ Stable**: No significant trend detected
                - **↓ Trending Down**: Statistically significant decrease in appearances

                Note: Trends are only shown when statistically significant (p < 0.05).
                """)

        with col_info4:
            with st.expander("ℹ️ Momentum & Regime Shift Info"):
                st.markdown("""
                **Momentum** (Recent vs baseline activity):
                - **🔥 Heating Up**: Appearing >20% more than historical baseline
                - **— Stable**: Within ±20% of baseline
                - **❄️ Cooling Down**: Appearing >20% less than baseline

                **Regime Shift**:
                - **Yes**: Number is currently experiencing a significant change in behavior pattern
                - **No**: Number is following its typical pattern

                These indicators help identify numbers undergoing phase transitions in their draw patterns.
                """)