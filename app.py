# app.py
import streamlit as st

# Page configuration must be first
st.set_page_config(
    page_title="Lotto Analysis Dashboard",
    page_icon="🎰",
    layout="wide"
)

# Import page modules
from pages import trigger_analysis, draw_history, statistics, freshness_analysis

# Navigation
PAGES = {
    "📊 Trigger Periods Analysis": trigger_analysis,
    "📅 Draw History": draw_history,
    "📈 Statistics": statistics,
    "🔥 Freshness Analysis": freshness_analysis
}

# Style adjustments
st.markdown("""
<style>
    /* Hide default sidebar navigation */
    [data-testid="stSidebarNav"] {
        display: none;
    }
    
    /* Style the navigation buttons */
    div[data-testid="column"] > div > div > button {
        width: 100%;
        border-radius: 6px;
        border: 2px solid #d0d0d0;
        background-color: #ffffff;
        color: #31333F;
        font-weight: 500;
        padding: 12px 20px;
        transition: all 0.2s ease;
    }
    
    div[data-testid="column"] > div > div > button:hover {
        border-color: #FF4B4B;
        color: #FF4B4B;
        background-color: #fff5f5;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    /* Active button styling */
    div[data-testid="column"] > div > div > button[kind="primary"] {
        background-color: #FF4B4B !important;
        color: white !important;
        border-color: #FF4B4B !important;
    }
    
    div[data-testid="column"] > div > div > button[kind="primary"]:hover {
        background-color: #E63946 !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(255,75,75,0.3);
    }
    
    /* Navigation area background */
    .stApp > header {
        background-color: #f0f2f6;
    }
    
    /* First container background (navigation area) */
    section[data-testid="stVerticalBlock"] > div:first-child {
        background-color: #f0f2f6;
        padding: 1.5rem 1rem;
        margin: -1rem -1rem 1rem -1rem;
        border-bottom: 1px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for navigation
if 'current_page' not in st.session_state:
    st.session_state.current_page = "📊 Trigger Periods Analysis"

# Create navigation at the top
st.markdown("### 🎰 Navigation")
nav_cols = st.columns(len(PAGES))

for idx, (page_name, page_module) in enumerate(PAGES.items()):
    with nav_cols[idx]:
        # Use type="primary" for active page
        button_type = "primary" if st.session_state.current_page == page_name else "secondary"
        if st.button(page_name, key=f"nav_{idx}", use_container_width=True, type=button_type):
            st.session_state.current_page = page_name
            st.rerun()

st.markdown("---")

# Display selected page
page = PAGES[st.session_state.current_page]
page.show()

