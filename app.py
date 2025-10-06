import streamlit as st
import pandas as pd
from data_loader import load_patient_data, load_pm25_data
from plotting import plot_patient_vs_pm25, plot_vulnerable_pie
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

# --- Geocoding (Temporarily Disabled) ---
# หากต้องการเปิดใช้งานใหม่ ให้ลบเครื่องหมาย # หน้าบรรทัด import ด้านบน และบรรทัดด้านล่างนี้
# df_pat = add_coordinates_to_dataframe(df_pat)

# ----------------------------
# 🎛 Sidebar Filter
# ----------------------------
st.sidebar.header("🔍 ตัวกรองข้อมูล")

# Ensure required columns exist before creating filters
if "เดือน" in df_pat.columns and "4 กลุ่มโรคเฝ้าระวัง" in df_pat.columns:
    months = sorted(df_pat["เดือน"].dropna().unique().tolist())
    gp_list = sorted(df_pat["4 กลุ่มโรคเฝ้าระวัง"].dropna().unique().tolist())

    month_sel = st.sidebar.selectbox("เลือกเดือน", ["ทั้งหมด"] + months)
    gp_sel = st.sidebar.selectbox("เลือกกลุ่มโรค", ["ทั้งหมด"] + gp_list)

    # Apply filters
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

# --- Plotting ---
plot_patient_vs_pm25(dff, df_pm)
plot_vulnerable_pie(dff, month_sel)

# ----------------------------
# 🗺️ Map Display (Temporarily Disabled)
# ----------------------------
st.subheader("🗺️ แผนที่แสดงตำบลของผู้ป่วย (ตามตัวกรอง)")
st.info("ℹ️ การแสดงผลแผนที่ถูกปิดใช้งานชั่วคราวเพื่อประหยัดโควต้า API")
# if "lat" in df_pat.columns and not dff[["lat", "lon"]].dropna().empty:
#     st.map(dff[["lat", "lon"]].dropna())
# else:
#     st.info("ℹ️ ไม่มีข้อมูลพิกัดสำหรับข้อมูลที่เลือก หรือการแสดงแผนที่ถูกปิดใช้งาน")


# ----------------------------
# 📋 Data Table
# ----------------------------
st.subheader("📋 ตารางข้อมูลผู้ป่วย (หลังกรอง)")
st.dataframe(dff, use_container_width=True)

