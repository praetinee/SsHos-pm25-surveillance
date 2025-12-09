import streamlit as st
import pandas as pd
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

st.set_page_config(page_title="PM2.5 Surveillance Dashboard", layout="wide")

# --- Load Data ---
df_pat = load_patient_data(URL_PATIENT)
df_pm = load_pm25_data(URL_PM25)
df_latlon = load_lat_lon_data(URL_LATLON)


if df_pat.empty:
    st.error("ไม่สามารถโหลดข้อมูลผู้ป่วยได้ กรุณาตรวจสอบ URL หรือการเชื่อมต่อ")
    st.stop()
else:
    # --- Data Transformation Logic ---
    # Define conditions for the new category
    condition1 = df_pat["4 กลุ่มโรคเฝ้าระวัง"] == "ไม่จัดอยู่ใน 4 กลุ่มโรค"
    condition2 = df_pat["Y96, Y97, Z58.1"] == "Z58.1"
    
    # Apply the new category where both conditions are met
    df_pat.loc[condition1 & condition2, "4 กลุ่มโรคเฝ้าระวัง"] = "แพทย์วินิจฉัยโรคร่วมด้วย Z58.1"
    
    # NEW FILTERING LOGIC: Remove patients NOT in the 4 surveillance groups for all subsequent analysis.
    # This ensures that the primary groups are the focus of the dashboard.
    df_pat = df_pat[df_pat["4 กลุ่มโรคเฝ้าระวัง"] != "ไม่จัดอยู่ใน 4 กลุ่มโรค"]

    st.success("✅ โหลดข้อมูลสำเร็จ")

# ----------------------------
# 🎛 Sidebar Navigation Setup
# ----------------------------
# List of all "pages" (formerly tabs)
PAGE_NAMES = [
    "📈 Dashboard ปัจจุบัน",
    "📅 มุมมองเปรียบเทียบรายปี",
    "🔗 วิเคราะห์ความสัมพันธ์",
    "📊 กลุ่มเปราะบาง",
    "🗺️ แผนที่",
    "⚠️ J44.0 (ปอดอุดกั้นเฉียบพลัน)",
    "🏥 การวิเคราะห์การมาซ้ำ", 
    "🕵️‍♀️ เส้นเวลาผู้ป่วยรายบุคคล" # NEW Page
]

st.sidebar.header("🗺️ เมนูหลัก")

# Initialize session state for navigation if not set
if 'page_selection' not in st.session_state:
    st.session_state['page_selection'] = PAGE_NAMES[0]

# Create function to handle button click
def navigate_to(page_name):
    st.session_state['page_selection'] = page_name

# Use buttons for main navigation
for page in PAGE_NAMES:
    button_style = 'primary' if st.session_state['page_selection'] == page else 'secondary'
    
    # Use st.button with the desired key and callback function
    st.sidebar.button(
        page, 
        key=f"nav_{page}",
        on_click=navigate_to, 
        args=(page,),
        use_container_width=True,
        # Adding a little style/color hint for the selected page
        type=button_style
    )

page_selection = st.session_state['page_selection']

# Removed Placeholder info for the old filter location
# st.sidebar.markdown("---")
# st.sidebar.info("ตัวกรองสำหรับ Dashboard ปัจจุบัน ย้ายไปอยู่ในหน้าหลักแล้ว")

# ----------------------------
# 🎨 Main Panel
# ----------------------------
st.title("Dashboards เฝ้าระวังผลกระทบต่อสุขภาพจาก PM2.5")


# --- Content Logic based on Sidebar Selection (replaces st.tabs) ---

