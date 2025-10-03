import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

@st.cache_data
def generate_data():
    """สร้างข้อมูลผู้ป่วยและข้อมูล PM2.5 จำลอง"""
    start_date = datetime.now() - timedelta(days=90)
    date_range = pd.to_datetime([start_date + timedelta(days=x) for x in range(90)])

    # สร้างข้อมูล PM2.5
    base_pm25 = np.random.randint(15, 40, size=90)
    seasonal_effect = (np.sin(np.arange(90) * (2 * np.pi / 90)) + 1) * 25
    pm25_levels = base_pm25 + seasonal_effect
    pm25_df = pd.DataFrame({'date': date_range.date, 'pm25_level': pm25_levels.astype(int)})

    # สร้างข้อมูลผู้ป่วย
    num_patients = int(pm25_levels.sum() / 10) # จำนวนผู้ป่วยสัมพันธ์กับค่าฝุ่น
    admission_dates_raw = np.random.choice(date_range, size=num_patients, p=pm25_levels/pm25_levels.sum())
    
    # --- FIX: แปลง numpy.datetime64 เป็น pandas Timestamps ก่อน ---
    admission_dates = pd.to_datetime(admission_dates_raw)


    diseases = ['โรคหอบหืด (Asthma)', 'โรคปอดอุดกั้นเรื้อรัง (COPD)', 'โรคภูมิแพ้ (Allergic Rhinitis)', 'โรคหัวใจขาดเลือด (Ischemic Heart)', 'โรคหลอดเลือดสมอง (Stroke)']
    districts = ['อำเภอเมือง', 'อำเภอแม่ริม', 'อำเภอสันทราย', 'อำเภอหางดง', 'อำเภอสารภี']
    statuses = ['กำลังรักษา', 'กลับบ้านแล้ว']

    patient_data = {
        'patient_id': [f'HN{1000+i}' for i in range(num_patients)],
        'admission_date': [d.date() for d in admission_dates], # ตอนนี้สามารถใช้ .date() ได้แล้ว
        'age': np.random.randint(5, 85, size=num_patients),
        'gender': np.random.choice(['ชาย', 'หญิง'], size=num_patients, p=[0.48, 0.52]),
        'district': np.random.choice(districts, size=num_patients),
        'diagnosis': np.random.choice(diseases, size=num_patients, p=[0.3, 0.25, 0.2, 0.15, 0.1]),
        'status': np.random.choice(statuses, size=num_patients, p=[0.4, 0.6])
    }
    patients_df = pd.DataFrame(patient_data)
    patients_df['admission_date'] = pd.to_datetime(patients_df['admission_date'])
    pm25_df['date'] = pd.to_datetime(pm25_df['date'])

    return patients_df, pm25_df

