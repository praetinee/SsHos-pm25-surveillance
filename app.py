import streamlit as st
import streamlit.components.v1 as components
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# --- การตั้งค่าหน้าเว็บ ---
st.set_page_config(layout="wide")

# --- ฟังก์ชันเชื่อมต่อและดึงข้อมูลจาก Google Sheets ---
@st.cache_data(ttl=600) # โหลดข้อมูลใหม่ทุก 10 นาที
def load_data_from_gsheet():
    try:
        # เชื่อมต่อกับ Google API โดยใช้ข้อมูล credentials จาก secrets
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=scopes
        )
        client = gspread.authorize(creds)

        # --- !!! สำคัญ: แก้ไขชื่อ Google Sheet ของคุณตรงนี้ !!! ---
        # ต้องเป็นชื่อไฟล์ Google Sheet ที่ถูกต้องตรงกันทุกตัวอักษร
        spreadsheet_name = "4 โรคเฝ้าระวัง" 
        spreadsheet = client.open(spreadsheet_name)
        
        # 1. ดึงข้อมูลหลักจากชีต '4 โรคเฝ้าระวัง'
        worksheet_main = spreadsheet.worksheet("4 โรคเฝ้าระวัง")
        df_main = pd.DataFrame(worksheet_main.get_all_records())
        
        # 2. ดึงข้อมูล PM2.5 จากชีต 'PM2.5 รายเดือน'
        worksheet_pm25 = spreadsheet.worksheet("PM2.5 รายเดือน")
        df_pm25 = pd.DataFrame(worksheet_pm25.get_all_records())

        # --- การประมวลผลข้อมูล ---
        
        # A. เตรียมข้อมูลสำหรับกราฟแท่ง (จำนวนผู้ป่วยรายตำบล)
        df_bar = df_main['ตำบล'].value_counts().reset_index()
        df_bar.columns = ['tambon', 'patient_count']

        # B. เตรียมข้อมูลสำหรับกราฟเส้น (ข้อมูลรายเดือน)
        # แปลงคอลัมน์วันที่ให้เป็นรูปแบบ datetime
        df_main['วันที่มารับบริการ'] = pd.to_datetime(df_main['วันที่มารับบริการ'])
        df_pm25['Date'] = pd.to_datetime(df_pm25['Date'])

        # สร้างคอลัมน์ 'Month' เพื่อใช้จัดกลุ่มข้อมูล
        df_main['Month'] = df_main['วันที่มารับบริการ'].dt.to_period('M').dt.to_timestamp()

        # นับจำนวนผู้ป่วยในแต่ละกลุ่มโรค แบบรายเดือน
        monthly_cases = df_main.groupby(['Month', '4 กลุ่มโรคเฝ้าระวัง']).size().unstack(fill_value=0)

        # เตรียมข้อมูล PM2.5 รายเดือน
        df_pm25['Month'] = df_pm25['Date'].dt.to_timestamp()
        df_pm25_monthly = df_pm25.set_index('Month')['PM2.5 (ug/m3)'].rename('pm25_level')
        
        # รวมข้อมูลผู้ป่วยและข้อมูล PM2.5 เข้าด้วยกัน
        df_line = pd.concat([monthly_cases, df_pm25_monthly], axis=1).fillna(0).reset_index()
        
        # เปลี่ยนชื่อคอลัมน์ให้สอดคล้องกับที่โค้ด JavaScript ต้องการ
        rename_map = {
            'Month': 'date',
            'กลุ่มโรคทางเดินหายใจ': 'disease_group_1',
            'กลุ่มโรคผิวหนังอักเสบ': 'disease_group_2',
            'กลุ่มโรคตาอักเสบ': 'disease_group_3',
            'กลุ่มโรคหัวใจและหลอดเลือด': 'disease_group_4'
        }
        df_line = df_line.rename(columns=rename_map)

        # ตรวจสอบเผื่อบางกลุ่มโรคไม่มีข้อมูลในเดือนนั้นๆ
        for col in rename_map.values():
            if col not in df_line.columns:
                df_line[col] = 0
        
        return True, df_bar, df_line

    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"ไม่พบ Google Sheet ชื่อ '{spreadsheet_name}' กรุณาตรวจสอบชื่อและสิทธิ์การเข้าถึง")
        return False, None, None
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อหรือประมวลผลข้อมูล: {e}")
        return False, None, None

