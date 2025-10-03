import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

def format_gsheet_url(sheet_id, gid):
    """Formats the Google Sheet URL to be readable by pandas."""
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}"

@st.cache_data(ttl=600) # Cache data for 10 minutes
def load_data():
    """
    Loads patient and PM2.5 data from Google Sheets.
    """
    # --- 1. Load Patient Data ---
    sheet_id = "1vvQ8YLChHXvCowQQzcKIeV4PWt0CCt76f5Sj3fNTOV0"
    patient_gid = "795124395"
    patient_url = format_gsheet_url(sheet_id, patient_gid)
    
    patient_cols_map = {
        'วันที่มารับบริการ': 'admission_date',
        'HN': 'patient_id',
        'เพศ': 'gender',
        'อายุ': 'age',
        'อำเภอ': 'district',
        '4 กลุ่มโรคเฝ้าระวัง': 'diagnosis'
    }
    
    try:
        patients_df = pd.read_csv(patient_url, usecols=patient_cols_map.keys())
        patients_df.rename(columns=patient_cols_map, inplace=True)
        
        # --- Data Cleaning & Preparation for Patients ---
        patients_df['admission_date'] = pd.to_datetime(patients_df['admission_date'], errors='coerce', dayfirst=True)
        patients_df.dropna(subset=['admission_date'], inplace=True)
        
        current_year_ad = datetime.now().year
        patients_df['admission_date'] = patients_df['admission_date'].apply(
            lambda d: d - pd.DateOffset(years=543) if d.year > current_year_ad + 100 else d
        )
        
        statuses = ['กำลังรักษา', 'กลับบ้านแล้ว']
        patients_df['status'] = np.random.choice(statuses, size=len(patients_df), p=[0.4, 0.6])
        patients_df['district'] = patients_df['district'].astype(str)

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูลผู้ป่วย: {e}")
        return pd.DataFrame(), pd.DataFrame()

    # --- 2. Load PM2.5 Data (New Format) ---
    pm25_gid = "1038807599"
    pm25_url = format_gsheet_url(sheet_id, pm25_gid)
    
    try:
        # Read the new format of PM2.5 data
        pm25_monthly_df = pd.read_csv(pm25_url, usecols=['Date', 'PM2.5 (ug/m3)'])
        pm25_monthly_df.rename(columns={'Date': 'date_str', 'PM2.5 (ug/m3)': 'pm25_level'}, inplace=True)
        pm25_monthly_df.dropna(subset=['date_str', 'pm25_level'], inplace=True)

        # Map for Thai abbreviated months to month number
        thai_month_map = {
            'ม.ค.': 1, 'ก.พ.': 2, 'มี.ค.': 3, 'เม.ย.': 4,
            'พ.ค.': 5, 'มิ.ย.': 6, 'ก.ค.': 7, 'ส.ค.': 8,
            'ก.ย.': 9, 'ต.ค.': 10, 'พ.ย.': 11, 'ธ.ค.': 12
        }

        def convert_thai_date(date_str):
            try:
                parts = date_str.replace('.', '').split()
                if len(parts) != 2: return None
                
                month_abbr, year_str = parts
                month_num = thai_month_map.get(month_abbr)
                
                if month_num and year_str.isdigit():
                    year_int = int(year_str)
                    if year_int > 2500: year_int -= 543 # Convert BE to AD
                    return datetime(year_int, month_num, 1)
                return None
            except (ValueError, IndexError):
                return None

        pm25_monthly_df['date'] = pm25_monthly_df['date_str'].apply(convert_thai_date)
        pm25_monthly_df.dropna(subset=['date'], inplace=True)
        pm25_monthly_df = pm25_monthly_df[['date', 'pm25_level']].sort_values('date')

        if patients_df.empty:
            return patients_df, pd.DataFrame()

        # Convert monthly PM2.5 data to daily data for merging
        date_range = pd.date_range(start=patients_df['admission_date'].min(), end=patients_df['admission_date'].max(), freq='D')
        pm25_daily_df = pd.DataFrame({'date': date_range})
        
        pm25_daily_df = pd.merge_asof(
            pm25_daily_df, 
            pm25_monthly_df, 
            on='date'
        )
        
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล PM2.5: {e}")
        return pd.DataFrame(), pd.DataFrame()

    return patients_df, pm25_daily_df

generate_data = load_data

