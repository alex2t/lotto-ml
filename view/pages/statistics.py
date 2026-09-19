# view/pages/statistics.py
import streamlit as st
import pandas as pd
import json
from pathlib import Path
from typing import Dict, Any
from view.utils.data_loader import load_trigger_data, load_high_number_distribution
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


def show_high_number_breakdown():
    """Share of past draws with 0-6 main numbers >= 32, from drawpick.py Phase 6 (F-19)."""
    distribution = load_high_number_distribution()
    high_from = distribution['high_from']
    by_count = distribution['by_count']
    total = sum(v['count'] for v in by_count.values())

    st.header(f"High Numbers ({high_from} and above) per Draw")
    st.markdown(
        f"How many of each draw's 6 main numbers were {high_from} or above, over {total} past "
        f"draws. Numbers 1-31 are the birthday range many players pick from."
    )

    cols = st.columns(3)
    for col, k in zip(cols, ('1', '2', '3')):
        with col:
            st.metric(f"{k} number(s) >= {high_from}", f"{by_count[k]['percentage']:.1f}% of draws",
                      delta=f"{by_count[k]['count']} draws", delta_color="off")

    st.dataframe(
        pd.DataFrame([
            {
                f"Numbers >= {high_from}": int(k),
                "Draws": v['count'],
                "Share of draws (%)": v['percentage'],
                "Fair draw (%)": v['fair_percentage'],
            }
            for k, v in by_count.items()
        ]),
        hide_index=True,
    )
    st.caption(
        "Fair draw = the share expected if every number is equally likely. Past draws match it "
        "closely, so no count is more likely to win; the breakdown shows what real draws look like."
    )


