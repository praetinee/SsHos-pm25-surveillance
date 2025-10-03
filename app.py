import streamlit as st
import pandas as pd
from data_loader import generate_data
from plotting import plot_main_chart

st.set_page_config(layout="wide")

st.title("📊 แดชบอร์ดเฝ้าระวังผลกระทบจากฝุ่น PM2.5")
st.markdown("แสดงความสัมพันธ์ระหว่างค่าฝุ่น PM2.5 และจำนวนผู้ป่วยในกลุ่มโรคที่เกี่ยวข้อง")

# --- โหลดข้อมูลที่เตรียมไว้ ---
# ฟังก์ชัน generate_data() จาก data_loader จะคืนค่า DataFrame ที่รวมข้อมูลแล้ว
df = generate_data()

if not df.empty:
    # --- ส่วนของการกรองข้อมูล ---
    st.sidebar.header("ตัวกรองข้อมูล")
    
    # แปลงคอลัมน์ date เป็น datetime เพื่อให้ st.date_input ใช้งานได้
    df['date'] = pd.to_datetime(df['date'])
    
    min_date = df['date'].min().date()
    max_date = df['date'].max().date()

    date_range = st.sidebar.date_input(
        "เลือกช่วงเวลา (รายเดือน)",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        format="YYYY-MM"
    )

    if len(date_range) == 2:
        start_date, end_date = date_range
        
        # กรอง DataFrame ตามช่วงวันที่ที่เลือก
        mask = (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
        filtered_df = df.loc[mask]

        # --- ส่วนของการแสดงผล ---
        st.header("กราฟแสดงแนวโน้มจำนวนผู้ป่วยเทียบกับค่าฝุ่น PM2.5")
        
        # ดึงชื่อกลุ่มโรคทั้งหมดจากคอลัมน์ของ DataFrame (ยกเว้น 'date' และ 'pm25_level')
        disease_groups = [col for col in filtered_df.columns if col not in ['date', 'pm25_level']]
        
        fig = plot_main_chart(filtered_df, disease_groups)
        st.plotly_chart(fig, use_container_width=True)

        # แสดงตารางข้อมูล
        with st.expander("ดูตารางข้อมูล"):
            st.dataframe(filtered_df.style.format({"pm25_level": "{:.2f}"}))
    else:
        st.warning("กรุณาเลือกช่วงวันที่ที่สมบูรณ์")
else:
    st.error("ไม่สามารถโหลดข้อมูลได้ กรุณาตรวจสอบการตั้งค่าใน data_loader.py")

