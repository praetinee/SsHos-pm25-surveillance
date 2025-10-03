import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

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
@st.cache_data(ttl=600) # Cache ข้อมูลไว้ 10 นาที
def load_from_gsheet():
    """
    ฟังก์ชันสำหรับโหลดและแปลงข้อมูลจาก Google Sheet
    """
    SHEET_URL = "https://docs.google.com/spreadsheets/d/1vvQ8YLChHXvCowQQzcKIeV4PWt0CCt76f5Sj3fNTOV0/export?format=csv&gid=795124395"
    
    try:
        df_raw = pd.read_csv(SHEET_URL)
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูลจาก Google Sheet: {e}")
        return pd.DataFrame()

    # --- การแปลงข้อมูล (Data Transformation) ---
    df_processed = df_raw.copy()
    
    # 1. แปลงคอลัมน์วันที่: ใช้ errors='coerce' เพื่อเปลี่ยนค่าที่ผิดพลาดเป็น NaT (Not a Time)
    df_processed['date'] = pd.to_datetime(df_processed['วันที่มารับบริการ'], errors='coerce').dt.date
    
    # 2. แปลงคอลัมน์อายุ: ใช้ errors='coerce' เพื่อเปลี่ยนค่าที่ไม่ใช่ตัวเลขเป็น NaN
    df_processed['age_numeric'] = pd.to_numeric(df_processed['อายุ'], errors='coerce')

    # 3. สร้างคอลัมน์กลุ่มอายุจากคอลัมน์ 'age_numeric'
    bins = [0, 10, 20, 40, 60, 120]
    labels = ["0-10 ปี", "11-20 ปี", "21-40 ปี", "41-60 ปี", "60+ ปี"]
    df_processed['age_group'] = pd.cut(df_processed['age_numeric'], bins=bins, labels=labels, right=True)

    # 4. ตั้งชื่อคอลัมน์โรคให้ง่ายขึ้น
    df_processed['disease'] = df_processed['4 กลุ่มโรคเฝ้าระวัง']

    # 5. (สำคัญมาก) ลบแถวที่ข้อมูลหลักไม่สมบูรณ์ออกทั้งหมด
    df_processed.dropna(subset=['date', 'disease', 'age_group'], inplace=True)

    # 6. เลือกเฉพาะคอลัมน์ที่ต้องใช้
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
        selected_diseases = st.multiselect(
            "เลือกกลุ่มโรค:", options=all_diseases, default=all_diseases
        )

        all_age_groups = sorted(df['age_group'].dropna().astype(str).unique())
        selected_age_groups = st.multiselect(
            "เลือกกลุ่มอายุ:", options=all_age_groups, default=all_age_groups
        )

    # --- Filtering Data based on selections ---
    df_filtered = df[
        (df['date'] >= start_date) &
        (df['date'] <= end_date) &
        (df['disease'].isin(selected_diseases)) &
        (df['age_group'].astype(str).isin(selected_age_groups))
    ]
else:
    st.warning("ไม่สามารถโหลดข้อมูลได้ หรือข้อมูลที่โหลดมาไม่สมบูรณ์พอที่จะแสดงผล กรุณาตรวจสอบ Google Sheet")
    df_filtered = pd.DataFrame()

# --- Main Dashboard ---
st.title("🏥 Dashboard ติดตามผู้ป่วยจากผลกระทบ PM2.5")
st.markdown("แดชบอร์ดวิเคราะห์ข้อมูลเชิงลึกสำหรับบุคลากรทางการแพทย์ เพื่อติดตามสถานการณ์และแนวโน้มของผู้ป่วยที่เกี่ยวข้องกับมลพิษทางอากาศ")

if not df_filtered.empty:
    # --- Key Metrics (KPIs) ---
    st.markdown("### 📊 ภาพรวมข้อมูลสำคัญ")

    today = df['date'].max()
    yesterday = today - timedelta(days=1)
    patients_today = len(df[df['date'] == today])
    patients_yesterday = len(df[df['date'] == yesterday])
    delta_today = patients_today - patients_yesterday if patients_yesterday > 0 else patients_today
    delta_color_class = "negative" if delta_today < 0 else ""
    total_patients_selected_range = len(df_filtered)
    avg_patients_per_day = total_patients_selected_range / ((end_date - start_date).days + 1) if (end_date - start_date).days >= 0 else 0

    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">ผู้ป่วยล่าสุด ({today.strftime('%d %b')})</div>
            <div class="kpi-value">{patients_today} คน</div>
            <div class="kpi-delta {delta_color_class}">{delta_today:+} vs วันก่อนหน้า</div>
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
    daily_counts = df_filtered.groupby('date').size().reset_index(name='count')
    daily_counts['moving_avg_7_days'] = daily_counts['count'].rolling(window=7, min_periods=1).mean()

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Bar(x=daily_counts['date'], y=daily_counts['count'], name='จำนวนผู้ป่วยรายวัน', marker_color='#1f77b4', opacity=0.6))
    fig_trend.add_trace(go.Scatter(x=daily_counts['date'], y=daily_counts['moving_avg_7_days'], name='ค่าเฉลี่ยเคลื่อนที่ 7 วัน', mode='lines', line=dict(color='#ff7f0e', width=3)))
    fig_trend.update_layout(
        title='<b>แนวโน้มจำนวนผู้ป่วยรายวัน</b>',
        xaxis_title='วันที่',
        yaxis_title='จำนวนผู้ป่วย (คน)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        disease_counts = df_filtered['disease'].value_counts().reset_index()
        fig_disease = px.bar(
            disease_counts, x='count', y='disease', orientation='h',
            title='<b>สัดส่วนผู้ป่วยตามกลุ่มโรค</b>',
            labels={'count': 'จำนวนผู้ป่วย', 'disease': 'กลุ่มโรค'},
            text='count'
        )
        fig_disease.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_disease, use_container_width=True)

    with col2:
        age_counts = df_filtered['age_group'].value_counts().reset_index()
        fig_age = px.pie(
            age_counts, names='age_group', values='count',
            title='<b>สัดส่วนผู้ป่วยตามกลุ่มอายุ</b>',
            hole=0.5
        )
        fig_age.update_traces(textposition='inside', textinfo='percent+label', pull=[0.05]*len(age_counts))
        st.plotly_chart(fig_age, use_container_width=True)

    with st.expander("📄 แสดงข้อมูลดิบ (Raw Data)"):
        st.dataframe(df_filtered.sort_values('date', ascending=False), use_container_width=True)

st.markdown("---")
st.markdown("<div style='text-align: center; color: #888;'>Developed for Hospital Staff | Data Source: Google Sheets</div>", unsafe_allow_html=True)