if page_selection == "📈 Dashboard ปัจจุบัน":
    st.header("แนวโน้มผู้ป่วยเทียบกับค่า PM2.5")
    
    # --- Local Filter for Dashboard Tab (Content of former tab1) ---
    if "เดือน" in df_pat.columns and "4 กลุ่มโรคเฝ้าระวัง" in df_pat.columns:
        months = sorted(df_pat["เดือน"].dropna().unique().tolist())
        gp_list = sorted(df_pat["4 กลุ่มโรคเฝ้าระวัง"].dropna().unique().tolist())
    
        # Display filters side-by-side with a new column for lag
        col_m, col_g, col_l = st.columns([1, 1, 1]) # Adjusted column layout
        with col_m:
            month_sel = st.selectbox("เลือกเดือน", ["ทั้งหมด"] + months, key="tab1_month_sel")
        with col_g:
            gp_sel = st.selectbox("เลือกกลุ่มโรค", ["ทั้งหมด"] + gp_list, key="tab1_gp_sel")
        with col_l: # New column for Lag selection
            lag_options = {
                "0 เดือน (เดือนเดียวกัน)": 0,
                "1 เดือนก่อนหน้า": 1,
                "2 เดือนก่อนหน้า": 2
            }
            lag_sel_name = st.selectbox("เลือกค่า PM2.5 แบบล่าช้า", list(lag_options.keys()), key="tab1_lag_sel")
            lag_months = lag_options[lag_sel_name]

        # Create Filtered Data (dff_tab1)
        dff_tab1 = df_pat.copy()
        if month_sel != "ทั้งหมด":
            dff_tab1 = dff_tab1[dff_tab1["เดือน"] == month_sel]
        if gp_sel != "ทั้งหมด":
            dff_tab1 = dff_tab1[dff_tab1["4 กลุ่มโรคเฝ้าระวัง"] == gp_sel]
    else:
        dff_tab1 = df_pat.copy() # Fallback
        st.error("ไม่พบคอลัมน์ที่จำเป็น (เดือน, 4 กลุ่มโรคเฝ้าระวัง) ในข้อมูล")
        lag_months = 0 # Default lag

    # Plot using the locally filtered data
    # UPDATED: Pass lag_months parameter
    plot_patient_vs_pm25(dff_tab1, df_pm, lag_months=lag_months) 

elif page_selection == "📅 มุมมองเปรียบเทียบรายปี":
    st.header("เปรียบเทียบข้อมูลแบบปีต่อปี (Year-over-Year)")
    
    # --- KPI Cards (Content of former tab2) ---
    df_merged_all = pd.merge(df_pat.groupby('เดือน').size().reset_index(name='count'), df_pm, on='เดือน', how='inner')
    
    if not df_merged_all.empty:
        max_pm_month = df_merged_all.loc[df_merged_all['PM2.5 (ug/m3)'].idxmax()]
        max_patient_month = df_merged_all.loc[df_merged_all['count'].idxmax()]
        avg_pm = df_merged_all['PM2.5 (ug/m3)'].mean()
        avg_patients = df_merged_all['count'].mean()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("เดือนที่ค่าฝุ่นสูงสุด", f"{max_pm_month['เดือน']}", f"{max_pm_month['PM2.5 (ug/m3)']:.2f} µg/m³")
        col2.metric("เดือนที่ผู้ป่วยสูงสุด", f"{max_patient_month['เดือน']}", f"{int(max_patient_month['count'])} คน")
        col3.metric("ค่าฝุ่นเฉลี่ย", f"{avg_pm:.2f} µg/m³")
        col4.metric("ผู้ป่วยเฉลี่ย/เดือน", f"{int(avg_patients)} คน")
    
    plot_yearly_comparison(df_pat, df_pm)

elif page_selection == "🔗 วิเคราะห์ความสัมพันธ์":
    st.header("ความสัมพันธ์ระหว่างค่า PM2.5 และจำนวนผู้ป่วยรวม")
    # Content of former tab3
    plot_correlation_scatter(df_pat, df_pm)

elif page_selection == "📊 กลุ่มเปราะบาง":
    st.header("การวิเคราะห์เชิงลึกสำหรับกลุ่มเปราะบาง")
    # Content of former tab4
    # Note: df_pat is used as the filtered data in this context after previous refactoring.
    plot_vulnerable_dashboard(df_pat, df_pm, df_pat)

elif page_selection == "🗺️ แผนที่":
    st.header("แผนที่แสดงการกระจายตัวของผู้ป่วยในระดับตำบล")
    # Content of former tab5
    plot_patient_map(df_pat, df_latlon)

elif page_selection == "⚠️ J44.0 (ปอดอุดกั้นเฉียบพลัน)":
    st.header("แนวโน้มผู้ป่วยปอดอุดกั้นเฉียบพลัน (J44.0) เทียบกับค่า PM2.5")
    # Content of former tab6
    plot_specific_icd10_trend(
        df_pat=df_pat, 
        df_pm=df_pm, 
        icd10_code="J44.0", 
        disease_name="ปอดอุดกั้นเฉียบพลัน",
        icd10_column_name="ICD10ทั้งหมด"
    )

