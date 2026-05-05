import streamlit as st
import pandas as pd
from data_processor import load_and_prep_data
from ui_components import create_sidebar_filters, plot_trend_dual_axis, plot_demographics, plot_geographic, plot_icd10_trend
from stats_analyzer import render_smart_insights, render_statistical_matrix

def main():
    st.set_page_config(page_title="PM2.5 Health Surveillance", layout="wide")
    
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;700&display=swap');
        html, body, [data-testid="stAppViewContainer"], .stApp, p, h1, h2, h3, h4, h5, h6, label, li, span {
            font-family: 'Sarabun', sans-serif !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("ระบบเฝ้าระวังสุขภาพจากฝุ่น PM2.5")
    st.markdown("---")

    with st.spinner('กำลังโหลดข้อมูล...'):
        df_patients, df_pm25 = load_and_prep_data()

    if df_patients.empty:
        st.stop()

    selected_year, selected_disease, selected_vulnerable, acute_only, lag_days, selected_icd10 = create_sidebar_filters(df_patients)

    # ประยุกต์ใช้ Lag และ Filters
    df_filtered = df_patients.copy()
    if lag_days > 0:
        df_filtered['Date'] = df_filtered['Date'] - pd.Timedelta(days=lag_days)
        df_filtered['Month_Year'] = df_filtered['Date'].dt.to_period('M')

    if selected_year: df_filtered = df_filtered[df_filtered['Date'].dt.year.isin(selected_year)]
    if selected_disease: df_filtered = df_filtered[df_filtered['4 กลุ่มโรคเฝ้าระวัง'].isin(selected_disease)]
    if selected_vulnerable: df_filtered = df_filtered[df_filtered['กลุ่มเปราะบาง'].isin(selected_vulnerable)]
    if acute_only: df_filtered = df_filtered[df_filtered['Is_Acute'] == True]
    if selected_icd10: df_filtered = df_filtered[df_filtered['ICD10_โรคเฝ้าระวัง'].astype(str).str.startswith(tuple(selected_icd10), na=False)]

    # เพิ่ม Tab 3
    tab1, tab2, tab3 = st.tabs(["📊 ภาพรวม", "🔬 เจาะลึกรหัสโรค", "🧪 ตารางสรุปสถิติ"])

    with tab1:
        render_smart_insights(df_filtered, df_pm25, lag_days)
        plot_trend_dual_axis(df_filtered, df_pm25)
        c1, c2 = st.columns(2)
        with c1: plot_demographics(df_filtered)
        with c2: plot_geographic(df_filtered)

    with tab2:
        # (โค้ดเดิมใน Tab 2)
        st.markdown("### 🔬 วิเคราะห์เจาะลึกรายรหัสโรค")
        # ... ส่วนแสดงผลเจาะลึกรหัสโรค ...
        # (เพื่อให้โค้ดสั้นลงตรงนี้ผมขอละส่วนเดิมไว้ แต่ในไฟล์จริงของคุณจะยังอยู่ครบครับ)

    with tab3:
        # แสดงตารางสถิติตามที่คุณต้องการ
        render_statistical_matrix(df_filtered, df_pm25)
        
        # เพิ่ม Note อธิบายตัวกรองเฉียบพลัน
        if acute_only:
            st.warning("⚠️ ขณะนี้ตารางแสดงเฉพาะสถิติของ 'เคสอาการเฉียบพลัน' ตามที่คุณเลือกไว้ใน Sidebar")
        else:
            st.info("ℹ️ ตารางนี้แสดงสถิติภาพรวมทุกอาการ คุณสามารถเปลี่ยนเป็น 'เคสเฉียบพลัน' ได้ที่ Sidebar")

if __name__ == "__main__":
    main()
