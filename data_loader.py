import streamlit as st
import pandas as pd
import numpy as np

# --- Data Loading and Caching ---

@st.cache_data(ttl=600) # Cache data for 10 minutes
def load_pm25_realtime():
    """
    Loads real-time PM2.5 data from the specified Google Sheet.
    Returns the latest timestamp and PM2.5 value.
    """
    try:
        sheet_url = "https://docs.google.com/spreadsheets/d/1-Une9oA0-ln6ApbhwaXFNpkniAvX7g1K9pNR800MJwQ/export?format=csv&gid=0"
        df = pd.read_csv(sheet_url)
        latest_data = df.iloc[-1]
        timestamp = pd.to_datetime(latest_data['Date-Time'], dayfirst=True)
        pm25_value = float(latest_data['PM2.5'])
        return timestamp, pm25_value
    except Exception as e:
        # st.error(f"Error loading real-time data: {e}")
        return None, None

@st.cache_data
def generate_mock_data():
    """
    Generates a more comprehensive mock DataFrame for patient and PM2.5 data over the last 3 years.
    """
    end_date = pd.to_datetime("now")
    start_date = end_date - pd.DateOffset(years=3)
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    num_days = len(dates)
    
    # Simulate daily patient visits (more visits on weekdays)
    base_visits = np.random.randint(50, 150, num_days)
    weekday_factor = [1.2 if d.weekday() < 5 else 0.7 for d in dates]
    total_visits = (base_visits * weekday_factor).astype(int)

    # Generate records for each visit
    records = []
    
    # Define categories
    disease_groups = ['กลุ่มโรคทางเดินหายใจ', 'กลุ่มโรคหัวใจและหลอดเลือด', 'กลุ่มโรคตาอักเสบ', 'กลุ่มโรคผิวหนังอักเสบ']
    patient_groups = ['เด็ก (0-15 ปี)', 'ผู้สูงอายุ (60+ ปี)', 'หญิงตั้งครรภ์', 'ประชาชนทั่วไป']
    districts = ['อ.เมืองเชียงใหม่', 'อ.สันทราย', 'อ.แม่ริม', 'อ.สารภี', 'อ.หางดง', 'อ.ดอยสะเก็ด']

    for i, date in enumerate(dates):
        # Simulate PM2.5 levels (higher in winter/spring)
        month = date.month
        seasonal_factor = np.sin((month - 1) * (np.pi / 6))**2 * 100 + 10
        random_noise = np.random.normal(0, 15)
        pm25 = max(5, seasonal_factor + random_noise)

        for _ in range(total_visits[i]):
            # Assign disease group (more respiratory cases when PM2.5 is high)
            pm_factor = min(pm25 / 100, 1.0) # Normalized PM2.5 effect
            disease_prob = [0.4 + 0.4 * pm_factor, 0.2, 0.15, 0.25 - 0.4 * pm_factor]
            disease_prob = np.array(disease_prob) / sum(disease_prob) # Normalize probabilities
            
            records.append({
                'visit_date': date,
                'pm25_value': pm25,
                'disease_group': np.random.choice(disease_groups, p=disease_prob),
                'patient_group': np.random.choice(patient_groups, p=[0.2, 0.2, 0.05, 0.55]),
                'district': np.random.choice(districts, p=[0.3, 0.25, 0.15, 0.1, 0.1, 0.1])
            })
            
    df = pd.DataFrame(records)
    df['visit_date'] = pd.to_datetime(df['visit_date'])
    return df

