# view/pages/post_draw_analysis.py
import streamlit as st
import pandas as pd
import json
from typing import List, Dict, Set, Tuple, Any


def load_analysis_data() -> Dict[str, Any]:
    """Load all necessary data for post-draw analysis."""
    data = {}

    try:
        with open('data/lotto_trigger_periods.json', 'r') as f:
            data['trigger'] = json.load(f)
    except FileNotFoundError:
        data['trigger'] = {}

    try:
        with open('data/lotto_advanced_patterns.json', 'r') as f:
            data['advanced'] = json.load(f)
    except FileNotFoundError:
        data['advanced'] = {}

    return data


def load_latest_draw_from_csv(csv_path: str = 'data/irish500.csv'):
    """Load the most recent draw from the CSV file (chronologically sorted)."""
    from datetime import datetime
    try:
        draws = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            lines = [l.strip() for l in f if l.strip()]
        for line in lines[1:]:
            parts = line.split(',')
            if len(parts) >= 8:
                date_str = parts[0].strip()
                dt = None
                for fmt in ("%d %b %Y", "%Y-%m-%d", "%d/%m/%Y"):
                    try:
                        dt = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        pass
                if dt:
                    main_nums = [int(p.strip()) for p in parts[1:7]]
                    bonus_num = int(parts[7].strip())
                    draws.append({'dt': dt, 'date': date_str, 'main': main_nums, 'bonus': bonus_num})
        if draws:
            draws.sort(key=lambda x: x['dt'], reverse=True)
            latest = draws[0]
            return {'date': latest['date'], 'main': latest['main'], 'bonus': latest['bonus']}
    except Exception:
        pass
    return None


def load_latest_predictions_from_picks(picks_path: str = 'lottery_picks.txt'):
    """Extract Model 4's candidate pool or predictions from lottery_picks.txt."""
    import re
    try:
        with open(picks_path, 'r', encoding='utf-8') as f:
            content = f.read()
        pool_match = re.search(r'Full Pool \(ranked by probability\):\s*\[(.*?)\]', content)
        if pool_match:
            nums = [int(n.strip()) for n in pool_match.group(1).split(',') if n.strip().isdigit()]
            if nums:
                return nums
    except Exception:
        pass
    return None


def get_number_details(number: int, trigger_data: Dict, advanced_data: Dict) -> Dict[str, Any]:
    """Get detailed information about a specific number."""
    trigger_info = trigger_data.get(str(number), {})
    advanced_info = advanced_data.get('per_number_features', {}).get(str(number), {})

    # Get HMC category
    category = trigger_info.get('category', 'N/A').upper()

    # Get recent activity
    recent = trigger_info.get('recent', {})
    last_5 = recent.get('last_5', 0)

    # Determine freshness weight
    if last_5 == 0:
        freshness = "C0"
    elif last_5 == 1:
        freshness = "C1"
    else:
        freshness = f"C≥2 ({last_5})"

    # Get volatility/trend
    volatility = advanced_info.get('appearance_volatility', 0)
    if volatility >= 1.15:
        volatility_label = "High"
    elif volatility >= 0.85:
        volatility_label = "Med"
    else:
        volatility_label = "Low"

    trend = advanced_info.get('appearance_trend', 0)
    is_significant = advanced_info.get('trend_is_significant', False)
    if is_significant and trend > 0.2:
        trend_label = "↑ Up"
    elif is_significant and trend < -0.2:
        trend_label = "↓ Down"
    else:
        trend_label = "→ Stable"

    momentum = advanced_info.get('recent_vs_baseline', 1.0)
    if momentum > 1.2:
        momentum_label = "🔥 Heating"
    elif momentum < 0.8:
        momentum_label = "❄️ Cooling"
    else:
        momentum_label = "— Stable"

    return {
        'number': number,
        'hmc': category,
        'freshness': freshness,
        'last_4': recent.get('last_4', 0),
        'last_5': last_5,
        'last_9': recent.get('last_9', 0),
        'last_24': recent.get('last_24', 0),
        'last_seen': trigger_info.get('last_seen', 'N/A'),
        'total_count': trigger_info.get('total_count', 0),
        'volatility': volatility_label,
        'trend': trend_label,
        'momentum': momentum_label
    }


