import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import re

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
@st.cache_data(ttl=600) # Cache patient data for 10 minutes
def load_from_gsheet():
    """
    Loads and transforms patient data from Google Sheet with enhanced debugging.
    """
    SHEET_URL = "https://docs.google.com/spreadsheets/d/1vvQ8YLChHXvCowQQzcKIeV4PWt0CCt76f5Sj3fNTOV0/export?format=csv&gid=795124395"
    
    st.info("🔄 กำลังโหลดข้อมูลผู้ป่วย...")
    try:
        df_raw = pd.read_csv(SHEET_URL)
        st.success("✅ โหลดข้อมูลผู้ป่วยดิบสำเร็จ!")
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูลผู้ป่วย: {e}")
        return pd.DataFrame()

    df_processed = df_raw.copy()
    df_processed.columns = df_processed.columns.str.strip()
    
    required_patient_cols = ['วันที่มารับบริการ', 'อายุ', '4 กลุ่มโรคเฝ้าระวัง']
    if not all(col in df_processed.columns for col in required_patient_cols):
        st.error(f"ชีตข้อมูลผู้ป่วยขาดคอลัมน์ที่จำเป็น! ต้องมี: {required_patient_cols}")
        st.info(f"คอลัมน์ที่พบ: {df_processed.columns.tolist()}")
        return pd.DataFrame()

    st.info("🛠️ กำลังแปลงข้อมูลผู้ป่วย...")
    
    df_processed['date'] = pd.to_datetime(df_processed['วันที่มารับบริการ'], errors='coerce').dt.date
    if df_processed['date'].isnull().all():
        st.warning("⚠️ ไม่สามารถแปลงคอลัมน์ 'วันที่มารับบริการ' เป็นวันที่ได้ทั้งหมด")

    df_processed['age_numeric'] = pd.to_numeric(df_processed['อายุ'], errors='coerce')
    if df_processed['age_numeric'].isnull().all():
        st.warning("⚠️ ไม่สามารถแปลงคอลัมน์ 'อายุ' เป็นตัวเลขได้ทั้งหมด")

    bins = [0, 10, 20, 40, 60, 120]
    labels = ["0-10 ปี", "11-20 ปี", "21-40 ปี", "41-60 ปี", "60+ ปี"]
    df_processed['age_group'] = pd.cut(df_processed['age_numeric'], bins=bins, labels=labels, right=True)
    
    df_processed['disease'] = df_processed['4 กลุ่มโรคเฝ้าระวัง']
    
    rows_before_drop = len(df_processed)
    df_processed.dropna(subset=['date', 'disease', 'age_group'], inplace=True)
    rows_after_drop = len(df_processed)
    
    st.info(f"จากข้อมูลดิบ {rows_before_drop} แถว, หลังทำความสะอาดเหลือ {rows_after_drop} แถวที่ใช้งานได้")

    if rows_after_drop == 0:
        st.error("❌ ไม่มีข้อมูลผู้ป่วยที่ใช้งานได้หลังจากการทำความสะอาด ทำให้ไม่สามารถแสดงกราฟได้")
        return pd.DataFrame()

    st.success("✅ แปลงข้อมูลผู้ป่วยสำเร็จ!")
    return df_processed[['date', 'disease', 'age_group']]

@st.cache_data(ttl=600) # Cache PM2.5 data for 10 minutes
def load_pm25_data():
    """
    Loads and transforms PM2.5 data from a separate Google Sheet.
    """
    PM25_SHEET_URL = "https://docs.google.com/spreadsheets/d/1vvQ8YLChHXvCowQQzcKIeV4PWt0CCt76f5Sj3fNTOV0/export?format=csv&gid=1038807599"
    
    try:
        df_pm25 = pd.read_csv(PM25_SHEET_URL)
        original_cols = df_pm25.columns.tolist()
        df_pm25.columns = [re.sub(r'[^A-Za-z0-9_.()/ ]+', '', col).strip() for col in df_pm25.columns]
        
        date_col, pm25_col = 'Date', 'PM2.5 (ug/m3)'
        if not all(col in df_pm25.columns for col in [date_col, pm25_col]):
            st.error(f"ชีตข้อมูล PM2.5 ขาดคอลัมน์ที่จำเป็น! ต้องการ: `{date_col}` และ `{pm25_col}`")
            st.info(f"คอลัมน์ดั้งเดิมที่พบ: {original_cols}")
            return pd.DataFrame()

        df_pm25['Date'] = pd.to_datetime(df_pm25[date_col], errors='coerce')
        df_pm25.rename(columns={pm25_col: 'pm25'}, inplace=True)
        df_pm25.dropna(subset=['Date', 'pm25'], inplace=True)
        return df_pm25
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล PM2.5: {e}")
        return pd.DataFrame()

