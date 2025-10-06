import streamlit as st
import pandas as pd
import plotly.express as px

# ตั้งค่าหัวข้อและคำอธิบายของแอป
st.set_page_config(layout="wide")
st.title("📊 กราฟแสดงจำนวนผู้ป่วยเข้ารับการรักษา")
st.write("แอปนี้แสดงข้อมูลจำนวนผู้ป่วยรายวันจาก Google Sheet")

# --- ฟังก์ชันโหลดและประมวลผลข้อมูล ---
@st.cache_data(ttl=600) # Cache ข้อมูลไว้ 10 นาที เพื่อไม่ให้โหลดใหม่ทุกครั้งที่รีเฟรช
def load_data(url):
    """
    ฟังก์ชันสำหรับโหลดข้อมูลจาก Google Sheet URL และประมวลผลข้อมูลวันที่
    """
    try:
        # โหลดข้อมูลจาก URL ที่เป็น CSV export
        df = pd.read_csv(url)

        # --- ส่วนที่สำคัญที่สุด ---
        # !!! กรุณาเปลี่ยน 'date' ในบรรทัดถัดไป ให้เป็นชื่อคอลัมน์ "วันที่" ที่ถูกต้องในไฟล์ Google Sheet ของคุณ
        # เช่น ถ้าชื่อคอลัมน์คือ 'วันที่รับบริการ' ให้เปลี่ยนเป็น df['วันที่รับบริการ']
        date_column_name = 'วันที่มารับบริการ' # <--- ❗️❗️ เปลี่ยนตรงนี้

        # ตรวจสอบว่ามีคอลัมน์วันที่ที่ระบุหรือไม่
        if date_column_name not in df.columns:
            st.error(f"ไม่พบคอลัมน์ '{date_column_name}' ใน Google Sheet ของคุณ")
            st.info(f"คอลัมน์ที่มีอยู่คือ: {list(df.columns)}")
            return None, None

        # แปลงคอลัมน์วันที่ให้เป็นรูปแบบ datetime ซึ่งจำเป็นสำหรับการทำงานกับข้อมูลเวลา
        # errors='coerce' จะทำให้ค่าที่แปลงไม่ได้กลายเป็น NaT (Not a Time)
        df['date_processed'] = pd.to_datetime(df[date_column_name], errors='coerce')

        # ลบแถวที่ข้อมูลวันที่เสียหายหรือไม่สามารถแปลงได้
        df.dropna(subset=['date_processed'], inplace=True)

        # นับจำนวนผู้ป่วยในแต่ละวัน
        # เราจัดกลุ่มข้อมูลตาม 'วัน' (ไม่รวมเวลา) แล้วนับจำนวนแถวในแต่ละกลุ่ม
        daily_counts = df.groupby(df['date_processed'].dt.date).size().reset_index(name='patient_count')
        daily_counts.rename(columns={'date_processed': 'date'}, inplace=True)

        return df, daily_counts

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดหรือประมวลผลข้อมูล: {e}")
        return None, None

# --- ส่วนการทำงานหลักของแอป ---

# ดึง URL ของ Google Sheet จาก Streamlit Secrets เพื่อความปลอดภัย
# เราจะไปตั้งค่านี้ในขั้นตอนสุดท้าย
try:
    G_SHEET_URL = st.secrets["G_SHEET_URL"]
except:
    st.error("⚠️ กรุณาตั้งค่า G_SHEET_URL ใน Streamlit Secrets ก่อน")
    st.stop()


# โหลดข้อมูล
original_df, patient_counts_df = load_data(G_SHEET_URL)

# ถ้าโหลดข้อมูลสำเร็จ ให้แสดงผล
if patient_counts_df is not None:

    # --- แสดงกราฟเส้น ---
    st.header("จำนวนผู้ป่วยรายวัน")

    # สร้างกราฟเส้นด้วย Plotly Express
    fig = px.line(
        patient_counts_df,
        x='date',
        y='patient_count',
        title='แนวโน้มจำนวนผู้ป่วย',
        labels={'date': 'วันที่', 'patient_count': 'จำนวนผู้ป่วย'},
        markers=True # แสดงจุดบนกราฟ
    )
    fig.update_layout(
        xaxis_title="วันที่",
        yaxis_title="จำนวนผู้ป่วย",
        font=dict(family="Arial, sans-serif", size=14)
    )

    # แสดงกราฟในแอป
    st.plotly_chart(fig, use_container_width=True)


    # --- แสดงตารางข้อมูลสรุป ---
    st.header("ข้อมูลสรุปรายวัน")
    st.dataframe(patient_counts_df.sort_values(by='date', ascending=False), use_container_width=True)


    # --- แสดงข้อมูลดิบ (เผื่อต้องการตรวจสอบ) ---
    with st.expander("แสดงข้อมูลดิบจาก Google Sheet"):
        st.dataframe(original_df, use_container_width=True)
