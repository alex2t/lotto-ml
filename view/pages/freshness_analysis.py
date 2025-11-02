# view/pages/freshness_analysis.py
import streamlit as st
import pandas as pd
import json
from pathlib import Path
from typing import Dict, Any

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
    
    # --- Pattern Lookup Tool ---
    st.subheader("🔍 Pattern Lookup Tool")
    st.markdown(f"Enter the count of numbers for each freshness category (C0 to C≥{C_max}) to find the historical percentage:")
    
    # Dynamic Input Fields
    
    # Create columns dynamically (C_max + 1 bins)
    input_cols = st.columns(C_max + 1)
    input_values = {}
    default_input_values = {0: 3, 1: 3, 2: 1, 3: 0, 4: 0, 5: 0} # Extended defaults
    
    for i in range(C_max + 1):
        with input_cols[i]:
            label = bin_labels[i]
            # Use default values corresponding to the original C0=3, C1=3, C>=2=1 pattern
            default_value = 0
            if C_max >= 2:
                if i == 0 or i == 1:
                    default_value = 3
                elif i == C_max:
                    default_value = 1
                else:
                    default_value = 0
            
            # Use a slightly safer, generic default if C_max is small (e.g., C_max=1)
            if i == C_max and C_max <= 2:
                 default_value = 1

            # Use a pre-defined default if available
            default_value = default_input_values.get(i, 0)


            input_values[i] = st.number_input(
                label, 
                min_value=0, 
                max_value=7, 
                value=default_value, # Use dynamic default
                step=1, 
                key=f"input_c{i}"
            )
    
    # Validate total
    total_numbers = sum(input_values.values())
    
    if st.button("🔎 Search Pattern", type="primary"):
        if total_numbers != 7:
            st.error(f"⚠️ Total must equal 7 numbers. Current total: {total_numbers}")
        else:
            # Dynamically construct the pattern string and search criteria
            
            # Construct pattern_str (e.g., C0=3, C1=3, C_GE_2=1)
            search_pattern_str_parts = []
            for i in range(C_max + 1):
                label = bin_labels[i]
                search_pattern_str_parts.append(f"{label}={input_values[i]}")
            search_pattern_str = ", ".join(search_pattern_str_parts)
            
            distributions = freshness_data.get("distribution_analysis_7_numbers", [])
            found_pattern = None
            
            for pattern in distributions:
                is_match = True
                for i in range(C_max + 1):
                    # Check the input value against the corresponding dynamic JSON key
                    key = json_keys[i]
                    if pattern.get(key) != input_values[i]:
                        is_match = False
                        break
                
                if is_match:
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
                - **Pattern**: {found_pattern.get('pattern', 'N/A')}
                - **Draws Matched**: {found_pattern.get('draws_matched', 0)} out of {total_draws} draws
                - **Percentage**: {found_pattern.get('percentage', 0):.2f}%
                """)
            else:
                st.warning(f"❌ Pattern `{search_pattern_str}` not found in historical data. This combination has never occurred in the analyzed {total_draws} draws.")
    
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