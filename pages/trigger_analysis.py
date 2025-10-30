# pages/trigger_analysis.py
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
    
    # Get all unique series names and sort by window size
    all_series_names = set()
    for series_data in trigger_df["Series Data"]:
        all_series_names.update(series_data.keys())
    all_series_names = sort_series_names(list(all_series_names))
    
    TRIGGER_COLUMNS = ["Category", "Total Count", "Last Seen"] + dynamic_recent_columns
    
    # --- Sidebar Filters ---
    st.sidebar.header("🔍 Data Filters")
    
    hmc_category = st.sidebar.selectbox(
        "Select HMC Category",
        options=["All", "hot", "medium", "cold"]
    )
    
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
        st.dataframe(scenarios_df.set_index(["Window Size", "Appearance"]), use_container_width=True)
    else:
        st.warning("No scenario data found in lotto_odds_results.json.")
    
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
                st.dataframe(series_df.set_index("Number"), use_container_width=True)
            else:
                st.info(f"No numbers matching the current filters belong to this series.")
    
    else:
        st.info("No numbers match the current selection criteria.")
    
    st.markdown("---")
    
    # --- Date Color Coding Info ---
    with st.expander("ℹ️ Date Color Coding Info"):
        st.markdown(f"""
        - **🔴 Red**: Less than {THRESHOLD_RED} weeks ago
        - **🟣 Purple**: {THRESHOLD_RED} to {THRESHOLD_PURPLE} weeks ago
        - **🟡 Yellow**: {THRESHOLD_PURPLE} to {THRESHOLD_YELLOW} weeks ago
        - **⚫ Black**: More than {THRESHOLD_YELLOW} weeks ago
        """)
