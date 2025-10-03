import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

@st.cache_data(ttl=600) # Cache data for 10 minutes
def load_pm25_realtime():
    """Loads real-time PM2.5 data from a public Google Sheet."""
    try:
        sheet_id = "1-Une9oA0-ln6ApbhwaXFNpkniAvX7g1K9pNR800MJwQ"
        sheet_gid = "0"
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={sheet_gid}"
        df = pd.read_csv(url)
        # Assuming the structure is [Timestamp, PM2.5 Value]
        latest_data = df.iloc[-1]
        timestamp = pd.to_datetime(latest_data.iloc[0])
        pm25_value = latest_data.iloc[1]
        return timestamp, pm25_value
    except Exception as e:
        # We'll show a friendlier error in the UI, but log the detail here
        print(f"Error loading PM2.5 data: {e}")
        return None, None

@st.cache_data
def generate_mock_data():
    """Generates a DataFrame with mock patient and PM2.5 data for the last 3 years."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=3*365)
    dates = pd.to_datetime(pd.date_range(start=start_date, end=end_date, freq='D'))
    
    # Simulate seasonal PM2.5 peaks (higher in winter/spring)
    month_factors = [1.5, 2.0, 2.5, 1.8, 1.0, 0.8, 0.7, 0.8, 1.0, 1.2, 1.3, 1.4] # Jan-Dec
    seasonal_pm25 = [month_factors[d.month-1] for d in dates]
    base_pm25 = np.random.rand(len(dates)) * 30 + 15
    pm25_values = base_pm25 * seasonal_pm25 + np.random.randn(len(dates)) * 5
    pm25_values = np.clip(pm25_values, 5, 150)

    # Simulate patient counts, correlated with PM2.5
    group1 = np.random.randint(5, 20, len(dates)) + (pm25_values / 5).astype(int)
    group2 = np.random.randint(3, 15, len(dates)) + (pm25_values / 8).astype(int)
    group3 = np.random.randint(2, 10, len(dates)) + (pm25_values / 10).astype(int)
    group4 = np.random.randint(10, 30, len(dates))

    df = pd.DataFrame({
        'Date': dates,
        'PM2.5': pm25_values,
        'กลุ่มโรคระบบทางเดินหายใจ': group1,
        'กลุ่มโรคหัวใจและหลอดเลือด': group2,
        'กลุ่มโรคตาอักเสบ': group3,
        'กลุ่มโรคอื่นๆ': group4
    })
    return df
