import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- Page Configuration ---
st.set_page_config(
    page_title="Dashboard เฝ้าระวังผลกระทบจาก PM2.5",
    page_icon="😷",
    layout="wide",
)

# --- Data Loading and Caching ---

# Function to load real-time PM2.5 data from Google Sheet
# We use a special URL format to directly download the sheet as a CSV.
@st.cache_data(ttl=600) # Cache data for 10 minutes
def load_pm25_realtime():
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
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล PM2.5: {e}")
        return None, None

# Function to generate mock historical data for demonstration
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
    # Group 1: Respiratory (highly correlated)
    group1 = np.random.randint(5, 20, len(dates)) + (pm25_values / 5).astype(int)
    # Group 2: Cardiovascular (moderately correlated)
    group2 = np.random.randint(3, 15, len(dates)) + (pm25_values / 8).astype(int)
    # Group 3: Eye Irritation (moderately correlated)
    group3 = np.random.randint(2, 10, len(dates)) + (pm25_values / 10).astype(int)
    # Group 4: Others (less correlated)
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

# --- UI Layout ---

# Title
st.title("😷 Dashboard เฝ้าระวังผลกระทบสุขภาพจาก PM2.5")
st.subheader("โรงพยาบาลสันทราย (ข้อมูลจำลองเพื่อการพัฒนา)")

# --- Real-time PM2.5 Display ---
timestamp, pm25_value = load_pm25_realtime()

def get_aqi_color(pm_value):
    if pm_value <= 25: return "green"
    if pm_value <= 37: return "yellow"
    if pm_value <= 50: return "orange"
    if pm_value <= 90: return "red"
    return "purple"

if timestamp and pm25_value is not None:
    col1, col2 = st.columns([1, 4])
    with col1:
        color = get_aqi_color(pm25_value)
        st.markdown(f"""
        <div style="background-color:{color}; padding: 20px; border-radius: 10px; text-align: center;">
            <h3 style="color:white; margin:0;">PM2.5 ขณะนี้</h3>
            <h1 style="color:white; margin:0; font-size: 3em;">{pm25_value:.1f}</h1>
            <p style="color:white; margin:0;">μg/m³</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.info(f"ข้อมูลล่าสุดเมื่อ: {timestamp.strftime('%d %B %Y, %H:%M:%S')}")
        st.markdown("""
        **คำแนะนำ:**
        - **0-25 (สีเขียว):** คุณภาพอากาศดีมาก
        - **26-37 (สีเหลือง):** คุณภาพอากาศปานกลาง ประชาชนทั่วไปทำกิจกรรมได้ปกติ
        - **38-50 (สีส้ม):** เริ่มมีผลกระทบต่อสุขภาพ กลุ่มเสี่ยงควรลดกิจกรรมกลางแจ้ง
        - **51-90 (สีแดง):** มีผลกระทบต่อสุขภาพ ทุกคนควรลดกิจกรรมกลางแจ้ง
        - **91+ (สีม่วง):** มีผลกระทบต่อสุขภาพรุนแรง ควรงดกิจกรรมกลางแจ้ง
        """)
else:
    st.warning("ไม่สามารถแสดงข้อมูล PM2.5 Real-time ได้ในขณะนี้")

st.markdown("---")

# --- Historical Data Visualization ---
st.header("📊 ความสัมพันธ์ระหว่างค่า PM2.5 และจำนวนผู้ป่วย (ข้อมูลรายเดือนย้อนหลัง)")

# Load mock data
df_historical = generate_mock_data()

# --- Sidebar for Filters ---
with st.sidebar:
    st.header("ตัวกรองข้อมูล")
    
    # Date Range Filter
    min_date = df_historical['Date'].min().date()
    max_date = df_historical['Date'].max().date()
    
    selected_date_range = st.date_input(
        "เลือกช่วงวันที่",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        format="DD/MM/YYYY"
    )

    # Disease Group Filter
    disease_groups = ['กลุ่มโรคระบบทางเดินหายใจ', 'กลุ่มโรคหัวใจและหลอดเลือด', 'กลุ่มโรคตาอักเสบ', 'กลุ่มโรคอื่นๆ']
    selected_groups = st.multiselect(
        "เลือกกลุ่มโรคที่สนใจ",
        options=disease_groups,
        default=disease_groups
    )

# Filter data based on sidebar selection
if len(selected_date_range) == 2:
    start_date_filter, end_date_filter = selected_date_range
    mask = (df_historical['Date'].dt.date >= start_date_filter) & (df_historical['Date'].dt.date <= end_date_filter)
    filtered_df = df_historical.loc[mask]
else:
    filtered_df = df_historical.copy()

if not selected_groups:
    st.warning("กรุณาเลือกอย่างน้อยหนึ่งกลุ่มโรคเพื่อแสดงผล")
    st.stop()

# Aggregate data by month for plotting
filtered_df['Month'] = filtered_df['Date'].dt.to_period('M').astype(str)
monthly_agg = filtered_df.groupby('Month').agg({
    'PM2.5': 'mean',
    **{group: 'sum' for group in selected_groups}
}).reset_index()

# Add a 'Total Patients' column for the bar chart
monthly_agg['Total Patients'] = monthly_agg[selected_groups].sum(axis=1)

# --- Create Dual-Axis Chart ---
fig = make_subplots(specs=[[{"secondary_y": True}]])

# Add Bar Chart for Total Patients
fig.add_trace(
    go.Bar(
        x=monthly_agg['Month'], 
        y=monthly_agg['Total Patients'], 
        name="จำนวนผู้ป่วยรวม",
        marker_color='cornflowerblue'
    ),
    secondary_y=False,
)

# Add Line Chart for PM2.5
fig.add_trace(
    go.Scatter(
        x=monthly_agg['Month'], 
        y=monthly_agg['PM2.5'], 
        name="ค่าเฉลี่ย PM2.5",
        mode='lines+markers',
        line=dict(color='firebrick', width=3)
    ),
    secondary_y=True,
)

# Update layout and axis titles
fig.update_layout(
    title_text="กราฟแสดงจำนวนผู้ป่วยรวมเทียบกับค่า PM2.5 เฉลี่ยรายเดือน",
    xaxis_title="เดือน-ปี",
    legend=dict(x=0, y=1.1, traceorder="normal", orientation="h")
)

fig.update_yaxes(title_text="<b>จำนวนผู้ป่วย (คน)</b>", secondary_y=False)
fig.update_yaxes(title_text="<b>ค่า PM2.5 เฉลี่ย (μg/m³)</b>", secondary_y=True)

st.plotly_chart(fig, use_container_width=True)

# --- Display Raw Data (Optional) ---
with st.expander("แสดงข้อมูลตารางแบบสรุปรายเดือน"):
    st.dataframe(monthly_agg)
