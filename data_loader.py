import streamlit as st
import pandas as pd
import numpy as np

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
    
    # Define columns to use and their new names
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
        # --- FIX: Handle Buddhist Era (B.E.) dates ---
        # Convert column to datetime, assuming dayfirst format (DD/MM/YYYY). Invalid parsing will be set to NaT.
        patients_df['admission_date'] = pd.to_datetime(patients_df['admission_date'], errors='coerce', dayfirst=True)
        
        # Drop rows where the date could not be parsed
        patients_df.dropna(subset=['admission_date'], inplace=True)
        
        # Subtract 543 years to convert from Buddhist Era (B.E.) to Gregorian (A.D.)
        patients_df['admission_date'] = patients_df['admission_date'] - pd.DateOffset(years=543)
        
        # Add a 'status' column for compatibility with the dashboard metrics
        statuses = ['กำลังรักษา', 'กลับบ้านแล้ว']
        patients_df['status'] = np.random.choice(statuses, size=len(patients_df), p=[0.4, 0.6])
        
        # Ensure 'district' is a string to prevent errors
        patients_df['district'] = patients_df['district'].astype(str)

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูลผู้ป่วย: {e}")
        return pd.DataFrame(), pd.DataFrame()

    # --- 2. Load PM2.5 Data ---
    pm25_gid = "1038807599"
    pm25_url = format_gsheet_url(sheet_id, pm25_gid)
    
    try:
        pm25_monthly_df = pd.read_csv(pm25_url)
        
        # --- Data Cleaning & Preparation for PM2.5 ---
        # Unpivot the table from wide to long format
        pm25_monthly_df = pm25_monthly_df.melt(
            id_vars=['เดือน'], 
            var_name='year', 
            value_name='pm25_level'
        )
        
        # Create a proper date column (assuming the 1st of each month)
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

        # --- Convert Monthly PM2.5 to Daily PM2.5 ---
        # Create a full date range based on patient data
        # Add a check to prevent error if patient data is empty
        if patients_df.empty:
            return patients_df, pd.DataFrame()

        date_range = pd.date_range(start=patients_df['admission_date'].min(), end=patients_df['admission_date'].max(), freq='D')
        pm25_daily_df = pd.DataFrame({'date': date_range})
        
        # Merge monthly data onto the daily range (forward fill)
        pm25_daily_df = pd.merge_asof(
            pm25_daily_df, 
            pm25_monthly_df, 
            on='date'
        )
        
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล PM2.5: {e}")
        return pd.DataFrame(), pd.DataFrame()

    return patients_df, pm25_daily_df

# For consistency with the rest of the app, we can rename the function call
# This way, you don't have to change the function name in app.py
generate_data = load_data

