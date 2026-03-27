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

        [data-testid="collapsedControl"] button, 
        [data-testid="collapsedControl"] svg, 
        [data-testid="stHeader"] svg,
        button[kind="header"] {
            font-family: "Source Sans Pro", sans-serif !important;
        }

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
        
        /* ตกแต่ง Tabs */
        .stTabs [data-baseweb="tab-list"] { gap: 20px; }
        .stTabs [data-baseweb="tab"] {
            height: 50px; white-space: pre-wrap; background-color: transparent;
            border-radius: 8px 8px 0px 0px; padding-top: 10px; padding-bottom: 10px;
            font-size: 1.1rem; font-weight: 500;
        }
        .stTabs [aria-selected="true"] {
            background-color: #f8fafc; border-bottom: 3px solid #3b82f6 !important; color: #0f172a;
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
    if selected_vulnerable and 'กลุ่มเปราะบาง' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['กลุ่มเปราะบาง'].isin(selected_vulnerable)]

    # =========================================================================
    # สร้าง TABS 
    # =========================================================================
    tab1, tab2 = st.tabs(["📊 ภาพรวม (Overview)", "🔬 เจาะลึกรายรหัสโรค (Top 3 ICD-10)"])

    # ------------------ แท็บที่ 1: ภาพรวม ------------------
    with tab1:
        total_cases = len(df_filtered)
        walk_in_count = len(df_filtered[df_filtered['Is_Walk_in'] == 'Walk-in (ไม่ได้นัด)'])
        walk_in_percent = (walk_in_count / total_cases * 100) if total_cases > 0 else 0
        
        max_pm = "-"
        if not df_pm25.empty and selected_year:
            max_pm_val = df_pm25[df_pm25['Month_Year'].dt.year.isin(selected_year)]['PM25'].max()
            max_pm = f"{max_pm_val:.1f}"

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        with kpi1: st.metric(label="👥 จำนวนผู้ป่วยสะสม (เคส)", value=f"{total_cases:,}")
        with kpi2: st.metric(label="🚨 ผู้ป่วย Walk-in", value=f"{walk_in_count:,}")
        with kpi3: st.metric(label="📊 สัดส่วน Walk-in (%)", value=f"{walk_in_percent:.1f}%")
        with kpi4: st.metric(label="🌫️ ค่า PM2.5 สูงสุด (µg/m³)", value=max_pm)

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
        st.markdown("<p style='color: #64748b;'>รวมข้อมูลสถิติเชิงลึกและแนวโน้มปริมาณฝุ่น PM2.5 เทียบกับจำนวนผู้ป่วย โดยเจาะจงเฉพาะระดับรหัสโรค (ICD-10)</p>", unsafe_allow_html=True)
        
        if not selected_disease:
            st.info("👈 กรุณาเลือก 'กลุ่มโรคเฝ้าระวัง' จากเมนูด้านข้างเพื่อดูข้อมูลเจาะลึก")
        else:
            # 1. กำหนดชื่อคอลัมน์ที่ชัดเจน (P = ICD10_โรคเฝ้าระวัง, S = โรคหลัก)
            icd_col = 'ICD10_โรคเฝ้าระวัง'
            icd_desc_col = 'โรคหลัก'
            
            if icd_col not in df_filtered.columns or icd_desc_col not in df_filtered.columns:
                st.warning(f"⚠️ ไม่พบคอลัมน์ '{icd_col}' หรือ '{icd_desc_col}' ในชุดข้อมูล กรุณาตรวจสอบชื่อคอลัมน์อีกครั้ง")
                st.stop()
                
            # 2. หา Top 3 ICD-10 ของแต่ละกลุ่มโรคที่ถูกเลือกมา
            icd_options = []
            
            for disease in selected_disease:
                # ข้ามกลุ่มโรคที่ไม่ต้องการแสดงในตัวเลือก (ทำงาน, สิ่งแวดล้อม, Z58.1)
                if any(exclude_word in disease for exclude_word in ["ทำงาน", "สิ่งแวดล้อม", "Z58.1"]):
                    continue
                    
                df_d = df_filtered[df_filtered['4 กลุ่มโรคเฝ้าระวัง'] == disease]
                if not df_d.empty:
                    # นับจำนวนและดึงมาแค่ 3 อันดับแรกของกลุ่มนี้
                    top3_icds = df_d[icd_col].value_counts().head(3).index.tolist()
                    
                    for icd in top3_icds:
                        # หาคำแปลของรหัส ICD นี้จากคอลัมน์ S (ดึงค่าแรกที่เจอ)
                        desc_series = df_d[df_d[icd_col] == icd][icd_desc_col]
                        desc_val = desc_series.iloc[0] if not desc_series.empty else None
                        icd_desc = desc_val if pd.notna(desc_val) and str(desc_val).strip() != '' else "ไม่มีคำแปล"
                        
                        # จัด Format ให้สวยงามเวลาแสดงใน Dropdown
                        icd_options.append(f"{disease} | รหัส ICD-10: {icd} | คำแปล: {icd_desc}")
            
            # 2.5 เพิ่มตัวเลือกสุดท้ายที่เจาะจง J44.1 (ใส่ Icon ให้เด่นขึ้นแทนการใช้เส้นคั่น)
            icd_options.append("🌟 กลุ่มโรคเจาะจง | รหัส ICD-10: J44.1 | คำแปล: COPD with acute exacerbation")
            
            # 3. แสดงตัวเลือก (Selectbox) เพียง 1 ตัวเพื่อใช้ควบคู่กับสถิติ 1 ส่วน
            st.markdown("<hr style='border-color: #f1f5f9; margin-top: 10px; margin-bottom: 20px;'>", unsafe_allow_html=True)
            selected_option = st.selectbox(
                "📌 เลือกรหัสโรคเพื่อพลอตกราฟและดูสถิติ (ดึงมาจาก Top 3 ของแต่ละกลุ่ม):", 
                options=icd_options
            )
            
            # 4. แกะชื่อกลุ่มโรค, รหัสโรค (ICD-10), และคำแปล ออกมาจาก String
            # ใช้ .replace("🌟 ", "") เพื่อตัดไอคอนออกก่อนนำไปประมวลผลต่อ
            parts = selected_option.replace("🌟 ", "").split(" | ")
            selected_group = parts[0]
            selected_icd = parts[1].replace("รหัส ICD-10: ", "")
            selected_desc = parts[2].replace("คำแปล: ", "") if len(parts) > 2 else "ไม่มีคำแปล"
            
            # 5. กรองข้อมูลเฉพาะรหัสโรคนี้
            if selected_group == "กลุ่มโรคเจาะจง":
                # ถ้าเป็นกลุ่มเจาะจงพิเศษ (J44.1) ไม่ต้องสนว่ามาจากกลุ่มไหน
                df_icd_specific = df_filtered[df_filtered[icd_col] == selected_icd]
            else:
                df_icd_specific = df_filtered[(df_filtered['4 กลุ่มโรคเฝ้าระวัง'] == selected_group) & (df_filtered[icd_col] == selected_icd)]
            
            st.markdown(f"<h4 style='color: #0f172a; margin-top: 15px;'>รหัสโรค: <span style='color: #8b5cf6;'>{selected_icd} - {selected_desc}</span></h4><p style='font-size: 1rem; color: #64748b;'>(จากกลุ่ม: {selected_group})</p>", unsafe_allow_html=True)
            
            # 6. แสดง Smart Insights สถิติอัจฉริยะ 
            render_smart_insights(df_icd_specific, df_pm25)
            
            # 7. แสดงกราฟแนวโน้มเฉพาะของ ICD-10 นี้
            st.markdown(f"**📈 แนวโน้มผู้ป่วยรหัสโรค '{selected_icd}' เทียบกับระดับ PM2.5**")
            plot_icd10_trend(df_icd_specific, df_pm25, selected_icd)

if __name__ == "__main__":
    main()