def show():
    """Display the statistics page."""
    st.title("📈 Lotto Statistics")

    # Load data
    try:
        _, odds_data, _, _ = load_trigger_data()

        # Load odd/even validation data
        with open('data/lotto_odd_even_validated.json', 'r') as f:
            odd_even_data = json.load(f)
    except FileNotFoundError as e:
        st.error(f"Required data file not found: {e}")
        return
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return
    
    # --- Lotto Odds Results Display ---
    st.header("🎲 Lotto Odds Results Interpretation")
    st.markdown("This section analyzes historical draw patterns to show the probability of certain combinations of 'hot', 'medium', and 'cold' numbers occurring.")

    # --- OVERALL HMC PERCENTAGE FOR MAIN NUMBERS ---
    st.subheader("📊 Overall HMC Distribution in Main Numbers")
    st.markdown("""
    **What percentage of main numbers (across all historical draws) are Hot, Medium, or Cold?**

    This analysis counts all main numbers (6 per draw, excluding bonus) across all historical draws
    and shows the overall percentage distribution by HMC category.
    """)

    # Load draw history to calculate overall percentages
    try:
        with open('data/lotto_draw_history.json', 'r') as f:
            draw_history = json.load(f)

        # Calculate HMC percentages for main numbers only
        total_hot_main = 0
        total_medium_main = 0
        total_cold_main = 0

        for date, draw_data in draw_history.items():
            winning_numbers = draw_data.get('winning_numbers_details', [])

            for number_detail in winning_numbers:
                category = number_detail.get('category', 'medium')
                is_bonus = number_detail.get('is_bonus', False)

                # Count only main numbers (exclude bonus)
                if not is_bonus:
                    if category == 'hot':
                        total_hot_main += 1
                    elif category == 'cold':
                        total_cold_main += 1
                    else:
                        total_medium_main += 1

        total_main = total_hot_main + total_medium_main + total_cold_main

        # Calculate percentages
        hot_pct = (total_hot_main / total_main * 100) if total_main > 0 else 0
        medium_pct = (total_medium_main / total_main * 100) if total_main > 0 else 0
        cold_pct = (total_cold_main / total_main * 100) if total_main > 0 else 0

        # Display as metrics
        col_hmc1, col_hmc2, col_hmc3, col_hmc4 = st.columns(4)

        with col_hmc1:
            st.metric("🔥 Hot Numbers", f"{hot_pct:.2f}%", f"{total_hot_main} / {total_main}")

        with col_hmc2:
            st.metric("🌡️ Medium Numbers", f"{medium_pct:.2f}%", f"{total_medium_main} / {total_main}")

        with col_hmc3:
            st.metric("❄️ Cold Numbers", f"{cold_pct:.2f}%", f"{total_cold_main} / {total_main}")

        with col_hmc4:
            st.metric("Total Draws", len(draw_history), f"{total_main / len(draw_history):.0f} main/draw")

        # Visual bar chart
        st.markdown("**Visual Distribution:**")
        hmc_dist_chart = pd.DataFrame({
            'Category': ['🔥 Hot', '🌡️ Medium', '❄️ Cold'],
            'Percentage': [hot_pct, medium_pct, cold_pct]
        })
        st.bar_chart(hmc_dist_chart.set_index('Category'))

        st.info(f"""
        **Key Insight:** Across all {len(draw_history)} historical draws ({total_main} main numbers total),
        Hot numbers appear most frequently at {hot_pct:.1f}%, followed by Cold at {cold_pct:.1f}%,
        and Medium at {medium_pct:.1f}%. This suggests selecting more hot numbers may align with historical trends.
        """)

    except FileNotFoundError:
        st.warning("Draw history data not available for overall HMC percentage calculation.")
    except Exception as e:
        st.error(f"Error calculating overall HMC percentages: {str(e)}")

    st.markdown("---")

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

    # --- ODD/EVEN ANALYSIS ---
    st.header("⚖️ Odd/Even Pattern Analysis")
    st.markdown("""
    **What past draws looked like:**
    - Most draws have 2-4 odd numbers
    - Historical data shows balanced distribution (≈50/50)
    - Some numbers have statistical preference for odd/even draws
    - Use this to validate your number selections
    """)

    # Overall Distribution
    overall_dist = odd_even_data.get('overall_distribution_test', {})

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Odd Numbers %",
            f"{overall_dist.get('odd_percentage', 0):.2f}%",
            delta=f"{overall_dist.get('total_odd', 0)} total"
        )
    with col2:
        st.metric(
            "Even Numbers %",
            f"{overall_dist.get('even_percentage', 0):.2f}%",
            delta=f"{overall_dist.get('total_even', 0)} total"
        )
    with col3:
        is_balanced = overall_dist.get('significant', False)
        balance_status = "Balanced ✅" if not is_balanced else "Imbalanced ⚠️"
        st.metric(
            "Distribution",
            balance_status,
            delta=f"p={overall_dist.get('p_value', 1):.4f}"
        )

    st.info(f"📊 {overall_dist.get('interpretation', 'No interpretation available')}")

    # Per-Number Affinity Analysis
    st.subheader("🎯 Per-Number Odd/Even Affinity")
    st.markdown("""
    Numbers with **statistically validated** preference (p < 0.05) are highlighted.
    - **Aligned**: Number's parity matches its preferred draw type
    - **Affinity Score > 0.75**: Strong preference for odd/even draws
    """)

    affinity_data = odd_even_data.get('per_number_affinity', {})

    affinity_list = []
    for number, stats in affinity_data.items():
        affinity_list.append({
            'Number': int(number),
            'Parity': stats.get('number_parity', 'N/A').upper(),
            'Preferred Type': stats.get('preferred_type', 'N/A').upper(),
            'Affinity Score': f"{stats.get('affinity_score', 0):.3f}",
            'Validated': '✅' if stats.get('statistically_validated', False) else '',
            'Alignment': stats.get('alignment', 'N/A').capitalize(),
            'p-value': f"{stats.get('p_value_adjusted', 1):.6f}"
        })

    affinity_df = pd.DataFrame(affinity_list)
    affinity_df = affinity_df.sort_values(by='Number')

    # Filter options
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        show_validated_only = st.checkbox("Show only statistically validated numbers", value=False)
    with col_filter2:
        min_affinity = st.slider("Minimum affinity score", 0.0, 1.0, 0.0, 0.05)

    display_affinity_df = affinity_df.copy()
    if show_validated_only:
        display_affinity_df = display_affinity_df[display_affinity_df['Validated'] == '✅']

    display_affinity_df['Affinity Score'] = display_affinity_df['Affinity Score'].astype(float)
    display_affinity_df = display_affinity_df[display_affinity_df['Affinity Score'] >= min_affinity]
    display_affinity_df['Affinity Score'] = display_affinity_df['Affinity Score'].apply(lambda x: f"{x:.3f}")

    st.dataframe(
        display_affinity_df,
        hide_index=True,
        width='stretch',
        column_config={
            'Number': st.column_config.NumberColumn('Number', width='small'),
            'Affinity Score': st.column_config.TextColumn('Affinity Score', width='small'),
            'Validated': st.column_config.TextColumn('Validated', width='small'),
        }
    )

    # Validation Helper
    with st.expander("🔍 Validate Your Number Selection"):
        st.markdown("Enter your 6 numbers to check their odd/even distribution:")

        validation_input = st.text_input(
            "Enter 6 numbers (comma-separated)",
            placeholder="e.g., 5, 12, 23, 31, 42, 47"
        )

        if validation_input:
            try:
                selected_numbers = [int(n.strip()) for n in validation_input.split(',') if n.strip().isdigit()]

                if len(selected_numbers) == 6:
                    odd_count = sum(1 for n in selected_numbers if n % 2 == 1)
                    even_count = 6 - odd_count

                    odd_pct = (odd_count / 6) * 100
                    even_pct = (even_count / 6) * 100

                    col_val1, col_val2, col_val3 = st.columns(3)
                    with col_val1:
                        st.metric("Odd Numbers", odd_count, delta=f"{odd_pct:.1f}%")
                    with col_val2:
                        st.metric("Even Numbers", even_count, delta=f"{even_pct:.1f}%")
                    with col_val3:
                        # How common the ratio has been
                        if (odd_count >= 2 and odd_count <= 4):
                            st.success("✅ Common ratio")
                        elif (odd_count == 1 or odd_count == 5):
                            st.warning("⚠️ Uncommon ratio")
                        else:
                            st.error("❌ Very rare ratio")

                    # Show affinity scores for selected numbers
                    st.markdown("**Selected Numbers' Affinity:**")
                    selected_affinity = affinity_df[affinity_df['Number'].isin(selected_numbers)]
                    st.dataframe(selected_affinity, hide_index=True, width=800)

                elif len(selected_numbers) > 0:
                    st.warning(f"Please enter exactly 6 numbers. Currently: {len(selected_numbers)}")
            except Exception as e:
                st.error(f"Invalid input: {str(e)}")

    st.markdown("---")

    show_high_number_breakdown()
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