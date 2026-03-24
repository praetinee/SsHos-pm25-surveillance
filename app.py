import streamlit as st
import pandas as pd
from data_loader import load_and_clean_data, load_pm25_data
from analytics import (
    calculate_kpis, get_pm_color, plot_dual_axis, 
    plot_disease_breakdown, plot_walkin_vs_appt, plot_new_old_opd
)

# 1. ตั้งค่าหน้าเพจ
st.set_page_config(page_title="PM2.5 Health Surveillance", layout="wide")
st.title("ระบบเฝ้าระวังผลกระทบทางสุขภาพจาก PM2.5 (Dashboard)")

# 2. โหลดข้อมูล (ใช้ st.cache_data เพื่อความรวดเร็ว)
@st.cache_data
def fetch_data():
    # หมายเหตุ: ในการ Deploy จริง ต้องเปลี่ยน Path ไปที่ที่เก็บไฟล์ CSV ใน GitHub
    df = load_and_clean_data("โรคเฝ้าระวังจาก pm2.5 - 4 โรคเฝ้าระวัง.csv")
    df_pm = load_pm25_data("โรคเฝ้าระวังจาก pm2.5 - PM2.5 รายเดือน.csv")
    return df, df_pm

try:
    data, pm_data = fetch_data()
except Exception as e:
    st.error(f"ไม่สามารถโหลดข้อมูลได้: {e}")
    st.stop()

# 3. แผงควบคุม (Sidebar Filters)
st.sidebar.header("ตัวกรองข้อมูล (Filters)")

# Filter: กลุ่มโรค
disease_list = data['4 กลุ่มโรคเฝ้าระวัง'].dropna().unique().tolist()
selected_diseases = st.sidebar.multiselect("กลุ่มโรคเฝ้าระวัง", disease_list, default=disease_list)

# Filter: อำเภอ (ถ้ามี)
if 'อำเภอ' in data.columns:
    district_list = data['อำเภอ'].dropna().unique().tolist()
    selected_districts = st.sidebar.multiselect("อำเภอ", district_list, default=district_list)
else:
    selected_districts = []

# Filter: ประเภทผู้ป่วย (Walk-in ปะทะ นัด)
appt_filter = st.sidebar.radio("ประเภทการรับบริการ", ["ทั้งหมด", "เฉพาะ Walk-in (ฉุกเฉิน)", "เฉพาะผู้ป่วยนัด"])

# 4. ประมวลผลตัวกรอง
filtered_df = data.copy()
if selected_diseases:
    filtered_df = filtered_df[filtered_df['4 กลุ่มโรคเฝ้าระวัง'].isin(selected_diseases)]
if selected_districts:
    filtered_df = filtered_df[filtered_df['อำเภอ'].isin(selected_districts)]
    
if appt_filter == "เฉพาะ Walk-in (ฉุกเฉิน)":
    filtered_df = filtered_df[~filtered_df['ผู้ป่วยนัด'].astype(str).str.contains('นัด')]
elif appt_filter == "เฉพาะผู้ป่วยนัด":
    filtered_df = filtered_df[filtered_df['ผู้ป่วยนัด'].astype(str).str.contains('นัด')]

# 5. สรุปสถานการณ์ (KPIs)
st.markdown("### 📊 สรุปสถานการณ์ (KPIs)")
col1, col2, col3, col4 = st.columns(4)

total_cases, unique_cases, top_disease = calculate_kpis(filtered_df)
latest_pm = pm_data['PM2.5'].iloc[-1] if not pm_data.empty else 0

col1.metric("จำนวนรับบริการสะสม (ครั้ง)", f"{total_cases:,}")
col2.metric("จำนวนผู้ป่วย (คน)", f"{unique_cases:,}")
col3.metric("ระดับ PM2.5 ล่าสุด (µg/m³)", f"{latest_pm}", get_pm_color(latest_pm))
col4.metric("กลุ่มโรคที่พบมากที่สุด", top_disease)

st.divider()

# 6. กราฟวิเคราะห์ความสัมพันธ์ (Correlation)
st.markdown("### 📈 ความสัมพันธ์ระหว่าง PM2.5 และการป่วยรายเดือน")
fig_trend, r_value = plot_dual_axis(filtered_df, pm_data)
st.plotly_chart(fig_trend, use_container_width=True)

if r_value > 0.5:
    st.info(f"**วิเคราะห์สถิติ:** พบความสัมพันธ์เชิงบวกที่ค่อนข้างแข็งแกร่ง (r={r_value:.2f}) ระหว่าง PM2.5 และปริมาณผู้ป่วย")

# 7. ระบาดวิทยาเชิงลึก
st.markdown("### 🔬 การวิเคราะห์ทางระบาดวิทยา")
c1, c2, c3 = st.columns(3)

with c1:
    fig_pie = plot_disease_breakdown(filtered_df)
    st.plotly_chart(fig_pie, use_container_width=True)

with c2:
    fig_appt = plot_walkin_vs_appt(filtered_df)
    st.plotly_chart(fig_appt, use_container_width=True)

with c3:
    fig_new_old = plot_new_old_opd(filtered_df)
    if fig_new_old:
        st.plotly_chart(fig_new_old, use_container_width=True)
    else:
        st.write("ไม่มีข้อมูลการแบ่งผู้ป่วยใหม่/เก่า")

st.caption("ระบบปฏิบัติตามมาตรฐาน PDPA: ข้อมูลส่วนบุคคลทั้งหมดถูกเข้ารหัสหรือลบออกจากระบบประมวลผลแล้ว")
