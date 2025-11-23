import streamlit as st
import pandas as pd
from typing import Dict, Any
from view.utils.data_loader import load_draw_history, get_sorted_draw_dates
from view.utils.formatting import get_category_color


def create_draw_table_html(draw_data: Dict[str, Any], draw_date: str) -> str:
    """Create an HTML table for a single draw with horizontal scrolling."""
    draw_info = draw_data[draw_date]
    hmc_summary = draw_info.get('hmc_summary', {})
    winning_numbers = draw_info.get('winning_numbers_details', [])
    recent_bonus_numbers = draw_info.get('recent_bonus_numbers', [])
    
    # 1. Determine the set of winning numbers (excluding bonus in this context, just the numbers drawn)
    # Note: winning_numbers_details contains all 7, including bonus. We'll use the 'number' field.
    winning_number_set = {d['number'] for d in winning_numbers}
    
    # 2. Format the list of recent bonus numbers with highlights
    formatted_bonus_numbers = []
    for number in recent_bonus_numbers:
        if number in winning_number_set:
            # Highlight if the number was one of the last 10 bonus numbers AND hit in this draw
            formatted_number = f"""
                <span style='background-color: #ffcccc; color: #cc0000; font-weight: bold; border-radius: 3px; padding: 2px 5px; margin: 0 1px; white-space: nowrap;'>
                    {number}
                </span>
            """
        else:
            # Standard formatting
            formatted_number = f"<span style='padding: 2px 5px;'>{number}</span>"

        formatted_bonus_numbers.append(formatted_number)

    formatted_list_html = " ".join(formatted_bonus_numbers) # Use space separator for better HTML rendering

    # Create comma-separated plain text version for easy copying
    comma_separated_bonus = ", ".join(str(num) for num in recent_bonus_numbers)
    
    
    # Extract dynamic recent_counts keys from first number
    recent_keys = []
    if winning_numbers and 'recent_counts' in winning_numbers[0]:
        recent_keys = sorted(
            winning_numbers[0]['recent_counts'].keys(),
            key=lambda x: int(x.split('_')[-1]) if x.split('_')[-1].isdigit() else 0
        )
    
    html = f"""
    <div style="margin-bottom: 30px; border: 2px solid #ddd; border-radius: 8px; padding: 15px; background-color: #f9f9f9;">
        <div style="margin-bottom: 15px;">
            <h3 style="margin: 0; color: #333;">Draw #{draw_info.get('draw_index', 'N/A')} - {draw_info.get('draw_date', 'N/A')}</h3>
            <div style="margin-top: 8px;">
                <span style="background-color: #e8f4f8; padding: 5px 10px; border-radius: 4px; margin-right: 10px;">
                    <strong>HMC Distribution:</strong> {hmc_summary.get('hmc_distribution', 'N/A')}
                </span>
                <span style="background-color: #fff4e6; padding: 5px 10px; border-radius: 4px;">
                    <strong>Draw Range:</strong> {hmc_summary.get('draw_range', 'N/A')}
                </span>
            </div>
            
            <div style="margin-top: 10px; background-color: #ffe6f2; padding: 5px 10px; border-radius: 4px;">
                <div style="display: flex; align-items: center; flex-wrap: wrap;">
                    <strong style="margin-right: 10px;">Last 10 Bonus Numbers:</strong> {formatted_list_html}
                </div>
                <div style="margin-top: 8px; font-size: 12px;">
                    <strong style="color: #666;">Copy to filter:</strong>
                    <input type="text" readonly value="{comma_separated_bonus}"
                           onclick="this.select();"
                           style="width: 100%; max-width: 500px; padding: 4px 8px; margin-left: 8px; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; background-color: #f5f5f5; cursor: pointer;"
                           title="Click to select, then Ctrl+C to copy">
                </div>
            </div>
            
        </div>
        
        <div style="overflow-x: auto; max-width: 100%;">
            <table style="border-collapse: collapse; width: 100%; background-color: white;">
                <thead>
                    <tr style="background-color: #4a90e2; color: white;">
                        <th style='padding: 12px; text-align: center; border: 1px solid #ddd; white-space: nowrap;'>Number</th>
                        <th style='padding: 12px; text-align: center; border: 1px solid #ddd; white-space: nowrap;'>Bonus</th>
                        <th style='padding: 12px; text-align: center; border: 1px solid #ddd; white-space: nowrap;'>Category</th>
                        <th style='padding: 12px; text-align: center; border: 1px solid #ddd; white-space: nowrap;'>Days Since Last Hit</th>
    """
    
    # Add dynamic recent count headers
    for key in recent_keys:
        header_name = key.replace('_', ' ').title()
        html += f"<th style='padding: 12px; text-align: center; border: 1px solid #ddd; white-space: nowrap;'>{header_name}</th>"
    
    html += """
                    </tr>
                </thead>
                <tbody>
    """
    
    # Add rows for each winning number
    for number_detail in winning_numbers:
        number = number_detail.get('number', 'N/A')
        is_bonus = '✓' if number_detail.get('is_bonus', False) else ''
        category = number_detail.get('category', 'N/A')
        category_color = get_category_color(category)
        days_since = number_detail.get('days_since_last_hit', 'N/A')
        recent_counts = number_detail.get('recent_counts', {})
        
        html += f"""
                    <tr style='border-bottom: 1px solid #ddd;'>
                        <td style='padding: 10px; border: 1px solid #ddd; text-align: center; font-weight: bold; font-size: 16px;'>{number}</td>
                        <td style='padding: 10px; border: 1px solid #ddd; text-align: center; font-size: 16px;'>{is_bonus}</td>
                        <td style='padding: 10px; border: 1px solid #ddd; text-align: center;'>
                            <span style='background-color: {category_color}; color: white; padding: 4px 12px; border-radius: 12px; font-weight: bold;'>
                                {category.upper()}
                            </span>
                        </td>
                        <td style='padding: 10px; border: 1px solid #ddd; text-align: center;'>{days_since}</td>
        """
        
        # Add dynamic recent count values
        for key in recent_keys:
            value = recent_counts.get(key, 0)
            html += f"<td style='padding: 10px; border: 1px solid #ddd; text-align: center;'>{value}</td>"
        
        html += """
                    </tr>
        """
    
    html += """
                </tbody>
            </table>
        </div>
    </div>
    """
    
    return html


