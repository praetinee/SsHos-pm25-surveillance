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
    df = pd.read_csv(URL_PATIENT)
    df.columns = df.columns.str.strip()
    if "วันที่เข้ารับบริการ" in df.columns:
        df["วันที่เข้ารับบริการ"] = pd.to_datetime(df["วันที่เข้ารับบริการ"], errors="coerce")
        df["เดือน"] = df["วันที่เข้ารับบริการ"].dt.to_period("M").astype(str)
    return df

@st.cache_data(show_spinner="กำลังโหลดข้อมูล PM2.5...")
def load_pm25():
    df = pd.read_csv(URL_PM25)
    df.columns = df.columns.str.strip()
    return df

df_pat = load_patient()
df_pm = load_pm25()

st.success("✅ โหลดข้อมูลสำเร็จ")

# ----------------------------
# 🌍 ฟังก์ชัน geocoding ด้วย Google Maps API
# ----------------------------
@st.cache_data(show_spinner="กำลังดึงพิกัดจาก Google Maps...")
def geocode_address(address):
    """Return (lat, lon) using Google Maps Geocoding API"""
    if not isinstance(address, str) or address.strip() == "":
        return None, None
    api_key = st.secrets["google_maps"]["api_key"]
    url = f"https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": api_key}
    r = requests.get(url, params=params)
    if r.status_code == 200:
        data = r.json()
        if data.get("status") == "OK":
            loc = data["results"][0]["geometry"]["location"]
            return loc["lat"], loc["lng"]
    return None, None

# ----------------------------
# 🧭 สร้างพิกัดตำบล
# ----------------------------
if all(col in df_pat.columns for col in ["ตำบล", "อำเภอ", "จังหวัด"]):
    st.info("🔍 กำลังประมวลผลพิกัดตำบล ... (ระบบจะ cache ครั้งแรกเท่านั้น)")
    df_pat["full_address"] = df_pat.apply(
        lambda r: f"{r['ตำบล']} {r['อำเภอ']} {r['จังหวัด']}", axis=1
    )
    df_pat[["lat", "lon"]] = df_pat["full_address"].apply(
        lambda x: pd.Series(geocode_address(x))
    )
else:
    df_pat["lat"], df_pat["lon"] = None, None

# ----------------------------
# 🎛 Sidebar Filter
# ----------------------------
st.sidebar.header("🔍 ตัวกรองข้อมูล")

months = sorted(df_pat["เดือน"].dropna().unique().tolist()) if "เดือน" in df_pat.columns else []
gp_list = sorted(df_pat["4 กลุ่มโรคเฝ้าระวัง"].dropna().unique().tolist()) if "4 กลุ่มโรคเฝ้าระวัง" in df_pat.columns else []

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

if "4 กลุ่มโรคเฝ้าระวัง" in df_pat.columns and "เดือน" in df_pat.columns:
    agg = df_pat.groupby(["เดือน", "4 กลุ่มโรคเฝ้าระวัง"]).size().reset_index(name="count")
    df_merge = agg.merge(df_pm, on="เดือน", how="left")

    fig_comb = make_subplots(specs=[[{"secondary_y": True}]])
    for grp in df_merge["4 กลุ่มโรคเฝ้าระวัง"].unique():
        d2 = df_merge[df_merge["4 กลุ่มโรคเฝ้าระวัง"] == grp]
        fig_comb.add_trace(
            go.Scatter(x=d2["เดือน"], y=d2["count"], name=f"ผู้ป่วย {grp}", mode="lines+markers"),
            secondary_y=False
        )

    if "PM2.5 (ug/m3)" in df_merge.columns:
        fig_comb.add_trace(
            go.Scatter(x=df_merge["เดือน"], y=df_merge["PM2.5 (ug/m3)"], name="PM2.5 (ug/m3)", line=dict(color="black", dash="dash")),
            secondary_y=True
        )

    fig_comb.update_layout(title_text="แนวโน้มผู้ป่วย 4 กลุ่มโรค vs PM2.5", legend_title_text="ข้อมูล")
    fig_comb.update_yaxes(title_text="จำนวนผู้ป่วย", secondary_y=False)
    fig_comb.update_yaxes(title_text="PM2.5 (ug/m3)", secondary_y=True)
    st.plotly_chart(fig_comb, use_container_width=True)
else:
    st.warning("⚠️ ไม่พบคอลัมน์ '4 กลุ่มโรคเฝ้าระวัง' หรือ 'เดือน'")

# ----------------------------
# 🗺️ แผนที่ตำบลผู้ป่วย
# ----------------------------
st.subheader("🗺️ แผนที่ตำบลที่มีผู้ป่วย")
map_df = dff[["lat", "lon", "full_address"]].dropna() if "lat" in dff.columns else pd.DataFrame()
if not map_df.empty:
    st.map(map_df.rename(columns={"lat": "latitude", "lon": "longitude"}))
else:
    st.info("ℹ️ ยังไม่มีข้อมูลพิกัดตำบล หรือยังไม่สามารถ geocode ได้")

# ----------------------------
# 👥 สัดส่วนกลุ่มเปราะบาง
# ----------------------------
st.subheader("👥 สัดส่วนกลุ่มเปราะบาง")
if "กลุ่มเปราะบาง" in df_pat.columns:
    sp = df_pat["กลุ่มเปราะบาง"].value_counts().reset_index()
    sp.columns = ["กลุ่ม", "จำนวน"]
    pie = px.pie(sp, values="จำนวน", names="กลุ่ม", title="สัดส่วนกลุ่มเปราะบาง")
    st.plotly_chart(pie, use_container_width=True)
else:
    st.info("ℹ️ ยังไม่มีคอลัมน์ 'กลุ่มเปราะบาง' ในข้อมูล")

# ----------------------------
# 📋 ตารางข้อมูล
# ----------------------------
st.subheader("📋 ตารางข้อมูลผู้ป่วย (หลังกรอง)")
st.dataframe(dff, use_container_width=True)