def analyze_predictions(winning_main: List[int], winning_bonus: int, predictions: List[int],
                       trigger_data: Dict, advanced_data: Dict) -> Dict[str, Any]:
    """
    Analyze model predictions against actual winning numbers.

    Returns detailed analysis including correct predictions, missed numbers, and statistics.
    """
    winning_main_set = set(winning_main)
    predictions_set = set(predictions)

    # Find correct predictions (intersection with main numbers)
    correct_predictions = winning_main_set.intersection(predictions_set)

    # Find missed numbers (main numbers not in predictions)
    missed_numbers = winning_main_set - predictions_set

    # Check if bonus was predicted
    bonus_predicted = winning_bonus in predictions_set

    # Numbers predicted but didn't win
    wrong_predictions = predictions_set - winning_main_set
    if winning_bonus in wrong_predictions:
        wrong_predictions.remove(winning_bonus)  # Remove bonus from wrong predictions

    # Get details for each category
    correct_details = [get_number_details(num, trigger_data, advanced_data) for num in sorted(correct_predictions)]
    missed_details = [get_number_details(num, trigger_data, advanced_data) for num in sorted(missed_numbers)]
    wrong_details = [get_number_details(num, trigger_data, advanced_data) for num in sorted(wrong_predictions)]

    # Calculate statistics
    total_main_numbers = len(winning_main)
    correct_count = len(correct_predictions)
    accuracy = (correct_count / total_main_numbers * 100) if total_main_numbers > 0 else 0

    # Analyze HMC distribution of correct predictions
    hmc_correct = {'HOT': 0, 'MEDIUM': 0, 'COLD': 0}
    for detail in correct_details:
        hmc = detail['hmc']
        if hmc in hmc_correct:
            hmc_correct[hmc] += 1

    # Analyze HMC distribution of missed numbers
    hmc_missed = {'HOT': 0, 'MEDIUM': 0, 'COLD': 0}
    for detail in missed_details:
        hmc = detail['hmc']
        if hmc in hmc_missed:
            hmc_missed[hmc] += 1

    return {
        'correct_predictions': correct_predictions,
        'correct_details': correct_details,
        'correct_count': correct_count,
        'missed_numbers': missed_numbers,
        'missed_details': missed_details,
        'missed_count': len(missed_numbers),
        'bonus_predicted': bonus_predicted,
        'bonus_number': winning_bonus,
        'bonus_details': get_number_details(winning_bonus, trigger_data, advanced_data) if winning_bonus else None,
        'wrong_predictions': wrong_predictions,
        'wrong_details': wrong_details,
        'wrong_count': len(wrong_predictions),
        'accuracy': accuracy,
        'total_predictions': len(predictions),
        'total_main_numbers': total_main_numbers,
        'hmc_correct': hmc_correct,
        'hmc_missed': hmc_missed
    }


