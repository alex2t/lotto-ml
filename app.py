import streamlit as st

# Page configuration must be first
st.set_page_config(
    page_title="Lotto Analysis Dashboard",
    page_icon="🎰",
    layout="wide"
)

# Import page modules
from pages import trigger_analysis, draw_history

# Navigation
PAGES = {
    "Trigger Periods Analysis": trigger_analysis,
    "Draw History": draw_history
}

# Sidebar navigation
st.sidebar.title("Navigation")
selection = st.sidebar.radio("Go to", list(PAGES.keys()))

# Display selected page
page = PAGES[selection]
page.show()