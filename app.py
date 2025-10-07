import streamlit as st
import pandas as pd
from data_loader import load_patient_data, load_pm25_data
from plotting import (
    plot_patient_vs_pm25,
    plot_vulnerable_pie,
    plot_yearly_comparison,
    plot_calendar_heatmap,
    plot_correlation_scatter,
)
# from geocoder import add_coordinates_to_dataframe # ปิดการนำเข้าโมดูลชั่วคราว

# ----------------------------
# 🔧 CONFIG: Google Sheets URL
# ----------------------------
URL_PATIENT = (
    "https://docs.google.com/spreadsheets/d/1vvQ8YLChHXvCowQQzcKIeV4PWt0CCt76f5Sj3fNTOV0/export?format=csv&gid=795124395"
)
URL_PM25 = (
    "https://docs.google.com/spreadsheets/d/1vvQ8YLChHXvCowQQzcKIeV4PWt0CCt76f5Sj3fNTOV0/export?format=csv&gid=1038807599"
)

st.set_page_config(page_title="PM2.5 Surveillance Dashboard", layout="wide")

# --- Load Data ---
df_pat = load_patient_data(URL_PATIENT)
df_pm = load_pm25_data(URL_PM25)

if df_pat.empty:
    st.error("ไม่สามารถโหลดข้อมูลผู้ป่วยได้ กรุณาตรวจสอบ URL หรือการเชื่อมต่อ")
    st.stop()
else:
    st.success("✅ โหลดข้อมูลสำเร็จ")

# --- DATA TRANSFORMATION: Add custom Z58.1 diagnosis group ---
# This section creates a new category based on the user's logic.
# If a patient is 'ไม่จัดอยู่ใน 4 กลุ่มโรค' but has 'Z58.1',
# they are recategorized.
required_cols_for_transform = ["4 กลุ่มโรคเฝ้าระวัง", "Y96, Y97, Z58.1"]
if all(col in df_pat.columns for col in required_cols_for_transform):
    # Define the conditions
    condition1 = df_pat["4 กลุ่มโรคเฝ้าระวัง"] == "ไม่จัดอยู่ใน 4 กลุ่มโรค"
    condition2 = df_pat["Y96, Y97, Z58.1"] == "Z58.1"
    
    # Apply the new category where both conditions are met
    df_pat.loc[condition1 & condition2, "4 กลุ่มโรคเฝ้าระวัง"] = "แพทย์วินิจฉัยโรคร่วมด้วย Z58.1"
    st.info("ℹ️ ได้ทำการจัดกลุ่มข้อมูล 'แพทย์วินิจฉัยโรคร่วมด้วย Z58.1' ตามเงื่อนไขที่กำหนด")
else:
    st.warning("⚠️ ไม่สามารถจัดกลุ่มข้อมูล Z58.1 ได้ เนื่องจากไม่พบคอลัมน์ '4 กลุ่มโรคเฝ้าระวัง' หรือ 'Y96, Y97, Z58.1'")


# --- Geocoding (Temporarily Disabled) ---
# df_pat = add_coordinates_to_dataframe(df_pat)

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
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Dashboard ปัจจุบัน",
    "📅 มุมมองเปรียบเทียบรายปี",
    "🗓️ ปฏิทินข้อมูล (Heatmap)",
    "🔗 วิเคราะห์ความสัมพันธ์"
])

with tab1:
    st.header("แนวโน้มผู้ป่วยเทียบกับค่า PM2.5")
    plot_patient_vs_pm25(dff, df_pm)

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
    st.header("ปฏิทินแสดงความรุนแรงของฝุ่นและจำนวนผู้ป่วย")
    plot_calendar_heatmap(df_pat, df_pm)

with tab4:
    st.header("ความสัมพันธ์ระหว่างค่า PM2.5 และจำนวนผู้ป่วยรวม")
    plot_correlation_scatter(df_pat, df_pm)


# --- Other Plots and Data Table ---
st.divider()
col_pie, col_table = st.columns([1, 2])

with col_pie:
    plot_vulnerable_pie(dff, month_sel)

with col_table:
    st.subheader("📋 ตารางข้อมูลผู้ป่วย (หลังกรอง)")
    st.dataframe(dff, use_container_width=True)


# ----------------------------
# 🗺️ Map Display (Temporarily Disabled)
# ----------------------------
st.subheader("🗺️ แผนที่แสดงตำบลของผู้ป่วย (ตามตัวกรอง)")
st.info("ℹ️ การแสดงผลแผนที่ถูกปิดใช้งานชั่วคราวเพื่อประหยัดโควต้า API")
