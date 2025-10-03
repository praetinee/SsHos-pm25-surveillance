import streamlit as st
import pandas as pd
from data_loader import generate_data
from plotting import plot_main_chart

# --- Page Configuration ---
st.set_page_config(
    page_title="แดชบอร์ดเฝ้าระวัง PM2.5",
    page_icon="💨",
    layout="wide"
)

# --- Main Application ---
st.title("📊 แดชบอร์ดเฝ้าระวังผลกระทบจากฝุ่น PM2.5")
st.markdown("แสดงความสัมพันธ์ระหว่างค่าฝุ่น PM2.5 และจำนวนผู้ป่วยในกลุ่มโรคที่เกี่ยวข้อง (ข้อมูลรายเดือน)")

# --- Load Data ---
# The generate_data() function from data_loader.py returns a clean, merged DataFrame
df = generate_data()

if not df.empty:
    # --- Sidebar for Filters ---
    st.sidebar.header("ตัวกรองข้อมูล")
    
    df['date'] = pd.to_datetime(df['date'])
    
    min_date = df['date'].min().date()
    max_date = df['date'].max().date()

    # Date range selector in the sidebar
    date_range = st.sidebar.date_input(
        "เลือกช่วงเวลา",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        format="YYYY-MM"
    )

    if len(date_range) == 2:
        start_date, end_date = date_range
        
        # Filter DataFrame based on the selected date range
        mask = (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
        filtered_df = df.loc[mask]

        # --- Display Area ---
        st.header("แนวโน้มจำนวนผู้ป่วยเทียบกับค่าฝุ่น PM2.5")
        
        # Get all disease group names from the DataFrame columns
        disease_groups = [col for col in filtered_df.columns if col not in ['date', 'pm25_level']]
        
        # Plot the main chart
        fig = plot_main_chart(filtered_df, disease_groups)
        st.plotly_chart(fig, use_container_width=True)

        # Display data table in an expander
        with st.expander("ดูตารางข้อมูล"):
            display_df = filtered_df.rename(columns={'date': 'เดือน', 'pm25_level': 'PM2.5 (ug/m3)'})
            for col in disease_groups:
                display_df[col] = display_df[col].astype(int)
            st.dataframe(display_df.style.format({"PM2.5 (ug/m3)": "{:.2f}"}), use_container_width=True)
    else:
        st.sidebar.warning("กรุณาเลือกช่วงวันที่ที่สมบูรณ์")
else:
    # This message will show if data loading fails, guided by errors in data_loader.py
    st.error("ไม่สามารถโหลดหรือประมวลผลข้อมูลได้ กรุณาตรวจสอบการตั้งค่าใน `data_loader.py` และการเชื่อมต่ออินเทอร์เน็ต")