# --- Load data ---
df = load_from_gsheet() 
df_pm25 = load_pm25_data()

# --- Sidebar Filters ---
if not df.empty:
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3004/3004458.png", width=80)
        st.title("ตัวกรองข้อมูล (Filters)")
        
        min_date, max_date = df['date'].min(), df['date'].max()
        start_date, end_date = st.date_input(
            "เลือกช่วงวันที่:",
            value=(max_date - timedelta(days=365), max_date),
            min_value=min_date,
            max_value=max_date,
            help="เลือกช่วงเวลาที่ต้องการแสดงข้อมูล"
        )

        all_diseases = sorted(df['disease'].unique())
        selected_diseases = st.multiselect("เลือกกลุ่มโรค:", options=all_diseases, default=all_diseases)

        all_age_groups = sorted(df['age_group'].dropna().astype(str).unique())
        selected_age_groups = st.multiselect("เลือกกลุ่มอายุ:", options=all_age_groups, default=all_age_groups)

    df_filtered = df[
        (df['date'] >= start_date) & (df['date'] <= end_date) &
        (df['disease'].isin(selected_diseases)) &
        (df['age_group'].astype(str).isin(selected_age_groups))
    ]
else:
    st.warning("ไม่สามารถโหลดข้อมูลผู้ป่วยเพื่อสร้างตัวกรองได้")
    df_filtered = pd.DataFrame()

# --- Main Dashboard ---
st.title("🏥 Dashboard ติดตามผู้ป่วยจากผลกระทบ PM2.5")
st.markdown("แดชบอร์ดวิเคราะห์ข้อมูลเชิงลึกสำหรับบุคลากรทางการแพทย์ เพื่อติดตามสถานการณ์และแนวโน้มของผู้ป่วยที่เกี่ยวข้องกับมลพิษทางอากาศ")

# --- New Dual-Axis Chart Section ---
if not df.empty and not df_pm25.empty:
    st.markdown("### 📉 ความสัมพันธ์ระหว่างค่าฝุ่น PM2.5 และจำนวนผู้ป่วย")

    df['date_dt'] = pd.to_datetime(df['date'])
    monthly_patients = df.set_index('date_dt').groupby('disease').resample('M').size().unstack(level=0, fill_value=0)
    
    df_pm25['date_dt'] = pd.to_datetime(df_pm25['Date'])
    df_pm25_monthly = df_pm25.set_index('date_dt').resample('M')[['pm25']].mean()
    
    df_merged = pd.merge(monthly_patients, df_pm25_monthly, left_index=True, right_index=True, how='inner')
    df_merged.reset_index(inplace=True)
    
    if not df_merged.empty:
        three_years_ago = datetime.now() - timedelta(days=3*365)
        df_plot = df_merged[df_merged['date_dt'] >= three_years_ago]

        if not df_plot.empty:
            fig_dual_axis = go.Figure()
            for disease in monthly_patients.columns:
                if disease in df_plot.columns:
                    fig_dual_axis.add_trace(go.Scatter(x=df_plot['date_dt'], y=df_plot[disease], name=disease, mode='lines+markers', line=dict(width=2.5), marker=dict(size=5), yaxis='y1'))
            
            fig_dual_axis.add_trace(go.Scatter(x=df_plot['date_dt'], y=df_plot['pm25'], name='ค่า PM2.5', yaxis='y2', mode='lines', line=dict(color='grey', width=3, dash='dash')))
            
            fig_dual_axis.update_layout(
                title='<b>จำนวนผู้ป่วยรายเดือนเทียบกับค่าเฉลี่ย PM2.5 (ย้อนหลัง 3 ปี)</b>',
                xaxis_title='เดือน',
                yaxis=dict(title='<b>จำนวนผู้ป่วย (คน)</b>', titlefont=dict(color='#1f77b4'), tickfont=dict(color='#1f77b4')),
                yaxis2=dict(title='<b>ค่า PM2.5 (ug/m3)</b>', titlefont=dict(color='grey'), tickfont=dict(color='grey'), overlaying='y', side='right'),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_dual_axis, use_container_width=True)
        else:
            st.info("ไม่มีข้อมูลที่ตรงกันในช่วง 3 ปีที่ผ่านมา")
    else:
        st.info("ไม่สามารถรวมข้อมูลผู้ป่วยและ PM2.5 ได้ (อาจเพราะช่วงเวลาไม่ตรงกัน)")

