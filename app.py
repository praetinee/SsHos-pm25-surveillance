import streamlit as st
import pandas as pd

# นำเข้าฟังก์ชันจากไฟล์โมดูลที่เราแยกไว้
from data_processor import load_and_prep_data
# เพิ่มการ import ฟังก์ชัน plot_disease_group_trend ที่เราจะสร้างใหม่
from ui_components import create_sidebar_filters, plot_trend_dual_axis, plot_demographics, plot_geographic, plot_disease_group_trend
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

        /* 3. วิธีแก้เฉพาะจุดสำหรับปุ่มย่อ-ขยาย Sidebar และ Header */
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
        
        /* 5. ตกแต่ง Tabs ของ Streamlit ให้ดูสวยงามขึ้น */
        .stTabs [data-baseweb="tab-list"] {
            gap: 20px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: transparent;
            border-radius: 8px 8px 0px 0px;
            padding-top: 10px;
            padding-bottom: 10px;
            font-size: 1.1rem;
            font-weight: 500;
        }
        .stTabs [aria-selected="true"] {
            background-color: #f8fafc;
            border-bottom: 3px solid #3b82f6 !important;
            color: #0f172a;
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

    # 4. สร้าง Sidebar และรับค่าตัวกรอง
    selected_year, selected_disease, walk_in_filter, selected_vulnerable = create_sidebar_filters(df_patients)

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

    if selected_vulnerable:
        if 'กลุ่มเปราะบาง' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['กลุ่มเปราะบาง'].isin(selected_vulnerable)]

    # =========================================================================
    # สร้าง TABS แบ่งหน้าจอการทำงาน (เพิ่มใหม่ตามความต้องการ)
    # =========================================================================
    tab1, tab2 = st.tabs(["📊 ภาพรวม (Overview)", "🔬 เจาะลึกรายกลุ่มโรค (Disease Insights)"])

    # ------------------ แท็บที่ 1: ภาพรวม (โค้ดเดิมทั้งหมด) ------------------
    with tab1:
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
            st.metric(label="🚨 ผู้ป่วย Walk-in", value=f"{walk_in_count:,}")
            
        with kpi3:
            st.metric(label="📊 สัดส่วน Walk-in (%)", value=f"{walk_in_percent:.1f}%")
            
        with kpi4:
            st.metric(label="🌫️ ค่า PM2.5 สูงสุด (µg/m³)", value=max_pm)

        st.markdown("<br>", unsafe_allow_html=True) # เว้นบรรทัด

        # --- 6.5 Smart Statistical Insight (ดึงจาก Module สถิติ) ---
        render_smart_insights(df_filtered, df_pm25)

        # --- 7. แสดงผลกราฟหลัก (Trend) ---
        st.markdown("### 📈 แนวโน้มการรับบริการเทียบกับระดับ PM2.5")
        plot_trend_dual_axis(df_filtered, df_pm25)

        st.markdown("<br>", unsafe_allow_html=True)

        # --- 8. แสดงผลกราฟรอง แบ่ง 2 คอลัมน์ ---
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🩺 สัดส่วนกลุ่มโรคที่ได้รับผลกระทบ")
            plot_demographics(df_filtered)
            
        with col2:
            st.markdown("### 📍 10 อันดับพื้นที่เฝ้าระวัง (ระดับตำบล)")
            plot_geographic(df_filtered)

    # ------------------ แท็บที่ 2: เจาะลึกรายกลุ่มโรค (ส่วนที่เพิ่มใหม่) ------------------
    with tab2:
        st.markdown("### 🔬 วิเคราะห์เจาะลึกแนวโน้มตามกลุ่มโรค")
        st.markdown("<p style='color: #64748b;'>แสดงความสัมพันธ์ทางสถิติและแนวโน้มระหว่างปริมาณฝุ่น PM2.5 เทียบกับจำนวนผู้ป่วย <b>แยกตามแต่ละกลุ่มโรคอย่างละเอียด</b></p>", unsafe_allow_html=True)
        
        if not selected_disease:
            st.info("👈 กรุณาเลือก 'กลุ่มโรคเฝ้าระวัง' จากเมนูด้านข้างเพื่อดูข้อมูลเจาะลึก")
        else:
            # วนลูปแสดงข้อมูลของแต่ละกลุ่มโรคที่ถูกเลือกจาก Sidebar
            for disease in selected_disease:
                st.markdown(f"<hr style='margin-top: 2rem; margin-bottom: 2rem; border-color: #e2e8f0;'>", unsafe_allow_html=True)
                st.markdown(f"<h4 style='color: #0f172a;'>🩺 กลุ่มโรค: <span style='color: #3b82f6;'>{disease}</span></h4>", unsafe_allow_html=True)

                # กรองข้อมูลเฉพาะกลุ่มโรคนี้
                df_disease_specific = df_filtered[df_filtered['4 กลุ่มโรคเฝ้าระวัง'] == disease]

                if df_disease_specific.empty:
                    st.warning(f"ไม่มีข้อมูลผู้ป่วยสำหรับกลุ่มโรค '{disease}' ในช่วงเวลา/เงื่อนไข ที่เลือก")
                    continue

                # 1. แสดง Smart Insights สถิติอัจฉริยะ (ใช้ฟังก์ชันเดิม แต่ข้อมูลถูกกรองเฉพาะโรคแล้ว)
                render_smart_insights(df_disease_specific, df_pm25)

                # 2. แสดงกราฟแนวโน้มเฉพาะของโรคนี้
                st.markdown(f"**📈 แนวโน้มผู้ป่วย '{disease}' เทียบกับระดับ PM2.5**")
                plot_disease_group_trend(df_disease_specific, df_pm25, disease)

# จุดเริ่มต้นการทำงานของสคริปต์
if __name__ == "__main__":
    main()
