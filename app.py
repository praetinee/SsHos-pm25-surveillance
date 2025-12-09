import streamlit as st
import pandas as pd
from data_loader import load_patient_data, load_pm25_data, load_lat_lon_data
from plots_main import (
    plot_patient_vs_pm25,
    plot_yearly_comparison,
    plot_specific_disease_trend, # NEW: Import the new function
)
from plots_correlation import plot_correlation_scatter
from plots_vulnerable import plot_vulnerable_dashboard
from plots_map import plot_patient_map

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
    st.success("✅ โหลดข้อมูลสำเร็จ")

# ----------------------------
# 🎛 Sidebar Filter
# ----------------------------
st.sidebar.header("🔍 ตัวกรองข้อมูล")

if "เดือน" in df_pat.columns and "4 กลุ่มโรคเฝ้าระวัง" in df_pat.columns:
    months = sorted(df_pat["เดือน"].dropna().unique().tolist())
    gp_list = sorted(df_pat["4 กลุ่มโรคเฝ้าระวัง"].dropna().unique().tolist())

    month_sel = st.sidebar.selectbox("เลือกเดือน", ["ทั้งหมด"] + months)
    gp_sel = st.sidebar.selectbox("เลือกกลุ่มโรค", ["ทั้งหมด"] + gp_list)

    dff = df_pat.copy()
    if month_sel != "ทั้งหมด":
        dff = dff[dff["เดือน"] == month_sel]
    if gp_sel != "ทั้งหมด":
        dff = dff[dff["4 กลุ่มโรคเฝ้าระวัง"] == gp_sel]
else:
    st.sidebar.error("ไม่พบคอลัมน์ที่จำเป็น (เดือน, 4 กลุ่มโรคเฝ้าระวัง) ในข้อมูล")
    st.stop()

# ----------------------------
# 🎨 Main Panel
# ----------------------------
st.title("Dashboards เฝ้าระวังผลกระทบต่อสุขภาพจาก PM2.5")

# --- Create Tabs for different visualizations ---
# NEW: Added "J44.0 เฉพาะโรค" tab
tab1, tab_j44, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Dashboard ปัจจุบัน",
    "💨 J44.0 เฉพาะโรค",
    "📅 มุมมองเปรียบเทียบรายปี",
    "🔗 วิเคราะห์ความสัมพันธ์",
    "📊 กลุ่มเปราะบาง",
    "🗺️ แผนที่"
])

with tab1:
    st.header("แนวโน้มผู้ป่วยเทียบกับค่า PM2.5")
    plot_patient_vs_pm25(dff, df_pm)
    
with tab_j44: # NEW Tab Content
    # Constants for J44.0
    J44_CODE = "J440" # Assuming the ICD-10 code is stored as J440 (without dot)
    J44_NAME = "ปอดอุดกั้นเฉียบพลัน"
    # แก้ไข: ใช้ชื่อคอลัมน์จริง 'ICD10ทั้งหมด' แทนการใช้ 'R'
    J44_FILTER_COL = 'ICD10ทั้งหมด' # IMPORTANT: ใช้ชื่อคอลัมน์จริงสำหรับกรองรหัสโรค J44.0 ตามที่คุณแจ้ง
    
    st.header(f"แนวโน้มผู้ป่วย {J44_NAME} (J44.0) เทียบกับค่า PM2.5")
    # Call the new function, explicitly setting filter_col_name='ICD10ทั้งหมด'
    plot_specific_disease_trend(df_pat, df_pm, J44_CODE, J44_NAME, filter_col_name=J44_FILTER_COL)

with tab2:
    st.header("เปรียบเทียบข้อมูลแบบปีต่อปี (Year-over-Year)")
    
    # --- KPI Cards ---
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


with tab3:
    st.header("ความสัมพันธ์ระหว่างค่า PM2.5 และจำนวนผู้ป่วยรวม")
    plot_correlation_scatter(df_pat, df_pm)

with tab4:
    st.header("การวิเคราะห์เชิงลึกสำหรับกลุ่มเปราะบาง")
    plot_vulnerable_dashboard(dff, df_pm, dff)

with tab5:
    st.header("แผนที่แสดงการกระจายตัวของผู้ป่วยในระดับตำบล")
    plot_patient_map(dff, df_latlon)
