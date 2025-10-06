import streamlit as st
import streamlit.components.v1 as components
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime
import pytz

# --- การตั้งค่าหน้าเว็บ ---
st.set_page_config(layout="wide")

# --- ฟังก์ชันตัวช่วย ---

def convert_thai_month_to_datetime(date_series):
    """Converts a pandas Series of strings with Thai month abbreviations to datetime objects."""
    processed_series = date_series.astype(str).str.strip()
    thai_to_eng_month = {
        'ม.ค.': 'Jan', 'ก.พ.': 'Feb', 'มี.ค.': 'Mar', 'เม.ย.': 'Apr',
        'พ.ค.': 'May', 'มิ.ย.': 'Jun', 'ก.ค.': 'Jul', 'ส.ค.': 'Aug',
        'ก.ย.': 'Sep', 'ต.ค.': 'Oct', 'พ.ย.': 'Nov', 'ธ.ค.': 'Dec'
    }
    for thai, eng in thai_to_eng_month.items():
        processed_series = processed_series.str.replace(thai, eng, regex=False)
    return pd.to_datetime(processed_series.str.replace('.', '', regex=False), errors='coerce')

# --- ฟังก์ชันเชื่อมต่อและดึงข้อมูลจาก Google Sheets ---
@st.cache_data(ttl=600) # โหลดข้อมูลใหม่ทุก 10 นาที
def load_data_from_gsheet():
    """Loads and does initial processing of data from Google Sheets."""
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        client = gspread.authorize(creds)
        spreadsheet_name = "โรคเฝ้าระวังจาก pm2.5" 
        spreadsheet = client.open(spreadsheet_name)
        
        # ดึงข้อมูลจากชีตต่างๆ
        worksheet_main = spreadsheet.worksheet("4 โรคเฝ้าระวัง")
        df_main = pd.DataFrame(worksheet_main.get_all_records())
        worksheet_pm25 = spreadsheet.worksheet("PM2.5 รายเดือน")
        df_pm25 = pd.DataFrame(worksheet_pm25.get_all_records())

        # --- การประมวลผลเบื้องต้น ---
        # แปลงชนิดข้อมูลให้ถูกต้อง
        df_pm25['PM2.5 (ug/m3)'] = pd.to_numeric(df_pm25['PM2.5 (ug/m3)'], errors='coerce')
        df_main['วันที่มารับบริการ'] = pd.to_datetime(df_main['วันที่มารับบริการ'], format='mixed', dayfirst=True, errors='coerce')
        df_pm25['Date'] = convert_thai_month_to_datetime(df_pm25['Date'])
        
        # ลบแถวที่ข้อมูลสำคัญเป็นค่าว่าง
        df_main.dropna(subset=['วันที่มารับบริการ', 'จังหวัด', 'อำเภอ', 'ตำบล', '4 กลุ่มโรคเฝ้าระวัง'], inplace=True)
        df_pm25.dropna(subset=['Date', 'PM2.5 (ug/m3)'], inplace=True)
        
        return df_main, df_pm25

    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"ไม่พบ Google Sheet ชื่อ '{spreadsheet_name}'")
        return None, None
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อหรือประมวลผลข้อมูล: {e}")
        return None, None

# --- โหลดข้อมูล ---
df_main, df_pm25 = load_data_from_gsheet()

# --- ส่วนของ Sidebar และ Filters ---
with st.sidebar:
    st.header("ตัวกรองข้อมูล")
    
    if df_main is not None:
        # สร้างตัวเลือกจากข้อมูลที่ไม่ซ้ำกัน
        province = st.multiselect("จังหวัด", options=df_main["จังหวัด"].unique(), default=df_main["จังหวัด"].unique())
        district = st.multiselect("อำเภอ", options=df_main[df_main["จังหวัด"].isin(province)]["อำเภอ"].unique(), default=df_main[df_main["จังหวัด"].isin(province)]["อำเภอ"].unique())
        tambon = st.multiselect("ตำบล", options=df_main[df_main["อำเภอ"].isin(district)]["ตำบล"].unique(), default=df_main[df_main["อำเภอ"].isin(district)]["ตำบล"].unique())
        disease_group = st.multiselect("4 กลุ่มโรคเฝ้าระวัง", options=df_main["4 กลุ่มโรคเฝ้าระวัง"].unique(), default=df_main["4 กลุ่มโรคเฝ้าระวัง"].unique())

        # กรองข้อมูลหลักตามตัวเลือกของผู้ใช้
        df_filtered = df_main.query(
            "จังหวัด == @province & อำเภอ == @district & ตำบล == @tambon & `4 กลุ่มโรคเฝ้าระวัง` == @disease_group"
        )
        
        # --- กราฟวงกลมใน Sidebar ---
        st.header("สัดส่วนกลุ่มโรค")
        if not df_filtered.empty:
            pie_data = df_filtered['4 กลุ่มโรคเฝ้าระวัง'].value_counts()
            pie_labels = pie_data.index.tolist()
            pie_values = pie_data.values.tolist()
            pie_chart_html = f"""
                <canvas id="pieChart"></canvas>
                <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                <script>
                    new Chart(document.getElementById('pieChart'), {{
                        type: 'pie',
                        data: {{
                            labels: {pie_labels},
                            datasets: [{{
                                data: {pie_values},
                                backgroundColor: ['#ef4444', '#f97316', '#10b981', '#a855f7', '#3b82f6'],
                                hoverOffset: 4
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            plugins: {{ legend: {{ position: 'bottom' }} }}
                        }}
                    }});
                </script>
            """
            components.html(pie_chart_html, height=350)

