import streamlit as st
import pandas as pd

from data_processor import load_and_prep_data
from ui_components import create_sidebar_filters, plot_trend_dual_axis, plot_demographics, plot_geographic

def main():
    st.set_page_config(page_title="PM2.5 Health Surveillance", layout="wide")
    
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;700&display=swap');
        html, body, [data-testid="stAppViewContainer"], .stApp, p, h1, h2, h3, h4, h5, h6, label, li, span {
            font-family: 'Sarabun', "Source Sans Pro", "Segoe UI", "Apple Color Emoji", "Segoe UI Emoji", sans-serif !important;
        }
        [data-testid="collapsedControl"] button, [data-testid="collapsedControl"] svg, [data-testid="stHeader"] svg, button[kind="header"] {
            font-family: "Source Sans Pro", sans-serif !important;
        }
        div[data-testid="metric-container"] {
            background-color: #ffffff; border: 1px solid #f0f2f6; padding: 20px; border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        }
        div[data-testid="metric-container"] > div > div > div > div > p { font-size: 1rem; color: #64748b; font-weight: 500; }
        div[data-testid="metric-container"] > div > div > div > div:nth-child(2) > p { font-size: 2rem; color: #0f172a; font-weight: 700; }
        </style>
    """, unsafe_allow_html=True)

    st.title("จำนวนผู้ป่วยด้วยโรคที่เกี่ยวข้องกับการสัมผัส PM2.5")
    st.markdown("<p style='font-size: 1.1rem; color: #64748b;'>ระบบเฝ้าระวังและการเข้ารับบริการที่โรงพยาบาล</p>", unsafe_allow_html=True)
    st.markdown("---")

    with st.spinner('กำลังประมวลผลข้อมูลสาธารณสุข...'):
        df_patients, df_pm25 = load_and_prep_data()

    if df_patients.empty:
        st.warning("⚠️ ไม่สามารถดำเนินการต่อได้ กรุณาอัปโหลดหรือตรวจสอบไฟล์ข้อมูลต้นทาง")
        st.stop()

    # รับค่าทั้ง 5 ตัวแปรที่กรองมาจาก Sidebar
    selected_year, selected_disease, selected_acute, selected_vulnerable, selected_icd10 = create_sidebar_filters(df_patients)

    df_filtered = df_patients.copy()
    
    # 1. กรองปี
    if selected_year:
        df_filtered = df_filtered[df_filtered['Date'].dt.year.isin(selected_year)]
    
    # 2. กรองกลุ่มโรค
    if selected_disease:
        df_filtered = df_filtered[df_filtered['4 กลุ่มโรคเฝ้าระวัง'].isin(selected_disease)]

    # 3. กรองเคสเฉียบพลัน
    if selected_acute and 'เคสเฉียบพลัน' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['เคสเฉียบพลัน'].isin(selected_acute)]

    # 4. กรองกลุ่มเปราะบาง
    if selected_vulnerable and 'กลุ่มเปราะบาง' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['กลุ่มเปราะบาง'].isin(selected_vulnerable)]

    # 5. กรองรหัสโรค
    if selected_icd10:
        icd_col = 'รหัสโรค' if 'รหัสโรค' in df_filtered.columns else ('ICD10' if 'ICD10' in df_filtered.columns else None)
        if icd_col:
            df_filtered = df_filtered[df_filtered[icd_col].astype(str).isin(selected_icd10)]

    total_cases = len(df_filtered)
    
    max_pm = "-"
    if not df_pm25.empty and selected_year:
        max_pm_val = df_pm25[df_pm25['Month_Year'].dt.year.isin(selected_year)]['PM25'].max()
        max_pm = f"{max_pm_val:.1f}"

    kpi1, kpi2 = st.columns(2)
    with kpi1:
        st.metric(label="👥 จำนวนผู้ป่วยสะสม (เคส)", value=f"{total_cases:,}")
    with kpi2:
        st.metric(label="🌫️ ค่า PM2.5 สูงสุด (µg/m³)", value=max_pm)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("### 📈 แนวโน้มผู้ป่วย 4 กลุ่มโรคเทียบกับระดับ PM2.5")
    plot_trend_dual_axis(df_filtered, df_pm25)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🩺 สัดส่วนกลุ่มโรคที่ได้รับผลกระทบ")
        plot_demographics(df_filtered)
    with col2:
        st.markdown("### 📍 10 อันดับพื้นที่เฝ้าระวัง (ระดับตำบล)")
        plot_geographic(df_filtered)

if __name__ == "__main__":
    main()
