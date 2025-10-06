import pandas as pd
import streamlit as st

@st.cache_data(show_spinner="กำลังโหลดข้อมูลผู้ป่วย...")
def load_patient_data(url):
    """Loads patient data from a Google Sheets URL."""
    try:
        df = pd.read_csv(url)

        # FIX: Rename the first column to 'วันที่เข้ารับบริการ' based on user confirmation
        # This makes the app robust to the actual header name in the Google Sheet.
        if not df.empty:
            original_first_column_name = df.columns[0]
            df.rename(columns={original_first_column_name: "วันที่เข้ารับบริการ"}, inplace=True)

        df.columns = df.columns.str.strip()
        
        if "วันที่เข้ารับบริการ" in df.columns:
            # Convert to datetime, coercing errors will turn failures into NaT (Not a Time)
            df["วันที่เข้ารับบริการ"] = pd.to_datetime(df["วันที่เข้ารับบริการ"], errors="coerce")
            
            # Drop rows where date conversion failed to avoid errors downstream
            df.dropna(subset=["วันที่เข้ารับบริการ"], inplace=True) 
            
            # Create 'เดือน' column after cleaning
            df["เดือน"] = df["วันที่เข้ารับบริการ"].dt.to_period("M").astype(str)
        
        return df
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูลผู้ป่วย: {e}")
        return pd.DataFrame()

@st.cache_data(show_spinner="กำลังโหลดข้อมูล PM2.5...")
def load_pm25_data(url):
    """Loads PM2.5 data from a Google Sheets URL."""
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล PM2.5: {e}")
        return pd.DataFrame()