# --- ส่วนหัวเรื่อง (Header) ---
if df_main is not None:
    # สร้างเวลาปัจจุบัน
    tz = pytz.timezone("Asia/Bangkok")
    now = datetime.now(tz)
    last_updated_date = now.strftime("%d %b %Y").replace("Oct", "ต.ค.") # ตัวอย่างการแปลงเดือน
    last_updated_time = now.strftime("%H:%M:%S")

    st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 20px; margin-bottom: 2rem;">
            <div style="text-align: center; border: 3px solid #3b82f6; border-radius: 50%; width: 100px; height: 100px; display: flex; flex-direction: column; justify-content: center; align-items: center; background-color: #eff6ff;">
                <div style="font-size: 1rem; font-weight: bold; color: #1e40af;">5</div>
                <div style="font-size: 0.7rem; color: #1e40af;">{last_updated_date}</div>
                <div style="font-size: 0.7rem; color: #1e40af;">{last_updated_time}</div>
                <div style="font-size: 0.6rem; color: #6b7280;">คุณภาพอากาศ</div>
            </div>
            <h1 style="font-size: 1.5rem; font-weight: 700; color: #374151;">
                การเฝ้าระวังโรคที่อาจมีผลกระทบจาก PM2.5 ของผู้เข้ารับบริการในโรงพยาบาลสันทราย
            </h1>
        </div>
        """, unsafe_allow_html=True)

# --- กราฟหลัก (Main Content) ---
if df_main is not None and not df_filtered.empty:
    
    # --- คำนวณข้อมูลสำหรับกราฟจาก df_filtered ---
    # กราฟแท่ง
    df_bar = df_filtered['ตำบล'].value_counts().reset_index()
    df_bar.columns = ['tambon', 'patient_count']

    # กราฟเส้น
    df_filtered['Month'] = df_filtered['วันที่มารับบริการ'].dt.to_period('M')
    df_pm25['Month'] = df_pm25['Date'].dt.to_period('M')
    monthly_cases = df_filtered.groupby(['Month', '4 กลุ่มโรคเฝ้าระวัง']).size().unstack(fill_value=0)
    df_pm25_monthly = df_pm25.groupby('Month')['PM2.5 (ug/m3)'].mean().rename('pm25_level')
    df_line = pd.concat([monthly_cases, df_pm25_monthly], axis=1).fillna(0).reset_index()
    df_line['Month'] = df_line['Month'].dt.to_timestamp()
    rename_map = {
        'Month': 'date', 'กลุ่มโรคทางเดินหายใจ': 'disease_group_1', 'กลุ่มโรคผิวหนังอักเสบ': 'disease_group_2',
        'กลุ่มโรคตาอักเสบ': 'disease_group_3', 'กลุ่มโรคหัวใจและหลอดเลือด': 'disease_group_4'
    }
    df_line = df_line.rename(columns=rename_map)
    for col in rename_map.values():
        if col not in df_line.columns:
            df_line[col] = 0

    # --- แสดงผลกราฟ ---
    st.subheader("สถานการณ์ PM2.5 และจำนวนผู้เข้ารับการรักษา (รายเดือน)")
    # (โค้ด HTML/JS ของกราฟเส้นเหมือนเดิม แต่ใช้ข้อมูลจาก df_line ที่คำนวณใหม่)
    if not df_line.empty:
        def format_to_buddhist_era(dt):
            thai_months = {1: 'ม.ค.', 2: 'ก.พ.', 3: 'มี.ค.', 4: 'เม.ย.', 5: 'พ.ค.', 6: 'มิ.ย.', 7: 'ก.ค.', 8: 'ส.ค.', 9: 'ก.ย.', 10: 'ต.ค.', 11: 'พ.ย.', 12: 'ธ.ค.'}
            return f"{thai_months[dt.month]} {dt.year + 543}"
        labels_line = df_line['date'].apply(format_to_buddhist_era).tolist()
        line_chart_html = f""" ... """ # โค้ด HTML/JS ส่วนนี้เหมือนเดิม
        components.html(line_chart_html, height=400)

    st.subheader("จำนวนผู้ป่วยในแต่ละตำบล")
    # (โค้ด HTML/JS ของกราฟแท่งเหมือนเดิม แต่ใช้ข้อมูลจาก df_bar ที่คำนวณใหม่)
    if not df_bar.empty:
        df_bar = df_bar.sort_values('patient_count', ascending=False)
        labels_bar = df_bar['tambon'].tolist()
        data_bar = df_bar['patient_count'].tolist()
        bar_chart_html = f""" ... """ # โค้ด HTML/JS ส่วนนี้เหมือนเดิม
        components.html(bar_chart_html, height=420)

elif df_main is not None:
    st.warning("ไม่พบข้อมูลตามตัวกรองที่เลือก กรุณาปรับเปลี่ยนตัวกรอง")

