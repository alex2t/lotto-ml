# view/pages/freshness_analysis.py
import streamlit as st
import pandas as pd
import json
from pathlib import Path
from typing import Dict, Any
from view.utils.freshness_calculator import (
    calculate_6_ball_freshness_probabilities,
    get_6_ball_freshness_breakdown,
    get_7_ball_freshness_details
)

def load_freshness_data() -> Dict[str, Any]:
 
    file_path = Path('data/lotto_7_number_freshness_results.json')
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        st.error(f"Freshness analysis file not found at: {file_path}")
        st.stop()
    except json.JSONDecodeError as e:
        st.error(f"Error decoding freshness analysis JSON: {str(e)}")
        st.stop()


def show():
    """Display the freshness analysis page."""
    # Load data
    freshness_data = load_freshness_data()
    
    # --- Dynamic Metadata Extraction ---
    window_size = freshness_data.get("window_size_W", 5)
    recent_count_key = freshness_data.get("recent_count_key", "last_4")
    total_draws = freshness_data.get("total_draws_analyzed", 0)
    # Get dynamic threshold C_max
    C_max = freshness_data.get("c_max_threshold", 3)
    
    # Generate bin labels dynamically
    bin_labels = {
        i: f"C{i}" for i in range(C_max)
    }
    bin_labels[C_max] = f"C≥{C_max}"
    
    # Generate JSON keys dynamically
    json_keys = {
        i: f"C{i}" for i in range(C_max)
    }
    json_keys[C_max] = f"C_GE_{C_max}"
    
    
    page_title = f"🔥 {recent_count_key.replace('_', ' ').title()} Freshness Analysis"
    st.title(page_title)
    
    # Description
    st.markdown(f"""
    ### Understanding Number Freshness Analysis
    
    This analysis examines **{total_draws} historical draws** to identify the most common winning combinations 
    based on how recently numbers appeared in the previous **{window_size} draws**.
    
    #### Freshness Categories (C = Count in Last {window_size} Draws):
    """)
    
    # Dynamic Category List Generation
    category_list_md = []
    for i in range(C_max + 1):
        label = bin_labels[i]
        
        if i == 0:
            desc = "The number did **NOT** appear at all."
        elif i < C_max:
            desc = f"The number appeared **exactly {i} time{'s' if i > 1 else ''}**."
        else:
            desc = f"The number appeared **{i} or more times** ($\text{{C}}\ge {i}$), showing high activity."
        
        category_list_md.append(f"- **{label}**: {desc}")
    
    st.markdown("\n".join(category_list_md))
    
    st.markdown("---")

    # --- Pattern Lookup Tool with 6-ball and 7-ball support ---
    st.subheader("🔍 Pattern Lookup Tool")

    # Mode selector
    mode = st.radio(
        "Select number of balls to analyze:",
        options=["6 balls (Player Selection)", "7 balls (Full Draw)"],
        horizontal=True,
        help="Choose 6 balls to see combined probability, or 7 balls to see exact match probability"
    )

    is_6_ball_mode = "6 balls" in mode
    target_total = 6 if is_6_ball_mode else 7

    if is_6_ball_mode:
        st.markdown(f"""
        **6-Ball Mode:** Enter your selection pattern. The system will calculate the combined probability
        of matching when the 7th ball (which could be any freshness category) is drawn.
        """)
    else:
        st.markdown(f"""
        **7-Ball Mode:** Enter the complete pattern to find its exact historical occurrence rate.
        """)

    # Dynamic Input Fields
    input_cols = st.columns(C_max + 1)
    input_values = {}

    # Set defaults based on mode
    if is_6_ball_mode:
        default_input_values = {0: 3, 1: 2, 2: 1}  # 6 balls total
    else:
        default_input_values = {0: 3, 1: 3, 2: 1}  # 7 balls total

    for i in range(C_max + 1):
        with input_cols[i]:
            label = bin_labels[i]
            default_value = default_input_values.get(i, 0)

            input_values[i] = st.number_input(
                label,
                min_value=0,
                max_value=7,
                value=default_value,
                step=1,
                key=f"input_c{i}_{mode}"
            )

    # Validate total
    total_numbers = sum(input_values.values())

    if st.button("🔎 Search Pattern", type="primary"):
        if total_numbers != target_total:
            st.error(f"⚠️ Total must equal {target_total} numbers. Current total: {total_numbers}")
        else:
            # Convert input_values to list for calculator
            pattern_counts = [input_values[i] for i in range(C_max + 1)]

            if is_6_ball_mode:
                # 6-ball mode: show combined probability
                try:
                    breakdown = get_6_ball_freshness_breakdown(pattern_counts, freshness_data, C_max)

                    st.success(f"✅ Pattern: **{breakdown['pattern_6_ball']}**")
                    st.metric(
                        label="Combined Probability (All possible 7th balls)",
                        value=f"{breakdown['total_percentage']:.2f}%",
                        delta=f"{breakdown['total_count']} total occurrences"
                    )

                    st.markdown("**Breakdown by 7th Ball:**")
                    breakdown_display = []
                    for item in breakdown['breakdown']:
                        breakdown_display.append({
                            'Scenario': item['scenario'],
                            '7-Ball Pattern': item['pattern_str'],
                            'Probability (%)': f"{item['percentage']:.2f}%",
                            'Occurrences': item['count']
                        })

                    breakdown_df = pd.DataFrame(breakdown_display)
                    st.dataframe(breakdown_df, hide_index=True, width=900)

                    # Visual chart
                    st.markdown("**Probability Distribution:**")
                    chart_data = pd.DataFrame({
                        'Scenario': [item['scenario'] for item in breakdown['breakdown']],
                        'Percentage': [item['percentage'] for item in breakdown['breakdown']]
                    })
                    st.bar_chart(chart_data.set_index('Scenario'))

                except Exception as e:
                    st.error(f"Error calculating pattern: {str(e)}")
            else:
                # 7-ball mode: show exact match
                try:
                    details = get_7_ball_freshness_details(pattern_counts, freshness_data, C_max)

                    if details['found']:
                        st.success(f"✅ Pattern Found!")
                        st.metric(
                            label="Historical Occurrence Rate",
                            value=f"{details['percentage']:.2f}%",
                            delta=f"{details['draws_matched']} draws matched"
                        )

                        st.info(f"""
                        **Pattern Details:**
                        - **Pattern**: {details['pattern_str']}
                        - **Draws Matched**: {details['draws_matched']} out of {total_draws} draws
                        - **Percentage**: {details['percentage']:.2f}%
                        """)
                    else:
                        st.warning(f"❌ Pattern `{details['pattern_str']}` not found in historical data. This combination has never occurred in the analyzed {total_draws} draws.")

                except Exception as e:
                    st.error(f"Error searching pattern: {str(e)}")

    # --- 6-BALL PATTERN ANALYSIS SECTION ---
    st.markdown("---")
    st.subheader("🎯 6-Ball Freshness Pattern Analysis")
    st.markdown("""
    **Understanding 6-Ball Patterns:**
    - Players select **6 numbers**, but Irish Lotto draws **7 numbers** (6 main + 1 bonus)
    - When you pick 6 numbers with a specific freshness pattern, the 7th ball drawn could be:
      - **C0** (not recently seen) → Your pattern adds one C0 number
      - **C1** (seen once recently) → Your pattern adds one C1 number
      - **C≥2** (seen frequently) → Your pattern adds one C≥2 number
    - The table below shows the **combined probability** of matching any of these 7-ball outcomes
    """)

    # Calculate all 6-ball patterns
    six_ball_results = calculate_6_ball_freshness_probabilities(freshness_data, C_max)

    # Display top 10 patterns
    st.markdown("##### Top 10 Best 6-Ball Freshness Patterns")
    top_10_six_ball = six_ball_results[:10]

    six_ball_display = []
    for result in top_10_six_ball:
        six_ball_display.append({
            '6-Ball Pattern': result['pattern_6_ball'],
            'Combined Probability (%)': f"{result['total_percentage']:.2f}%",
            'Total Occurrences': result['total_count']
        })

    six_ball_df = pd.DataFrame(six_ball_display)
    st.dataframe(six_ball_df, hide_index=True, width=800)

    # Full comparison table
    with st.expander("📊 View All 6-Ball Patterns (Sorted by Probability)"):
        all_six_ball_display = []
        for result in six_ball_results:
            all_six_ball_display.append({
                '6-Ball Pattern': result['pattern_6_ball'],
                'Combined Probability (%)': f"{result['total_percentage']:.2f}%",
                'Total Occurrences': result['total_count']
            })

        all_six_ball_df = pd.DataFrame(all_six_ball_display)
        st.dataframe(all_six_ball_df, hide_index=True, height=400)

    st.markdown("---")
    
    # --- Full Distribution Table ---
    st.subheader("📊 Complete Freshness Pattern Distribution")
    st.markdown(f"All {len(freshness_data.get('distribution_analysis_7_numbers', []))} observed patterns from {total_draws} draws:")
    
    # Convert to DataFrame
    distributions = freshness_data.get("distribution_analysis_7_numbers", [])
    
    if distributions:
        df_data = []
        
        # Dynamically create column map for display
        column_map = {}
        for i in range(C_max + 1):
            column_map[json_keys[i]] = bin_labels[i]
        
        for pattern in distributions:
            row_data = {
                "Pattern": pattern.get("pattern", "N/A"),
                "Draws Matched": pattern.get("draws_matched", 0),
                "Percentage (%)": f"{pattern.get('percentage', 0):.2f}"
            }
            
            # Map dynamic JSON keys to dynamic column labels
            for json_key, label in column_map.items():
                row_data[label] = pattern.get(json_key, 0)
                
            df_data.append(row_data)
        
        df = pd.DataFrame(df_data)
        
        # Determine final column order for display
        display_columns = ["Pattern"] + list(column_map.values()) + ["Draws Matched", "Percentage (%)"]
        df = df[display_columns]
        
        # Sort by percentage (descending)
        df = df.sort_values(by="Draws Matched", ascending=False)
        
        # Display with dynamic column configuration
        st.dataframe(
            df,
            width='stretch', # FIX: use_container_width -> width='stretch'
            hide_index=True,
            column_config={
                "Pattern": st.column_config.TextColumn("Pattern", width="medium"),
                "Draws Matched": st.column_config.NumberColumn("Draws", width="small"),
                "Percentage (%)": st.column_config.TextColumn("Percentage", width="small")
                # Dynamic C-columns will default to NumberColumn, which is fine
            }
        )
        
        # Summary statistics
        st.markdown("### 📈 Summary Statistics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Patterns Found", len(distributions))
        with col2:
            st.metric("Most Common Pattern", df.iloc[0]["Pattern"] if not df.empty else "N/A")
        with col3:
            st.metric("Highest Percentage", df.iloc[0]["Percentage (%)"] if not df.empty else "0.00")
        
    else:
        st.warning("No distribution data available.")