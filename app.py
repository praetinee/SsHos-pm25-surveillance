import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- Page Configuration ---
st.set_page_config(
    page_title="PM2.5 Patient Dashboard",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Data Generation (Mock Data) ---
# In a real-world scenario, you would connect to a database here.
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
        # Simulate more patients during high PM2.5 seasons (e.g., Jan-Apr)
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

df = generate_mock_data()

# --- Sidebar Filters ---
st.sidebar.header("ตัวกรองข้อมูล (Filters) 🔬")

# Date Range Filter
min_date = df['date'].min()
max_date = df['date'].max()
start_date, end_date = st.sidebar.date_input(
    "เลือกช่วงวันที่:",
    value=(max_date - timedelta(days=30), max_date),
    min_value=min_date,
    max_value=max_date,
    help="เลือกช่วงเวลาที่ต้องการแสดงข้อมูล"
)

# Disease Filter
all_diseases = df['disease'].unique()
selected_diseases = st.sidebar.multiselect(
    "เลือกกลุ่มโรค:",
    options=all_diseases,
    default=all_diseases,
    help="เลือกกลุ่มโรคที่ต้องการวิเคราะห์"
)

# Age Group Filter
all_age_groups = df['age_group'].unique()
selected_age_groups = st.sidebar.multiselect(
    "เลือกกลุ่มอายุ:",
    options=all_age_groups,
    default=all_age_groups,
    help="เลือกกลุ่มอายุที่ต้องการวิเคราะห์"
)


# --- Filtering Data based on selections ---
df_filtered = df[
    (df['date'] >= start_date) &
    (df['date'] <= end_date) &
    (df['disease'].isin(selected_diseases)) &
    (df['age_group'].isin(selected_age_groups))
]

# --- Main Dashboard ---
st.title("🩺 Dashboard ติดตามผู้ป่วยจากผลกระทบ PM2.5")
st.markdown("แดชบอร์ดสำหรับเจ้าหน้าที่โรงพยาบาลเพื่อติดตามแนวโน้มและสถิติผู้ป่วยที่เกี่ยวข้องกับมลพิษทางอากาศ")

# --- Key Metrics (KPIs) ---
st.markdown("---")
st.subheader("ภาพรวมข้อมูลสำคัญ (Key Metrics)")

# Prepare data for metrics
today = max_date
yesterday = today - timedelta(days=1)

patients_today = len(df[df['date'] == today])
patients_yesterday = len(df[df['date'] == yesterday])
delta_today = patients_today - patients_yesterday if patients_yesterday > 0 else 0

total_patients_selected_range = len(df_filtered)
avg_patients_per_day = total_patients_selected_range / ((end_date - start_date).days + 1) if (end_date - start_date).days > 0 else 0

# Display Metrics
kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric(
    label=f"ผู้ป่วยวันนี้ ({today.strftime('%d %b')})",
    value=f"{patients_today} คน",
    delta=f"{delta_today} vs วันก่อนหน้า",
    help="จำนวนผู้ป่วยที่เข้ารับการรักษาในวันนี้เทียบกับวันก่อนหน้า"
)

kpi2.metric(
    label="ผู้ป่วยทั้งหมดในข่วงที่เลือก",
    value=f"{total_patients_selected_range} คน",
    help=f"จำนวนผู้ป่วยทั้งหมดตั้งแต่วันที่ {start_date.strftime('%d %b')} ถึง {end_date.strftime('%d %b')}"
)

kpi3.metric(
    label="ค่าเฉลี่ยผู้ป่วยต่อวัน",
    value=f"{avg_patients_per_day:.1f} คน/วัน",
    help="ค่าเฉลี่ยจำนวนผู้ป่วยต่อวันในช่วงเวลาที่เลือก"
)
st.markdown("---")


# --- Charts ---
st.subheader("การแสดงผลข้อมูล (Visualizations)")

# Daily Patient Trend Chart
daily_counts = df_filtered.groupby('date').size().reset_index(name='count')
daily_counts['moving_avg_7_days'] = daily_counts['count'].rolling(window=7, min_periods=1).mean()

fig_trend = go.Figure()

# Bar chart for daily count
fig_trend.add_trace(go.Bar(
    x=daily_counts['date'],
    y=daily_counts['count'],
    name='จำนวนผู้ป่วยรายวัน',
    marker_color='#1f77b4',
    opacity=0.6
))

# Line chart for moving average
fig_trend.add_trace(go.Scatter(
    x=daily_counts['date'],
    y=daily_counts['moving_avg_7_days'],
    name='ค่าเฉลี่ยเคลื่อนที่ 7 วัน',
    mode='lines',
    line=dict(color='#ff7f0e', width=3)
))

fig_trend.update_layout(
    title='แนวโน้มจำนวนผู้ป่วยรายวัน',
    xaxis_title='วันที่',
    yaxis_title='จำนวนผู้ป่วย (คน)',
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)'
)
st.plotly_chart(fig_trend, use_container_width=True)


# Breakdown Charts (Disease and Age Group)
col1, col2 = st.columns(2)

with col1:
    # Disease Breakdown
    disease_counts = df_filtered['disease'].value_counts().reset_index()
    disease_counts.columns = ['disease', 'count']
    fig_disease = px.bar(
        disease_counts,
        x='count',
        y='disease',
        orientation='h',
        title='สัดส่วนผู้ป่วยตามกลุ่มโรค',
        labels={'count': 'จำนวนผู้ป่วย', 'disease': 'กลุ่มโรค'},
        text='count',
        color='disease',
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig_disease.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_disease, use_container_width=True)

with col2:
    # Age Group Breakdown
    age_counts = df_filtered['age_group'].value_counts().reset_index()
    age_counts.columns = ['age_group', 'count']
    fig_age = px.pie(
        age_counts,
        names='age_group',
        values='count',
        title='สัดส่วนผู้ป่วยตามกลุ่มอายุ',
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig_age.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_age, use_container_width=True)


# --- Raw Data Table ---
with st.expander("แสดงข้อมูลดิบ (Raw Data)  Raw Data) 📄"):
    st.dataframe(df_filtered.style.format({"date": lambda x: x.strftime("%Y-%m-%d")}))

# --- Footer ---
st.markdown("---")
st.markdown("Developed for Hospital Staff | Data is for demonstration purposes only.")
