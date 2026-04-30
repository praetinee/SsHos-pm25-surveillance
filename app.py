import streamlit as st
import pandas as pd

# นำเข้าฟังก์ชันจากไฟล์โมดูลที่เราแยกไว้
from data_processor import load_and_prep_data
from ui_components import create_sidebar_filters, plot_trend_dual_axis, plot_demographics, plot_geographic, plot_icd10_trend
from stats_analyzer import render_smart_insights 

def main():
    # 1. ตั้งค่าหน้าเพจ
    st.set_page_config(page_title="PM2.5 Health Surveillance", layout="wide")
    
    # --- Custom CSS ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;700&display=swap');
        
        html, body, [data-testid="stAppViewContainer"], .stApp, p, h1, h2, h3, h4, h5, h6, label, li, span {
            font-family: 'Sarabun', "Source Sans Pro", "Segoe UI", "Apple Color Emoji", "Segoe UI Emoji", sans-serif !important;
        }

        div[data-testid="metric-container"] {
            background-color: #ffffff;
            border: 1px solid #f0f2f6;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        }
        </style>
    """, unsafe_allow_html=True)

    # 2. ส่วนหัวของ Dashboard
    st.title("จำนวนผู้ป่วยด้วยโรคที่เกี่ยวข้องกับการสัมผัส PM2.5")
    st.markdown("<p style='font-size: 1.1rem; color: #64748b;'>วิเคราะห์ความสัมพันธ์ระหว่างคุณภาพอากาศ และการเข้ารับบริการที่โรงพยาบาลสันทราย</p>", unsafe_allow_html=True)
    st.markdown("---")

    # 3. โหลดข้อมูล
    with st.spinner('กำลังประมวลผลข้อมูลสาธารณสุข...'):
        df_patients, df_pm25 = load_and_prep_data()

    if df_patients.empty:
        st.warning("⚠️ ไม่สามารถดำเนินการต่อได้ กรุณาอัปโหลดหรือตรวจสอบไฟล์ข้อมูลต้นทาง")
        st.stop()

    # 4. สร้าง Sidebar และรับค่าตัวกรอง (รับค่า 3 ตัวแปรตามที่ UI Component ส่งมา)
    selected_year, selected_disease, selected_vulnerable = create_sidebar_filters(df_patients)

    # --- 5. การประยุกต์ใช้ตัวกรองข้อมูล ---
    df_filtered = df_patients.copy()
    
    if selected_year:
        df_filtered = df_filtered[df_filtered['Date'].dt.year.isin(selected_year)]
    if selected_disease:
        df_filtered = df_filtered[df_filtered['4 กลุ่มโรคเฝ้าระวัง'].isin(selected_disease)]
    if selected_vulnerable and 'กลุ่มเปราะบาง' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['กลุ่มเปราะบาง'].isin(selected_vulnerable)]

    # =========================================================================
    # สร้าง TABS 
    # =========================================================================
    tab1, tab2 = st.tabs(["📊 ภาพรวม (Overview)", "🔬 เจาะลึกรายรหัสโรค (Top 3 ICD-10)"])

    # ------------------ แท็บที่ 1: ภาพรวม ------------------
    with tab1:
        total_cases = len(df_filtered)
        max_pm = "-"
        if not df_pm25.empty and selected_year:
            max_pm_val = df_pm25[df_pm25['Month_Year'].dt.year.isin(selected_year)]['PM25'].max()
            max_pm = f"{max_pm_val:.1f}"

        kpi1, kpi2 = st.columns(2)
        with kpi1: st.metric(label="👥 จำนวนผู้ป่วยสะสม (เคส)", value=f"{total_cases:,}")
        with kpi2: st.metric(label="🌫️ ค่า PM2.5 สูงสุด (µg/m³)", value=max_pm)

        st.markdown("<br>", unsafe_allow_html=True)
        render_smart_insights(df_filtered, df_pm25)

        st.markdown("### 📈 แนวโน้มการรับบริการเทียบกับระดับ PM2.5")
        plot_trend_dual_axis(df_filtered, df_pm25)
        st.markdown("<br>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🩺 สัดส่วนกลุ่มโรคที่ได้รับผลกระทบ")
            plot_demographics(df_filtered)
        with col2:
            st.markdown("### 📍 10 อันดับพื้นที่เฝ้าระวัง (ระดับตำบล)")
            plot_geographic(df_filtered)

    # ------------------ แท็บที่ 2: เจาะลึกตามรหัสโรค (ICD-10) ------------------
    with tab2:
        st.markdown("### 🔬 วิเคราะห์เจาะลึก 3 อันดับโรคฮิตของแต่ละกลุ่มโรค")
        if not selected_disease:
            st.info("👈 กรุณาเลือก 'กลุ่มโรคเฝ้าระวัง' จากเมนูด้านข้างเพื่อดูข้อมูลเจาะลึก")
        else:
            icd_col = 'ICD10_โรคเฝ้าระวัง'
            icd_desc_col = 'โรคหลัก'
            icd_options = []
            for disease in selected_disease:
                if any(exclude_word in disease for exclude_word in ["ทำงาน", "สิ่งแวดล้อม", "Z58.1"]): continue
                df_d = df_filtered[df_filtered['4 กลุ่มโรคเฝ้าระวัง'] == disease]
                if not df_d.empty:
                    top3_icds = df_d[icd_col].value_counts().head(3).index.tolist()
                    for icd in top3_icds:
                        desc_series = df_d[df_d[icd_col] == icd][icd_desc_col]
                        desc_val = desc_series.iloc[0] if not desc_series.empty else "ไม่มีคำแปล"
                        icd_options.append(f"{disease} | รหัส ICD-10: {icd} | คำแปล: {desc_val}")
            icd_options.append("🌟 กลุ่มโรคเจาะจง | รหัส ICD-10: J44.1 | คำแปล: COPD with acute exacerbation")
            
            selected_option = st.selectbox("📌 เลือกรหัสโรคเพื่อพลอตกราฟและดูสถิติ:", options=icd_options)
            parts = selected_option.replace("🌟 ", "").split(" | ")
            selected_group, selected_icd = parts[0], parts[1].replace("รหัส ICD-10: ", "")
            selected_desc = parts[2].replace("คำแปล: ", "") if len(parts) > 2 else "ไม่มีคำแปล"
            
            df_icd_specific = df_filtered[df_filtered[icd_col] == selected_icd] if selected_group == "กลุ่มโรคเจาะจง" else df_filtered[(df_filtered['4 กลุ่มโรคเฝ้าระวัง'] == selected_group) & (df_filtered[icd_col] == selected_icd)]
            st.markdown(f"#### รหัสโรค: {selected_icd} - {selected_desc}")
            render_smart_insights(df_icd_specific, df_pm25)
            plot_icd10_trend(df_icd_specific, df_pm25, selected_icd)

if __name__ == "__main__":
    main()