if not df_filtered.empty:
    st.markdown("### 📊 ภาพรวมข้อมูลสำคัญ (ตามช่วงเวลาที่เลือก)")
    today, yesterday = df['date'].max(), df['date'].max() - timedelta(days=1)
    patients_today = len(df[df['date'] == today])
    patients_yesterday = len(df[df['date'] == yesterday])
    delta_today = patients_today - patients_yesterday if patients_yesterday > 0 else patients_today
    delta_color_class = "negative" if delta_today < 0 else ""
    total_patients_selected_range = len(df_filtered)
    avg_patients_per_day = total_patients_selected_range / ((end_date - start_date).days + 1) if (end_date - start_date).days >= 0 else 0

    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-title">ผู้ป่วยล่าสุด ({today.strftime('%d %b')})</div><div class="kpi-value">{patients_today} คน</div><div class="kpi-delta {delta_color_class}">{delta_today:+} vs วันก่อนหน้า</div></div>""", unsafe_allow_html=True)
    with kpi2:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-title">ผู้ป่วยทั้งหมด (ช่วงที่เลือก)</div><div class="kpi-value">{total_patients_selected_range} คน</div><div class="kpi-delta" style="color: #555;">{start_date.strftime('%d %b')} - {end_date.strftime('%d %b')}</div></div>""", unsafe_allow_html=True)
    with kpi3:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-title">ค่าเฉลี่ยผู้ป่วยต่อวัน</div><div class="kpi-value">{avg_patients_per_day:.1f}</div><div class="kpi-delta" style="color: #555;">คน/วัน</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📈 การแสดงผลข้อมูล (ตามช่วงเวลาที่เลือก)")
    
    col1, col2 = st.columns(2)
    with col1:
        disease_counts = df_filtered['disease'].value_counts().reset_index()
        fig_disease = px.bar(disease_counts, x='count', y='disease', orientation='h', title='<b>สัดส่วนผู้ป่วยตามกลุ่มโรค</b>', labels={'count': 'จำนวนผู้ป่วย', 'disease': 'กลุ่มโรค'}, text='count')
        fig_disease.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_disease, use_container_width=True)
    with col2:
        age_counts = df_filtered['age_group'].value_counts().reset_index()
        fig_age = px.pie(age_counts, names='age_group', values='count', title='<b>สัดส่วนผู้ป่วยตามกลุ่มอายุ</b>', hole=0.5)
        fig_age.update_traces(textposition='inside', textinfo='percent+label', pull=[0.05]*len(age_counts))
        st.plotly_chart(fig_age, use_container_width=True)

    with st.expander("📄 แสดงข้อมูลดิบ (Raw Data)"):
        st.dataframe(df_filtered.sort_values('date', ascending=False), use_container_width=True)

st.markdown("---")
st.markdown("<div style='text-align: center; color: #888;'>Developed for Hospital Staff | Data Source: Google Sheets</div>", unsafe_allow_html=True)

