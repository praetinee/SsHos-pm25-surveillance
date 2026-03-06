import streamlit as st
import pandas as pd
import plotly.express as px # NEW: Import for internal plots
# NEW: Import Auto Refresh library
from streamlit_autorefresh import st_autorefresh
# NEW: Import Statistics libraries
from scipy.stats import pearsonr, spearmanr

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
    
    # 1. CLEANUP: Filter out future dates (ป้องกันข้อมูลปีผิด เช่น 2026 ที่ยังมาไม่ถึง)
    today = pd.Timestamp.now().normalize()
    future_data_mask = df_pat["วันที่เข้ารับบริการ"] > today
    if future_data_mask.any():
         future_count = future_data_mask.sum()
         # แจ้งเตือนเล็กน้อยว่ามีการตัดข้อมูลอนาคตออก
         st.toast(f"⚠️ พบข้อมูลวันที่ในอนาคต {future_count} รายการ (อาจเกิดจากปีผิด) ระบบได้กรองออกแล้ว", icon="🧹")
         df_pat = df_pat[~future_data_mask]

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
    "⚠️ เจาะลึกรายโรค (ICD-10 Explorer)", # REPLACED J44.0
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

# --- Content Logic ---

if page_selection == "📈 Dashboard ปัจจุบัน":
    
    # --- Filter Section in a nice container ---
    with st.container():
        st.markdown("#### 🔍 ตัวกรองข้อมูล")
        
        # Prepare lists for dropdowns
        # 1. Disease Groups
        if "4 กลุ่มโรคเฝ้าระวัง" in df_pat.columns:
            gp_list = sorted(df_pat["4 กลุ่มโรคเฝ้าระวัง"].dropna().unique().tolist())
        else:
            gp_list = []
            
        # 2. Vulnerable Groups (NEW)
        if "กลุ่มเปราะบาง" in df_pat.columns:
            vul_list = sorted(df_pat["กลุ่มเปราะบาง"].dropna().unique().tolist())
        else:
            vul_list = []
        
        # Adjust columns to fit 4 filters: Date(1.2) | Disease(1) | Vulnerable(1) | Lag(1)
        col_date, col_disease, col_vul, col_lag = st.columns([1.2, 1, 1, 1])
        
        with col_date:
            if "วันที่เข้ารับบริการ" in df_pat.columns and not df_pat.empty:
                min_date = df_pat["วันที่เข้ารับบริการ"].min().date()
                max_date = df_pat["วันที่เข้ารับบริการ"].max().date()
                
                st.write("📅 เลือกช่วงเวลา")
                c1, c2 = st.columns(2)
                with c1:
                    start_date = st.date_input("เริ่ม", value=min_date, min_value=min_date, max_value=max_date, key="tab1_start")
                with c2:
                    end_date = st.date_input("สิ้นสุด", value=max_date, min_value=min_date, max_value=max_date, key="tab1_end")
                    
                if start_date > end_date:
                    st.error("⚠️ วันที่เริ่มต้นต้องไม่เกินวันสิ้นสุด")
                    start_date, end_date = min_date, max_date
                
                # สร้าง list date_range ให้รองรับโค้ดด้านล่างที่ตรวจสอบ len(date_range)
                date_range = [start_date, end_date]
            else:
                st.error("ไม่พบคอลัมน์ 'วันที่เข้ารับบริการ' หรือข้อมูลว่างเปล่า")
                date_range = []

        with col_disease:
            gp_sel = st.selectbox("เลือกกลุ่มโรค", ["ทั้งหมด"] + gp_list, key="tab1_gp_sel")
            
        with col_vul: # NEW Column
            vul_sel = st.selectbox("เลือกกลุ่มเปราะบาง", ["ทั้งหมด"] + vul_list, key="tab1_vul_sel")
            
        with col_lag:
            # ตัดตัวเลือกล่วงหน้าออก เหลือแค่ก่อนหน้าและเดือนเดียวกัน
            lag_options = {
                "3 เดือนก่อนหน้า": 3,
                "2 เดือนก่อนหน้า": 2,
                "1 เดือนก่อนหน้า": 1,
                "0 เดือน (เดือนเดียวกัน)": 0
            }
            # ใช้ index=3 เพื่อให้ default เป็น "0 เดือน (เดือนเดียวกัน)"
            lag_sel_name = st.selectbox("⏱️ การเปรียบเทียบ PM2.5", list(lag_options.keys()), index=3, key="tab1_lag_sel")
            lag_months = lag_options[lag_sel_name]

        # UPDATED CHECKBOX: Filter Scheduled Visits using "ผู้ป่วยนัด" column
        exclude_scheduled = st.checkbox(
            "🕵️ กรองผู้ป่วยที่มาตามนัด (Scheduled Visits) ออก", 
            value=False,
            help="ระบบจะกรองข้อมูลโดยอ้างอิงจากคอลัมน์ 'ผู้ป่วยนัด' ในฐานข้อมูล (ตัดรายการที่เป็น 'True', '1', 'ใช่' หรือ 'นัด')"
        )

        # --- Filter Logic Implementation ---
        dff_tab1 = df_pat.copy()
        
        # 0. Base Data & Scheduled Logic Calculation (UPDATED)
        if exclude_scheduled:
            if "ผู้ป่วยนัด" in dff_tab1.columns:
                # สร้าง Mask เพื่อหาแถวที่เป็นผู้ป่วยนัด (Convert to string -> Lowercase -> Check values)
                # รองรับค่า: 'true', '1', 'yes', 'ใช่', 'นัด'
                scheduled_mask = dff_tab1["ผู้ป่วยนัด"].astype(str).str.strip().str.lower().isin(
                    ['true', '1', 'yes', 'ใช่', 'นัด', 'มาตามนัด']
                )
                
                removed_count = scheduled_mask.sum()
                dff_tab1 = dff_tab1[~scheduled_mask] # เก็บเฉพาะแถวที่ไม่ใช่ผู้ป่วยนัด
                
                if removed_count > 0:
                    st.toast(f"ระบบกรองข้อมูลออก {removed_count} รายการ (จากคอลัมน์ 'ผู้ป่วยนัด')", icon="🗑️")
            else:
                st.warning("⚠️ ไม่พบคอลัมน์ 'ผู้ป่วยนัด' ในข้อมูล กรุณาตรวจสอบชื่อคอลัมน์ใน Google Sheets")

        # 1. Filter by Date Range AND Prepare PM2.5 Filter
        df_pm_filtered = df_pm.copy() # Default to full data
        
        if len(date_range) == 2:
            start_date, end_date = date_range
            # Filter Patients
            dff_tab1 = dff_tab1[
                (dff_tab1["วันที่เข้ารับบริการ"].dt.date >= start_date) & 
                (dff_tab1["วันที่เข้ารับบริการ"].dt.date <= end_date)
            ]
            
            # Filter PM2.5 to match the selected range (Prevents graph from extending to future)
            # PM2.5 'เดือน' format is 'YYYY-MM'
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

        # 2. Filter by Disease Group
        if gp_sel != "ทั้งหมด":
            dff_tab1 = dff_tab1[dff_tab1["4 กลุ่มโรคเฝ้าระวัง"] == gp_sel]
            
        # 3. Filter by Vulnerable Group (NEW)
        if vul_sel != "ทั้งหมด":
            dff_tab1 = dff_tab1[dff_tab1["กลุ่มเปราะบาง"] == vul_sel]

    st.markdown("---")
    
    # Plot using filtered PM2.5 data
    plot_patient_vs_pm25(dff_tab1, df_pm_filtered, lag_months=lag_months) 

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
    # --- Unified Global Filter Section ---
    with st.container():
        st.markdown("#### 🔍 กำหนดเงื่อนไขสำหรับวิเคราะห์ความสัมพันธ์")
        
        # Lists for dropdowns
        if "4 กลุ่มโรคเฝ้าระวัง" in df_pat.columns:
            gp_list = sorted(df_pat["4 กลุ่มโรคเฝ้าระวัง"].dropna().unique().tolist())
        else:
            gp_list = []
        
        if "กลุ่มเปราะบาง" in df_pat.columns:
            vul_list = sorted(df_pat["กลุ่มเปราะบาง"].dropna().unique().tolist())
        else:
            vul_list = []

        # Layout: Date | Disease | Vulnerable
        col1, col2, col3 = st.columns([1.2, 1, 1])
        
        with col1:
             # Date Range (Split Input for better UX)
            if "วันที่เข้ารับบริการ" in df_pat.columns and not df_pat.empty:
                min_date = df_pat["วันที่เข้ารับบริการ"].min().date()
                max_date = df_pat["วันที่เข้ารับบริการ"].max().date()
                
                st.write("📅 เลือกช่วงเวลา")
                c1, c2 = st.columns(2)
                with c1:
                    start_date = st.date_input("เริ่ม", value=min_date, min_value=min_date, max_value=max_date, key="corr_start")
                with c2:
                    end_date = st.date_input("สิ้นสุด", value=max_date, min_value=min_date, max_value=max_date, key="corr_end")
                
                if start_date > end_date:
                    st.error("วันที่เริ่มต้นต้องไม่เกินวันสิ้นสุด")
                    start_date, end_date = min_date, max_date
                    
                corr_date_range = [start_date, end_date]
            else:
                corr_date_range = []

        with col2:
            corr_gp_sel = st.selectbox("เลือกกลุ่มโรค", ["ทั้งหมด"] + gp_list, key="corr_gp_sel")
        
        with col3:
            corr_vul_sel = st.selectbox("เลือกกลุ่มเปราะบาง", ["ทั้งหมด"] + vul_list, key="corr_vul_sel")

        # Checkbox
        exclude_scheduled_corr = st.checkbox(
            "🕵️ กรองผู้ป่วยที่มาตามนัด (Scheduled Visits) ออก", 
            value=False,
            key="corr_exclude_scheduled",
            help="ระบบจะกรองข้อมูลโดยอ้างอิงจากคอลัมน์ 'ผู้ป่วยนัด' ในฐานข้อมูล"
        )
    
    # --- Apply Filters ---
    dff_corr = df_pat.copy()
    
    # 1. Date
    if len(corr_date_range) == 2:
        dff_corr = dff_corr[
            (dff_corr["วันที่เข้ารับบริการ"].dt.date >= corr_date_range[0]) & 
            (dff_corr["วันที่เข้ารับบริการ"].dt.date <= corr_date_range[1])
        ]
    elif len(corr_date_range) == 1:
        dff_corr = dff_corr[dff_corr["วันที่เข้ารับบริการ"].dt.date >= corr_date_range[0]]
        
    # 2. Disease
    if corr_gp_sel != "ทั้งหมด":
        dff_corr = dff_corr[dff_corr["4 กลุ่มโรคเฝ้าระวัง"] == corr_gp_sel]
        
    # 3. Vulnerable
    if corr_vul_sel != "ทั้งหมด":
        dff_corr = dff_corr[dff_corr["กลุ่มเปราะบาง"] == corr_vul_sel]

    # 4. Scheduled
    if exclude_scheduled_corr:
        if "ผู้ป่วยนัด" in dff_corr.columns:
            scheduled_mask = dff_corr["ผู้ป่วยนัด"].astype(str).str.strip().str.lower().isin(
                ['true', '1', 'yes', 'ใช่', 'นัด', 'มาตามนัด']
            )
            dff_corr = dff_corr[~scheduled_mask]

    st.markdown("---")
    
    # --- Data Prep for Analysis ---
    # We need monthly aggregated data for correlation
    df_analysis = pd.merge(
        dff_corr.groupby('เดือน').size().reset_index(name='จำนวนผู้ป่วย'), 
        df_pm, on='เดือน', how='inner'
    )

    if len(df_analysis) < 3:
        st.warning(f"⚠️ ข้อมูลไม่เพียงพอสำหรับการวิเคราะห์ทางสถิติ (พบ {len(df_analysis)} เดือน)")
        st.caption("กรุณาขยายช่วงเวลา หรือ เลือกกลุ่มโรคที่มีข้อมูลมากขึ้น")
    else:
        # --- NEW SECTION: Statistical Metrics Calculation ---
        st.subheader("1. สรุปผลทางสถิติ (Statistical Summary)")
        
        # Calculate Statistics using Scipy
        x_data = df_analysis['PM2.5 (ug/m3)']
        y_data = df_analysis['จำนวนผู้ป่วย']
        
        # 1. Pearson (Linear)
        pearson_r, pearson_p = pearsonr(x_data, y_data)
        
        # 2. Spearman (Monotonic/Rank)
        spearman_rho, spearman_p = spearmanr(x_data, y_data)
        
        # Display Metrics
        col_stat1, col_stat2 = st.columns(2)
        
        with col_stat1:
            st.metric(
                label="Pearson Correlation (r) [ความสัมพันธ์เชิงเส้น]",
                value=f"{pearson_r:.4f}",
                delta=f"p-value: {pearson_p:.4f}",
                delta_color="off" if pearson_p > 0.05 else "normal",
                help="วัดความสัมพันธ์แบบเส้นตรง (-1 ถึง 1) เหมาะกับข้อมูลที่มีการกระจายตัวปกติ"
            )
            if pearson_p < 0.05:
                st.success(f"✅ มีนัยสำคัญทางสถิติ (p < 0.05)")
            else:
                st.warning(f"⚠️ ไม่มีนัยสำคัญทางสถิติ (p >= 0.05)")
                
        with col_stat2:
            st.metric(
                label="Spearman Correlation (ρ) [ความสัมพันธ์แบบลำดับ]",
                value=f"{spearman_rho:.4f}",
                delta=f"p-value: {spearman_p:.4f}",
                delta_color="off" if spearman_p > 0.05 else "normal",
                help="วัดความสัมพันธ์แบบทิศทางเดียวกัน (-1 ถึง 1) เหมาะกับข้อมูลที่ไม่เป็นเส้นตรง หรือมีค่าผิดปกติ (Outliers)"
            )
            if spearman_p < 0.05:
                st.success(f"✅ มีนัยสำคัญทางสถิติ (p < 0.05)")
            else:
                st.warning(f"⚠️ ไม่มีนัยสำคัญทางสถิติ (p >= 0.05)")

        # --- 🤖 AUTOMATED INTERPRETATION LOGIC (NEW) ---
        st.markdown("### 🤖 การแปลผลอัตโนมัติ (Automated Interpretation)")
        
        # 1. Decision Logic: Choose best metric to explain
        main_r = 0
        main_type = "N/A"
        is_sig = False
        
        if pearson_p < 0.05 and spearman_p < 0.05:
            # Both significant: Choose stronger one
            if abs(spearman_rho) > abs(pearson_r):
                main_r = spearman_rho
                main_type = "แบบลำดับ (Spearman)"
            else:
                main_r = pearson_r
                main_type = "เชิงเส้น (Pearson)"
            is_sig = True
        elif pearson_p < 0.05:
            main_r = pearson_r
            main_type = "เชิงเส้น (Pearson)"
            is_sig = True
        elif spearman_p < 0.05:
            main_r = spearman_rho
            main_type = "แบบลำดับ (Spearman)"
            is_sig = True
        else:
            # None significant
            is_sig = False

        # 2. Build Text Components (FIXED Logic: "Working Age" is NOT Vulnerable)
        target_group_text = f"กลุ่มโรค **{corr_gp_sel}**"
        
        if corr_vul_sel != "ทั้งหมด":
            # ตรวจสอบคำว่า "ผู้ใหญ่" หรือ "ทำงาน" เพื่อไม่ให้ใช้คำนำหน้าว่า "กลุ่มเปราะบาง"
            if "ผู้ใหญ่" in corr_vul_sel or "ทำงาน" in corr_vul_sel:
                target_group_text += f" ในกลุ่ม **{corr_vul_sel}**"
            else:
                target_group_text += f" เฉพาะกลุ่มเปราะบาง **{corr_vul_sel}**"
            
        interpretation_html = ""
        
        if not is_sig:
            interpretation_html = f"""
            <div style="background-color: var(--secondary-background-color); padding: 20px; border-radius: 10px; border-left: 5px solid #ff4b4b;">
                <h5 style="margin-top:0;">❌ ไม่พบความสัมพันธ์ที่มีนัยสำคัญทางสถิติ</h5>
                <p>จากการวิเคราะห์ข้อมูล {target_group_text} พบว่าการเปลี่ยนแปลงของค่า PM2.5 
                <b>ไม่มีความสัมพันธ์ที่ชัดเจน</b> กับจำนวนผู้ป่วยในช่วงเวลาเดียวกัน (p-value > 0
