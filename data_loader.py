import streamlit as st
import pandas as pd
from datetime import datetime

# --- กรุณาใส่ข้อมูล Google Sheet ที่คุณเตรียมไว้ ---
# 1. ใส่ Sheet ID (ส่วนที่อยู่ใน URL ระหว่าง /d/ และ /edit)
PREPARED_SHEET_ID = "1vvQ8YLChHXvCowQQzcKIeV4PWt0CCt76f5Sj3fNTOV0"

# 2. ใส่ GID ของชีต "กราฟจำนวนคนป่วย" (ดูจากพารามิเตอร์ gid= ใน URL)
PATIENT_COUNT_GID = "1182042858"

# 3. ใส่ GID ของชีต "กราฟค่าฝุ่น"
PM25_GID = "1038807599"
# -------------------------------------------------------------

def format_gsheet_url(sheet_id, gid):
    """Formats the Google Sheet URL to be readable by pandas."""
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}"

def convert_thai_month_year_date(date_str):
    """แปลง 'เดือน. ปี' (เช่น 'ม.ค. 2023') ให้เป็น datetime"""
    thai_month_map = {
        'ม.ค.': 1, 'ก.พ.': 2, 'มี.ค.': 3, 'เม.ย.': 4, 'พ.ค.': 5, 'มิ.ย.': 6,
        'ก.ค.': 7, 'ส.ค.': 8, 'ก.ย.': 9, 'ต.ค.': 10, 'พ.ย.': 11, 'ธ.ค.': 12
    }
    try:
        parts = str(date_str).replace('.', '').split()
        if len(parts) != 2: return None
        month_abbr, year_str = parts
        month_num = thai_month_map.get(month_abbr)
        if month_num and year_str.isdigit():
            year = int(year_str)
            if year > 2500: year -= 543 # แปลง พ.ศ. เป็น ค.ศ.
            return datetime(year, month_num, 1)
        return None
    except:
        return None

@st.cache_data(ttl=600)
def load_prepared_data():
    """
    โหลดข้อมูลที่เตรียมไว้จาก Google Sheets และรวมข้อมูลให้พร้อมใช้งาน
    """
    if PREPARED_SHEET_ID == "YOUR_SHEET_ID_HERE" or PATIENT_COUNT_GID == "YOUR_PATIENT_GID" or PM25_GID == "YOUR_PM25_GID":
        st.warning("กรุณาอัปเดต PREPARED_SHEET_ID และ GIDs ในไฟล์ data_loader.py")
        return pd.DataFrame()

    patient_url = format_gsheet_url(PREPARED_SHEET_ID, PATIENT_COUNT_GID)
    pm25_url = format_gsheet_url(PREPARED_SHEET_ID, PM25_GID)

    try:
        # 1. โหลดและเตรียมข้อมูลจำนวนผู้ป่วย
        patient_df = pd.read_csv(patient_url)
        patient_df.rename(columns={
            'เดือนของปี': 'date_str',
            '4 กลุ่มโรคเฝ้าระวัง': 'diagnosis',
            'VN': 'patient_count'
        }, inplace=True)
        patient_df['date'] = patient_df['date_str'].apply(convert_thai_month_year_date)
        patient_df.dropna(subset=['date'], inplace=True)
        
        patient_pivot_df = patient_df.pivot_table(
            index='date', columns='diagnosis', values='patient_count'
        ).fillna(0)
        
        # 2. โหลดและเตรียมข้อมูล PM2.5
        pm25_df = pd.read_csv(pm25_url)
        pm25_df.rename(columns={
            'Date': 'date_str',
            'PM2.5 (ug/m3)': 'pm25_level'
        }, inplace=True)
        pm25_df['date'] = pm25_df['date_str'].apply(convert_thai_month_year_date)
        pm25_df = pm25_df[['date', 'pm25_level']].dropna().set_index('date')
        
        # 3. รวมสองตารางเข้าด้วยกัน
        merged_df = patient_pivot_df.join(pm25_df, how='inner')
        return merged_df.reset_index()

    except Exception as e:
        st.error(f"ไม่สามารถโหลดข้อมูลจาก Google Sheet ที่ระบุได้: {e}")
        st.info("กรุณาตรวจสอบว่าได้ใส่ Sheet ID และ GID ถูกต้อง และตั้งค่าการแชร์เป็น 'ทุกคนที่มีลิงก์'")
        return pd.DataFrame()

def generate_data():
    return load_prepared_data()

