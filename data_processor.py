import pandas as pd
import streamlit as st

@st.cache_data # แคชข้อมูลไว้จะได้ไม่ต้องโหลดใหม่ทุกครั้งที่ผู้ใช้กด Filter
def load_and_prep_data():
    """
    ฟังก์ชันสำหรับโหลดข้อมูลจากไฟล์ CSV และทำความสะอาดข้อมูลให้อยู่ในรูปแบบที่พร้อมใช้งาน
    """
    try:
        # โหลดข้อมูล (ในการใช้งานจริง ให้ตั้งชื่อไฟล์ใน GitHub ให้ตรงกับตรงนี้)
        df_patients = pd.read_csv("โรคเฝ้าระวังจาก pm2.5 - 4 โรคเฝ้าระวัง.csv")
        df_pm25 = pd.read_csv("โรคเฝ้าระวังจาก pm2.5 - PM2.5 รายเดือน.csv")
    except FileNotFoundError:
        st.error("ไม่พบไฟล์ข้อมูล กรุณาตรวจสอบชื่อไฟล์และตำแหน่งที่ตั้ง")
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

    # ข. จัดการคอลัมน์ "ผู้ป่วยนัด"
    # สมมติว่า '-' คือ Walk-in, ถ้ามีคำว่า 'นัด' คือมาตามนัด
    df_patients['ผู้ป่วยนัด'] = df_patients['ผู้ป่วยนัด'].fillna('-')
    df_patients['Is_Walk_in'] = df_patients['ผู้ป่วยนัด'].apply(
        lambda x: 'Walk-in (ไม่ได้นัด)' if str(x).strip() == '-' else 'Appointment (นัดมา)'
    )

    # ค. จัดการคอลัมน์สถานะ OPD (สกัดคำว่า ผู้ป่วยใหม่/เก่า และ การจำหน่าย)
    df_patients['OPD_Status'] = df_patients['COPD+Asthma at OPD'].fillna('ไม่ระบุ')
    
    def extract_patient_type(status):
        if 'ผู้ป่วยใหม่' in str(status): return 'ผู้ป่วยใหม่'
        if 'ผู้ป่วยเก่า' in str(status): return 'ผู้ป่วยเก่า'
        return 'ไม่ระบุ'
        
    def extract_severity(status):
        if 'รับไว้รักษา' in str(status) or 'ส่งต่อ' in str(status) or 'Admit' in str(status): 
            return 'รุนแรง (Admit/Refer)'
        if 'กลับบ้าน' in str(status): 
            return 'กลับบ้านได้'
        return 'ไม่ระบุ'

    df_patients['Patient_Type'] = df_patients['OPD_Status'].apply(extract_patient_type)
    df_patients['Severity'] = df_patients['OPD_Status'].apply(extract_severity)

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
