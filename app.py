import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
from scipy.stats import pearsonr, spearmanr

# เอา load_lat_lon_data ออก เพราะไม่ใช้พิกัดแล้ว
from data_loader import load_patient_data, load_pm25_data
from plots_main import (
    plot_patient_vs_pm25,
    plot_yearly_comparison,
    plot_specific_icd10_trend, 
)
from plots_correlation import plot_correlation_scatter
from plots_vulnerable import plot_vulnerable_dashboard
from plots_revisit import plot_reattendance_rate

# ----------------------------
# 🛠️ HELPER FUNCTIONS: ตัวแปลง พ.ศ. สำหรับ UI
# ----------------------------
def date_to_be(d):
    """แปลง datetime.date เป็น พ.ศ. สำหรับแสดงบน UI"""
    if pd.isna(d) or d is None: return None
    try:
        return d.replace(year=d.year + 543)
    except ValueError: # กรณี 29 ก.พ. ในปีที่ไม่ใช่ปีอธิกสุรทินของ พ.ศ.
        return d.replace(year=d.year + 543, day=28)

def date_to_ce(d):
    """แปลงจาก UI (พ.ศ.) กลับมาเป็น ค.ศ. สำหรับประมวลผลหลังบ้าน"""
    if pd.isna(d) or d is None: return None
    try:
        return d.replace(year=d.year - 543)
    except ValueError:
        return d.replace(year=d.year - 543, day=28)

def format_month_be(yyyy_mm):
    """แปลงสตริง YYYY-MM เป็น พ.ศ. (เช่น 2024-01 -> 2567-01)"""
    if not isinstance(yyyy_mm, str) or len(yyyy_mm) != 7: return yyyy_mm
    try:
        y, m = yyyy_mm.split('-')
        return f"{int(y)+543}-{m}"
    except:
        return yyyy_mm

# ----------------------------
# 🔧 CONFIG: Google Sheets URL
# ----------------------------
URL_PATIENT = (
    "https://docs.google.com/spreadsheets/d/1vvQ8YLChHXvCowQQzcKIeV4PWt0CCt76f5Sj3fNTOV0/export?format=csv&gid=795124395"
)
URL_PM25 = (
    "https://docs.google.com/spreadsheets/d/1vvQ8YLChHXvCowQQzcKIeV4PWt0CCt76f5Sj3fNTOV0/export?format=csv&gid=1038807599"
)

st.set_page_config(
    page_title="PM2.5 Surveillance Dashboard", 
    layout="wide",
    page_icon="🏥"
)

