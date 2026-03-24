import streamlit as st

# นำเข้าฟังก์ชันจากไฟล์โมดูลที่เราแยกไว้
from data_processor import load_and_prep_data
from ui_components import create_sidebar_filters, plot_trend_dual_axis, plot_demographics, plot_geographic

def main():
    # 1. ตั้งค่าหน้าเพจ (ต้องอยู่บรรทัดแรกของคำสั่ง Streamlit เสมอ)
    st.set_page_config(page_title="PM2.5 Health Watch", page_icon="😷", layout="wide")
    
    st.title("😷 ระบบเฝ้าระวังผู้ป่วยจากผลกระทบ PM2.5")
    st.markdown("วิเคราะห์ความสัมพันธ์ระหว่างคุณภาพอากาศและการเข้ารับบริการที่โรงพยาบาล")

    # 2. โหลดข้อมูล (เรียกใช้จาก data_processor.py)
    with st.spinner('กำลังเตรียมข้อมูล...'):
        df_patients, df_pm25 = load_and_prep_data()

    if df_patients.empty:
        st.warning("ไม่สามารถดำเนินการต่อได้ กรุณาอัปโหลดหรือตรวจสอบไฟล์ข้อมูลต้นทาง")
        st.stop()

    # 3. สร้าง Sidebar และรับค่าตัวกรอง (เรียกใช้จาก ui_components.py)
    selected_year, selected_disease, walk_in_filter = create_sidebar_filters(df_patients)

    # --- 4. การประยุกต์ใช้ตัวกรองข้อมูล (Apply Filters) ---
    df_filtered = df_patients.copy()
    
    if selected_year:
        df_filtered = df_filtered[df_filtered['Date'].dt.year.isin(selected_year)]
    
    if selected_disease:
        df_filtered = df_filtered[df_filtered['4 กลุ่มโรคเฝ้าระวัง'].isin(selected_disease)]

    if walk_in_filter == "เฉพาะ Walk-in (ไม่ได้นัด)":
        df_filtered = df_filtered[df_filtered['Is_Walk_in'] == 'Walk-in (ไม่ได้นัด)']
    elif walk_in_filter == "เฉพาะมาตามนัด":
        df_filtered = df_filtered[df_filtered['Is_Walk_in'] == 'Appointment (นัดมา)']

    # --- 5. การแสดงผล KPI Cards ข้อมูลสรุป ---
    st.markdown("### 📊 สรุปภาพรวม (ตามเงื่อนไขที่กรอง)")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    with kpi1:
        st.metric(label="จำนวนผู้ป่วยทั้งหมด (เคส)", value=f"{len(df_filtered):,}")
    
    with kpi2:
        walk_in_count = len(df_filtered[df_filtered['Is_Walk_in'] == 'Walk-in (ไม่ได้นัด)'])
        st.metric(label="ผู้ที่ไม่ได้นัด (Walk-in)", value=f"{walk_in_count:,}")
        
    with kpi3:
        new_case_count = len(df_filtered[df_filtered['Patient_Type'] == 'ผู้ป่วยใหม่'])
        st.metric(label="ผู้ป่วยใหม่", value=f"{new_case_count:,}")
        
    with kpi4:
        # หาค่าฝุ่นสูงสุดในปีที่เลือก
        if not df_pm25.empty and selected_year:
            max_pm = df_pm25[df_pm25['Month_Year'].dt.year.isin(selected_year)]['PM25'].max()
            st.metric(label="PM2.5 สูงสุด (ug/m3)", value=f"{max_pm:.1f}")
        else:
            st.metric(label="PM2.5 สูงสุด (ug/m3)", value="-")

    st.markdown("---")

    # --- 6. แสดงผลกราฟต่างๆ (เรียกใช้จาก ui_components.py) ---
    st.markdown("### 📈 แนวโน้มและความสัมพันธ์")
    plot_trend_dual_axis(df_filtered, df_pm25)

    st.markdown("---")
    st.markdown("### 🔍 เจาะลึกข้อมูลทางคลินิกและพื้นที่")
    plot_demographics(df_filtered)
    plot_geographic(df_filtered)

# จุดเริ่มต้นการทำงานของสคริปต์
if __name__ == "__main__":
    main()
