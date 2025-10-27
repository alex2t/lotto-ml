import streamlit as st
import pandas as pd
from typing import Dict, Any, List
from utils.data_loader import load_trigger_data
from utils.formatting import (
    abbreviate_series_name, expand_series_data, sort_series_names,
    THRESHOLD_RED, THRESHOLD_PURPLE, THRESHOLD_YELLOW
)


def create_html_table(display_df: pd.DataFrame, all_series_names: List[str]) -> str:
    """Create an HTML table with color-coded dates and horizontal scrolling."""
    # Using triple quotes here is safe since they are defined directly inside this file,
    # not as a string inside another string (the installer script).
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


def extract_patterns_data(odds_data: Dict[str, Any]) -> pd.DataFrame:
    """Extract and format pattern data from odds_data for display."""
    patterns_data = odds_data.get("patterns", {})
    all_records = []
    
    for pattern_name, pattern_info in patterns_data.items():
        odds_percentage = pattern_info.get("odds", 0) * 100
        
        for occurrence in pattern_info.get("last20", []):
            date_str = occurrence.get("date", "N/A")
            numbers = occurrence.get("numbers", [])
            numbers_str = ", ".join(map(str, numbers))
            
            all_records.append({
                "Date": date_str,
                "Pattern": pattern_name.replace("_", " ").title(),
                "Numbers": numbers_str,
                "Odds (%)": f"{odds_percentage:.2f}"
            })
    
    if all_records:
        df = pd.DataFrame(all_records)
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values(by='Date', ascending=False)
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
        return df
    else:
        return pd.DataFrame()


def show():
    """Display the trigger analysis page."""
    st.title("🎰 Lotto Analysis Dashboard")
    
    with st.expander("ℹ️ Date Color Coding Info"):
        st.markdown(f"""
        - **🔴 Red**: Less than {THRESHOLD_RED} weeks ago
        - **🟣 Purple**: {THRESHOLD_RED} to {THRESHOLD_PURPLE} weeks ago
        - **🟡 Yellow**: {THRESHOLD_PURPLE} to {THRESHOLD_YELLOW} weeks ago
        - **⚫ Black**: More than {THRESHOLD_YELLOW} weeks ago
        """)
    
    # Load data
    trigger_df, odds_data, all_series_options, dynamic_recent_columns = load_trigger_data()
    
    # Get all unique series names and sort by window size
    all_series_names = set()
    for series_data in trigger_df["Series Data"]:
        all_series_names.update(series_data.keys())
    all_series_names = sort_series_names(list(all_series_names))
    
    TRIGGER_COLUMNS = ["Category", "Total Count", "Last Seen"] + dynamic_recent_columns
    
    # --- Sidebar Filters ---
    st.sidebar.header("Data Filters")
    
    hmc_category = st.sidebar.selectbox(
        "1. Select HMC Category",
        options=["All", "hot", "medium", "cold"]
    )
    
    numbers_input = st.sidebar.text_input(
        "2. Enter specific numbers (e.g., 1, 12, 45)",
        value=""
    )
    entered_numbers = [num.strip() for num in numbers_input.split(",") if num.strip().isdigit()]
    
    series_selection = st.sidebar.selectbox(
        "3. Filter by Series Name",
        options=["All Series"] + all_series_options,
        help="Select a series pattern to see which numbers belong to it."
    )
    
    # --- Data Filtering Logic ---
    filtered_df = trigger_df.copy()
    if hmc_category != "All":
        filtered_df = filtered_df[filtered_df["Category"] == hmc_category]
    
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
    
    # --- CONSECUTIVE PATTERNS ANALYSIS ---
    st.header("Consecutive Number Patterns Analysis")
    st.markdown("Historical occurrences of consecutive number patterns, sorted by date (most recent first).")
    
    patterns_df = extract_patterns_data(odds_data)
    if not patterns_df.empty:
        # FIX 2A: use_container_width=True -> width='stretch'
        st.dataframe(patterns_df, width='stretch', hide_index=True)
    else:
        st.warning("No pattern data available.")
    
    # --- MAIN PAGE DISPLAY ---
    st.header("Trigger Periods Analysis")
    
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
                # FIX 2B: use_container_width=True -> width='stretch'
                st.dataframe(series_df.set_index("Number"), width='stretch')
            else:
                st.info(f"No numbers matching the current filters belong to this series.")
    
    else:
        st.info("No numbers match the current selection criteria.")
    
    # --- Odds Results Display ---
    st.header("Lotto Odds Results Interpretation")
    st.markdown("This section analyzes historical draw patterns to show the probability of certain combinations of 'hot', 'medium', and 'cold' numbers occurring.")
    
    st.subheader("HMC (Hot-Medium-Cold) Distribution")
    
    hmc_data = odds_data.get("hmc", {})
    if hmc_data:
        hmc_list = []
        for pattern, metrics in hmc_data.items():
            hmc_list.append({
                'Pattern (H-M-C)': pattern,
                'Count': metrics.get('count', 0),
                'Original Percentage': metrics.get('percentage', 0.0)
            })
        
        hmc_df = pd.DataFrame(hmc_list)
        hmc_df['Count'] = pd.to_numeric(hmc_df['Count'], errors='coerce').fillna(0)
        
        total_count = hmc_df['Count'].sum()
        
        if total_count > 0:
            hmc_df['Calculated Percentage'] = hmc_df['Count'] / total_count
        else:
            hmc_df['Calculated Percentage'] = 0.0
        
        top_5_hmc = hmc_df.sort_values(by='Count', ascending=False).head(5)
        
        st.markdown("##### Top 5 Most Frequent HMC Patterns (Hot-Medium-Cold)")
        # FIX 2C: use_container_width=True -> width='stretch'
        st.dataframe(top_5_hmc.set_index('Pattern (H-M-C)'), width='stretch')
        
        st.markdown("##### Full HMC Distribution Chart")
        st.bar_chart(hmc_df.set_index('Pattern (H-M-C)')['Calculated Percentage'])
    
    st.subheader("Historical Scenario Results")
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
        # FIX 2D: use_container_width=True -> width='stretch'
        st.dataframe(scenarios_df.set_index(["Window Size", "Appearance"]), width='stretch')
    else:
        st.warning("No scenario data found in lotto_odds_results.json.")