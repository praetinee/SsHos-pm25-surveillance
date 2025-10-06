import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from datetime import datetime

# --- การตั้งค่าหน้าเว็บ Streamlit ---
st.set_page_config(
    page_title="Patient Data Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 กราฟแสดงจำนวนผู้ป่วยย้อนหลัง 3 ปี")

# --- การตั้งค่าที่ต้องแก้ไขใน Streamlit Secrets ---
try:
    SHEET_URL = st.secrets["google_sheet"]["sheet_url"]
    WORKSHEET_NAME = st.secrets["google_sheet"]["worksheet_name"]
    DATE_COLUMN = st.secrets["google_sheet"]["date_column"]
    COUNT_COLUMN = st.secrets["google_sheet"]["count_column"]
except (KeyError, FileNotFoundError):
    st.error("⚠️ ไม่พบการตั้งค่า Google Sheet ใน Secrets! กรุณาตั้งค่าใน .streamlit/secrets.toml หรือในหน้าตั้งค่าของ Streamlit Cloud")
    st.stop()


@st.cache_data(ttl=600) # Cache a copy of the data for 10 minutes.
def load_data():
    """
    ฟังก์ชันสำหรับเชื่อมต่อ Google Sheet และดึงข้อมูล
    """
    try:
        # กำหนดขอบเขต (scopes) การเข้าถึง API ให้ชัดเจน
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        sheet = client.open_by_url(SHEET_URL).worksheet(WORKSHEET_NAME)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อ Google Sheets: {e}")
        return pd.DataFrame()

def process_data(df):
    """
    ฟังก์ชันสำหรับประมวลผลข้อมูลที่ดึงมา
    """
    if df.empty:
        return pd.DataFrame()

    df_processed = df[[DATE_COLUMN, COUNT_COLUMN]].copy()
    df_processed.dropna(inplace=True)
    df_processed['visit_date'] = pd.to_datetime(df_processed[DATE_COLUMN], errors='coerce', dayfirst=True)
    df_processed.dropna(subset=['visit_date'], inplace=True)
    
    three_years_ago = datetime.now() - pd.DateOffset(years=3)
    df_processed = df_processed[df_processed['visit_date'] >= three_years_ago]

    if df_processed.empty:
        return pd.DataFrame()

    df_processed['year_be'] = df_processed['visit_date'].dt.year + 543
    df_processed['year_month_sort'] = df_processed['visit_date'].dt.strftime('%Y-%m')
    
    monthly_counts = df_processed.groupby('year_month_sort').size().reset_index(name='patient_count')
    monthly_counts['x_label'] = pd.to_datetime(monthly_counts['year_month_sort']).dt.strftime('%m-%Y')
    
    # แปลงปีใน x_label เป็น พ.ศ.
    monthly_counts['x_label'] = monthly_counts['x_label'].apply(
        lambda x: f"{x.split('-')[0]}-{int(x.split('-')[1]) + 543}"
    )
    
    monthly_counts.sort_values('year_month_sort', inplace=True)
    return monthly_counts

def create_plot(df_plot):
    """
    ฟังก์ชันสำหรับสร้างกราฟจากข้อมูลที่ประมวลผลแล้ว
    """
    try:
        # พยายามตั้งค่าฟอนต์ภาษาไทย (อาจต้องปรับเปลี่ยนตามสภาพแวดล้อมของ Server)
        font_name = 'Tahoma' # Default font
        for font in fm.fontManager.ttflist:
            if 'Leelawadee' in font.name or 'Tahoma' in font.name:
                font_name = font.name
                break
        plt.rcParams['font.family'] = font_name
    except Exception:
        st.warning("ไม่สามารถตั้งค่าฟอนต์ภาษาไทยได้ กราฟอาจแสดงผลผิดเพี้ยน")

    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(16, 8))

    ax.plot(df_plot['x_label'], df_plot['patient_count'], marker='o', linestyle='-', color='dodgerblue')
    
    for index, row in df_plot.iterrows():
        ax.text(row['x_label'], row['patient_count'] + 5, f"{row['patient_count']:,}", ha='center', fontsize=10, weight='bold')

    ax.set_title('กราฟแสดงจำนวนผู้ป่วยรายเดือน', fontsize=20, weight='bold')
    ax.set_xlabel('เดือน-ปี (พ.ศ.)', fontsize=14)
    ax.set_ylabel('จำนวนผู้ป่วย (คน)', fontsize=14)
    ax.tick_params(axis='x', rotation=45, labelsize=10)
    ax.tick_params(axis='y', labelsize=10)
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    return fig

# --- Main Logic ---
with st.spinner('กำลังดึงและประมวลผลข้อมูล...'):
    raw_df = load_data()

if not raw_df.empty:
    processed_df = process_data(raw_df)
    
    if not processed_df.empty:
        st.success('ประมวลผลข้อมูลสำเร็จ!')
        
        # แสดงตารางข้อมูลสรุป
        st.subheader("ตารางสรุปจำนวนผู้ป่วยรายเดือน")
        st.dataframe(
            processed_df[['x_label', 'patient_count']].rename(
                columns={'x_label': 'เดือน-ปี (พ.ศ.)', 'patient_count': 'จำนวนผู้ป่วย'}
            ),
            use_container_width=True,
            hide_index=True
        )
        
        # สร้างและแสดงกราฟ
        st.subheader("กราฟแนวโน้ม")
        chart_fig = create_plot(processed_df)
        st.pyplot(chart_fig)
    else:
        st.warning("ไม่พบข้อมูลในช่วง 3 ปีที่ผ่านมา")
else:
    st.info("ไม่สามารถโหลดข้อมูลได้ โปรดตรวจสอบการตั้งค่า")

