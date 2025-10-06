import streamlit as st
import pandas as pd

# Import modularized functions
from data_loader import load_patient_data, load_pm25_data
from geocoder import add_coordinates_to_dataframe
from plotting import plot_patient_vs_pm25, plot_vulnerable_pie

# --- Page Configuration ---
st.set_page_config(page_title="PM2.5 Surveillance Dashboard", layout="wide")
st.title(" dashboards เฝ้าระวังผลกระทบต่อสุขภาพจาก PM2.5")

# --- Data Source Configuration ---
URL_PATIENT = "https://docs.google.com/spreadsheets/d/1vvQ8YLChHXvCowQQzcKIeV4PWt0CCt76f5Sj3fNTOV0/export?format=csv&gid=795124395"
URL_PM25 = "https://docs.google.com/spreadsheets/d/1vvQ8YLChHXvCowQQzcKIeV4PWt0CCt76f5Sj3fNTOV0/export?format=csv&gid=1038807599"

# --- Main Application Flow ---

# 1. Load Data
df_patient_raw = load_patient_data(URL_PATIENT)
df_pm25 = load_pm25_data(URL_PM25)

if df_patient_raw.empty:
    st.error("ไม่สามารถโหลดข้อมูลผู้ป่วยได้ กรุณาตรวจสอบ URL หรือรูปแบบของ Google Sheet")
    st.stop()

st.success("✅ โหลดข้อมูลสำเร็จ")

# 2. Essential Column Check
ESSENTIAL_COLS = ["วันที่เข้ารับบริการ", "4 กลุ่มโรคเฝ้าระวัง", "ตำบล", "อำเภอ", "จังหวัด"]
missing_cols = [col for col in ESSENTIAL_COLS if col not in df_patient_raw.columns]
if missing_cols:
    st.error(f"❌ ไม่พบคอลัมน์ที่จำเป็นในข้อมูลผู้ป่วย: {', '.join(missing_cols)}")
    st.stop()

# 3. Geocode Data (This is a heavy operation, run it once on the full dataset)
df_patient = add_coordinates_to_dataframe(df_patient_raw)


# 4. Sidebar Filters
st.sidebar.header("🔍 ตัวกรองข้อมูล")
months = sorted(df_patient["เดือน"].dropna().unique().tolist())
disease_groups = sorted(df_patient["4 กลุ่มโรคเฝ้าระวัง"].dropna().unique().tolist())

month_selected = st.sidebar.selectbox("เลือกเดือน", ["ทั้งหมด"] + months)
group_selected = st.sidebar.selectbox("เลือกกลุ่มโรค", ["ทั้งหมด"] + disease_groups)

# 5. Filter Data based on selection
df_filtered = df_patient.copy()
if month_selected != "ทั้งหมด":
    df_filtered = df_filtered[df_filtered["เดือน"] == month_selected]
if group_selected != "ทั้งหมด":
    df_filtered = df_filtered[df_filtered["4 กลุ่มโรคเฝ้าระวัง"] == group_selected]

# --- Display Dashboard Components ---

# 6. Trend Plot
# Pass the full (unfiltered) dataset for the trend plot to show overall trends
plot_patient_vs_pm25(df_patient, df_pm25) 

# 7. Map
st.subheader("🗺️ แผนที่แสดงที่อยู่ของผู้ป่วย (ตามตัวกรอง)")
map_df = df_filtered[["lat", "lon"]].dropna()
if not map_df.empty:
    st.map(map_df)
else:
    st.info("ℹ️ ไม่พบข้อมูลพิกัดสำหรับข้อมูลที่กรอง")

# 8. Pie Chart
# Pass filtered data for the pie chart to reflect user's selection
plot_vulnerable_pie(df_filtered, month_selected)

# 9. Data Table
st.subheader("📋 ตารางข้อมูลผู้ป่วย (ตามตัวกรอง)")
st.dataframe(
    df_filtered.drop(columns=['full_address'], errors='ignore'),
    use_container_width=True
)

