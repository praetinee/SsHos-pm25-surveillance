import pandas as pd
import streamlit as st

@st.cache_data(ttl=3600) # เพิ่ม ttl=3600 เพื่อให้ดึงข้อมูลใหม่ทุกๆ 1 ชั่วโมง
def load_and_prep_data():
    """
    ฟังก์ชันสำหรับโหลดข้อมูลจาก Google Sheets และทำความสะอาดข้อมูลให้อยู่ในรูปแบบที่พร้อมใช้งาน
    """
    # แปลง URL ของ Google Sheets ให้อยู่ในรูปแบบ Export เป็น CSV (เปลี่ยนไปใช้ gid 1349362308)
    url_patients = "https://docs.google.com/spreadsheets/d/1vvQ8YLChHXvCowQQzcKIeV4PWt0CCt76f5Sj3fNTOV0/export?format=csv&gid=1349362308"
    url_pm25 = "https://docs.google.com/spreadsheets/d/1vvQ8YLChHXvCowQQzcKIeV4PWt0CCt76f5Sj3fNTOV0/export?format=csv&gid=1038807599"

    try:
        # โหลดข้อมูลจาก URL โดยตรง
        df_patients = pd.read_csv(url_patients)
        df_pm25 = pd.read_csv(url_pm25)
    except Exception as e:
        # ถ้าโหลดไม่ได้ ให้แสดง Error แจ้งเตือนผู้ใช้
        st.error(f"ไม่สามารถดึงข้อมูลจาก Google Sheets ได้ กรุณาตรวจสอบการตั้งค่าการแชร์ (ต้องเป็น 'Anyone with the link')\n\nข้อผิดพลาด: {e}")
        return pd.DataFrame(), pd.DataFrame()

    # --- การทำความสะอาดข้อมูลผู้ป่วย (df_patients) ---
    
    # ก. แปลงวันที่ (ปี พ.ศ. เป็น ค.ศ.)
    def convert_thai_date(date_str):
        try:
            d, m, y = str(date_str).split('/')
            return pd.to_datetime(f"{int(y)-543}-{m}-{d}")
        except:
            return pd.NaT
            
    df_patients['Date'] = df_patients['วันที่มารับบริการ'].apply(convert_thai_date)
    df_patients['Month_Year'] = df_patients['Date'].dt.to_period('M')

    # ข. เปลี่ยนชื่อกลุ่มโรค "ไม่จัดอยู่ใน 4 กลุ่มโรค" เป็น "โรคร่วม Z58.1" อย่างครอบคลุม
    if '4 กลุ่มโรคเฝ้าระวัง' in df_patients.columns:
        df_patients['4 กลุ่มโรคเฝ้าระวัง'] = df_patients['4 กลุ่มโรคเฝ้าระวัง'].replace(
            'ไม่จัดอยู่ใน 4 กลุ่มโรค', 'โรคร่วม Z58.1'
        )

    # --- การทำความสะอาดข้อมูล PM2.5 (df_pm25) ---
    
    # แปลง "ม.ค. 2021" เป็น Date
    thai_months = {'ม.ค.':'01', 'ก.พ.':'02', 'มี.ค.':'03', 'เม.ย.':'04', 'พ.ค.':'05', 'มิ.ย.':'06',
                   'ก.ค.':'07', 'ส.ค.':'08', 'ก.ย.':'09', 'ต.ค.':'10', 'พ.ย.':'11', 'ธ.ค.':'12'}
                   
    def parse_pm25_date(date_str):
        try:
            m_thai, y = str(date_str).split()
            m_num = thai_months.get(m_thai, '01')
            return pd.to_datetime(f"{y}-{m_num}-01").to_period('M')
        except:
            return pd.NaT

    df_pm25['Month_Year'] = df_pm25['Date'].apply(parse_pm25_date)
    
    # ลบช่องว่างในชื่อคอลัมน์และเปลี่ยนชื่อเพื่อความง่ายในการอ้างอิง
    if 'PM2.5 (ug/m3)' in df_pm25.columns:
        df_pm25.rename(columns={'PM2.5 (ug/m3)': 'PM25'}, inplace=True)

    return df_patients, df_pm25
