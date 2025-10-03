import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

st.title("🕵️‍♂️ เครื่องมือตรวจสอบการเชื่อมต่อ Google Sheet (เวอร์ชันสุดท้าย)")
st.markdown("---")

# --- ฟังก์ชันสำหรับโหลดข้อมูล ---
@st.cache_data(ttl=30) # ลดเวลา cache เพื่อให้เห็นการเปลี่ยนแปลงเร็วขึ้น
def load_data_from_gsheet():
    """
    ฟังก์ชันสำหรับโหลดข้อมูลดิบจาก Google Sheet เพื่อการตรวจสอบ
    """
    SHEET_URL = "https://docs.google.com/spreadsheets/d/1vvQ8YLChHXvCowQQzcKIeV4PWt0CCt76f5Sj3fNTOV0/export?format=csv&gid=795124395"
    try:
        # อ่านข้อมูลโดยไม่แปลงอะไรเลย
        df = pd.read_csv(SHEET_URL)
        return df
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดร้ายแรงระหว่างการโหลดข้อมูล: {e}")
        st.error("อาจเป็นเพราะไม่สามารถเข้าถึง URL ได้ กรุณาตรวจสอบการตั้งค่าการแชร์ของ Google Sheet อีกครั้ง")
        return None

# --- เริ่มการทำงาน ---
st.info("กำลังพยายามโหลดข้อมูลจาก Google Sheet... กรุณารอสักครู่")

df_raw = load_data_from_gsheet()

# --- แสดงผลลัพธ์ ---
if df_raw is not None and not df_raw.empty:
    st.success("🎉 เยี่ยม! โหลดข้อมูลดิบสำเร็จแล้วครับ")
    st.markdown("---")
    
    st.markdown("### 1. ชื่อคอลัมน์ทั้งหมดที่โปรแกรมได้รับ:")
    st.code(df_raw.columns.tolist(), language='python')
    st.markdown("""
    👆 **นี่คือ "ชื่อจริง" ของคอลัมน์ที่โปรแกรมเห็นครับ** เราจะใช้ชื่อเหล่านี้ในการแก้ไขโค้ดหลักต่อไป
    """)

    st.markdown("---")
    
    st.markdown("### 2. ตัวอย่างข้อมูล 10 แถวแรก (ข้อมูลดิบ):")
    st.dataframe(df_raw.head(10))
    st.markdown("""
    👆 **นี่คือ "หน้าตาข้อมูล" ที่โปรแกรมเห็น** กรุณาสังเกตคอลัมน์วันที่, อายุ, และกลุ่มโรค
    """)
    
else:
    st.error("ไม่สามารถโหลดข้อมูลได้ หรือข้อมูลที่โหลดมาว่างเปล่า")
    st.markdown("""
    **กรุณาตรวจสอบอีกครั้งว่า:**
    1.  **การตั้งค่าการแชร์:** ไฟล์ Google Sheet ของคุณได้ตั้งค่าเป็น **"ทุกคนที่มีลิงก์" (Anyone with the link)** แล้วจริงๆ
    2.  **URL และ GID ถูกต้อง:** URL และ GID (`gid=795124395`) ของชีตถูกต้อง
    3.  **ชีตมีข้อมูล:** ชีตที่คุณกำลังดึงข้อมูลมีข้อมูลอยู่จริงๆ
    """)

