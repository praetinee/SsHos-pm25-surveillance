import streamlit as st
import pandas as pd
from data_loader import load_pm25_realtime, generate_mock_data
from ui_components import (
    display_pm25_gauge, 
    display_historical_chart, 
    display_district_barchart,
    display_patient_group_chart
)

# --- Page Configuration ---
st.set_page_config(
    page_title="PM2.5 Health Dashboard",
    page_icon="😷",
    layout="wide"
)

# --- Load Data ---
timestamp, pm25_value = load_pm25_realtime()
df = generate_mock_data()

# --- Sidebar Filters ---
st.sidebar.header("ตัวกรองข้อมูล (Filters)")

# Date Range Filter
min_date = df['visit_date'].min().date()
max_date = df['visit_date'].max().date()
start_date, end_date = st.sidebar.date_input(
    "เลือกช่วงวันที่",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
    help="เลือกช่วงข้อมูลที่ต้องการแสดงผล"
)

# Disease Group Filter
all_disease_groups = df['disease_group'].unique()
selected_disease_groups = st.sidebar.multiselect(
    "เลือกกลุ่มโรค (เลือกได้หลายข้อ)",
    options=all_disease_groups,
    default=all_disease_groups
)

# Patient Group Filter
all_patient_groups = df['patient_group'].unique()
selected_patient_groups = st.sidebar.multiselect(
    "เลือกกลุ่มผู้เข้ารับบริการ",
    options=all_patient_groups,
    default=all_patient_groups
)

# --- Filter Data ---
# Convert date inputs to datetime for comparison
start_datetime = pd.to_datetime(start_date)
end_datetime = pd.to_datetime(end_date)

# Apply filters to the dataframe
filtered_df = df[
    (df['visit_date'] >= start_datetime) &
    (df['visit_date'] <= end_datetime) &
    (df['disease_group'].isin(selected_disease_groups)) &
    (df['patient_group'].isin(selected_patient_groups))
]

# --- Main Page Layout ---

# Header Section
col1, col2 = st.columns([3, 1])
with col1:
    st.title("😷 Dashboard เฝ้าระวังผลกระทบจาก PM2.5")
    st.subheader("โรงพยาบาลสันทราย (ข้อมูลจำลอง)")
with col2:
    display_pm25_gauge(timestamp, pm25_value)

st.markdown("---")

# Main Chart Section
display_historical_chart(filtered_df)

st.markdown("---")

# Detailed Charts Section
col_detail1, col_detail2 = st.columns(2)
with col_detail1:
    display_district_barchart(filtered_df)
with col_detail2:
    display_patient_group_chart(filtered_df)