def show():
    """Display the draw history page."""
    st.title("📊 Lotto Draw History")
    st.markdown("Historical data for each lotto draw, displayed from oldest to newest.")
    
    # Load draw history data
    draw_data = load_draw_history()
    # get_sorted_draw_dates returns dates from OLDEST to NEWEST
    sorted_dates = get_sorted_draw_dates(draw_data)
    
    if not sorted_dates:
        st.warning("No draw history data available.")
        return
    
    st.info(f"Total draws available: **{len(sorted_dates)}** (Draw #{draw_data[sorted_dates[0]].get('draw_index', 'N/A')} to #{draw_data[sorted_dates[-1]].get('draw_index', 'N/A')})")
    
    # Sidebar filters
    st.sidebar.header("Filter Options")
    
    # Date range filter
    min_index = draw_data[sorted_dates[0]].get('draw_index', 1) 
    max_index = draw_data[sorted_dates[-1]].get('draw_index', len(sorted_dates))
    
    start_index, end_index = st.sidebar.slider(
        "Select Draw Index Range",
        min_value=min_index,
        max_value=max_index,
        value=(min_index, max_index),
        help="Filter draws by their index number"
    )
    
    # HMC distribution filter
    hmc_filter = st.sidebar.multiselect(
        "Filter by HMC Distribution",
        options=sorted(list(set(
            draw_data[date].get('hmc_summary', {}).get('hmc_distribution', 'N/A')
            for date in sorted_dates
        ))),
        help="Select specific Hot-Medium-Cold distributions"
    )
    
    # Filter dates based on selections
    # Note: filtered_dates is still sorted OLDEST to NEWEST here
    filtered_dates = [
        date for date in sorted_dates
        if start_index <= draw_data[date].get('draw_index', 0) <= end_index
        and (not hmc_filter or draw_data[date].get('hmc_summary', {}).get('hmc_distribution', '') in hmc_filter)
    ]
    
    if not filtered_dates:
        st.warning("No draws match the selected filters.")
        return
    
    # Reverse the list to display MOST RECENT draw first
    filtered_dates.reverse() 
    
    st.markdown(f"**Displaying {len(filtered_dates)} draws**")
    
    # Display each draw as a separate table
    for draw_date in filtered_dates:
        html_table = create_draw_table_html(draw_data, draw_date)
        st.html(html_table)