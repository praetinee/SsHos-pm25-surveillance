import streamlit as st
from data_loader import load_pm25_realtime
from ui_components import display_pm25_gauge

# --- Page Configuration ---
st.set_page_config(
    page_title="PM2.5 Health Dashboard",
    page_icon="😷",
    layout="wide"
)

# --- Main Application ---
st.title("😷 Dashboard เฝ้าระวังผลกระทบสุขภาพจาก PM2.5")
st.subheader("โรงพยาบาลสันทราย")

# --- Real-time PM2.5 Display ---
# Load data first
timestamp, pm25_value = load_pm25_realtime()

# Then display the gauge using the UI component
display_pm25_gauge(timestamp, pm25_value)

st.markdown("---")

# The section for historical data, filters, and chart has been removed.