elif page_selection == "🏥 การวิเคราะห์การมาซ้ำ": # Content Block
    st.header("อัตราการมาซ้ำ (Re-attendance) ของผู้ป่วย")
    st.markdown("การวิเคราะห์ความถี่ที่ผู้ป่วยเดิมกลับมาเข้ารับบริการภายในระยะเวลาที่กำหนด")
    
    # Control for lookback days
    lookback_days = st.number_input(
        "ระบุระยะเวลาที่ถือว่าเป็นการมาซ้ำ (วัน)",
        min_value=7,
        max_value=180,
        value=30,
        step=7,
        key="revisit_lookback"
    )
    
    # Call the new plotting function
    plot_reattendance_rate(df_pat, df_pm, lookback_days)

elif page_selection == "🕵️‍♀️ เส้นเวลาผู้ป่วยรายบุคคล": # NEW Content Block
    st.header("เส้นเวลาการเข้ารับบริการของ HN รายบุคคล")
    st.markdown("แสดงลำดับการเข้ารับบริการของ HN ที่เลือก เทียบกับค่า PM2.5 รายเดือน")

    if 'HN' in df_pat.columns and 'เดือน' in df_pat.columns:
        # Get list of HNs who have more than one visit
        hn_visit_counts = df_pat['HN'].value_counts()
        meaningful_hns = hn_visit_counts[hn_visit_counts > 1].index.tolist()

        if not meaningful_hns:
            st.info("ℹ️ ไม่มีข้อมูลผู้ป่วยที่มีการเข้ารับบริการซ้ำ เพื่อใช้ในการวิเคราะห์เส้นเวลา")
            # st.stop() # Removed st.stop() to allow the rest of the dashboard to function
        
        # --- 1. Identify Interesting HNs ---
        
        # A. Top 5 Most Frequent Visitors
        top_freq_hns = hn_visit_counts[hn_visit_counts > 1].head(5).index.tolist()
        
        # B. Identify HNs visiting during high PM2.5 months (Threshold > 50)
        high_pm_threshold = 50
        # Check if PM2.5 column exists and is numeric before filtering
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
        
        # Prepare dropdown options
        selection_options = {}
        
        # Add a default instruction option
        selection_options["โปรดเลือก HN ผู้ป่วยที่ต้องการดูเส้นเวลา"] = "default"
        
        # Category 1: Top Frequent Visitors
        if top_freq_hns:
            selection_options["--- HN ที่มาบ่อยที่สุด (ความถี่สูงสุด) ---"] = "separator1"
            for hn in top_freq_hns:
                selection_options[f"✨ HN ที่มาบ่อยที่สุด: {hn} ({hn_visit_counts.get(hn, 0)} visits)"] = hn
            
        # Category 2: Peak Exposure (Avoid duplicates from Category 1)
        peak_hns_unique = [hn for hn in top_peak_hns if hn not in top_freq_hns]
        if peak_hns_unique:
            selection_options["--- HN ที่มาในช่วง PM2.5 พุ่งสูง (>{}) ---".format(high_pm_threshold)] = "separator2"
            for hn in peak_hns_unique:
                 selection_options[f"🚨 HN ที่มาช่วง PM2.5 พุ่ง: {hn} ({hn_peak_counts.get(hn, 0)} peak visits)"] = hn

        # Category 3: Manual Selection (All meaningful HNs)
        if meaningful_hns:
            selection_options["--- เลือก HN ด้วยตนเองจากรายการทั้งหมด ---"] = "separator3"
            for hn in meaningful_hns:
                selection_options[f"HN: {hn}"] = hn
        
        # Combine keys for the dropdown
        dropdown_keys = list(selection_options.keys())

        st.subheader("🕵️‍♀️ เลือก HN ผู้ป่วยเพื่อดูเส้นเวลา")
        
        # Single dropdown for selection
        selected_key = st.selectbox(
            "เลือก HN ตามเกณฑ์ที่แนะนำ หรือเลือกด้วยตนเอง",
            options=dropdown_keys,
            key="timeline_auto_select"
        )
        
        selected_hn_to_plot = selection_options[selected_key]
        
        # Filter out separators and default instruction
        if selected_hn_to_plot in ["default", "separator1", "separator2", "separator3"]:
            st.info("โปรดเลือก HN ผู้ป่วยที่ต้องการวิเคราะห์")
            selected_hn_to_plot = None

        st.markdown("---")

        if selected_hn_to_plot:
            st.success(f"กำลังแสดงเส้นเวลาสำหรับ HN: **{selected_hn_to_plot}**")
            plot_patient_timeline(df_pat, df_pm, selected_hn_to_plot)

    else:
        st.error("ไม่พบคอลัมน์ 'HN' หรือ 'เดือน' ในข้อมูลผู้ป่วย ไม่สามารถวิเคราะห์รายบุคคลได้")
