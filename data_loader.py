import pandas as pd
import hashlib

def hash_data(val):
    """เข้ารหัสข้อมูลส่วนบุคคลเป็น Hash แบบทิศทางเดียว"""
    if pd.isna(val):
        return val
    return hashlib.sha256(str(val).encode()).hexdigest()[:10]

def convert_thai_date(date_str):
    """แปลงวันที่แบบ พ.ศ. (เช่น 1/1/2564) เป็น datetime"""
    try:
        if pd.isna(date_str):
            return pd.NaT
        parts = str(date_str).split('/')
        if len(parts) == 3:
            day, month, year_th = int(parts[0]), int(parts[1]), int(parts[2])
            year_en = year_th - 543 if year_th > 2500 else year_th
            return pd.Timestamp(year=year_en, month=month, day=day)
    except:
        return pd.NaT
    return pd.NaT

def load_and_clean_data(file_path):
    """โหลด ลบข้อมูล PII และเตรียมข้อมูลให้พร้อมใช้"""
    # 1. โหลดข้อมูล
    df = pd.read_csv(file_path, dtype=str)
    
    # 2. ทำ Data Masking / Anonymization ทันที (PDPA)
    drop_cols = ['คำนำหน้า', 'ชื่อผู้ป่วย', 'บ้านเลขที่', 'หมู่', 'เลขบัตรประชาชน', 'เบอร์โทรศัพท์']
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors='ignore')
    
    if 'HN' in df.columns:
        df['HN'] = df['HN'].apply(hash_data)
    if 'VN' in df.columns:
        df['VN'] = df['VN'].apply(hash_data)
        
    # 3. จัดการประเภทข้อมูล
    if 'วันที่มารับบริการ' in df.columns:
        df['วันที่มารับบริการ'] = df['วันที่มารับบริการ'].apply(convert_thai_date)
        df['Month_Year'] = df['วันที่มารับบริการ'].dt.to_period('M')
        
    # แปลงอายุเป็นตัวเลข
    if 'อายุ' in df.columns:
        df['อายุ'] = pd.to_numeric(df['อายุ'], errors='coerce').fillna(0)
        
    # จัดการค่าว่าง
    if 'ผู้ป่วยนัด' in df.columns:
        df['ผู้ป่วยนัด'] = df['ผู้ป่วยนัด'].fillna('-')
        
    return df

def load_pm25_data(file_path):
    """โหลดและแปลงข้อมูล PM2.5 รายเดือน"""
    df_pm = pd.read_csv(file_path)
    
    # แปลง "ม.ค. 2021" เป็น Period('M')
    thai_months = {
        'ม.ค.': '01', 'ก.พ.': '02', 'มี.ค.': '03', 'เม.ย.': '04',
        'พ.ค.': '05', 'มิ.ย.': '06', 'ก.ค.': '07', 'ส.ค.': '08',
        'ก.ย.': '09', 'ต.ค.': '10', 'พ.ย.': '11', 'ธ.ค.': '12'
    }
    
    def parse_pm_date(d_str):
        try:
            m_th, y_en = d_str.split(' ')
            m_num = thai_months.get(m_th, '01')
            return pd.Period(f'{y_en}-{m_num}', freq='M')
        except:
            return pd.NaT
            
    if 'Date' in df_pm.columns:
        df_pm['Month_Year'] = df_pm['Date'].apply(parse_pm_date)
        df_pm['PM2.5'] = pd.to_numeric(df_pm.iloc[:, 2], errors='coerce')
        
    return df_pm[['Month_Year', 'PM2.5']].dropna()
