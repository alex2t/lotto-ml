# view/pages/statistics.py
import streamlit as st
import pandas as pd
from typing import Dict, Any
from view.utils.data_loader import load_trigger_data
from view.utils.hmc_calculator import (
    calculate_6_ball_hmc_probabilities,
    get_6_ball_pattern_breakdown
)


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

    # --- 6-BALL HMC PATTERN ANALYSIS ---
    st.markdown("---")
    st.subheader("🎯 6-Ball HMC Pattern Analysis for Players")
    st.markdown("""
    **Understanding 6-Ball Patterns:**
    - Players select **6 numbers**, but Irish Lotto draws **7 numbers** (6 main + 1 bonus)
    - When you pick 6 numbers with a specific Hot-Medium-Cold pattern, the 7th ball drawn could be:
      - **Hot** → Your 6-ball pattern becomes (H+1, M, C)
      - **Medium** → Your 6-ball pattern becomes (H, M+1, C)
      - **Cold** → Your 6-ball pattern becomes (H, M, C+1)
    - The table below shows the **combined probability** of matching any of these 7-ball outcomes
    """)

    if hmc_data:
        # Calculate all 6-ball pattern probabilities
        six_ball_results = calculate_6_ball_hmc_probabilities(hmc_data)

        # Display top 10 patterns
        st.markdown("##### Top 10 Best 6-Ball HMC Patterns")
        top_10_six_ball = six_ball_results[:10]

        six_ball_display = []
        for result in top_10_six_ball:
            six_ball_display.append({
                '6-Ball Pattern': result['pattern_6_ball'],
                'Hot': result['hot'],
                'Medium': result['medium'],
                'Cold': result['cold'],
                'Combined Probability (%)': f"{result['total_percentage']:.2f}%",
                'Total Occurrences': result['total_count']
            })

        six_ball_df = pd.DataFrame(six_ball_display)
        st.dataframe(six_ball_df, hide_index=True, width=900)

        # Interactive selector
        st.markdown("##### 🔍 Custom 6-Ball Pattern Analyzer")
        st.markdown("Select your 6-ball HMC pattern to see the detailed breakdown:")

        col1, col2, col3 = st.columns(3)
        with col1:
            hot_count = st.number_input("Hot Numbers", min_value=0, max_value=6, value=2, step=1)
        with col2:
            medium_count = st.number_input("Medium Numbers", min_value=0, max_value=6, value=2, step=1)
        with col3:
            cold_count = st.number_input("Cold Numbers", min_value=0, max_value=6, value=2, step=1)

        total_selected = hot_count + medium_count + cold_count

        if total_selected == 6:
            # Get breakdown for selected pattern
            breakdown = get_6_ball_pattern_breakdown(hot_count, medium_count, cold_count, hmc_data)

            st.success(f"✅ Pattern: **{breakdown['pattern_6_ball']}** - Combined Probability: **{breakdown['total_percentage']:.2f}%** ({breakdown['total_count']} occurrences)")

            st.markdown("**Breakdown by 7th Ball:**")
            breakdown_display = []
            for item in breakdown['breakdown']:
                breakdown_display.append({
                    'Scenario': item['scenario'],
                    '7-Ball Pattern': item['pattern_7_ball'],
                    'Probability (%)': f"{item['percentage']:.2f}%",
                    'Occurrences': item['count']
                })

            breakdown_df = pd.DataFrame(breakdown_display)
            st.dataframe(breakdown_df, hide_index=True, width=800)

            # Visual chart
            st.markdown("**Probability Distribution:**")
            chart_data = pd.DataFrame({
                'Scenario': [item['scenario'] for item in breakdown['breakdown']],
                'Percentage': [item['percentage'] for item in breakdown['breakdown']]
            })
            st.bar_chart(chart_data.set_index('Scenario'))

        elif total_selected > 6:
            st.error(f"❌ Total must equal 6. Currently: {total_selected}")
        else:
            st.warning(f"⚠️ Total must equal 6. Currently: {total_selected}")

        # Full comparison table
        with st.expander("📊 View All 6-Ball Patterns (Sorted by Probability)"):
            all_six_ball_display = []
            for result in six_ball_results:
                all_six_ball_display.append({
                    '6-Ball Pattern': result['pattern_6_ball'],
                    'Hot': result['hot'],
                    'Medium': result['medium'],
                    'Cold': result['cold'],
                    'Combined Probability (%)': f"{result['total_percentage']:.2f}%",
                    'Total Occurrences': result['total_count']
                })

            all_six_ball_df = pd.DataFrame(all_six_ball_display)
            st.dataframe(all_six_ball_df, hide_index=True, height=400)

    st.markdown("---")
    
    # --- CONSECUTIVE PATTERNS ANALYSIS ---
    st.header("🔢 Consecutive Number Patterns Analysis")
    st.markdown("Historical occurrences of consecutive number patterns, sorted by date (most recent first).")
    
    # NEW FEATURE: Display all_pairs for 2_consecutive
    consecutive_2 = odds_data.get("patterns", {}).get("2_consecutive", {})
    all_pairs = consecutive_2.get("all_pairs", {})
    
    if all_pairs:
        st.subheader("Detailed 2-Consecutive Pair Counts")
        
        pairs_list = [{"Pair": pair, "Count": count} for pair, count in all_pairs.items()]
        pairs_df = pd.DataFrame(pairs_list)
        pairs_df = pairs_df.sort_values(by="Count", ascending=False).set_index("Pair")
        
        st.dataframe(pairs_df, width='stretch') # FIX: use_container_width -> width='stretch'
        
        st.markdown("---")
    
    try:
        patterns_df = extract_patterns_data(odds_data)
        if not patterns_df.empty:
            st.dataframe(patterns_df, width=800, hide_index=True)
        else:
            st.warning("No pattern data available.")
    except Exception as e:
        st.error(f"Error extracting pattern data: {str(e)}")