import streamlit as st
import pandas as pd

# นำเข้าฟังก์ชันจากไฟล์โมดูลที่เราแยกไว้
from data_processor import load_and_prep_data
from ui_components import create_sidebar_filters, plot_trend_dual_axis, plot_demographics, plot_geographic

def main():
    # 1. ตั้งค่าหน้าเพจ (ต้องอยู่บรรทัดแรก)
    st.set_page_config(page_title="PM2.5 Health Surveillance", page_icon="🌬️", layout="wide")
    
    # --- Custom CSS เพื่อให้ UI ดูทันสมัยและฉลาดขึ้น ---
    st.markdown("""
        <style>
        /* ตกแต่งกล่อง Metric ให้เป็น Card ดูมีมิติ */
        div[data-testid="metric-container"] {
            background-color: #ffffff;
            border: 1px solid #f0f2f6;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        }
        /* เปลี่ยนสีหัวข้อของ Metric */
        div[data-testid="metric-container"] > div > div > div > div > p {
            font-size: 1rem;
            color: #64748b;
            font-weight: 500;
        }
        /* เปลี่ยนสีตัวเลขของ Metric */
        div[data-testid="metric-container"] > div > div > div > div:nth-child(2) > p {
            font-size: 2rem;
            color: #0f172a;
            font-weight: 700;
        }
        </style>
    """, unsafe_allow_html=True)

    # 2. ส่วนหัวของ Dashboard
    st.title("🌬️ ระบบเฝ้าระวังผลกระทบทางสุขภาพจาก PM2.5")
    st.markdown("<p style='font-size: 1.1rem; color: #64748b;'>วิเคราะห์ความสัมพันธ์ระหว่างคุณภาพอากาศ และการเข้ารับบริการที่โรงพยาบาลแบบเรียลไทม์</p>", unsafe_allow_html=True)
    st.markdown("---")

    # 3. โหลดข้อมูล
    with st.spinner('กำลังประมวลผลข้อมูลสาธารณสุข...'):
        df_patients, df_pm25 = load_and_prep_data()

    if df_patients.empty:
        st.warning("⚠️ ไม่สามารถดำเนินการต่อได้ กรุณาอัปโหลดหรือตรวจสอบไฟล์ข้อมูลต้นทาง")
        st.stop()

    # 4. สร้าง Sidebar และรับค่าตัวกรอง
    selected_year, selected_disease, walk_in_filter = create_sidebar_filters(df_patients)

    # --- 5. การประยุกต์ใช้ตัวกรองข้อมูล ---
    df_filtered = df_patients.copy()
    
    if selected_year:
        df_filtered = df_filtered[df_filtered['Date'].dt.year.isin(selected_year)]
    
    if selected_disease:
        df_filtered = df_filtered[df_filtered['4 กลุ่มโรคเฝ้าระวัง'].isin(selected_disease)]

    if walk_in_filter == "เฉพาะ Walk-in (ไม่ได้นัด)":
        df_filtered = df_filtered[df_filtered['Is_Walk_in'] == 'Walk-in (ไม่ได้นัด)']
    elif walk_in_filter == "เฉพาะมาตามนัด":
        df_filtered = df_filtered[df_filtered['Is_Walk_in'] == 'Appointment (นัดมา)']

    # --- 6. การแสดงผล KPI Cards ข้อมูลสรุป ---
    total_cases = len(df_filtered)
    walk_in_count = len(df_filtered[df_filtered['Is_Walk_in'] == 'Walk-in (ไม่ได้นัด)'])
    walk_in_percent = (walk_in_count / total_cases * 100) if total_cases > 0 else 0
    
    max_pm = "-"
    if not df_pm25.empty and selected_year:
        max_pm_val = df_pm25[df_pm25['Month_Year'].dt.year.isin(selected_year)]['PM25'].max()
        max_pm = f"{max_pm_val:.1f}"

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    with kpi1:
        st.metric(label="👥 จำนวนผู้ป่วยสะสม (เคส)", value=f"{total_cases:,}")
    
    with kpi2:
        st.metric(label="🚨 ผู้ป่วยฉุกเฉิน (Walk-in)", value=f"{walk_in_count:,}")
        
    with kpi3:
        # เปลี่ยนเป็นอัตราส่วน Walk-in เพื่อให้ข้อมูลดู Insight และฉลาดขึ้น
        st.metric(label="📊 สัดส่วน Walk-in (%)", value=f"{walk_in_percent:.1f}%")
        
    with kpi4:
        st.metric(label="🌫️ ค่า PM2.5 สูงสุด (µg/m³)", value=max_pm)

    st.markdown("<br>", unsafe_allow_html=True) # เว้นบรรทัด

    # --- 7. แสดงผลกราฟหลัก (Trend) ---
    st.markdown("### 📈 แนวโน้มการรับบริการเทียบกับระดับ PM2.5")
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
