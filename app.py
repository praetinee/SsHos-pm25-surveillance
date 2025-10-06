import streamlit as st
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objs as go
import requests

st.set_page_config(page_title="PM2.5 Surveillance Dashboard", layout="wide")

# ----------------------------
# 🔧 CONFIG: Google Sheets URL
# ----------------------------
URL_PATIENT = (
    "https://docs.google.com/spreadsheets/d/1vvQ8YLChHXvCowQQzcKIeV4PWt0CCt76f5Sj3fNTOV0/export?format=csv&gid=795124395"
)
URL_PM25 = (
    "https://docs.google.com/spreadsheets/d/1vvQ8YLChHXvCowQQzcKIeV4PWt0CCt76f5Sj3fNTOV0/export?format=csv&gid=1038807599"
)

# ----------------------------
# 📥 โหลดข้อมูลจาก Google Sheets
# ----------------------------
@st.cache_data(show_spinner="กำลังโหลดข้อมูลผู้ป่วย...")
def load_patient():
    try:
        df = pd.read_csv(URL_PATIENT)
        df.columns = df.columns.str.strip()
        # ตรวจสอบคอลัมน์วันที่ก่อนแปลง
        if "วันที่เข้ารับบริการ" in df.columns:
            df["วันที่เข้ารับบริการ"] = pd.to_datetime(df["วันที่เข้ารับบริการ"], errors="coerce")
            # สร้างคอลัมน์ 'เดือน' เฉพาะแถวที่วันที่ไม่เป็น NaT
            df["เดือน"] = df["วันที่เข้ารับบริการ"].dropna().dt.to_period("M").astype(str)
        return df
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูลผู้ป่วย: {e}")
        return pd.DataFrame()

@st.cache_data(show_spinner="กำลังโหลดข้อมูล PM2.5...")
def load_pm25():
    try:
        df = pd.read_csv(URL_PM25)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล PM2.5: {e}")
        return pd.DataFrame()


# ----------------------------
# 🌍 ฟังก์ชัน geocoding ด้วย Google Maps API (ปรับปรุงใหม่)
# ----------------------------
@st.cache_data(show_spinner="กำลังดึงพิกัดจาก Google Maps...")
def geocode_address(address):
    """Return (lat, lon) using Google Maps Geocoding API with robust error handling"""
    if not isinstance(address, str) or address.strip() == "":
        return None, None
    
    try:
        api_key = st.secrets["google_maps"]["api_key"]
    except (KeyError, FileNotFoundError):
        st.error("❌ ไม่พบ API Key ของ Google Maps ใน secrets.toml")
        return None, None

    url = f"https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": api_key, "language": "th"}
    
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        data = r.json()

        if data.get("status") == "OK" and data.get("results"):
            loc = data["results"][0]["geometry"]["location"]
            return loc.get("lat"), loc.get("lng")
        else:
            # ไม่แสดง warning สำหรับ 'ZERO_RESULTS' เพื่อไม่ให้รกหน้าจอ
            if data.get("status") != "ZERO_RESULTS":
                st.warning(f"Geocoding ล้มเหลวสำหรับ '{address}'. Status: {data.get('status', 'N/A')}")
            return None, None
            
    except requests.exceptions.RequestException as e:
        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อ Google Maps API: {e}")
        return None, None
    except (KeyError, IndexError) as e:
        st.error(f"เกิดข้อผิดพลาดในการประมวลผลข้อมูลจาก Geocoding API: {e}")
        return None, None

# --- เริ่มการทำงานหลัก ---
df_pat = load_patient()
df_pm = load_pm25()

if df_pat.empty:
    st.error("ไม่สามารถโหลดข้อมูลผู้ป่วยได้ กรุณาตรวจสอบ URL และการตั้งค่า Google Sheets")
    st.stop()

st.success("✅ โหลดข้อมูลสำเร็จ")

# ----------------------------
# 🕵️ ตรวจสอบคอลัมน์ที่จำเป็น
# ----------------------------
ESSENTIAL_PAT_COLS = ["วันที่เข้ารับบริการ", "4 กลุ่มโรคเฝ้าระวัง", "ตำบล", "อำเภอ", "จังหวัด"]
missing_pat_cols = [col for col in ESSENTIAL_PAT_COLS if col not in df_pat.columns]
if missing_pat_cols:
    st.error(f"❌ ไม่พบคอลัมน์ที่จำเป็นในข้อมูลผู้ป่วย: {', '.join(missing_pat_cols)}")
    st.stop()

if not df_pm.empty:
    ESSENTIAL_PM_COLS = ["เดือน", "PM2.5 (ug/m3)"]
    missing_pm_cols = [col for col in ESSENTIAL_PM_COLS if col not in df_pm.columns]
    if missing_pm_cols:
        st.warning(f"⚠️ ไม่พบคอลัมน์ในข้อมูล PM2.5: {', '.join(missing_pm_cols)}. กราฟเทียบ PM2.5 อาจไม่แสดงผล")