# ----------------------------
# 🎨 CUSTOM CSS & STYLING
# ----------------------------
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Kanit', sans-serif;
        }
        
        h1, h2, h3 {
            font-weight: 600;
            color: var(--text-color); 
        }
        
        div[data-testid="stMetric"] {
            background-color: var(--secondary-background-color); 
            border: 1px solid rgba(128, 128, 128, 0.2); 
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        div[data-testid="stMetric"] label {
            color: var(--text-color); 
            opacity: 0.8;
            font-size: 0.9rem;
        }
        
        div.stButton > button {
            width: 100%;
            border-radius: 8px;
            height: 3em;
            font-weight: 500;
        }
        
        .stAlert {
            border-radius: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# ----------------------------
# 🔄 KEEP ALIVE LOGIC
# ----------------------------
st_autorefresh(interval=300000, key="keep_alive_refresh")

# --- Load Data ---
df_pat = load_patient_data(URL_PATIENT)
df_pm = load_pm25_data(URL_PM25)

if df_pat.empty:
    st.error("ไม่สามารถโหลดข้อมูลผู้ป่วยได้ กรุณาตรวจสอบ URL หรือการเชื่อมต่อ")
    st.stop()
else:
    # 1. CLEANUP: Filter out future dates
    today = pd.Timestamp.now().normalize()
    future_data_mask = df_pat["วันที่เข้ารับบริการ"] > today
    if future_data_mask.any():
         future_count = future_data_mask.sum()
         st.toast(f"⚠️ พบข้อมูลวันที่ในอนาคต {future_count} รายการ (อาจเกิดจากปีผิด) ระบบได้กรองออกแล้ว", icon="🧹")
         df_pat = df_pat[~future_data_mask]

    condition1 = df_pat["4 กลุ่มโรคเฝ้าระวัง"] == "ไม่จัดอยู่ใน 4 กลุ่มโรค"
    condition2 = df_pat["Y96, Y97, Z58.1"] == "Z58.1"
    
    df_pat.loc[condition1 & condition2, "4 กลุ่มโรคเฝ้าระวัง"] = "แพทย์วินิจฉัยโรคร่วมด้วย Z58.1"
    df_pat = df_pat[df_pat["4 กลุ่มโรคเฝ้าระวัง"] != "ไม่จัดอยู่ใน 4 กลุ่มโรค"]

    st.toast("✅ โหลดข้อมูลสำเร็จ", icon="🎉")

# ----------------------------
# 🎛 Sidebar Navigation Setup
# ----------------------------
PAGE_NAMES = [
    "📈 Dashboard ปัจจุบัน",
    "📅 มุมมองเปรียบเทียบรายปี",
    "🔗 วิเคราะห์ความสัมพันธ์",
    "📊 กลุ่มเปราะบาง",
    "📍 วิเคราะห์ระดับพื้นที่", 
    "⚠️ เจาะลึกรายโรค (ICD-10 Explorer)",
    "🏥 การวิเคราะห์การมาซ้ำ"
]

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2964/2964514.png", width=80)
    st.title("ระบบเฝ้าระวัง")
    st.caption("ผลกระทบต่อสุขภาพจาก PM2.5")
    st.markdown("---")
    st.header("📌 เมนูหลัก")

# Initialize session state
if 'page_selection' not in st.session_state:
    st.session_state['page_selection'] = PAGE_NAMES[0]

def navigate_to(page_name):
    st.session_state['page_selection'] = page_name

for page in PAGE_NAMES:
    button_style = 'primary' if st.session_state['page_selection'] == page else 'secondary'
    st.sidebar.button(
        page, 
        key=f"nav_{page}",
        on_click=navigate_to, 
        args=(page,),
        use_container_width=True,
        type=button_style
    )

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** ข้อมูลจะอัปเดตอัตโนมัติเมื่อ Google Sheets มีการเปลี่ยนแปลง")

page_selection = st.session_state['page_selection']

# ----------------------------
# 🎨 Main Panel
# ----------------------------

col_header, col_logo = st.columns([5, 1])
with col_header:
    st.title("Dashboards เฝ้าระวังสุขภาพ")

# --- Content Logic ---

if page_selection == "📈 Dashboard ปัจจุบัน":
    
    with st.container():
        st.markdown("#### 🔍 ตัวกรองข้อมูล")
        
        if "4 กลุ่มโรคเฝ้าระวัง" in df_pat.columns:
            gp_list = sorted(df_pat["4 กลุ่มโรคเฝ้าระวัง"].dropna().unique().tolist())
        else:
            gp_list = []
            
        if "กลุ่มเปราะบาง" in df_pat.columns:
            vul_list = sorted(df_pat["กลุ่มเปราะบาง"].dropna().unique().tolist())
        else:
            vul_list = []
        
        col_start, col_end, col_disease, col_vul, col_lag = st.columns([1, 1, 1.2, 1.2, 1.5])
        
        if "วันที่เข้ารับบริการ" in df_pat.columns and not df_pat.empty:
            min_date = df_pat["วันที่เข้ารับบริการ"].min().date()
            max_date = df_pat["วันที่เข้ารับบริการ"].max().date()
            # แปลงวันที่สำหรับโชว์ใน Date Picker เป็น พ.ศ.
            min_date_be = date_to_be(min_date)
            max_date_be = date_to_be(max_date)
        else:
            min_date_be = max_date_be = None

        with col_start:
            if min_date_be:
                start_date_be = st.date_input("📅 เริ่มต้น", value=min_date_be, min_value=min_date_be, max_value=max_date_be, key="tab1_start", format="DD/MM/YYYY")
                start_date = date_to_ce(start_date_be) # แปลงกลับเป็น ค.ศ. ไปใช้กรองข้อมูล
            else:
                start_date = None
        
        with col_end:
            if max_date_be:
                end_date_be = st.date_input("📅 สิ้นสุด", value=max_date_be, min_value=min_date_be, max_value=max_date_be, key="tab1_end", format="DD/MM/YYYY")
                end_date = date_to_ce(end_date_be)
            else:
                end_date = None

        if start_date and end_date:
            if start_date > end_date:
                st.error("⚠️ วันที่เริ่มต้นต้องไม่เกินวันสิ้นสุด")
                start_date, end_date = min_date, max_date
            date_range = [start_date, end_date]
        else:
            date_range = []

        with col_disease:
            gp_sel = st.selectbox("🩺 เลือกกลุ่มโรค", ["ทั้งหมด"] + gp_list, key="tab1_gp_sel")
            
        with col_vul:
            vul_sel = st.selectbox("🛡️ กลุ่มเปราะบาง", ["ทั้งหมด"] + vul_list, key="tab1_vul_sel")
            
        with col_lag:
            lag_options = {
                "3 เดือนก่อนหน้า": 3,
                "2 เดือนก่อนหน้า": 2,
                "1 เดือนก่อนหน้า": 1,
                "0 เดือน (เดือนเดียวกัน)": 0
            }
            lag_sel_name = st.selectbox("⏱️ การเปรียบเทียบ PM2.5", list(lag_options.keys()), index=3, key="tab1_lag_sel")
            lag_months = lag_options[lag_sel_name]

        exclude_scheduled = st.checkbox(
            "🕵️ กรองผู้ป่วยที่มาตามนัด (Scheduled Visits) ออก", 
            value=False,
            help="ระบบจะกรองข้อมูลโดยอ้างอิงจากคอลัมน์ 'ผู้ป่วยนัด' ในฐานข้อมูล"
        )

        dff_tab1 = df_pat.copy()
        
        if exclude_scheduled:
            if "ผู้ป่วยนัด" in dff_tab1.columns:
                scheduled_mask = dff_tab1["ผู้ป่วยนัด"].astype(str).str.strip().str.lower().isin(
                    ['true', '1', 'yes', 'ใช่', 'นัด', 'มาตามนัด']
                )
                removed_count = scheduled_mask.sum()
                dff_tab1 = dff_tab1[~scheduled_mask]
                
                if removed_count > 0:
                    st.toast(f"ระบบกรองข้อมูลออก {removed_count} รายการ (จากคอลัมน์ 'ผู้ป่วยนัด')", icon="🗑️")
            else:
                st.warning("⚠️ ไม่พบคอลัมน์ 'ผู้ป่วยนัด' ในข้อมูล กรุณาตรวจสอบชื่อคอลัมน์ใน Google Sheets")

        df_pm_filtered = df_pm.copy()
        
        if len(date_range) == 2:
            start_date, end_date = date_range
            dff_tab1 = dff_tab1[
                (dff_tab1["วันที่เข้ารับบริการ"].dt.date >= start_date) & 
                (dff_tab1["วันที่เข้ารับบริการ"].dt.date <= end_date)
            ]
            
            start_month_str = start_date.strftime('%Y-%m')
            end_month_str = end_date.strftime('%Y-%m')
            
            df_pm_filtered = df_pm[
                (df_pm['เดือน'] >= start_month_str) & 
                (df_pm['เดือน'] <= end_month_str)
            ]

        elif len(date_range) == 1:
            start_date = date_range[0]
            dff_tab1 = dff_tab1[dff_tab1["วันที่เข้ารับบริการ"].dt.date >= start_date]
            start_month_str = start_date.strftime('%Y-%m')
            df_pm_filtered = df_pm[df_pm['เดือน'] >= start_month_str]

        if gp_sel != "ทั้งหมด":
            dff_tab1 = dff_tab1[dff_tab1["4 กลุ่มโรคเฝ้าระวัง"] == gp_sel]
            
        if vul_sel != "ทั้งหมด":
            dff_tab1 = dff_tab1[dff_tab1["กลุ่มเปราะบาง"] == vul_sel]

    st.markdown("---")
    plot_patient_vs_pm25(dff_tab1, df_pm_filtered, lag_months=lag_months) 

elif page_selection == "📅 มุมมองเปรียบเทียบรายปี":
    df_merged_all = pd.merge(df_pat.groupby('เดือน').size().reset_index(name='count'), df_pm, on='เดือน', how='inner')
    
    if not df_merged_all.empty:
        max_pm_month = df_merged_all.loc[df_merged_all['PM2.5 (ug/m3)'].idxmax()]
        max_patient_month = df_merged_all.loc[df_merged_all['count'].idxmax()]
        avg_patients = df_merged_all['count'].mean()

        st.markdown("#### 🏆 สรุปสถิติสำคัญ")
        col1, col2, col3 = st.columns(3)
        # โชว์ Metric เดือนให้เป็น พ.ศ.
        col1.metric("🌪️ เดือนที่ฝุ่นสูงสุด", f"{format_month_be(max_pm_month['เดือน'])}", f"{max_pm_month['PM2.5 (ug/m3)']:.2f} µg/m³", delta_color="inverse")
        col2.metric("🤒 เดือนที่ป่วยสูงสุด", f"{format_month_be(max_patient_month['เดือน'])}", f"{int(max_patient_month['count'])} คน", delta_color="inverse")
        col3.metric("👥 ผู้ป่วยเฉลี่ย/เดือน", f"{int(avg_patients)}", "คน")
        st.markdown("---")
    
    plot_yearly_comparison(df_pat, df_pm)

elif page_selection == "🔗 วิเคราะห์ความสัมพันธ์":
    with st.container():
        st.markdown("#### 🔍 กำหนดเงื่อนไขสำหรับวิเคราะห์ความสัมพันธ์")

        col_start, col_end, col_chk = st.columns([1, 1, 2])
        
        if "วันที่เข้ารับบริการ" in df_pat.columns and not df_pat.empty:
            min_date = df_pat["วันที่เข้ารับบริการ"].min().date()
            max_date = df_pat["วันที่เข้ารับบริการ"].max().date()
            min_date_be = date_to_be(min_date)
            max_date_be = date_to_be(max_date)
        else:
            min_date_be = max_date_be = None

        with col_start:
            if min_date_be:
                start_date_be = st.date_input("📅 เริ่มต้น", value=min_date_be, min_value=min_date_be, max_value=max_date_be, key="corr_start", format="DD/MM/YYYY")
                start_date = date_to_ce(start_date_be)
            else:
                start_date = None
                
        with col_end:
            if max_date_be:
                end_date_be = st.date_input("📅 สิ้นสุด", value=max_date_be, min_value=min_date_be, max_value=max_date_be, key="corr_end", format="DD/MM/YYYY")
                end_date = date_to_ce(end_date_be)
            else:
                end_date = None
                
        if start_date and end_date:
            if start_date > end_date:
                st.error("วันที่เริ่มต้นต้องไม่เกินวันสิ้นสุด")
                start_date, end_date = min_date, max_date
            corr_date_range = [start_date, end_date]
        else:
            corr_date_range = []

        with col_chk:
            st.markdown("<br>", unsafe_allow_html=True)
            exclude_scheduled_corr = st.checkbox(
                "🕵️ กรองผู้ป่วยที่มาตามนัด (Scheduled Visits) ออก", 
                value=False,
                key="corr_exclude_scheduled",
                help="ระบบจะกรองข้อมูลโดยอ้างอิงจากคอลัมน์ 'ผู้ป่วยนัด' ในฐานข้อมูล"
            )
    
    dff_corr = df_pat.copy()
    
    if len(corr_date_range) == 2:
        dff_corr = dff_corr[
            (dff_corr["วันที่เข้ารับบริการ"].dt.date >= corr_date_range[0]) & 
            (dff_corr["วันที่เข้ารับบริการ"].dt.date <= corr_date_range[1])
        ]
    elif len(corr_date_range) == 1:
        dff_corr = dff_corr[dff_corr["วันที่เข้ารับบริการ"].dt.date >= corr_date_range[0]]

    if exclude_scheduled_corr:
        if "ผู้ป่วยนัด" in dff_corr.columns:
            scheduled_mask = dff_corr["ผู้ป่วยนัด"].astype(str).str.strip().str.lower().isin(
                ['true', '1', 'yes', 'ใช่', 'นัด', 'มาตามนัด']
            )
            dff_corr = dff_corr[~scheduled_mask]

    st.markdown("---")
    plot_correlation_scatter(dff_corr, df_pm)


elif page_selection == "📊 กลุ่มเปราะบาง":
    plot_vulnerable_dashboard(df_pat, df_pm, df_pat)

elif page_selection == "📍 วิเคราะห์ระดับพื้นที่":
    st.markdown("#### 📍 การกระจายตัวของผู้ป่วยตามพื้นที่ (จังหวัด/อำเภอ/ตำบล)")
    
    with st.container():
        st.markdown("##### 🔍 ตัวกรองข้อมูลพื้นที่")
        
        if "4 กลุ่มโรคเฝ้าระวัง" in df_pat.columns:
            map_gp_list = ["ทั้งหมด"] + sorted(df_pat["4 กลุ่มโรคเฝ้าระวัง"].dropna().unique().tolist())
        else:
            map_gp_list = ["ทั้งหมด"]
        
        col_start, col_end, col_disease = st.columns([1, 1, 2])
        
        if "วันที่เข้ารับบริการ" in df_pat.columns and not df_pat.empty:
            min_d = df_pat["วันที่เข้ารับบริการ"].min().date()
            max_d = df_pat["วันที่เข้ารับบริการ"].max().date()
            min_d_be = date_to_be(min_d)
            max_d_be = date_to_be(max_d)
        else:
            min_d_be = max_d_be = None

        with col_start:
            if min_d_be:
                start_date_be = st.date_input("📅 เริ่มต้น", value=min_d_be, min_value=min_d_be, max_value=max_d_be, key="map_start", format="DD/MM/YYYY")
                start_date = date_to_ce(start_date_be)
            else:
                start_date = None
        with col_end:
            if max_d_be:
                end_date_be = st.date_input("📅 สิ้นสุด", value=max_d_be, min_value=min_d_be, max_value=max_d_be, key="map_end", format="DD/MM/YYYY")
                end_date = date_to_ce(end_date_be)
            else:
                end_date = None
                
        if start_date and end_date:
            if start_date > end_date:
                st.error("วันที่เริ่มต้นต้องไม่เกินวันสิ้นสุด")
                start_date, end_date = min_d, max_d
            map_date_range = [start_date, end_date]
        else:
            map_date_range = []
            
        with col_disease:
            map_gp_sel = st.selectbox("🩺 เลือกกลุ่มโรค", map_gp_list, key="map_gp")

        dff_map = df_pat.copy()
        if len(map_date_range) == 2:
            dff_map = dff_map[(dff_map["วันที่เข้ารับบริการ"].dt.date >= map_date_range[0]) & (dff_map["วันที่เข้ารับบริการ"].dt.date <= map_date_range[1])]
        elif len(map_date_range) == 1:
            dff_map = dff_map[dff_map["วันที่เข้ารับบริการ"].dt.date >= map_date_range[0]]
            
        if map_gp_sel != "ทั้งหมด":
            dff_map = dff_map[dff_map["4 กลุ่มโรคเฝ้าระวัง"] == map_gp_sel]

        col_prov, col_amp, col_tam = st.columns(3)
        
        with col_prov:
            if "จังหวัด" in dff_map.columns:
                cleaned_prov = dff_map["จังหวัด"].dropna().astype(str).str.replace(r'^(จ\.|จังหวัด)\s*', '', regex=True).str.strip()
                dff_map.loc[cleaned_prov.index, "จังหวัด"] = cleaned_prov 
                prov_list = ["ทั้งหมด"] + sorted(cleaned_prov.unique().tolist())
                prov_sel = st.selectbox("📍 จังหวัด (พิมพ์ค้นหาได้)", prov_list, key="map_prov")
                if prov_sel != "ทั้งหมด":
                    dff_map = dff_map[dff_map["จังหวัด"] == prov_sel]
            else:
                st.selectbox("📍 จังหวัด", ["ไม่มีคอลัมน์ข้อมูล"], disabled=True)
        
        with col_amp:
            if "อำเภอ" in dff_map.columns:
                cleaned_amp = dff_map["อำเภอ"].dropna().astype(str).str.replace(r'^(อ\.|อำเภอ)\s*', '', regex=True).str.strip()
                dff_map.loc[cleaned_amp.index, "อำเภอ"] = cleaned_amp
                amp_list = ["ทั้งหมด"] + sorted(cleaned_amp.unique().tolist())
                amp_sel = st.selectbox("📍 อำเภอ (พิมพ์ค้นหาได้)", amp_list, key="map_amp")
                if amp_sel != "ทั้งหมด":
                    dff_map = dff_map[dff_map["อำเภอ"] == amp_sel]
            else:
                st.selectbox("📍 อำเภอ", ["ไม่มีคอลัมน์ข้อมูล"], disabled=True)
                
        with col_tam:
            if "ตำบล" in dff_map.columns:
                cleaned_tam = dff_map["ตำบล"].dropna().astype(str).str.replace(r'^(ต\.|ตำบล)\s*', '', regex=True).str.strip()
                dff_map.loc[cleaned_tam.index, "ตำบล"] = cleaned_tam
                tam_list = ["ทั้งหมด"] + sorted(cleaned_tam.unique().tolist())
                tam_sel = st.selectbox("📍 ตำบล (พิมพ์ค้นหาได้)", tam_list, key="map_tam")
                if tam_sel != "ทั้งหมด":
                    dff_map = dff_map[dff_map["ตำบล"] == tam_sel]
            else:
                st.selectbox("📍 ตำบล", ["ไม่มีคอลัมน์ข้อมูล"], disabled=True)

    st.markdown("---")

    if "ตำบล" in dff_map.columns and not dff_map.empty:
        col_chart, col_stats = st.columns([3, 1])
        tam_counts = dff_map['ตำบล'].value_counts().reset_index()
        tam_counts.columns = ['ตำบล', 'จำนวน (คน)']
        
        with col_chart:
            st.markdown("##### 📊 จำนวนผู้ป่วยรายตำบล")
            plot_data = tam_counts.sort_values('จำนวน (คน)', ascending=True)
            show_top_n = 20
            
            if len(plot_data) > show_top_n:
                st.caption(f"กำลังแสดงผลข้อมูล **{show_top_n} อันดับแรก** (จากทั้งหมด {len(tam_counts)} ตำบล)")
                plot_data = plot_data.tail(show_top_n)
            else:
                st.caption(f"แสดงข้อมูลทั้งหมด {len(tam_counts)} ตำบล")
                
            fig_bar = px.bar(
                plot_data,
                x='จำนวน (คน)',
                y='ตำบล',
                orientation='h',
                color='จำนวน (คน)',
                color_continuous_scale='Reds',
                text='จำนวน (คน)'
            )
            fig_bar.update_traces(textposition='outside')
            fig_bar.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Kanit, sans-serif"),
                coloraxis_showscale=False,
                margin=dict(l=0, r=30, t=30, b=0),
                xaxis_title="จำนวนผู้ป่วย (คน)",
                yaxis_title=""
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_stats:
            st.markdown("##### 🏆 อันดับความเสี่ยง")
            st.dataframe(tam_counts, use_container_width=True, hide_index=True, height=400)
    else:
        st.info("ไม่มีข้อมูลผู้ป่วยที่ตรงกับเงื่อนไขที่เลือก กรุณาลองปรับตัวกรองใหม่")

elif page_selection == "⚠️ เจาะลึกรายโรค (ICD-10 Explorer)":
    st.markdown("#### 🕵️ เจาะลึกรายโรค (Specific Disease Discovery)")
    
    dff_icd = df_pat.copy()
    
    if "4 กลุ่มโรคเฝ้าระวัง" in df_pat.columns:
        icd_gp_list = ["ทั้งหมด"] + sorted(df_pat["4 กลุ่มโรคเฝ้าระวัง"].dropna().unique().tolist())
    else:
        icd_gp_list = ["ทั้งหมด"]

    col_icd_gp, col_icd_yr = st.columns([1, 1])
    
    with col_icd_gp:
        selected_icd_group = st.selectbox("🩺 เลือกกลุ่มโรค", icd_gp_list, key="icd_group_sel")
        if selected_icd_group != "ทั้งหมด":
            dff_icd = dff_icd[dff_icd["4 กลุ่มโรคเฝ้าระวัง"] == selected_icd_group]

    selected_year_text = "ที่มีการเฝ้าระวังทั้งหมด"
    
    with col_icd_yr:
        if "วันที่เข้ารับบริการ" in dff_icd.columns and not dff_icd.empty:
            # ดึงปีที่เป็น ค.ศ. มาบวก 543 ให้เป็นตัวเลือก พ.ศ.
            years_ce = sorted(dff_icd["วันที่เข้ารับบริการ"].dt.year.dropna().unique().tolist(), reverse=True)
            year_options = ["ทุกปี (All Years)"] + [y + 543 for y in years_ce]
            
            selected_year_be = st.selectbox("📅 เลือกปีที่ต้องการดูข้อมูล", year_options, key="icd_year_sel")
            
            if selected_year_be != "ทุกปี (All Years)":
                selected_year_ce = selected_year_be - 543
                dff_icd = dff_icd[dff_icd["วันที่เข้ารับบริการ"].dt.year == selected_year_ce]
                selected_year_text = f"ปี {selected_year_be}"
        else:
             st.selectbox("📅 เลือกปีที่ต้องการดูข้อมูล", ["ไม่มีข้อมูลสำหรับกลุ่มโรคนี้"], disabled=True)
            
    if not dff_icd.empty and "วันที่เข้ารับบริการ" in dff_icd.columns:
        # แปลงข้อความคำอธิบายให้เป็น พ.ศ. ด้วย
        min_date_str = date_to_be(dff_icd["วันที่เข้ารับบริการ"].min().date()).strftime('%d/%m/%Y')
        max_date_str = date_to_be(dff_icd["วันที่เข้ารับบริการ"].max().date()).strftime('%d/%m/%Y')
        
        caption_text = f"แสดงข้อมูลโรคที่พบบ่อยในช่วง: **{min_date_str} - {max_date_str}**"
        if selected_icd_group != "ทั้งหมด":
            caption_text += f" (เฉพาะกลุ่ม: **{selected_icd_group}**)"
            
        st.caption(caption_text)
    else:
        st.caption("ค้นหาโรค (ICD-10) ที่พบบ่อยที่สุดในช่วงเวลาและกลุ่มโรคที่เลือก")
    
    if "ICD10ทั้งหมด" in dff_icd.columns and not dff_icd.empty:
        all_codes = dff_icd['ICD10ทั้งหมด'].astype(str).str.split(',').explode().str.strip()
        all_codes = all_codes[all_codes != 'nan']
        all_codes = all_codes[all_codes != '']
        
        if not all_codes.empty:
            top_codes = all_codes.value_counts().head(30)
            
            code_options = top_codes.index.tolist()
            if "J44.0" in code_options:
                code_options.remove("J44.0")
                code_options.insert(0, "J44.0")
                
            col_sel_icd, col_dummy = st.columns([1, 2])
            with col_sel_icd:
                selected_icd = st.selectbox(
                    "เลือก ICD-10 ที่ต้องการวิเคราะห์ (เรียงตามความถี่)", 
                    options=code_options,
                    format_func=lambda x: f"{x} (พบ {top_codes.get(x, 0)} ครั้ง)"
                )
                
            if selected_icd:
                plot_specific_icd10_trend(
                    df_pat=dff_icd,
                    df_pm=df_pm, 
                    icd10_code=selected_icd, 
                    disease_name=f"ICD-10: {selected_icd}",
                    icd10_column_name="ICD10ทั้งหมด"
                )
        else:
             st.info(f"ไม่พบข้อมูลรหัสโรคตามเงื่อนไขที่เลือก")
            
    else:
        if dff_icd.empty:
             st.warning(f"ไม่พบข้อมูลผู้ป่วยตามเงื่อนไขที่เลือก")
        else:
             st.error("ไม่พบคอลัมน์ 'ICD10ทั้งหมด' ในข้อมูล")

elif page_selection == "🏥 การวิเคราะห์การมาซ้ำ":
    st.markdown("#### 🔍 ตัวกรองและตั้งค่าการวิเคราะห์")
    
    if "4 กลุ่มโรคเฝ้าระวัง" in df_pat.columns:
        gp_list = sorted(df_pat["4 กลุ่มโรคเฝ้าระวัง"].dropna().unique().tolist())
    else:
        gp_list = []
        
    if "กลุ่มเปราะบาง" in df_pat.columns:
        vul_list = sorted(df_pat["กลุ่มเปราะบาง"].dropna().unique().tolist())
    else:
        vul_list = []

    col_start, col_end, col_disease, col_vul = st.columns([1, 1, 1.5, 1.5])
    
    if "วันที่เข้ารับบริการ" in df_pat.columns and not df_pat.empty:
        min_date = df_pat["วันที่เข้ารับบริการ"].min().date()
        max_date = df_pat["วันที่เข้ารับบริการ"].max().date()
        min_date_be = date_to_be(min_date)
        max_date_be = date_to_be(max_date)
    else:
        min_date_be = max_date_be = None

    with col_start:
        if min_date_be:
            start_date_be = st.date_input("📅 เริ่มต้น", value=min_date_be, min_value=min_date_be, max_value=max_date_be, key="rev_start", format="DD/MM/YYYY")
            start_date = date_to_ce(start_date_be)
        else:
            start_date = None
    with col_end:
        if max_date_be:
            end_date_be = st.date_input("📅 สิ้นสุด", value=max_date_be, min_value=min_date_be, max_value=max_date_be, key="rev_end", format="DD/MM/YYYY")
            end_date = date_to_ce(end_date_be)
        else:
            end_date = None
            
    if start_date and end_date:
        if start_date > end_date:
            st.error("วันที่เริ่มต้นต้องไม่เกินวันสิ้นสุด")
            start_date, end_date = min_date, max_date
        revisit_date_range = [start_date, end_date]
    else:
        revisit_date_range = []
            
    with col_disease:
        revisit_gp_sel = st.selectbox("🩺 เลือกกลุ่มโรค", ["ทั้งหมด"] + gp_list, key="revisit_gp_sel")
        
    with col_vul:
        revisit_vul_sel = st.selectbox("🛡️ กลุ่มเปราะบาง", ["ทั้งหมด"] + vul_list, key="revisit_vul_sel")

    col_r2_1, col_r2_2 = st.columns([1, 2])
    with col_r2_1:
        lookback_days = st.number_input(
            "⚙️ ระยะเวลาการมาซ้ำ (วัน)",
            min_value=7,
            max_value=180,
            value=30,
            step=7,
            key="revisit_lookback"
        )
    with col_r2_2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.info(f"ℹ️ ระบบจะนับจำนวนครั้งที่ผู้ป่วยคนเดิมกลับมาโรงพยาบาลภายใน **{lookback_days} วัน** หลังจากนัดครั้งก่อน")
        
    exclude_scheduled_revisit = st.checkbox(
        "🕵️ กรองผู้ป่วยที่มาตามนัด (Scheduled Visits) ออก", 
        value=False,
        key="revisit_exclude_scheduled",
        help="ระบบจะกรองข้อมูลโดยอ้างอิงจากคอลัมน์ 'ผู้ป่วยนัด' ในฐานข้อมูล"
    )

    dff_revisit = df_pat.copy()
    
    if exclude_scheduled_revisit:
        if "ผู้ป่วยนัด" in dff_revisit.columns:
            scheduled_mask = dff_revisit["ผู้ป่วยนัด"].astype(str).str.strip().str.lower().isin(
                ['true', '1', 'yes', 'ใช่', 'นัด', 'มาตามนัด']
            )
            
            removed_count = scheduled_mask.sum()
            dff_revisit = dff_revisit[~scheduled_mask]
            
            if removed_count > 0:
                st.toast(f"ระบบกรองผู้ป่วยนัดออก {removed_count} รายการ", icon="🗑️")
        else:
            st.warning("⚠️ ไม่พบคอลัมน์ 'ผู้ป่วยนัด' ในข้อมูล")

    if len(revisit_date_range) == 2:
        start_date, end_date = revisit_date_range
        dff_revisit = dff_revisit[
            (dff_revisit["วันที่เข้ารับบริการ"].dt.date >= start_date) & 
            (dff_revisit["วันที่เข้ารับบริการ"].dt.date <= end_date)
        ]
    elif len(revisit_date_range) == 1:
        start_date = revisit_date_range[0]
        dff_revisit = dff_revisit[dff_revisit["วันที่เข้ารับบริการ"].dt.date >= start_date]

    if revisit_gp_sel != "ทั้งหมด":
        dff_revisit = dff_revisit[dff_revisit["4 กลุ่มโรคเฝ้าระวัง"] == revisit_gp_sel]

    if revisit_vul_sel != "ทั้งหมด":
        dff_revisit = dff_revisit[dff_revisit["กลุ่มเปราะบาง"] == revisit_vul_sel]

    st.markdown("---")
    
    plot_reattendance_rate(dff_revisit, df_pm, lookback_days)
    
    st.markdown("### 📋 รายชื่อผู้ป่วยที่กลับมาซ้ำ (Drill Down)")
    st.caption("แสดงรายละเอียดการมาซ้ำของผู้ป่วยตามเงื่อนไขที่กรองด้านบน")

    df_table = dff_revisit.copy()
    df_table = df_table.sort_values(by=['HN', 'วันที่เข้ารับบริการ'])
    
    df_table['วันที่ครั้งก่อน'] = df_table.groupby('HN')['วันที่เข้ารับบริการ'].shift(1)
    df_table['ระยะห่าง(วัน)'] = (df_table['วันที่เข้ารับบริการ'] - df_table['วันที่ครั้งก่อน']).dt.days
    
    df_revisit_list = df_table[
        (df_table['ระยะห่าง(วัน)'] > 0) & 
        (df_table['ระยะห่าง(วัน)'] <= lookback_days)
    ].copy()
    
    if not df_revisit_list.empty:
        # แปลงข้อมูลวันแสดงในตารางให้เป็น พ.ศ.
        df_revisit_list['วันที่เข้ารับบริการ'] = df_revisit_list['วันที่เข้ารับบริการ'].dt.date.apply(lambda d: date_to_be(d).strftime('%d/%m/%Y') if d else None)
        df_revisit_list['วันที่ครั้งก่อน'] = df_revisit_list['วันที่ครั้งก่อน'].dt.date.apply(lambda d: date_to_be(d).strftime('%d/%m/%Y') if d else None)
        
        cols_to_show = ['HN', 'วันที่เข้ารับบริการ', 'วันที่ครั้งก่อน', 'ระยะห่าง(วัน)', '4 กลุ่มโรคเฝ้าระวัง', 'กลุ่มเปราะบาง', 'ICD10ทั้งหมด']
        final_cols = [c for c in cols_to_show if c in df_revisit_list.columns]
        
        st.write(f"พบการมาซ้ำทั้งหมด: **{len(df_revisit_list)}** ครั้ง (จากผู้ป่วย {df_revisit_list['HN'].nunique()} คน)")
        
        st.dataframe(
            df_revisit_list[final_cols],
            use_container_width=True,
            hide_index=True,
        )
            
    else:
        st.info("ไม่พบผู้ป่วยที่มาซ้ำตามเงื่อนไขและช่วงเวลาที่กำหนด")
