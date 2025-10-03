import streamlit as st
import pandas as pd
from data_loader import generate_data
from plotting import (
    create_time_series_chart,
    create_diagnosis_pie_chart,
    create_age_gender_bar_chart
)

# --- Page Configuration (ตั้งค่าหน้าเว็บ) ---
st.set_page_config(
    page_title="แดชบอร์ดผู้ป่วย PM2.5",
    page_icon="😷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Load Data (โหลดข้อมูล) ---
# โหลดข้อมูลจากโมดูล data_loader.py
patients_df, pm25_df = generate_data()

# --- FIX: เพิ่มการตรวจสอบเพื่อป้องกันการแครชหากโหลดข้อมูลไม่สำเร็จ ---
if patients_df.empty or pm25_df.empty:
    st.error("ไม่สามารถโหลดข้อมูลได้ กรุณาตรวจสอบแหล่งข้อมูล (Google Sheets) หรือการเชื่อมต่ออินเทอร์เน็ต")
    st.stop() # หยุดการทำงานของแอปถ้าไม่มีข้อมูล


# --- Sidebar Filters (ฟิลเตอร์ข้อมูลด้านข้าง) ---
st.sidebar.header('ตัวกรองข้อมูล (Filters)')

# Filter by Date Range
min_date = patients_df['admission_date'].min().date()
max_date = patients_df['admission_date'].max().date()

# ตรวจสอบว่า min_date ไม่ได้มากว่า max_date ก่อนสร้าง date_input
if min_date > max_date:
    st.sidebar.error("ข้อมูลเริ่มต้นไม่ถูกต้อง: วันที่เริ่มต้นอยู่หลังวันที่สิ้นสุด")
    # หยุดการทำงานของแอปถ้าวันที่ผิดพลาด
    st.stop()

date_range = st.sidebar.date_input(
    'เลือกช่วงวันที่',
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# ตรวจสอบว่า date_range มี 2 ค่า
if len(date_range) != 2:
    st.stop()

start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])


# Filter by District
all_districts = patients_df['district'].unique()
selected_districts = st.sidebar.multiselect(
    'เลือกอำเภอ',
    options=all_districts,
    default=all_districts
)

# Filter by Diagnosis
all_diagnoses = patients_df['diagnosis'].unique()
selected_diagnoses = st.sidebar.multiselect(
    'เลือกกลุ่มโรค',
    options=all_diagnoses,
    default=all_diagnoses
)

# Apply filters
filtered_patients = patients_df[
    (patients_df['admission_date'] >= start_date) &
    (patients_df['admission_date'] <= end_date) &
    (patients_df['district'].isin(selected_districts)) &
    (patients_df['diagnosis'].isin(selected_diagnoses))
]

# --- Main Page Layout (เนื้อหาหลัก) ---
st.title('😷 แดชบอร์ดเฝ้าระวังผู้ป่วยจากผลกระทบ PM2.5')
st.markdown("แดชบอร์ดสำหรับเจ้าหน้าที่โรงพยาบาล เพื่อติดตามแนวโน้มและภาพรวมของผู้ป่วยที่เกี่ยวข้องกับมลพิษทางอากาศ")

# --- Key Metrics (ตัวชี้วัดหลัก) ---
total_patients = filtered_patients.shape[0]
active_patients = filtered_patients[filtered_patients['status'] == 'กำลังรักษา'].shape[0]
avg_age = int(filtered_patients['age'].mean()) if not filtered_patients.empty else 0

col1, col2, col3 = st.columns(3)
col1.metric(label="ผู้ป่วยทั้งหมด (ในช่วงที่เลือก)", value=f"{total_patients:,}")
col2.metric(label="ผู้ป่วยที่กำลังรักษา", value=f"{active_patients:,}")
col3.metric(label="อายุเฉลี่ย", value=f"{avg_age} ปี")

st.markdown("---")

# --- Charts (กราฟแสดงผล) ---
# สร้างและแสดงกราฟโดยเรียกใช้ฟังก์ชันจาก plotting.py

st.subheader("แนวโน้มจำนวนผู้ป่วยรายวันเทียบกับค่า PM2.5")
fig_timeseries = create_time_series_chart(filtered_patients, pm25_df, start_date, end_date)
st.plotly_chart(fig_timeseries, use_container_width=True)


col_a, col_b = st.columns(2)
with col_a:
    st.subheader("สัดส่วนกลุ่มโรค")
    fig_pie = create_diagnosis_pie_chart(filtered_patients)
    if fig_pie:
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("ไม่มีข้อมูลผู้ป่วยในช่วงที่เลือก")

with col_b:
    st.subheader("ผู้ป่วยตามกลุ่มอายุและเพศ")
    fig_bar = create_age_gender_bar_chart(filtered_patients)
    if fig_bar:
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("ไม่มีข้อมูลผู้ป่วยในช่วงที่เลือก")


# --- Patient Data Table (ตารางข้อมูลผู้ป่วย) ---
st.subheader("รายละเอียดข้อมูลผู้ป่วย")
st.dataframe(filtered_patients, use_container_width=True)


# --- CSS for modern look (ปรับแต่งหน้าตาให้สวยงาม) ---
st.markdown("""
<style>
    .stMetric {
        border-radius: 10px;
        background-color: #f0f2f6;
        padding: 15px;
        text-align: center;
    }
    .stMetric > label {
        font-weight: bold;
    }
    .stMetric > div > div > span {
        font-size: 1.8rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

