import pandas as pd
import streamlit as st

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
            df["วันที่เข้ารับบริการ"] = pd.to_datetime(df["วันที่เข้ารับบริการ"], errors="coerce")
            df.dropna(subset=["วันที่เข้ารับบริการ"], inplace=True) 
            df["เดือน"] = df["วันที่เข้ารับบริการ"].dt.to_period("M").astype(str)
        
        return df
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูลผู้ป่วย: {e}")
        return pd.DataFrame()

def _convert_thai_month_to_period(thai_date_str):
    """Converts a string like 'ม.ค. 2023' to '2023-01'."""
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
        return f"{year_str}-{month_num}"
    
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