# ----------------------------
# 🧭 สร้างพิกัดตำบล
# ----------------------------
st.info("🔍 กำลังประมวลผลพิกัดตำบล ... (ระบบจะ cache ผลลัพธ์ครั้งแรกเพื่อความรวดเร็ว)")
df_pat["full_address"] = df_pat.apply(
    lambda r: f"{r['ตำบล']} {r['อำเภอ']} {r['จังหวัด']}", axis=1
)
# ใช้ progress bar เพื่อแสดงสถานะ
lat_lon_data = []
progress_bar = st.progress(0, text="กำลังแปลงที่อยู่เป็นพิกัด...")
for i, address in enumerate(df_pat["full_address"]):
    lat_lon_data.append(geocode_address(address))
    progress_bar.progress((i + 1) / len(df_pat), text=f"กำลังแปลงที่อยู่เป็นพิกัด... ({i+1}/{len(df_pat)})")

df_pat[["lat", "lon"]] = pd.DataFrame(lat_lon_data, index=df_pat.index)
progress_bar.empty()


# ----------------------------
# 🎛 Sidebar Filter
# ----------------------------
st.sidebar.header("🔍 ตัวกรองข้อมูล")

months = sorted(df_pat["เดือน"].dropna().unique().tolist())
gp_list = sorted(df_pat["4 กลุ่มโรคเฝ้าระวัง"].dropna().unique().tolist())

month_sel = st.sidebar.selectbox("เลือกเดือน", ["ทั้งหมด"] + months)
gp_sel = st.sidebar.selectbox("เลือกกลุ่มโรค", ["ทั้งหมด"] + gp_list)

dff = df_pat.copy()
if month_sel != "ทั้งหมด":
    dff = dff[dff["เดือน"] == month_sel]
if gp_sel != "ทั้งหมด":
    dff = dff[dff["4 กลุ่มโรคเฝ้าระวัง"] == gp_sel]

# ----------------------------
# 📈 กราฟ: ผู้ป่วย 4 กลุ่ม vs PM2.5
# ----------------------------
st.subheader("📊 แนวโน้มผู้ป่วย 4 กลุ่มโรคเทียบกับค่า PM2.5")

agg = df_pat.groupby(["เดือน", "4 กลุ่มโรคเฝ้าระวัง"]).size().reset_index(name="count")

fig_comb = make_subplots(specs=[[{"secondary_y": True}]])
for grp in agg["4 กลุ่มโรคเฝ้าระวัง"].unique():
    d2 = agg[agg["4 กลุ่มโรคเฝ้าระวัง"] == grp]
    fig_comb.add_trace(
        go.Scatter(x=d2["เดือน"], y=d2["count"], name=f"ผู้ป่วย {grp}", mode="lines+markers"),
        secondary_y=False
    )

# รวมข้อมูล PM2.5 ถ้ามี
if not df_pm.empty and "PM2.5 (ug/m3)" in df_pm.columns and "เดือน" in df_pm.columns:
    # ตรวจสอบว่า df_pm มีข้อมูลสำหรับเดือนใน agg หรือไม่
    df_merge = pd.merge(agg[['เดือน']].drop_duplicates(), df_pm, on="เดือน", how="left")
    fig_comb.add_trace(
        go.Scatter(x=df_merge["เดือน"], y=df_merge["PM2.5 (ug/m3)"], name="PM2.5 (ug/m3)", line=dict(color="black", dash="dash")),
        secondary_y=True
    )
    fig_comb.update_yaxes(title_text="PM2.5 (ug/m3)", secondary_y=True)
else:
    st.info("ℹ️ ไม่ได้แสดงข้อมูล PM2.5 เนื่องจากไม่พบข้อมูลหรือคอลัมน์ที่จำเป็น")

fig_comb.update_layout(title_text="แนวโน้มผู้ป่วย 4 กลุ่มโรค vs PM2.5", legend_title_text="ข้อมูล")
fig_comb.update_yaxes(title_text="จำนวนผู้ป่วย", secondary_y=False)

st.plotly_chart(fig_comb, use_container_width=True)

# ----------------------------
# 🗺️ แผนที่ตำบลผู้ป่วย
# ----------------------------
st.subheader("🗺️ แผนที่ตำบลที่มีผู้ป่วย")
map_df = dff[["lat", "lon"]].dropna()
if not map_df.empty:
    st.map(map_df)
else:
    st.info("ℹ️ ไม่พบข้อมูลพิกัดสำหรับข้อมูลที่กรอง หรือไม่สามารถแปลงที่อยู่เป็นพิกัดได้")

# ----------------------------
# 👥 สัดส่วนกลุ่มเปราะบาง
# ----------------------------
st.subheader("👥 สัดส่วนกลุ่มเปราะบาง")
if "กลุ่มเปราะบาง" in dff.columns:
    sp = dff["กลุ่มเปราะบาง"].value_counts().reset_index()
    sp.columns = ["กลุ่ม", "จำนวน"]
    pie = px.pie(sp, values="จำนวน", names="กลุ่ม", title=f"สัดส่วนกลุ่มเปราะบาง (เดือน: {month_sel})")
    st.plotly_chart(pie, use_container_width=True)
else:
    st.info("ℹ️ ไม่มีคอลัมน์ 'กลุ่มเปราะบาง' ในข้อมูล")

# ----------------------------
# 📋 ตารางข้อมูล
# ----------------------------
st.subheader("📋 ตารางข้อมูลผู้ป่วย (หลังกรอง)")
st.dataframe(dff.drop(columns=['full_address'], errors='ignore'), use_container_width=True)
