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
            # Calculate min and max dates from data for default range
            if "วันที่เข้ารับบริการ" in df_pat.columns and not df_pat.empty:
                min_date = df_pat["วันที่เข้ารับบริการ"].min().date()
                max_date = df_pat["วันที่เข้ารับบริการ"].max().date()
                
                date_range = st.date_input(
                    "📅 เลือกช่วงเวลา (วันเริ่มต้น - วันสิ้นสุด)",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date,
                    key="tab1_date_range"
                )
            else:
                st.error("ไม่พบคอลัมน์ 'วันที่เข้ารับบริการ' หรือข้อมูลว่างเปล่า")
                date_range = []

        with col_disease:
            gp_sel = st.selectbox("เลือกกลุ่มโรค", ["ทั้งหมด"] + gp_list, key="tab1_gp_sel")
            
        with col_vul: # NEW Column
            vul_sel = st.selectbox("เลือกกลุ่มเปราะบาง", ["ทั้งหมด"] + vul_list, key="tab1_vul_sel")
            
        with col_lag:
            lag_options = {
                "0 เดือน (เดือนเดียวกัน)": 0,
                "1 เดือนก่อนหน้า": 1,
                "2 เดือนก่อนหน้า": 2
            }
            lag_sel_name = st.selectbox("⏱️ PM2.5 แบบล่าช้า", list(lag_options.keys()), key="tab1_lag_sel")
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
             # Date Range (Full range usually better for correlation, but user might want to filter years)
            if "วันที่เข้ารับบริการ" in df_pat.columns and not df_pat.empty:
                min_date = df_pat["วันที่เข้ารับบริการ"].min().date()
                max_date = df_pat["วันที่เข้ารับบริการ"].max().date()
                corr_date_range = st.date_input(
                    "📅 เลือกช่วงเวลา",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date,
                    key="corr_date_range"
                )
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

        st.info("""
        **คำแนะนำในการอ่านค่า:**
        * **r / ρ > 0:** สัมพันธ์ทางบวก (PM2.5 สูง -> ป่วยเยอะ)
        * **p-value < 0.05:** เชื่อถือได้ทางสถิติ (โอกาสเกิดจากความบังเอิญน้อยกว่า 5%)
        * ถ้า Pearson ต่ำแต่ Spearman สูง อาจแปลว่ามีความสัมพันธ์แต่ไม่ใช่เส้นตรง (เช่น ต้องรอฝุ่นสูงระดับหนึ่งคนถึงจะเริ่มป่วย)
        """)
        
        st.divider()

        # --- PART 2: Scatter Plot ---
        st.subheader("2. แผนภาพการกระจาย (Scatter Plot)")
        
        # Build Title based on filters
        title_text = "ความสัมพันธ์: "
        if corr_gp_sel != "ทั้งหมด": title_text += f"กลุ่ม {corr_gp_sel} "
        if corr_vul_sel != "ทั้งหมด": title_text += f"({corr_vul_sel}) "
        title_text += "vs PM2.5"

        fig_scatter = px.scatter(
            df_analysis,
            x="PM2.5 (ug/m3)",
            y="จำนวนผู้ป่วย",
            trendline="ols",
            trendline_color_override="red",
            title=title_text,
            labels={"PM2.5 (ug/m3)": "ค่า PM2.5 (µg/m³)", "จำนวนผู้ป่วย": "จำนวนผู้ป่วย (คน)"},
            hover_data=['เดือน']
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
        
        st.divider()

        # --- PART 3: Optimal Lag Finder (With P-Value) ---
        st.subheader("3. การวิเคราะห์ผลกระทบย้อนหลัง (Lag Analysis)")
        st.markdown(f"ค้นหาระยะเวลาที่ฝุ่นส่งผลกระทบสูงสุด และ **มีนัยสำคัญทางสถิติ**")

        # Base Data Preparation
        df_pat_monthly = dff_corr.groupby('เดือน').size().reset_index(name='จำนวนผู้ป่วย')
        df_pat_monthly['เดือน'] = pd.to_datetime(df_pat_monthly['เดือน'])
        
        df_pm_base = df_pm[['เดือน', 'PM2.5 (ug/m3)']].copy()
        df_pm_base['เดือน'] = pd.to_datetime(df_pm_base['เดือน'])
        
        lag_results = []
        best_lag_info = None
        max_corr = -1
        
        for lag in range(7): # 0 to 6 months
            # Shift PM date forward by lag
            df_pm_shifted = df_pm_base.copy()
            df_pm_shifted['เดือน'] = df_pm_shifted['เดือน'] + pd.DateOffset(months=lag)
            
            # Merge on Month
            df_lag_merged = pd.merge(df_pat_monthly, df_pm_shifted, on='เดือน', how='inner')
            
            if len(df_lag_merged) > 2:
                # Calculate Pearson Correlation AND P-value
                r_lag, p_lag = pearsonr(df_lag_merged['PM2.5 (ug/m3)'], df_lag_merged['จำนวนผู้ป่วย'])
                
                sig_text = "✅" if p_lag < 0.05 else "❌"
                
                lag_results.append({
                    'Lag (เดือน)': str(lag), 
                    'ค่าความสัมพันธ์ (r)': r_lag,
                    'p-value': p_lag,
                    'Significance': sig_text
                })
                
                # Check for best SIGNIFICANT lag
                if p_lag < 0.05 and abs(r_lag) > max_corr:
                    max_corr = abs(r_lag)
                    best_lag_info = (lag, r_lag, p_lag)

        if lag_results:
            df_lags = pd.DataFrame(lag_results)
            
            # Plot
            fig_lag = px.bar(
                df_lags, 
                x='Lag (เดือน)', 
                y='ค่าความสัมพันธ์ (r)',
                title=f"ค่าความสัมพันธ์ (r) ที่ระยะเวลาต่างๆ (✅ = มีนัยสำคัญ p<0.05)",
                color='ค่าความสัมพันธ์ (r)',
                color_continuous_scale='Viridis',
                text='Significance', # Show Check/Cross on bar
                hover_data=['p-value']
            )
            fig_lag.update_traces(textposition='outside')
            fig_lag.update_layout(
                 paper_bgcolor='rgba(0,0,0,0)', 
                 plot_bgcolor='rgba(0,0,0,0)',
                 font=dict(family="Kanit, sans-serif")
            )
            st.plotly_chart(fig_lag, use_container_width=True)
            
            if best_lag_info:
                lag, r, p = best_lag_info
                st.success(f"💡 **ผลการวิเคราะห์:** ฝุ่น PM2.5 ส่งผลกระทบสูงสุดที่ **Lag {lag} เดือน** (r = {r:.4f}) อย่างมีนัยสำคัญ (p = {p:.4f})")
            else:
                # Fallback if no lag is significant
                top_row = df_lags.loc[df_lags['ค่าความสัมพันธ์ (r)'].abs().idxmax()]
                st.warning(f"⚠️ ไม่พบช่วงเวลาที่มีนัยสำคัญทางสถิติ (ค่าสูงสุดอยู่ที่ Lag {top_row['Lag (เดือน)']} แต่ p={top_row['p-value']:.4f})")
                
        else:
            st.warning("ข้อมูลไม่เพียงพอสำหรับการคำนวณ Lag")

elif page_selection == "📊 กลุ่มเปราะบาง":
    plot_vulnerable_dashboard(df_pat, df_pm, df_pat)

elif page_selection == "🗺️ แผนที่":
    st.markdown("#### 🗺️ การกระจายตัวของผู้ป่วยตามพื้นที่")
    
    # --- Filter Logic for Map ---
    with st.container():
        col_map_date, col_map_dis = st.columns([1.5, 1])
        with col_map_date:
            if "วันที่เข้ารับบริการ" in df_pat.columns and not df_pat.empty:
                min_d = df_pat["วันที่เข้ารับบริการ"].min().date()
                max_d = df_pat["วันที่เข้ารับบริการ"].max().date()
                map_date_range = st.date_input("📅 ช่วงเวลา (Map)", value=(min_d, max_d), min_value=min_d, max_value=max_d, key="map_date")
            else:
                map_date_range = []
        with col_map_dis:
            if "4 กลุ่มโรคเฝ้าระวัง" in df_pat.columns:
                map_gp_list = ["ทั้งหมด"] + sorted(df_pat["4 กลุ่มโรคเฝ้าระวัง"].dropna().unique().tolist())
                map_gp_sel = st.selectbox("เลือกกลุ่มโรค", map_gp_list, key="map_gp")
            else:
                map_gp_sel = "ทั้งหมด"

    # Apply Filters
    dff_map = df_pat.copy()
    if len(map_date_range) == 2:
        dff_map = dff_map[(dff_map["วันที่เข้ารับบริการ"].dt.date >= map_date_range[0]) & (dff_map["วันที่เข้ารับบริการ"].dt.date <= map_date_range[1])]
    elif len(map_date_range) == 1:
        dff_map = dff_map[dff_map["วันที่เข้ารับบริการ"].dt.date >= map_date_range[0]]
        
    if map_gp_sel != "ทั้งหมด":
        dff_map = dff_map[dff_map["4 กลุ่มโรคเฝ้าระวัง"] == map_gp_sel]

    # Layout: Map + Top Districts
    col_map_viz, col_map_stats = st.columns([3, 1])
    
    with col_map_viz:
        plot_patient_map(dff_map, df_latlon)
        
    with col_map_stats:
        st.markdown("##### 🏆 5 อันดับตำบลเสี่ยง")
        if not dff_map.empty and 'ตำบล' in dff_map.columns:
            top_districts = dff_map['ตำบล'].value_counts().head(5).reset_index()
            top_districts.columns = ['ตำบล', 'จำนวน (คน)']
            st.dataframe(top_districts, use_container_width=True, hide_index=True)
        else:
            st.info("ไม่มีข้อมูล")

elif page_selection == "⚠️ เจาะลึกรายโรค (ICD-10 Explorer)":
    st.markdown("#### 🕵️ เจาะลึกรายโรค (Specific Disease Discovery)")
    
    # --- Year Selection Logic ---
    dff_icd = df_pat.copy()
    selected_year_text = "ที่มีการเฝ้าระวังทั้งหมด"
    
    if "วันที่เข้ารับบริการ" in df_pat.columns and not df_pat.empty:
        # Get unique years sorted descending
        years = sorted(df_pat["วันที่เข้ารับบริการ"].dt.year.dropna().unique().tolist(), reverse=True)
        year_options = ["ทุกปี (All Years)"] + years
        
        col_year_sel, col_dummy = st.columns([1, 2])
        with col_year_sel:
            selected_year = st.selectbox("📅 เลือกปีที่ต้องการดูข้อมูล", year_options)
        
        # Filter Data by Year
        if selected_year != "ทุกปี (All Years)":
            dff_icd = dff_icd[dff_icd["วันที่เข้ารับบริการ"].dt.year == selected_year]
            selected_year_text = f"ปี {selected_year}"
            
    # Calculate Date Range for Caption
    if not dff_icd.empty and "วันที่เข้ารับบริการ" in dff_icd.columns:
        min_date = dff_icd["วันที่เข้ารับบริการ"].min().strftime('%d/%m/%Y')
        max_date = dff_icd["วันที่เข้ารับบริการ"].max().strftime('%d/%m/%Y')
        st.caption(f"แสดงข้อมูลโรคที่พบบ่อยในช่วง: **{min_date} - {max_date}**")
    else:
        st.caption("ค้นหาโรค (ICD-10) ที่พบบ่อยที่สุดในช่วงเวลาที่มีการเฝ้าระวัง")
    
    # 1. Discovery Logic: Find Top ICD-10 Codes
    if "ICD10ทั้งหมด" in dff_icd.columns and not dff_icd.empty:
        # Split codes (comma separated), explode to single rows, count
        all_codes = dff_icd['ICD10ทั้งหมด'].astype(str).str.split(',').explode().str.strip()
        # Remove empty or nan
        all_codes = all_codes[all_codes != 'nan']
        all_codes = all_codes[all_codes != '']
        
        if not all_codes.empty:
            top_codes = all_codes.value_counts().head(30) # Get Top 30
            
            # Create Selection List (Code + Count)
            code_options = top_codes.index.tolist()
            # Try to put J44.0 at the top if it exists (since it's important)
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
                    df_pat=dff_icd, # Pass the filtered dataframe
                    df_pm=df_pm, 
                    icd10_code=selected_icd, 
                    disease_name=f"ICD-10: {selected_icd}",
                    icd10_column_name="ICD10ทั้งหมด"
                )
        else:
             st.info(f"ไม่พบข้อมูลรหัสโรคใน{selected_year_text}")
            
    else:
        if dff_icd.empty:
             st.warning(f"ไม่พบข้อมูลผู้ป่วยใน{selected_year_text}")
        else:
             st.error("ไม่พบคอลัมน์ 'ICD10ทั้งหมด' ในข้อมูล")

