import streamlit as st
import pandas as pd
# NEW: Import Auto Refresh library
from streamlit_autorefresh import st_autorefresh
from data_loader import load_patient_data, load_pm25_data, load_lat_lon_data
from plots_main import (
    plot_patient_vs_pm25,
    plot_yearly_comparison,
    # NEW: Import the new specific ICD-10 trend function
    plot_specific_icd10_trend, 
)
from plots_correlation import plot_correlation_scatter
from plots_vulnerable import plot_vulnerable_dashboard
from plots_map import plot_patient_map
# NEW: Import the new re-attendance analysis function
from plots_revisit import plot_reattendance_rate
# NEW: Import the new patient timeline function
from plots_patient_timeline import plot_patient_timeline

# ----------------------------
# 🔧 CONFIG: Google Sheets URL
# ----------------------------
URL_PATIENT = (
    "https://docs.google.com/spreadsheets/d/1vvQ8YLChHXvCowQQzcKIeV4PWt0CCt76f5Sj3fNTOV0/export?format=csv&gid=795124395"
)
URL_PM25 = (
    "https://docs.google.com/spreadsheets/d/1vvQ8YLChHXvCowQQzcKIeV4PWt0CCt76f5Sj3fNTOV0/export?format=csv&gid=1038807599"
)
URL_LATLON = (
    "https://docs.google.com/spreadsheets/d/1vvQ8YLChHXvCowQQzcKIeV4PWt0CCt76f5Sj3fNTOV0/export?format=csv&gid=1769110594"
)

st.set_page_config(
    page_title="PM2.5 Surveillance Dashboard", 
    layout="wide",
    page_icon="🏥"
)

