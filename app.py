import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
# --- ไลบรารีที่อาจต้องใช้เพิ่มสำหรับการเชื่อมต่อข้อมูลจริง ---
# import sqlalchemy  # ตัวอย่างสำหรับ SQL
# import requests    # ตัวอย่างสำหรับ API

# --- Page Configuration ---
st.set_page_config(
    page_title="PM2.5 Patient Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for modern look ---
st.markdown("""
<style>
    /* General body style */
    body {
        font-family: 'Arial', sans-serif;
    }
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 5rem;
        padding-right: 5rem;
    }
    /* KPI Metric card styling */
    .kpi-card {
        background-color: #FFFFFF;
        border-radius: 15px;
        padding: 25px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        transition: transform 0.2s;
        text-align: center;
    }
    .kpi-card:hover {
        transform: scale(1.05);
    }
    .kpi-title {
        font-size: 1rem;
        font-weight: bold;
        color: #555;
    }
    .kpi-value {
        font-size: 2.5rem;
        font-weight: bolder;
        color: #1f77b4;
    }
    .kpi-delta {
        font-size: 0.9rem;
        color: #2ca02c; /* Green for positive */
    }
    .kpi-delta.negative {
        color: #d62728; /* Red for negative */
    }
    /* Expander styling */
    .st-expander {
        border: 1px solid #e6e6e6;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)


# --- Data Loading Section ---

# --- (ส่วนที่ 1) ฟังก์ชันข้อมูลจำลอง (ของเดิม) ---
# ฟังก์ชันนี้จะไม่ได้ถูกใช้งานเมื่อเชื่อมต่อข้อมูลจริง แต่เก็บไว้เพื่อทดสอบได้
@st.cache_data
def generate_mock_data():
    """Generates a DataFrame with mock patient data."""
    start_date = datetime(2024, 1, 1)
    end_date = datetime.now()
    date_range = pd.date_range(start_date, end_date)
    
    diseases = ["โรคหอบหืด (Asthma)", "โรคปอดอุดกั้นเรื้อรัง (COPD)", "โรคภูมิแพ้ (Allergic Rhinitis)", "โรคหัวใจและหลอดเลือด (Cardiovascular)", "โรคตาแดง (Conjunctivitis)"]
    age_groups = ["0-10 ปี", "11-20 ปี", "21-40 ปี", "41-60 ปี", "60+ ปี"]
    
    data = []
    for date in date_range:
        if date.month in [1, 2, 3, 4, 12]:
            daily_patients = np.random.randint(25, 60)
        else:
            daily_patients = np.random.randint(5, 20)
            
        for _ in range(daily_patients):
            data.append({
                "date": date,
                "disease": np.random.choice(diseases, p=[0.3, 0.2, 0.3, 0.15, 0.05]),
                "age_group": np.random.choice(age_groups, p=[0.15, 0.15, 0.3, 0.25, 0.15]),
            })
            
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date']).dt.date
    return df

# --- (ส่วนที่ 2) ฟังก์ชันใหม่สำหรับโหลดข้อมูลจริง ---
@st.cache_data(ttl=600) # Cache ข้อมูลไว้ 10 นาที (600 วินาที)
def load_from_gsheet():
    """
    ฟังก์ชันสำหรับโหลดข้อมูลจาก Google Sheet สาธารณะ
    """
    # URL ของ Google Sheet ที่แปลงให้เป็นลิงก์สำหรับดาวน์โหลดไฟล์ CSV โดยตรง
    SHEET_URL = "https://docs.google.com/spreadsheets/d/1vvQ8YLChHXvCowQQzcKIeV4PWt0CCt76f5Sj3fNTOV0/export?format=csv&gid=795124395"
    
    try:
        df_raw = pd.read_csv(SHEET_URL)
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูลจาก Google Sheet: {e}")
        return pd.DataFrame() # คืนค่า DataFrame ว่างเปล่าถ้ามีปัญหา

    # --- (ส่วนที่ 3) การแปลงข้อมูล (Data Transformation) ---
    # แก้ไขให้ใช้ชื่อคอลัมน์ที่ถูกต้องจาก Google Sheet
    
    df_processed = df_raw.copy()
    
    # 1. แปลงคอลัมน์วันที่ โดยใช้ชื่อคอลัมน์ 'ประทับเวลา'
    df_processed['date'] = pd.to_datetime(df_processed['ประทับเวลา']).dt.date
    
    # 2. ตั้งชื่อคอลัมน์โรค โดยใช้ชื่อคอลัมน์ 'กลุ่มอาการ'
    df_processed['disease'] = df_processed['กลุ่มอาการ']
    
    # 3. ตั้งชื่อคอลัมน์กลุ่มอายุ โดยใช้ชื่อคอลัมน์ 'ช่วงอายุ' (ข้อมูลมาเป็นกลุ่มอายุอยู่แล้ว ไม่ต้องคำนวณใหม่)
    df_processed['age_group'] = df_processed['ช่วงอายุ']

    # คืนค่า DataFrame ที่มีคอลัมน์ 'date', 'disease', 'age_group' ที่จำเป็นสำหรับ Dashboard
    return df_processed[['date', 'disease', 'age_group']]


# --- เรียกใช้ฟังก์ชันโหลดข้อมูล ---
df = load_from_gsheet() 

# --- Sidebar Filters ---
if not df.empty:
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3004/3004458.png", width=80)
        st.title("ตัวกรองข้อมูล (Filters)")
        
        min_date = df['date'].min()
        max_date = df['date'].max()
        start_date, end_date = st.date_input(
            "เลือกช่วงวันที่:",
            value=(max_date - timedelta(days=30), max_date),
            min_value=min_date,
            max_value=max_date,
            help="เลือกช่วงเวลาที่ต้องการแสดงข้อมูล"
        )

        all_diseases = sorted(df['disease'].unique())
        # แก้ไขจาก multelect เป็น multiselect
        selected_diseases = st.multiselect(
            "เลือกกลุ่มโรค:", options=all_diseases, default=all_diseases
        )

        all_age_groups = sorted(df['age_group'].unique())
        selected_age_groups = st.multiselect(
            "เลือกกลุ่มอายุ:", options=all_age_groups, default=all_age_groups
        )

    # --- Filtering Data based on selections ---
    df_filtered = df[
        (df['date'] >= start_date) &
        (df['date'] <= end_date) &
        (df['disease'].isin(selected_diseases)) &
        (df['age_group'].isin(selected_age_groups))
    ]
else:
    st.warning("ไม่สามารถโหลดข้อมูลได้ กรุณาตรวจสอบการตั้งค่า Google Sheet หรือลองอีกครั้งในภายหลัง")
    df_filtered = pd.DataFrame() # สร้าง DataFrame ว่างเปล่าเพื่อไม่ให้โค้ดส่วนที่เหลือ error

# --- Main Dashboard ---
st.title("🏥 Dashboard ติดตามผู้ป่วยจากผลกระทบ PM2.5")
st.markdown("แดชบอร์ดวิเคราะห์ข้อมูลเชิงลึกสำหรับบุคลากรทางการแพทย์ เพื่อติดตามสถานการณ์และแนวโน้มของผู้ป่วยที่เกี่ยวข้องกับมลพิษทางอากาศ")

if not df_filtered.empty:
    # --- Key Metrics (KPIs) with new styling ---
    st.markdown("### 📊 ภาพรวมข้อมูลสำคัญ")

    # Prepare data for metrics
    today = max_date
    yesterday = today - timedelta(days=1)
    patients_today = len(df[df['date'] == today])
    patients_yesterday = len(df[df['date'] == yesterday])
    delta_today = patients_today - patients_yesterday if patients_yesterday > 0 else 0
    delta_color_class = "negative" if delta_today < 0 else ""

    total_patients_selected_range = len(df_filtered)
    avg_patients_per_day = total_patients_selected_range / ((end_date - start_date).days + 1) if (end_date - start_date).days > 0 else 0

    # Display Metrics in custom cards
    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">ผู้ป่วยวันนี้ ({today.strftime('%d %b')})</div>
            <div class="kpi-value">{patients_today} คน</div>
            <div class="kpi-delta {delta_color_class}">{delta_today} vs วันก่อนหน้า</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">ผู้ป่วยทั้งหมด (ช่วงที่เลือก)</div>
            <div class="kpi-value">{total_patients_selected_range} คน</div>
            <div class="kpi-delta" style="color: #555;">{start_date.strftime('%d %b')} - {end_date.strftime('%d %b')}</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">ค่าเฉลี่ยผู้ป่วยต่อวัน</div>
            <div class="kpi-value">{avg_patients_per_day:.1f}</div>
             <div class="kpi-delta" style="color: #555;">คน/วัน</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Charts ---
    st.markdown("### 📈 การแสดงผลข้อมูล (Visualizations)")

    # Daily Patient Trend Chart
    daily_counts = df_filtered.groupby('date').size().reset_index(name='count')
    daily_counts['moving_avg_7_days'] = daily_counts['count'].rolling(window=7, min_periods=1).mean()

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Bar(x=daily_counts['date'], y=daily_counts['count'], name='จำนวนผู้ป่วยรายวัน', marker_color='#1f77b4', opacity=0.6))
    fig_trend.add_trace(go.Scatter(x=daily_counts['date'], y=daily_counts['moving_avg_7_days'], name='ค่าเฉลี่ยเคลื่อนที่ 7 วัน', mode='lines', line=dict(color='#ff7f0e', width=3)))
    fig_trend.update_layout(
        title='<b>แนวโน้มจำนวนผู้ป่วยรายวัน</b>',
        xaxis_title='วันที่',
        yaxis_title='จำนวนผู้ป่วย (คน)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Arial", size=12, color="#333")
    )
    st.plotly_chart(fig_trend, use_container_width=True)


    # Breakdown Charts
    col1, col2 = st.columns(2)
    with col1:
        disease_counts = df_filtered['disease'].value_counts().reset_index()
        fig_disease = px.bar(
            disease_counts, x='count', y='disease', orientation='h',
            title='<b>สัดส่วนผู้ป่วยตามกลุ่มโรค</b>',
            labels={'count': 'จำนวนผู้ป่วย', 'disease': 'กลุ่มโรค'},
            text='count',
            color='count',
            color_continuous_scale=px.colors.sequential.Blues
        )
        fig_disease.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'}, plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_disease, use_container_width=True)

    with col2:
        age_counts = df_filtered['age_group'].value_counts().reset_index()
        fig_age = px.pie(
            age_counts, names='age_group', values='count',
            title='<b>สัดส่วนผู้ป่วยตามกลุ่มอายุ</b>',
            hole=0.5,
            color_discrete_sequence=px.colors.sequential.Aggrnyl
        )
        fig_age.update_traces(textposition='inside', textinfo='percent+label', pull=[0.05]*len(age_counts))
        fig_age.update_layout(legend_title_text='กลุ่มอายุ')
        st.plotly_chart(fig_age, use_container_width=True)


    # --- Raw Data Table ---
    with st.expander("📄 แสดงข้อมูลดิบ (Raw Data)"):
        st.dataframe(df_filtered.sort_values('date', ascending=False), use_container_width=True)

# --- Footer ---
st.markdown("---")
st.markdown("<div style='text-align: center; color: #888;'>Developed for Hospital Staff | Data Source: Google Sheets</div>", unsafe_allow_html=True)