elif page_selection == "🏥 การวิเคราะห์การมาซ้ำ":
    st.markdown("#### 🔍 ตัวกรองและตั้งค่าการวิเคราะห์")
    
    # --- Prepare Lists ---
    if "4 กลุ่มโรคเฝ้าระวัง" in df_pat.columns:
        gp_list = sorted(df_pat["4 กลุ่มโรคเฝ้าระวัง"].dropna().unique().tolist())
    else:
        gp_list = []
        
    if "กลุ่มเปราะบาง" in df_pat.columns:
        vul_list = sorted(df_pat["กลุ่มเปราะบาง"].dropna().unique().tolist())
    else:
        vul_list = []

    # --- Layout for Filters ---
    # Row 1: Date, Disease, Vulnerable
    col_r1_1, col_r1_2, col_r1_3 = st.columns([1.2, 1, 1])
    
    with col_r1_1:
        # Date Range
        if "วันที่เข้ารับบริการ" in df_pat.columns and not df_pat.empty:
            min_date = df_pat["วันที่เข้ารับบริการ"].min().date()
            max_date = df_pat["วันที่เข้ารับบริการ"].max().date()
            
            revisit_date_range = st.date_input(
                "📅 เลือกช่วงเวลา (วันเริ่มต้น - วันสิ้นสุด)",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key="revisit_date_range"
            )
        else:
            revisit_date_range = []
            
    with col_r1_2:
        revisit_gp_sel = st.selectbox("เลือกกลุ่มโรค", ["ทั้งหมด"] + gp_list, key="revisit_gp_sel")
        
    with col_r1_3:
        revisit_vul_sel = st.selectbox("เลือกกลุ่มเปราะบาง", ["ทั้งหมด"] + vul_list, key="revisit_vul_sel")

    # Row 2: Lookback Days & Info
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
        st.info(f"ℹ️ ระบบจะนับจำนวนครั้งที่ผู้ป่วยคนเดิมกลับมาโรงพยาบาลภายใน **{lookback_days} วัน** หลังจากนัดครั้งก่อน")
        
    # UPDATED CHECKBOX for Re-visit Analysis
    exclude_scheduled_revisit = st.checkbox(
        "🕵️ กรองผู้ป่วยที่มาตามนัด (Scheduled Visits) ออก", 
        value=False,
        key="revisit_exclude_scheduled",
        help="ระบบจะกรองข้อมูลโดยอ้างอิงจากคอลัมน์ 'ผู้ป่วยนัด' ในฐานข้อมูล (ตัดรายการที่เป็น 'True', '1', 'ใช่' หรือ 'นัด')"
    )

    # --- Filter Logic ---
    dff_revisit = df_pat.copy()
    
    # 0. Apply Scheduled Filter (UPDATED)
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

    # 1. Filter by Date Range
    if len(revisit_date_range) == 2:
        start_date, end_date = revisit_date_range
        dff_revisit = dff_revisit[
            (dff_revisit["วันที่เข้ารับบริการ"].dt.date >= start_date) & 
            (dff_revisit["วันที่เข้ารับบริการ"].dt.date <= end_date)
        ]
    elif len(revisit_date_range) == 1:
        start_date = revisit_date_range[0]
        dff_revisit = dff_revisit[dff_revisit["วันที่เข้ารับบริการ"].dt.date >= start_date]

    # 2. Filter by Disease Group
    if revisit_gp_sel != "ทั้งหมด":
        dff_revisit = dff_revisit[dff_revisit["4 กลุ่มโรคเฝ้าระวัง"] == revisit_gp_sel]

    # 3. Filter by Vulnerable Group
    if revisit_vul_sel != "ทั้งหมด":
        dff_revisit = dff_revisit[dff_revisit["กลุ่มเปราะบาง"] == revisit_vul_sel]

    st.markdown("---")
    
    # Call Plot Function with Filtered Data
    plot_reattendance_rate(dff_revisit, df_pm, lookback_days)
    
    # -----------------------------------------------------
    # NEW SECTION: Drill Down Table for Re-visiting Patients
    # -----------------------------------------------------
    st.markdown("### 📋 รายชื่อผู้ป่วยที่กลับมาซ้ำ (Drill Down)")
    st.caption("แสดงรายละเอียดการมาซ้ำของผู้ป่วยตามเงื่อนไขที่กรองด้านบน")

    # Calculate specific re-visit instances for the table
    # Note: We use dff_revisit (which is already filtered by date/group/scheduled)
    # But for calculation of 'diff days', we ideally need the previous visit even if it was outside the date range.
    # However, to be consistent with the plot logic which usually considers visible data, we'll use dff_revisit logic
    # but strictly speaking, correct 'revisit' calculation needs full history sorted.
    # Here, for simplicity and performance in the filtered view, we process the filtered dataframe.
    
    df_table = dff_revisit.copy()
    df_table = df_table.sort_values(by=['HN', 'วันที่เข้ารับบริการ'])
    
    # Calculate difference
    df_table['วันที่ครั้งก่อน'] = df_table.groupby('HN')['วันที่เข้ารับบริการ'].shift(1)
    df_table['ระยะห่าง(วัน)'] = (df_table['วันที่เข้ารับบริการ'] - df_table['วันที่ครั้งก่อน']).dt.days
    
    # Filter rows that match the lookback criteria (Re-visit)
    df_revisit_list = df_table[
        (df_table['ระยะห่าง(วัน)'] > 0) & 
        (df_table['ระยะห่าง(วัน)'] <= lookback_days)
    ].copy()
    
    if not df_revisit_list.empty:
        # Format dates for better display
        df_revisit_list['วันที่เข้ารับบริการ'] = df_revisit_list['วันที่เข้ารับบริการ'].dt.date
        df_revisit_list['วันที่ครั้งก่อน'] = df_revisit_list['วันที่ครั้งก่อน'].dt.date
        
        # Select columns to display
        cols_to_show = ['HN', 'วันที่เข้ารับบริการ', 'วันที่ครั้งก่อน', 'ระยะห่าง(วัน)', '4 กลุ่มโรคเฝ้าระวัง', 'กลุ่มเปราะบาง', 'ICD10ทั้งหมด']
        # Ensure columns exist
        final_cols = [c for c in cols_to_show if c in df_revisit_list.columns]
        
        st.write(f"พบการมาซ้ำทั้งหมด: **{len(df_revisit_list)}** ครั้ง (จากผู้ป่วย {df_revisit_list['HN'].nunique()} คน)")
        
        # Show interactive dataframe
        # Note: on_select is available in newer streamlit versions. 
        # If running on older version, this might need adjustment, but standard in current cloud runtimes.
        st.dataframe(
            df_revisit_list[final_cols],
            use_container_width=True,
            hide_index=True,
        )
        
        # --- Selector to jump to Timeline ---
        st.divider()
        st.markdown("#### 🔎 ดูประวัติการรักษา (Timeline) รายบุคคล")
        
        # Get unique HNs from the re-visit list
        revisit_hns = sorted(df_revisit_list['HN'].unique())
        
        col_sel_hn, col_dummy = st.columns([1, 2])
        with col_sel_hn:
            selected_drilldown_hn = st.selectbox(
                "เลือก HN จากรายชื่อด้านบนเพื่อดูกราฟ",
                options=["กรุณาเลือก HN"] + revisit_hns,
                key="drilldown_hn_selector"
            )
        
        if selected_drilldown_hn != "กรุณาเลือก HN":
            st.info(f"กำลังแสดง Timeline ของ HN: {selected_drilldown_hn}")
            # Pass the ORIGINAL full dataframe (df_pat) to see complete history, not just the filtered view
            plot_patient_timeline(df_pat, df_pm, selected_drilldown_hn)
            
    else:
        st.info("ไม่พบผู้ป่วยที่มาซ้ำตามเงื่อนไขและช่วงเวลาที่กำหนด")

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
