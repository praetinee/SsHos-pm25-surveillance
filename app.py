import streamlit as st
import pandas as pd

# นำเข้าฟังก์ชันจากไฟล์โมดูลที่เราแยกไว้
from data_processor import load_and_prep_data
from ui_components import create_sidebar_filters, plot_trend_dual_axis, plot_demographics, plot_geographic
from stats_analyzer import render_smart_insights # นำเข้าโมดูลสถิติใหม่

def main():
    # 1. ตั้งค่าหน้าเพจ (ต้องอยู่บรรทัดแรก)
    st.set_page_config(page_title="PM2.5 Health Surveillance", layout="wide")
    
    # --- Custom CSS เพื่อให้ UI ดูทันสมัยและฉลาดขึ้น ---
    st.markdown("""
        <style>
        /* 1. นำเข้าฟอนต์ Sarabun */
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;700&display=swap');
        
        /* 2. วิธีแก้แบบตรงจุด: 
           - กำหนดฟอนต์ Sarabun ให้กับ Element ที่เป็นข้อความหลักทั้งหมด
           - ใช้ Fallback เป็นฟอนต์ระบบมาตรฐาน เพื่อให้สัญลักษณ์ (Icons/Emojis) แสดงผลได้ปกติ
        */
        html, body, [data-testid="stAppViewContainer"], .stApp, p, h1, h2, h3, h4, h5, h6, label, li, span {
            font-family: 'Sarabun', "Source Sans Pro", "Segoe UI", "Apple Color Emoji", "Segoe UI Emoji", sans-serif !important;
        }

        /* 3. วิธีแก้เฉพาะจุดสำหรับปุ่มย่อ-ขยาย Sidebar และ Header:
           - บังคับให้ปุ่มควบคุม (Icons) กลับไปใช้ฟอนต์ดั้งเดิมของ Streamlit 100% 
           - เพื่อป้องกันไม่ให้ Sarabun ไปทับรหัสสัญลักษณ์ของปุ่มเหล่านั้น
        */
        [data-testid="collapsedControl"] button, 
        [data-testid="collapsedControl"] svg, 
        [data-testid="stHeader"] svg,
        button[kind="header"] {
            font-family: "Source Sans Pro", sans-serif !important;
        }

        /* 4. ตกแต่งกล่อง Metric */
        div[data-testid="metric-container"] {
            background-color: #ffffff;
            border: 1px solid #f0f2f6;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        }
        div[data-testid="metric-container"] > div > div > div > div > p {
            font-size: 1rem;
            color: #64748b;
            font-weight: 500;
        }
        div[data-testid="metric-container"] > div > div > div > div:nth-child(2) > p {
            font-size: 2rem;
            color: #0f172a;
            font-weight: 700;
        }
        </style>
    """, unsafe_allow_html=True)

    # 2. ส่วนหัวของ Dashboard
    st.title("จำนวนผู้ป่วยด้วยโรคที่เกี่ยวข้องกับการสัมผัส PM2.5")
    st.markdown("<p style='font-size: 1.1rem; color: #64748b;'>วิเคราะห์ความสัมพันธ์ระหว่างคุณภาพอากาศ และการเข้ารับบริการที่โรงพยาบาลแบบเรียลไทม์</p>", unsafe_allow_html=True)
    st.markdown("---")

    # 3. โหลดข้อมูล
    with st.spinner('กำลังประมวลผลข้อมูลสาธารณสุข...'):
        df_patients, df_pm25 = load_and_prep_data()

    if df_patients.empty:
        st.warning("⚠️ ไม่สามารถดำเนินการต่อได้ กรุณาอัปโหลดหรือตรวจสอบไฟล์ข้อมูลต้นทาง")
        st.stop()

    # 4. สร้าง Sidebar และรับค่าตัวกรอง (อัปเดตให้รับค่า 3 ตัวแปร รวมถึงกลุ่มเปราะบาง)
    selected_year, selected_disease, selected_vulnerable = create_sidebar_filters(df_patients)

    # --- 5. การประยุกต์ใช้ตัวกรองข้อมูล ---
    df_filtered = df_patients.copy()
    
    if selected_year:
        df_filtered = df_filtered[df_filtered['Date'].dt.year.isin(selected_year)]
    
    if selected_disease:
        df_filtered = df_filtered[df_filtered['4 กลุ่มโรคเฝ้าระวัง'].isin(selected_disease)]

    # เพิ่มการกรองกลุ่มเปราะบางที่เลือกจาก Sidebar
    if selected_vulnerable:
        if 'กลุ่มเปราะบาง' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['กลุ่มเปราะบาง'].isin(selected_vulnerable)]

    # --- 6. การแสดงผล KPI Cards ข้อมูลสรุป (ปรับให้เหลือ 2 คอลัมน์หลัก) ---
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

    st.markdown("<br>", unsafe_allow_html=True) # เว้นบรรทัด

    # --- 6.5 Smart Statistical Insight (ดึงจาก Module สถิติ) ---
    render_smart_insights(df_filtered, df_pm25)

    # --- 7. แสดงผลกราฟหลัก (Trend) ---
    st.markdown("### 📈 แนวโน้มผู้ป่วย 4 กลุ่มโรคเทียบกับระดับ PM2.5")
    plot_trend_dual_axis(df_filtered, df_pm25)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 8. แสดงผลกราฟรอง แบ่ง 2 คอลัมน์ให้ดูสวยงาม ---
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🩺 สัดส่วนกลุ่มโรคที่ได้รับผลกระทบ")
        plot_demographics(df_filtered)
        
    with col2:
        st.markdown("### 📍 10 อันดับพื้นที่เฝ้าระวัง (ระดับตำบล)")
        plot_geographic(df_filtered)

# จุดเริ่มต้นการทำงานของสคริปต์
if __name__ == "__main__":
    main()
