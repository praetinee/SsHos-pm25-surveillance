import streamlit as st
import pandas as pd
from datetime import datetime

# --- Configuration for Google Sheets ---
# This is the main Sheet ID for your data
SHEET_ID = "1vvQ8YLChHXvCowQQzcKIeV4PWt0CCt76f5Sj3fNTOV0"

# GID for the raw patient data sheet ("4 โรคเฝ้าระวัง")
PATIENT_DATA_GID = "795124395"

# GID for the monthly PM2.5 data sheet ("PM2.5 รายเดือน")
PM25_DATA_GID = "1038807599"
# -------------------------------------------------------------

def format_gsheet_url(sheet_id, gid):
    """Formats the Google Sheet URL to be readable by pandas."""
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}"

@st.cache_data(ttl=600) # Cache for 10 minutes
def load_and_process_data():
    """
    Loads raw patient and PM2.5 data, processes it, and returns a merged DataFrame.
    """
    patient_url = format_gsheet_url(SHEET_ID, PATIENT_DATA_GID)
    pm25_url = format_gsheet_url(SHEET_ID, PM25_DATA_GID)

    try:
        # --- 1. Load and Process Patient Data ---
        patient_df = pd.read_csv(
            patient_url,
            usecols=['วันที่มารับบริการ', '4 กลุ่มโรคเฝ้าระวัง'],
            dtype={'วันที่มารับบริการ': str}  # Force date column to be read as string
        )
        patient_df.rename(columns={
            'วันที่มารับบริการ': 'date',
            '4 กลุ่มโรคเฝ้าระวัง': 'diagnosis'
        }, inplace=True)

        # More robust date conversion: Convert to datetime, coercing errors to NaT (Not a Time)
        patient_df['date'] = pd.to_datetime(patient_df['date'], errors='coerce')

        # Drop rows where date conversion failed or diagnosis is missing
        patient_df.dropna(subset=['date', 'diagnosis'], inplace=True)

        # Correctly handle Buddhist Era (BE) to Anno Domini (AD) conversion
        current_year_ad = datetime.now().year
        patient_df['date'] = patient_df['date'].apply(
            lambda d: d - pd.DateOffset(years=543) if d.year > current_year_ad + 50 else d
        )
        
        # Aggregate patient counts by month and diagnosis
        patient_counts = patient_df.groupby([
            pd.Grouper(key='date', freq='MS'), # MS = Month Start
            'diagnosis'
        ]).size().reset_index(name='patient_count')

        # Pivot the table to get diseases as columns
        patient_pivot = patient_counts.pivot_table(
            index='date',
            columns='diagnosis',
            values='patient_count'
        ).fillna(0)

        # --- 2. Load and Process PM2.5 Data ---
        pm25_df = pd.read_csv(pm25_url, usecols=['Date', 'PM2.5 (ug/m3)'])
        pm25_df.rename(columns={
            'Date': 'date',
            'PM2.5 (ug/m3)': 'pm25_level'
        }, inplace=True)
        
        # Robustly convert and clean PM2.5 date column
        pm25_df['date'] = pd.to_datetime(pm25_df['date'], errors='coerce')
        pm25_df.dropna(subset=['date'], inplace=True)
        
        # Also apply BE to AD conversion for consistency
        pm25_df['date'] = pm25_df['date'].apply(
            lambda d: d - pd.DateOffset(years=543) if d.year > current_year_ad + 50 else d
        )

        pm25_df['date'] = pm25_df['date'].dt.to_period('M').dt.start_time
        pm25_df.set_index('date', inplace=True)

        # --- 3. Merge DataFrames ---
        # Join patient data with PM2.5 data on the date (month start)
        merged_df = patient_pivot.join(pm25_df, how='inner')
        
        # Check if merged_df is empty after the join
        if merged_df.empty:
            st.warning("ไม่พบข้อมูลที่ตรงกันระหว่างข้อมูลผู้ป่วยและข้อมูล PM2.5 ในช่วงเวลาเดียวกัน")
            return pd.DataFrame()
            
        return merged_df.reset_index()

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดหรือประมวลผลข้อมูล: {e}")
        st.info("กรุณาตรวจสอบว่า Sheet ID และ GID ถูกต้อง และตั้งค่าการแชร์ Google Sheet เป็น 'ทุกคนที่มีลิงก์' (Anyone with the link)")
        return pd.DataFrame()

def generate_data():
    """Wrapper function to be called by app.py"""
    return load_and_process_data()

