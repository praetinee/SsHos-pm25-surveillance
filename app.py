import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from gspread_pandas import GSpread, Client
from google.oauth2.service_account import Credentials
import traceback

# --- CONFIGURATION & AUTHENTICATION ---
st.set_page_config(layout="wide")

def connect_to_gsheet():
    """Establishes a connection to the Google Sheet."""
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = Client(creds)
        return client
    except Exception as e:
        st.error(f"⚠️ เกิดข้อผิดพลาดในการเชื่อมต่อกับ Google API: {e}")
        st.stop()

def load_data(client, url):
    """Loads data from the Google Sheet."""
    try:
        gsheet = GSpread(client=client, gsheet_id_or_url=url)
        # Assuming the data is on the first sheet
        df = gsheet.sheet_to_df(index=False)
        return df
    except Exception as e:
        st.error(f"⚠️ ไม่สามารถโหลดข้อมูลจาก Google Sheet ได้: {e}")
        st.info("ตรวจสอบให้แน่ใจว่าได้แชร์ Sheet ให้กับอีเมลของ Service Account แล้ว และ URL ถูกต้อง")
        st.code(f"Traceback:\n{traceback.format_exc()}")
        st.stop()


# --- DATA PROCESSING ---
def preprocess_data(df, date_column):
    """Prepares the data for plotting."""
    if date_column not in df.columns:
        st.error(f"ไม่พบคอลัมน์วันที่ชื่อ '{date_column}' ในข้อมูลของคุณ")
        st.info(f"คอลัมน์ที่มีอยู่: {', '.join(df.columns)}")
        st.stop()

    df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
    df = df.dropna(subset=[date_column])
    daily_counts = df.set_index(date_column).resample('D').size().reset_index(name='count')
    return daily_counts

# --- MAIN APP LOGIC ---
st.title("📊 กราฟแสดงจำนวนผู้ป่วยรายวัน")

# Get configuration from secrets
try:
    g_sheet_url = st.secrets["google_sheet"]["url"]
    date_column_name = 'date' # <--- ❗️❗️ เปลี่ยนตรงนี้ให้เป็นชื่อคอลัมน์วันที่ของคุณ
except KeyError:
    st.error("⚠️ ไม่พบการตั้งค่า 'google_sheet' หรือ 'url' ในไฟล์ Secrets")
    st.stop()


# Connect and load data
gsheet_client = connect_to_gsheet()
raw_df = load_data(gsheet_client, g_sheet_url)


if not raw_df.empty:
    st.success("✅ เชื่อมต่อและโหลดข้อมูลสำเร็จ!")
    
    # Process and display data
    daily_patient_counts = preprocess_data(raw_df, date_column_name)

    st.header("จำนวนผู้ป่วยเข้ารับการรักษา (รายวัน)")
    fig = px.line(
        daily_patient_counts,
        x=date_column_name,
        y='count',
        title='จำนวนผู้ป่วยในแต่ละวัน',
        labels={'date': 'วันที่', 'count': 'จำนวนผู้ป่วย'}
    )
    fig.update_layout(
        xaxis_title="วันที่",
        yaxis_title="จำนวนผู้ป่วย (คน)",
        title_x=0.5,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("ข้อมูลดิบ")
    st.dataframe(raw_df)
else:
    st.warning("ไม่พบข้อมูลใน Google Sheet")

