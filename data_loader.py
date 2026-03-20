import pandas as pd
import streamlit as st
import re

def _convert_be_to_ad_in_string(date_str):
    """
    ฟังก์ชันช่วยแปลงปี พ.ศ. (ที่อยู่ในรูปแบบข้อความ) ให้เป็นปี ค.ศ.
    ก่อนนำไปเข้า pd.to_datetime เพื่อป้องกันปัญหา Error จากปีอธิกสุรทิน (29 ก.พ.)
    """
    if pd.isna(date_str):
        return date_str
    
    date_str = str(date_str).strip()

    def _sub_year(match):
        y = int(match.group(0))
        # หากปีมีค่ามากกว่า 2400 ให้ถือว่าเป็น พ.ศ. และลบ 543 เพื่อทำเป็น ค.ศ.
        if y > 2400:
            return str(y - 543)
        return str(y)

    # ค้นหาตัวเลข 4 หลัก (ปี) ในข้อความแล้วแทนที่ด้วย ค.ศ.
    return re.sub(r'\b\d{4}\b', _sub_year, date_str)


@st.cache_data(show_spinner="กำลังโหลดข้อมูลผู้ป่วย...")
def load_patient_data(url):
    """Loads patient data from a Google Sheets URL."""
    try:
        df = pd.read_csv(url)

        if not df.empty:
            original_first_column_name = df.columns[0]
            df.rename(columns={original_first_column_name: "วันที่เข้ารับบริการ"}, inplace=True)

        df.columns = df.columns.str.strip()
        
        if "วันที่เข้ารับบริการ" in df.columns:
            # FIX: ดักแปลงตัวเลข พ.ศ. ใน string ให้เป็น ค.ศ. ก่อนแปลงเป็น Datetime
            df["วันที่เข้ารับบริการ"] = df["วันที่เข้ารับบริการ"].apply(_convert_be_to_ad_in_string)
            
            # FIX: เพิ่ม dayfirst=True เพื่อบอกว่าข้อมูลไทยเป็น วัน/เดือน/ปี
            # และ coerce errors เพื่อเปลี่ยนค่าที่อ่านไม่ออกเป็น NaT แทนที่จะ Error
            df["วันที่เข้ารับบริการ"] = pd.to_datetime(df["วันที่เข้ารับบริการ"], dayfirst=True, errors="coerce")
            
            df.dropna(subset=["วันที่เข้ารับบริการ"], inplace=True) 
            df["เดือน"] = df["วันที่เข้ารับบริการ"].dt.to_period("M").astype(str)
        
        return df
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูลผู้ป่วย: {e}")
        return pd.DataFrame()

def _convert_thai_month_to_period(thai_date_str):
    """Converts a string like 'ม.ค. 2566' or 'ม.ค. 2023' to '2023-01'."""
    if not isinstance(thai_date_str, str):
        return None
        
    parts = thai_date_str.split()
    if len(parts) != 2:
        return None
        
    month_th, year_str = parts
    
    thai_month_map = {
        'ม.ค.': '01', 'ก.พ.': '02', 'มี.ค.': '03', 'เม.ย.': '04',
        'พ.ค.': '05', 'มิ.ย.': '06', 'ก.ค.': '07', 'ส.ค.': '08',
        'ก.ย.': '09', 'ต.ค.': '10', 'พ.ย.': '11', 'ธ.ค.': '12'
    }
    
    month_num = thai_month_map.get(month_th.strip())
    
    if month_num and year_str.isdigit():
        year_int = int(year_str)
        # FIX: ดักจับ หากปีที่กรอกมาเป็น พ.ศ. ให้แปลงเป็น ค.ศ.
        if year_int > 2400:
            year_int -= 543
            
        return f"{year_int}-{month_num}"
    
    return None

@st.cache_data(show_spinner="กำลังโหลดข้อมูล PM2.5...")
def load_pm25_data(url):
    """Loads and processes PM2.5 data from a Google Sheets URL."""
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()

        # FIX: Rename 'Date' column to 'เดือน' and convert its format
        if 'Date' in df.columns:
            df.rename(columns={'Date': 'เดือน'}, inplace=True)
            df['เดือน'] = df['เดือน'].apply(_convert_thai_month_to_period)
            # Drop rows where conversion might have failed
            df.dropna(subset=['เดือน'], inplace=True)
        
        return df
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล PM2.5: {e}")
        return pd.DataFrame()

@st.cache_data(show_spinner="กำลังโหลดข้อมูลพิกัด...")
def load_lat_lon_data(url):
    """Loads latitude and longitude data from a Google Sheets URL."""
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        # Ensure lat/lon are numeric
        if 'lat' in df.columns and 'lon' in df.columns:
            df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
            df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
            df.dropna(subset=['lat', 'lon'], inplace=True)
        return df
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูลพิกัด: {e}")
        return pd.DataFrame(columns=['ตำบล', 'lat', 'lon'])
