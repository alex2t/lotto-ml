# pages/freshness_analysis.py
import streamlit as st
import pandas as pd
import json
from pathlib import Path
from typing import Dict, Any


def load_freshness_data() -> Dict[str, Any]:
    """Load freshness analysis data from JSON file."""
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
    
    # Extract metadata
    window_size = freshness_data.get("window_size_W", 5)
    recent_count_key = freshness_data.get("recent_count_key", "last_4")
    total_draws = freshness_data.get("total_draws_analyzed", 0)
    
    # Dynamic page title based on recent_count_key
    page_title = f"🔥 {recent_count_key.replace('_', ' ').title()} Freshness Analysis"
    st.title(page_title)
    
    # Description
    st.markdown(f"""
    ### Understanding Number Freshness Analysis
    
    This analysis examines **{total_draws} historical draws** to identify the most common winning combinations 
    based on how recently numbers appeared in the previous **{window_size} draws**.
    
    #### Freshness Categories:
    
    Each winning number is classified into one of four "freshness" categories based on its appearance count (C) 
    in the preceding {window_size} draws:
    
    - **C0 (Very Cold)**: The number did **NOT** appear at all in the last {window_size} draws
    - **C1 (Lukewarm)**: The number appeared **exactly once** in the last {window_size} draws
    - **C2 (Warm)**: The number appeared **exactly twice** in the last {window_size} draws
    - **C≥3 (Very Hot)**: The number appeared **3 or more times** in the last {window_size} draws, showing high activity
    
    The table below shows all observed patterns and their historical frequency.
    """)
    
    st.markdown("---")
    
    # --- Pattern Lookup Tool ---
    st.subheader("🔍 Pattern Lookup Tool")
    st.markdown("Enter the count of numbers for each freshness category to find the historical percentage:")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        c0_input = st.number_input("C0 (Very Cold)", min_value=0, max_value=7, value=3, step=1)
    with col2:
        c1_input = st.number_input("C1 (Lukewarm)", min_value=0, max_value=7, value=3, step=1)
    with col3:
        c2_input = st.number_input("C2 (Warm)", min_value=0, max_value=7, value=1, step=1)
    with col4:
        c3_input = st.number_input("C≥3 (Very Hot)", min_value=0, max_value=7, value=0, step=1)
    
    # Validate total
    total_numbers = c0_input + c1_input + c2_input + c3_input
    
    if st.button("🔎 Search Pattern", type="primary"):
        if total_numbers != 7:
            st.error(f"⚠️ Total must equal 7 numbers. Current total: {total_numbers}")
        else:
            # Search for pattern
            pattern_str = f"C0={c0_input}, C1={c1_input}, C2={c2_input}, C>=3={c3_input}"
            
            distributions = freshness_data.get("distribution_analysis_7_numbers", [])
            found_pattern = None
            
            for pattern in distributions:
                if (pattern.get("C0") == c0_input and 
                    pattern.get("C1") == c1_input and 
                    pattern.get("C2") == c2_input and 
                    pattern.get("C_ge_3") == c3_input):
                    found_pattern = pattern
                    break
            
            if found_pattern:
                st.success(f"✅ Pattern Found!")
                st.metric(
                    label="Historical Occurrence Rate",
                    value=f"{found_pattern.get('percentage', 0):.2f}%",
                    delta=f"{found_pattern.get('draws_matched', 0)} draws matched"
                )
                
                st.info(f"""
                **Pattern Details:**
                - **Pattern**: {pattern_str}
                - **Draws Matched**: {found_pattern.get('draws_matched', 0)} out of {total_draws} draws
                - **Percentage**: {found_pattern.get('percentage', 0):.2f}%
                """)
            else:
                st.warning(f"❌ Pattern `{pattern_str}` not found in historical data. This combination has never occurred in the analyzed {total_draws} draws.")
    
    st.markdown("---")
    
    # --- Full Distribution Table ---
    st.subheader("📊 Complete Freshness Pattern Distribution")
    st.markdown(f"All {len(freshness_data.get('distribution_analysis_7_numbers', []))} observed patterns from {total_draws} draws:")
    
    # Convert to DataFrame
    distributions = freshness_data.get("distribution_analysis_7_numbers", [])
    
    if distributions:
        df_data = []
        for pattern in distributions:
            df_data.append({
                "Pattern": pattern.get("pattern", "N/A"),
                "C0 (Very Cold)": pattern.get("C0", 0),
                "C1 (Lukewarm)": pattern.get("C1", 0),
                "C2 (Warm)": pattern.get("C2", 0),
                "C≥3 (Very Hot)": pattern.get("C_ge_3", 0),
                "Draws Matched": pattern.get("draws_matched", 0),
                "Percentage (%)": f"{pattern.get('percentage', 0):.2f}"
            })
        
        df = pd.DataFrame(df_data)
        
        # Sort by percentage (descending)
        df = df.sort_values(by="Draws Matched", ascending=False)
        
        # Display with formatting
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Pattern": st.column_config.TextColumn("Pattern", width="medium"),
                "C0 (Very Cold)": st.column_config.NumberColumn("C0", width="small"),
                "C1 (Lukewarm)": st.column_config.NumberColumn("C1", width="small"),
                "C2 (Warm)": st.column_config.NumberColumn("C2", width="small"),
                "C≥3 (Very Hot)": st.column_config.NumberColumn("C≥3", width="small"),
                "Draws Matched": st.column_config.NumberColumn("Draws", width="small"),
                "Percentage (%)": st.column_config.TextColumn("Percentage", width="small")
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