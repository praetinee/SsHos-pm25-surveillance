import pandas as pd
import streamlit as st

@st.cache_data(ttl=3600) # เพิ่ม ttl=3600 เพื่อให้ดึงข้อมูลใหม่ทุกๆ 1 ชั่วโมง
def load_and_prep_data():
    """
    ฟังก์ชันสำหรับโหลดข้อมูลจาก Google Sheets และทำความสะอาดข้อมูลให้อยู่ในรูปแบบที่พร้อมใช้งาน
    """
    # อัปเดต URL ของ Google Sheets ตามฐานข้อมูลใหม่ (gid=1349362308)
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
    
    # ก. แปลงวันที่ (ปี พ.ศ. เป็น ค.ศ.) และสร้างคอลัมน์ Month_Year
    def convert_thai_date(date_str):
        try:
            d, m, y = str(date_str).split('/')
            return pd.to_datetime(f"{int(y)-543}-{m}-{d}")
        except:
            return pd.NaT
            
    df_patients['Date'] = df_patients['วันที่มารับบริการ'].apply(convert_thai_date)
    df_patients['Month_Year'] = df_patients['Date'].dt.to_period('M')

    # ข. สร้างคอลัมน์ "กลุ่มเปราะบาง" จากอายุและโรคร่วม
    def extract_vulnerable_group(row):
        comorbidity = str(row.get('โรคร่วม', ''))
        age = row.get('อายุ', None)
        if 'ครรภ์' in comorbidity:
            return "หญิงตั้งครรภ์"
        try:
            age_val = float(age)
            if age_val >= 60: return "ผู้สูงอายุ"
            elif age_val >= 18: return "วัยผู้ใหญ่"
            elif age_val >= 7: return "วัยเรียนและวัยรุ่น"
            elif age_val >= 0: return "เด็ก"
            else: return "ข้อมูลอายุไม่ถูกต้อง"
        except (ValueError, TypeError):
            return "ข้อมูลอายุไม่ถูกต้อง"

    df_patients['กลุ่มเปราะบาง'] = df_patients.apply(extract_vulnerable_group, axis=1)

    # ค. [NEW] สร้างคอลัมน์ "Is_Acute" สำหรับวิเคราะห์อาการเฉียบพลัน
    def check_acute(comorbidity):
        keywords = ['เฉียบพลัน', 'acute', 'กำเริบ', 'exacerbation', 'หอบเหนื่อย']
        text = str(comorbidity).lower()
        return any(k in text for k in keywords)

    df_patients['Is_Acute'] = df_patients['โรคร่วม'].apply(check_acute)
    df_patients['Acute_Label'] = df_patients['Is_Acute'].map({True: 'อาการเฉียบพลัน', False: 'อาการทั่วไป'})

    # ง. จัดการคอลัมน์สถานะ OPD และกลุ่มโรค
    df_patients['OPD_Status'] = df_patients.get('COPD+Asthma at OPD', pd.Series(['ไม่ระบุ']*len(df_patients))).fillna('ไม่ระบุ')
    if '4 กลุ่มโรคเฝ้าระวัง' in df_patients.columns:
        df_patients['4 กลุ่มโรคเฝ้าระวัง'] = df_patients['4 กลุ่มโรคเฝ้าระวัง'].replace('ไม่จัดอยู่ใน 4 กลุ่มโรค', 'โรคร่วม Z58.1')

    # --- การทำความสะอาดข้อมูล PM2.5 ---
    thai_months = {'ม.ค.':'01', 'ก.พ.':'02', 'มี.ค.':'03', 'เม.ย.':'04', 'พ.ค.':'05', 'มิ.ย.':'06',
                   'ก.ค.':'07', 'ส.ค.':'08', 'ก.ย.':'09', 'ต.ค.':'10', 'พ.ย.':'11', 'ธ.ค.':'12'}
    def parse_pm25_date(date_str):
        try:
            m_thai, y = str(date_str).split()
            return pd.to_datetime(f"{y}-{thai_months.get(m_thai, '01')}-01").to_period('M')
        except: return pd.NaT

    df_pm25['Month_Year'] = df_pm25['Date'].apply(parse_pm25_date)
    if 'PM2.5 (ug/m3)' in df_pm25.columns:
        df_pm25.rename(columns={'PM2.5 (ug/m3)': 'PM25'}, inplace=True)

    return df_patients, df_pm25