# ----------------------------
# 🎨 CUSTOM CSS & STYLING (UPDATED FOR DARK MODE)
# ----------------------------
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600&display=swap');
        
        /* เปลี่ยนฟอนต์ทั้งหน้าเป็น Kanit */
        html, body, [class*="css"] {
            font-family: 'Kanit', sans-serif;
        }
        
        /* ปรับแต่ง Header - ใช้ตัวแปรสีระบบเพื่อให้เข้ากับ Dark/Light Mode */
        h1, h2, h3 {
            font-weight: 600;
            color: var(--text-color); /* ปรับสีตาม Theme */
        }
        
        /* ตกแต่ง Metric Card (กล่องตัวเลข) - รองรับ Dark Mode */
        div[data-testid="stMetric"] {
            background-color: var(--secondary-background-color); /* ใช้สีพื้นหลังรองของ Theme (เทาอ่อนใน Light, เทาเข้มใน Dark) */
            border: 1px solid rgba(128, 128, 128, 0.2); /* ขอบจางๆ */
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        /* Label ของ Metric */
        div[data-testid="stMetric"] label {
            color: var(--text-color); 
            opacity: 0.8;
            font-size: 0.9rem;
        }
        
        /* ปรับแต่ง Sidebar */
        section[data-testid="stSidebar"] {
            /* ปล่อยให้สีพื้นหลังเป็นไปตาม Theme */
        }
        
        /* ปรับปุ่มใน Sidebar */
        div.stButton > button {
            width: 100%;
            border-radius: 8px;
            height: 3em;
            font-weight: 500;
        }
        
        /* ปรับแต่ง Info Box */
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
df_latlon = load_lat_lon_data(URL_LATLON)


if df_pat.empty:
    st.error("ไม่สามารถโหลดข้อมูลผู้ป่วยได้ กรุณาตรวจสอบ URL หรือการเชื่อมต่อ")
    st.stop()
else:
    # --- Data Transformation Logic ---
    condition1 = df_pat["4 กลุ่มโรคเฝ้าระวัง"] == "ไม่จัดอยู่ใน 4 กลุ่มโรค"
    condition2 = df_pat["Y96, Y97, Z58.1"] == "Z58.1"
    
    df_pat.loc[condition1 & condition2, "4 กลุ่มโรคเฝ้าระวัง"] = "แพทย์วินิจฉัยโรคร่วมด้วย Z58.1"
    
    df_pat = df_pat[df_pat["4 กลุ่มโรคเฝ้าระวัง"] != "ไม่จัดอยู่ใน 4 กลุ่มโรค"]

    # success message
    st.toast("✅ โหลดข้อมูลสำเร็จ", icon="🎉")

# ----------------------------
# 🎛 Sidebar Navigation Setup
# ----------------------------
PAGE_NAMES = [
    "📈 Dashboard ปัจจุบัน",
    "📅 มุมมองเปรียบเทียบรายปี",
    "🔗 วิเคราะห์ความสัมพันธ์",
    "📊 กลุ่มเปราะบาง",
    "🗺️ แผนที่",
    "⚠️ J44.0 (ปอดอุดกั้นเฉียบพลัน)",
    "🏥 การวิเคราะห์การมาซ้ำ", 
    "🕵️‍♀️ เส้นเวลาผู้ป่วยรายบุคคล" 
]

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2964/2964514.png", width=80) # Placeholder Icon
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

# Header Area with Styling
col_header, col_logo = st.columns([5, 1])
with col_header:
    st.title("Dashboards เฝ้าระวังสุขภาพ")
    st.markdown(f"### 👉 {page_selection}")

# --- Content Logic ---

if page_selection == "📈 Dashboard ปัจจุบัน":
    
    # --- Filter Section in a nice container ---
    with st.container():
        st.markdown("#### 🔍 ตัวกรองข้อมูล")
        if "เดือน" in df_pat.columns and "4 กลุ่มโรคเฝ้าระวัง" in df_pat.columns:
            months = sorted(df_pat["เดือน"].dropna().unique().tolist())
            gp_list = sorted(df_pat["4 กลุ่มโรคเฝ้าระวัง"].dropna().unique().tolist())
        
            col_m, col_g, col_l = st.columns([1, 1, 1])
            with col_m:
                month_sel = st.selectbox("📅 เลือกเดือน", ["ทั้งหมด"] + months, key="tab1_month_sel")
            with col_g:
                gp_sel = st.selectbox("เลือกกลุ่มโรค", ["ทั้งหมด"] + gp_list, key="tab1_gp_sel")
            with col_l:
                lag_options = {
                    "0 เดือน (เดือนเดียวกัน)": 0,
                    "1 เดือนก่อนหน้า": 1,
                    "2 เดือนก่อนหน้า": 2
                }
                lag_sel_name = st.selectbox("⏱️ PM2.5 แบบล่าช้า", list(lag_options.keys()), key="tab1_lag_sel")
                lag_months = lag_options[lag_sel_name]

            # Filter Data
            dff_tab1 = df_pat.copy()
            if month_sel != "ทั้งหมด":
                dff_tab1 = dff_tab1[dff_tab1["เดือน"] == month_sel]
            if gp_sel != "ทั้งหมด":
                dff_tab1 = dff_tab1[dff_tab1["4 กลุ่มโรคเฝ้าระวัง"] == gp_sel]
        else:
            dff_tab1 = df_pat.copy()
            st.error("ไม่พบคอลัมน์ที่จำเป็น")
            lag_months = 0

    st.markdown("---")
    # Plot
    plot_patient_vs_pm25(dff_tab1, df_pm, lag_months=lag_months) 

elif page_selection == "📅 มุมมองเปรียบเทียบรายปี":
    # --- KPI Cards (Enhanced Layout) ---
    df_merged_all = pd.merge(df_pat.groupby('เดือน').size().reset_index(name='count'), df_pm, on='เดือน', how='inner')
    
    if not df_merged_all.empty:
        max_pm_month = df_merged_all.loc[df_merged_all['PM2.5 (ug/m3)'].idxmax()]
        max_patient_month = df_merged_all.loc[df_merged_all['count'].idxmax()]
        avg_pm = df_merged_all['PM2.5 (ug/m3)'].mean()
        avg_patients = df_merged_all['count'].mean()

        st.markdown("#### 🏆 สรุปสถิติสำคัญ")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🌪️ เดือนที่ฝุ่นสูงสุด", f"{max_pm_month['เดือน']}", f"{max_pm_month['PM2.5 (ug/m3)']:.2f} µg/m³", delta_color="inverse")
        col2.metric("🤒 เดือนที่ป่วยสูงสุด", f"{max_patient_month['เดือน']}", f"{int(max_patient_month['count'])} คน", delta_color="inverse")
        col3.metric("📊 ค่าฝุ่นเฉลี่ย", f"{avg_pm:.2f}", "µg/m³")
        col4.metric("👥 ผู้ป่วยเฉลี่ย/เดือน", f"{int(avg_patients)}", "คน")
        st.markdown("---")
    
    plot_yearly_comparison(df_pat, df_pm)

elif page_selection == "🔗 วิเคราะห์ความสัมพันธ์":
    # Wrapper to control width or add explanation if needed
    plot_correlation_scatter(df_pat, df_pm)

elif page_selection == "📊 กลุ่มเปราะบาง":
    plot_vulnerable_dashboard(df_pat, df_pm, df_pat)

elif page_selection == "🗺️ แผนที่":
    plot_patient_map(df_pat, df_latlon)

elif page_selection == "⚠️ J44.0 (ปอดอุดกั้นเฉียบพลัน)":
    plot_specific_icd10_trend(
        df_pat=df_pat, 
        df_pm=df_pm, 
        icd10_code="J44.0", 
        disease_name="ปอดอุดกั้นเฉียบพลัน",
        icd10_column_name="ICD10ทั้งหมด"
    )

elif page_selection == "🏥 การวิเคราะห์การมาซ้ำ":
    st.markdown("#### ⚙️ ตั้งค่าการวิเคราะห์")
    col_input, col_desc = st.columns([1, 2])
    with col_input:
        lookback_days = st.number_input(
            "ระยะเวลา (วัน)",
            min_value=7,
            max_value=180,
            value=30,
            step=7,
            key="revisit_lookback"
        )
    with col_desc:
        st.info(f"ระบบจะนับจำนวนครั้งที่ผู้ป่วยคนเดิมกลับมาโรงพยาบาลภายใน **{lookback_days} วัน** หลังจากนัดครั้งก่อน")
    
    plot_reattendance_rate(df_pat, df_pm, lookback_days)

elif page_selection == "🕵️‍♀️ เส้นเวลาผู้ป่วยรายบุคคล":
    st.markdown("แสดงลำดับการเข้ารับบริการของ HN ที่เลือก เทียบกับค่า PM2.5 รายเดือน")

    if 'HN' in df_pat.columns and 'เดือน' in df_pat.columns:
        hn_visit_counts = df_pat['HN'].value_counts()
        meaningful_hns = hn_visit_counts[hn_visit_counts > 1].index.tolist()

        if not meaningful_hns:
            st.info("ℹ️ ไม่มีข้อมูลผู้ป่วยที่มีการเข้ารับบริการซ้ำ เพื่อใช้ในการวิเคราะห์เส้นเวลา")
        
        # --- 1. Identify Interesting HNs ---
        top_freq_hns = hn_visit_counts[hn_visit_counts > 1].head(5).index.tolist()
        
        high_pm_threshold = 50
        if 'PM2.5 (ug/m3)' in df_pm.columns:
            df_pm['PM2.5 (ug/m3)'] = pd.to_numeric(df_pm['PM2.5 (ug/m3)'], errors='coerce')
            high_pm_months = df_pm[df_pm['PM2.5 (ug/m3)'] >= high_pm_threshold]['เดือน'].tolist()
        else:
            high_pm_months = []
        
        hn_peak_counts = pd.Series(dtype='int64')
        if high_pm_months:
            df_peak_visits = df_pat[df_pat['เดือน'].isin(high_pm_months)]
            hn_peak_counts = df_peak_visits['HN'].value_counts()
        
        top_peak_hns = hn_peak_counts[hn_peak_counts > 1].head(5).index.tolist()

        # --- 2. Create Intelligent Selection List ---
        selection_options = {}
        selection_options["โปรดเลือก HN ผู้ป่วยที่ต้องการดูเส้นเวลา"] = "default"
        
        if top_freq_hns:
            selection_options["--- HN ที่มาบ่อยที่สุด (ความถี่สูงสุด) ---"] = "separator1"
            for hn in top_freq_hns:
                selection_options[f"✨ HN ที่มาบ่อยที่สุด: {hn} ({hn_visit_counts.get(hn, 0)} visits)"] = hn
            
        peak_hns_unique = [hn for hn in top_peak_hns if hn not in top_freq_hns]
        if peak_hns_unique:
            selection_options["--- HN ที่มาในช่วง PM2.5 พุ่งสูง (>{}) ---".format(high_pm_threshold)] = "separator2"
            for hn in peak_hns_unique:
                 selection_options[f"🚨 HN ที่มาช่วง PM2.5 พุ่ง: {hn} ({hn_peak_counts.get(hn, 0)} peak visits)"] = hn

        if meaningful_hns:
            selection_options["--- เลือก HN ด้วยตนเองจากรายการทั้งหมด ---"] = "separator3"
            for hn in meaningful_hns:
                selection_options[f"HN: {hn}"] = hn
        
        dropdown_keys = list(selection_options.keys())

        with st.container():
            st.markdown("#### 🔍 ค้นหา HN")
            selected_key = st.selectbox(
                "เลือก HN ตามเกณฑ์ที่แนะนำ หรือเลือกด้วยตนเอง",
                options=dropdown_keys,
                key="timeline_auto_select",
                label_visibility="collapsed"
            )
        
        selected_hn_to_plot = selection_options[selected_key]
        
        if selected_hn_to_plot in ["default", "separator1", "separator2", "separator3"]:
            st.info("👈 โปรดเลือก HN ผู้ป่วยจากเมนูด้านบน")
            selected_hn_to_plot = None

        st.markdown("---")

        if selected_hn_to_plot:
            st.success(f"กำลังแสดงเส้นเวลาสำหรับ HN: **{selected_hn_to_plot}**")
            plot_patient_timeline(df_pat, df_pm, selected_hn_to_plot)

    else:
        st.error("ไม่พบคอลัมน์ 'HN' หรือ 'เดือน' ในข้อมูลผู้ป่วย ไม่สามารถวิเคราะห์รายบุคคลได้")
