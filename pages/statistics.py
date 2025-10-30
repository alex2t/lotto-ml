# pages/statistics.py
import streamlit as st
import pandas as pd
from typing import Dict, Any
from utils.data_loader import load_trigger_data


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
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.sort_values(by='Date', ascending=False)
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
        return df
    else:
        return pd.DataFrame()


def show():
    """Display the statistics page."""
    st.title("📈 Lotto Statistics")
    
    # Load data
    try:
        _, odds_data, _, _ = load_trigger_data()
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return
    
    # --- Lotto Odds Results Display ---
    st.header("🎲 Lotto Odds Results Interpretation")
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
        st.dataframe(top_5_hmc.set_index('Pattern (H-M-C)'), width=800)
        
        st.markdown("##### Full HMC Distribution Chart")
        st.bar_chart(hmc_df.set_index('Pattern (H-M-C)')['Calculated Percentage'])
    else:
        st.warning("No HMC data available.")
    
    st.markdown("---")
    
    # --- CONSECUTIVE PATTERNS ANALYSIS ---
    st.header("🔢 Consecutive Number Patterns Analysis")
    st.markdown("Historical occurrences of consecutive number patterns, sorted by date (most recent first).")
    
    try:
        patterns_df = extract_patterns_data(odds_data)
        if not patterns_df.empty:
            st.dataframe(patterns_df, width=800, hide_index=True)
        else:
            st.warning("No pattern data available.")
    except Exception as e:
        st.error(f"Error extracting pattern data: {str(e)}")