# --- ส่วนของการแสดงผลบนหน้าเว็บ ---

# โหลดข้อมูลก่อนแสดงผล
success, df_bar, df_line = load_data_from_gsheet()

# --- ส่วนหัวเรื่อง (Header) ---
st.markdown("""
    <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 2rem;">
        <h1 style="font-size: 1.5rem; font-weight: 700; color: #374151;">
            การเฝ้าระวังโรคที่อาจมีผลกระทบจาก PM2.5 ของผู้เข้ารับบริการในโรงพยาบาลสันทราย
        </h1>
    </div>
    """, unsafe_allow_html=True)

# --- ส่วนตัวกรอง (Sidebar) ---
with st.sidebar:
    st.header("ตัวกรองข้อมูล")
    st.selectbox("เลือกช่วงวินิจฉัย", ["ภาพรวมทั้งหมด"])
    # (สามารถเพิ่มตัวกรองอื่นๆ ได้ในอนาคต)
    
    # กราฟวงกลมยังใช้ข้อมูลตัวอย่างไปก่อน
    st.header("สัดส่วนผู้ป่วย (ตัวอย่าง)")
    components.html("""<canvas id="pieChart"></canvas>...""", height=300) # (โค้ดยาวเหมือนเดิม)

# --- กราฟหลัก (Main Content) ---
if success:
    # --- กราฟเส้น (Line Chart) ---
    st.subheader("สถานการณ์ PM2.5 และจำนวนผู้เข้ารับการรักษา (รายเดือน)")
    if df_line is not None and not df_line.empty:
        labels_line = df_line['date'].dt.strftime('%b %Y').tolist()
        line_chart_html = f"""
            <canvas id="lineChart"></canvas>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <script>
                new Chart(document.getElementById('lineChart'), {{
                    type: 'line',
                    data: {{
                        labels: {labels_line},
                        datasets: [
                            {{ type: 'bar', label: 'PM2.5', data: {df_line['pm25_level'].tolist()}, backgroundColor: 'rgba(113, 113, 113, 0.3)', yAxisID: 'y1' }},
                            {{ label: 'ทางเดินหายใจ', data: {df_line['disease_group_1'].tolist()}, borderColor: '#ef4444', fill: false, tension: 0.4 }},
                            {{ label: 'ผิวหนังอักเสบ', data: {df_line['disease_group_2'].tolist()}, borderColor: '#f97316', fill: false, tension: 0.4 }},
                            {{ label: 'ตาอักเสบ', data: {df_line['disease_group_3'].tolist()}, borderColor: '#10b981', fill: false, tension: 0.4 }},
                            {{ label: 'หัวใจและหลอดเลือด', data: {df_line['disease_group_4'].tolist()}, borderColor: '#a855f7', fill: false, tension: 0.4 }}
                        ]
                    }},
                    options: {{
                        responsive: true, maintainAspectRatio: false,
                        scales: {{ y: {{ beginAtZero: true, position: 'left' }}, y1: {{ beginAtZero: true, position: 'right', grid: {{ drawOnChartArea: false }} }} }}
                    }}
                }});
            </script>
        """
        components.html(line_chart_html, height=400)

    # --- กราฟแท่ง (Bar Chart) ---
    st.subheader("จำนวนผู้ป่วยในแต่ละตำบล")
    if df_bar is not None and not df_bar.empty:
        # Sort values for better visualization
        df_bar = df_bar.sort_values('patient_count', ascending=False)
        labels_bar = df_bar['tambon'].tolist()
        data_bar = df_bar['patient_count'].tolist()
        bar_chart_html = f"""
            <div style="overflow-x: auto; height: 400px;">
                <div style="width: {len(labels_bar) * 60}px; height: 100%;">
                    <canvas id="barChart"></canvas>
                </div>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0"></script>
            <script>
                Chart.register(ChartDataLabels);
                new Chart(document.getElementById('barChart'), {{
                    type: 'bar',
                    data: {{ labels: {labels_bar}, datasets: [{{ data: {data_bar}, backgroundColor: '#4b5563' }}] }},
                    options: {{
                        maintainAspectRatio: false, responsive: true,
                        plugins: {{ legend: {{ display: false }}, datalabels: {{ anchor: 'end', align: 'top' }} }}
                    }}
                }});
            </script>
        """
        components.html(bar_chart_html, height=420)