def show():
    """Display the Post Draw Analysis page."""
    st.title("📊 Post Draw Analysis - Model Performance Evaluation")

    st.markdown("""
    **Evaluate your Model 4 predictions against actual draw results.**

    Enter the 7 winning numbers from the recent draw and your model's predictions to see:
    - ✅ Which numbers were correctly predicted
    - ❌ Which winning numbers were missed
    - 🎁 Whether the bonus number was predicted
    - 📈 Detailed HMC, freshness, and trend analysis for each number
    """)

    st.markdown("---")

    # Quick Load Section
    latest_draw = load_latest_draw_from_csv()
    latest_preds = load_latest_predictions_from_picks()

    st.subheader("⚡ Quick Load & Autofill")
    col_ql1, col_ql2 = st.columns([2, 1])
    with col_ql1:
        if latest_draw:
            st.info(f"📅 **Latest draw in dataset:** {latest_draw['date']} — **Main:** {', '.join(str(n) for n in sorted(latest_draw['main']))} | **Bonus:** {latest_draw['bonus']}")
        else:
            st.warning("⚠️ No draw data found in data/irish500.csv")
    with col_ql2:
        if st.button("📥 Autofill from Latest Draw & Predictions", use_container_width=True):
            if latest_draw:
                st.session_state["input_main_numbers"] = ', '.join(str(n) for n in sorted(latest_draw['main']))
                st.session_state["input_bonus_number"] = str(latest_draw['bonus'])
            if latest_preds:
                st.session_state["input_predictions"] = ', '.join(str(n) for n in latest_preds)
                st.session_state["input_prediction_count"] = len(latest_preds)
            st.rerun()

    # Input Section
    st.header("📝 Enter Draw Results")

    # Initialize session state keys directly matching widget keys
    if 'input_main_numbers' not in st.session_state:
        st.session_state['input_main_numbers'] = ""
    if 'input_bonus_number' not in st.session_state:
        st.session_state['input_bonus_number'] = ""
    if 'input_prediction_count' not in st.session_state:
        st.session_state['input_prediction_count'] = 20
    if 'input_predictions' not in st.session_state:
        st.session_state['input_predictions'] = ""

    col_input1, col_input2 = st.columns(2)

    with col_input1:
        st.subheader("🎯 Winning Numbers")
        winning_main_input = st.text_input(
            "Enter 6 Main Winning Numbers (comma-separated)",
            key="input_main_numbers",
            placeholder="e.g., 5, 12, 23, 31, 42, 47",
            help="Enter the 6 main numbers that were drawn"
        )

        winning_bonus_input = st.text_input(
            "Enter Bonus Number",
            key="input_bonus_number",
            placeholder="e.g., 15",
            help="Enter the bonus number"
        )

    with col_input2:
        st.subheader("🤖 Model 4 Predictions")
        prediction_count = st.number_input(
            "Number of Predictions",
            min_value=1,
            max_value=47,
            step=1,
            key="input_prediction_count",
            help="How many numbers did Model 4 predict? (Default: 20)"
        )

        predictions_input = st.text_input(
            f"Enter {prediction_count} Predicted Numbers (comma-separated)",
            key="input_predictions",
            placeholder="e.g., 1, 3, 5, 7, 9, 11, ...",
            help=f"Enter the {prediction_count} numbers predicted by Model 4"
        )

    # Analyze Button
    st.markdown("---")
    analyze_button = st.button("🔍 Analyze Results", type="primary", use_container_width=True)

    if analyze_button or (winning_main_input and winning_bonus_input and predictions_input):
        # Parse and validate inputs
        try:
            # Parse main winning numbers
            winning_main = [int(n.strip()) for n in winning_main_input.split(',') if n.strip().isdigit()]

            if len(winning_main) != 6:
                st.error(f"❌ Please enter exactly 6 main winning numbers. You entered {len(winning_main)}.")
                return

            if any(n < 1 or n > 47 for n in winning_main):
                st.error("❌ All main winning numbers must be between 1 and 47.")
                return

            if len(set(winning_main)) != 6:
                st.error("❌ Main winning numbers must be unique (no duplicates).")
                return

            # Parse bonus number
            try:
                winning_bonus = int(winning_bonus_input.strip())
                if winning_bonus < 1 or winning_bonus > 47:
                    st.error("❌ Bonus number must be between 1 and 47.")
                    return
                if winning_bonus in winning_main:
                    st.error("❌ Bonus number cannot be the same as any main number.")
                    return
            except ValueError:
                st.error("❌ Invalid bonus number. Please enter a single number.")
                return

            # Parse predictions
            predictions = [int(n.strip()) for n in predictions_input.split(',') if n.strip().isdigit()]

            if len(predictions) == 0:
                st.error("❌ Please enter at least one prediction.")
                return

            if any(n < 1 or n > 47 for n in predictions):
                st.error("❌ All predictions must be between 1 and 47.")
                return

            if len(set(predictions)) != len(predictions):
                st.warning("⚠️ Predictions contain duplicates. Using unique values only.")
                predictions = list(set(predictions))

            # Display what we're analyzing
            st.success(f"""
            ✅ **Analysis Ready**
            - Main Winning Numbers: {', '.join(str(n) for n in sorted(winning_main))}
            - Bonus Number: {winning_bonus}
            - Model 4 Predictions: {len(predictions)} numbers
            """)

            st.markdown("---")

            # Load data
            data = load_analysis_data()
            trigger_data = data.get('trigger', {})
            advanced_data = data.get('advanced', {})

            # Perform analysis
            analysis = analyze_predictions(
                winning_main,
                winning_bonus,
                predictions,
                trigger_data,
                advanced_data
            )

            # === PERFORMANCE SUMMARY ===
            st.header("🏆 Performance Summary")

            col_perf1, col_perf2, col_perf3, col_perf4 = st.columns(4)

            with col_perf1:
                st.metric(
                    "Accuracy",
                    f"{analysis['accuracy']:.1f}%",
                    f"{analysis['correct_count']}/{analysis['total_main_numbers']}"
                )

            with col_perf2:
                st.metric(
                    "Correct Predictions",
                    analysis['correct_count'],
                    delta="✅" if analysis['correct_count'] > 0 else None
                )

            with col_perf3:
                st.metric(
                    "Missed Numbers",
                    analysis['missed_count'],
                    delta="❌" if analysis['missed_count'] > 0 else None,
                    delta_color="inverse"
                )

            with col_perf4:
                bonus_status = "✅ Yes" if analysis['bonus_predicted'] else "❌ No"
                st.metric("Bonus Predicted", bonus_status)

            # Performance assessment
            if analysis['accuracy'] >= 83:  # 5 or 6 correct
                st.success(f"🌟 **EXCELLENT!** Model 4 predicted {analysis['correct_count']} out of 6 main numbers correctly!")
            elif analysis['accuracy'] >= 50:  # 3 or 4 correct
                st.info(f"👍 **GOOD!** Model 4 predicted {analysis['correct_count']} out of 6 main numbers correctly.")
            elif analysis['accuracy'] >= 33:  # 2 correct
                st.warning(f"⚖️ **FAIR.** Model 4 predicted {analysis['correct_count']} out of 6 main numbers correctly.")
            else:  # 0 or 1 correct
                st.error(f"⛔ **POOR.** Model 4 only predicted {analysis['correct_count']} out of 6 main numbers correctly.")

            st.markdown("---")

            # === CORRECT PREDICTIONS ===
            st.header(f"✅ Correct Predictions ({analysis['correct_count']})")

            if analysis['correct_count'] > 0:
                st.success(f"**Numbers:** {', '.join(str(n) for n in sorted(analysis['correct_predictions']))}")

                # Create detailed table
                correct_df = pd.DataFrame(analysis['correct_details'])
                if not correct_df.empty:
                    correct_display = correct_df[[
                        'number', 'hmc', 'freshness', 'volatility', 'trend', 'momentum',
                        'last_seen', 'last_4', 'last_5', 'last_9', 'total_count'
                    ]].copy()
                    correct_display.columns = [
                        'Number', 'HMC', 'Freshness', 'Volatility', 'Trend', 'Momentum',
                        'Last Seen', 'L4', 'L5', 'L9', 'Total Hits'
                    ]
                    st.dataframe(correct_display, width='stretch', hide_index=True)

                # HMC breakdown
                st.markdown("**HMC Breakdown of Correct Predictions:**")
                col_hmc1, col_hmc2, col_hmc3 = st.columns(3)
                with col_hmc1:
                    st.metric("🔥 Hot", analysis['hmc_correct']['HOT'])
                with col_hmc2:
                    st.metric("🌡️ Medium", analysis['hmc_correct']['MEDIUM'])
                with col_hmc3:
                    st.metric("❄️ Cold", analysis['hmc_correct']['COLD'])
            else:
                st.warning("No main numbers were correctly predicted.")

            st.markdown("---")

            # === MISSED NUMBERS ===
            st.header(f"❌ Missed Numbers ({analysis['missed_count']})")

            if analysis['missed_count'] > 0:
                st.error(f"**Numbers:** {', '.join(str(n) for n in sorted(analysis['missed_numbers']))}")

                # Create detailed table
                missed_df = pd.DataFrame(analysis['missed_details'])
                if not missed_df.empty:
                    missed_display = missed_df[[
                        'number', 'hmc', 'freshness', 'volatility', 'trend', 'momentum',
                        'last_seen', 'last_4', 'last_5', 'last_9', 'total_count'
                    ]].copy()
                    missed_display.columns = [
                        'Number', 'HMC', 'Freshness', 'Volatility', 'Trend', 'Momentum',
                        'Last Seen', 'L4', 'L5', 'L9', 'Total Hits'
                    ]
                    st.dataframe(missed_display, width='stretch', hide_index=True)

                # HMC breakdown
                st.markdown("**HMC Breakdown of Missed Numbers:**")
                col_hmc_m1, col_hmc_m2, col_hmc_m3 = st.columns(3)
                with col_hmc_m1:
                    st.metric("🔥 Hot", analysis['hmc_missed']['HOT'])
                with col_hmc_m2:
                    st.metric("🌡️ Medium", analysis['hmc_missed']['MEDIUM'])
                with col_hmc_m3:
                    st.metric("❄️ Cold", analysis['hmc_missed']['COLD'])

                # Analysis insight
                st.info("**💡 Insight:** Review the characteristics of missed numbers to improve future predictions. "
                       "Consider adjusting model weights for these HMC categories or freshness patterns.")
            else:
                st.success("🎉 All main numbers were correctly predicted!")

            st.markdown("---")

            # === BONUS NUMBER ANALYSIS ===
            st.header("🎁 Bonus Number Analysis")

            bonus_detail = analysis['bonus_details']
            if bonus_detail:
                if analysis['bonus_predicted']:
                    st.success(f"✅ **Bonus number {winning_bonus} was in your predictions!**")
                else:
                    st.warning(f"❌ **Bonus number {winning_bonus} was NOT in your predictions.**")

                # Display bonus details
                col_b1, col_b2, col_b3, col_b4, col_b5, col_b6 = st.columns(6)

                with col_b1:
                    st.metric("Number", winning_bonus)
                with col_b2:
                    st.metric("HMC", bonus_detail['hmc'])
                with col_b3:
                    st.metric("Freshness", bonus_detail['freshness'])
                with col_b4:
                    st.metric("Volatility", bonus_detail['volatility'])
                with col_b5:
                    st.metric("Trend", bonus_detail['trend'])
                with col_b6:
                    st.metric("Momentum", bonus_detail['momentum'])

                # Recent activity
                st.markdown("**Recent Activity:**")
                col_ba1, col_ba2, col_ba3, col_ba4 = st.columns(4)
                with col_ba1:
                    st.metric("Last 4", bonus_detail['last_4'])
                with col_ba2:
                    st.metric("Last 5", bonus_detail['last_5'])
                with col_ba3:
                    st.metric("Last 9", bonus_detail['last_9'])
                with col_ba4:
                    st.metric("Total Hits", bonus_detail['total_count'])

            st.markdown("---")

            # === WRONG PREDICTIONS ===
            if analysis['wrong_count'] > 0:
                with st.expander(f"📋 View Wrong Predictions ({analysis['wrong_count']} numbers)"):
                    st.markdown(f"**Numbers:** {', '.join(str(n) for n in sorted(analysis['wrong_predictions']))}")

                    wrong_df = pd.DataFrame(analysis['wrong_details'])
                    if not wrong_df.empty:
                        wrong_display = wrong_df[[
                            'number', 'hmc', 'freshness', 'volatility', 'trend', 'momentum',
                            'last_seen', 'last_4', 'last_5', 'total_count'
                        ]].copy()
                        wrong_display.columns = [
                            'Number', 'HMC', 'Freshness', 'Volatility', 'Trend', 'Momentum',
                            'Last Seen', 'L4', 'L5', 'Total Hits'
                        ]
                        st.dataframe(wrong_display, width='stretch', hide_index=True)

            # === RECOMMENDATIONS ===
            st.markdown("---")
            st.header("💡 Recommendations for Model Improvement")

            recommendations = []

            # Analyze what was missed
            if analysis['missed_count'] > 0:
                # Check if missed numbers have common HMC pattern
                if analysis['hmc_missed']['HOT'] >= 3:
                    recommendations.append("⚠️ **Hot numbers were missed:** Model may be under-weighting hot numbers. Consider increasing hot number emphasis.")
                if analysis['hmc_missed']['COLD'] >= 3:
                    recommendations.append("⚠️ **Cold numbers were missed:** Model may be over-filtering cold numbers. Consider including more cold numbers.")

                # Check freshness of missed numbers
                missed_c0_count = sum(1 for d in analysis['missed_details'] if d['freshness'].startswith('C0'))
                if missed_c0_count >= 2:
                    recommendations.append("⚠️ **Fresh numbers (C0) were missed:** Consider including more numbers that haven't appeared in last 5 draws.")

            # Check what was correct
            if analysis['correct_count'] > 0:
                if analysis['hmc_correct']['HOT'] >= 3:
                    recommendations.append("✅ **Hot number strategy working well:** Continue emphasizing hot numbers in predictions.")
                if analysis['hmc_correct']['MEDIUM'] >= 2:
                    recommendations.append("✅ **Medium number balance is good:** Current medium number weighting is effective.")

            # Overall recommendations
            if analysis['accuracy'] < 33:
                recommendations.append("🔄 **Consider model retraining:** Low accuracy suggests model may need retraining with recent data.")

            if len(predictions) > 30:
                recommendations.append("📉 **Too many predictions:** Consider reducing prediction count to improve precision.")
            elif len(predictions) < 15:
                recommendations.append("📈 **Too few predictions:** Consider increasing prediction count to improve coverage.")

            if recommendations:
                for rec in recommendations:
                    st.markdown(f"- {rec}")
            else:
                st.success("✅ Model performance is balanced. Continue with current strategy!")

        except ValueError as e:
            st.error(f"❌ Invalid input format. Please enter numbers only, separated by commas. Error: {str(e)}")
        except Exception as e:
            st.error(f"❌ Error during analysis: {str(e)}")

    else:
        st.info("👆 Enter the winning numbers and Model 4 predictions above, then click 'Analyze Results'")

        with st.expander("📖 How to Use This Tool"):
            st.markdown("""
            **Step 1: Enter Winning Numbers**
            - Input the 6 main winning numbers from the recent draw
            - Input the bonus number

            **Step 2: Enter Model 4 Predictions**
            - Set the number of predictions (default: 20, configurable)
            - Input all numbers that Model 4 predicted

            **Step 3: Analyze**
            - Click "Analyze Results" to see comprehensive comparison

            **What You'll Get:**
            - ✅ **Correct Predictions:** Numbers that Model 4 correctly predicted
            - ❌ **Missed Numbers:** Winning numbers that weren't in predictions
            - 🎁 **Bonus Analysis:** Whether bonus number was predicted
            - 📊 **Detailed Metrics:** HMC, freshness, volatility, trend for each number
            - 💡 **Recommendations:** Actionable insights to improve model performance

            **Model 4 Context:**
            Model 4 attempts to predict 6 winning numbers within a pool of N predictions
            (where N is typically 20 but configurable). This tool helps evaluate how well
            the model performed on a specific draw.
            """)
