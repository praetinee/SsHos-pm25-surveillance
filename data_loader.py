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
        
        # --- FIX: Conditionally convert Buddhist Era (B.E.) to Gregorian (A.D.) ---
        # Only subtract 543 years if the year is clearly a B.E. year (e.g., > 2500)
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

    # --- 2. Load PM2.5 Data ---
    pm25_gid = "1038807599"
    pm25_url = format_gsheet_url(sheet_id, pm25_gid)
    
    try:
        pm25_monthly_df = pd.read_csv(pm25_url)
        
        pm25_monthly_df = pm25_monthly_df.melt(
            id_vars=['เดือน'], 
            var_name='year', 
            value_name='pm25_level'
        )
        
        month_map = {
            'มกราคม': 1, 'กุมภาพันธ์': 2, 'มีนาคม': 3, 'เมษายน': 4, 
            'พฤษภาคม': 5, 'มิถุนายน': 6, 'กรกฎาคม': 7, 'สิงหาคม': 8, 
            'กันยายน': 9, 'ตุลาคม': 10, 'พฤศจิกายน': 11, 'ธันวาคม': 12
        }
        pm25_monthly_df['month_num'] = pm25_monthly_df['เดือน'].map(month_map)
        pm25_monthly_df['date'] = pd.to_datetime(
            pm25_monthly_df['year'].astype(str) + '-' + pm25_monthly_df['month_num'].astype(str) + '-01',
            errors='coerce'
        )
        pm25_monthly_df.dropna(subset=['date', 'pm25_level'], inplace=True)
        pm25_monthly_df = pm25_monthly_df[['date', 'pm25_level']].sort_values('date')

        if patients_df.empty:
            return patients_df, pd.DataFrame()

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

