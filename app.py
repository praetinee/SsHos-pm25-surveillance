import streamlit as st
import pandas as pd
import plotly.express as px
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from plotly.subplots import make_subplots
import plotly.graph_objs as go

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
# 🔁 โหลดข้อมูล
# ----------------------------
@st.cache_data
def load_patient():
    df = pd.read_csv(URL_PATIENT)
    df.columns = df.columns.str.strip()
    if 'วันที่เข้ารับบริการ' in df.columns:
        df['วันที่เข้ารับบริการ'] = pd.to_datetime(df['วันที่เข้ารับบริการ'], errors='coerce')
        df['เดือน'] = df['วันที่เข้ารับบริการ'].dt.to_period('M').astype(str)
    return df

@st.cache_data
def load_pm25():
    df = pd.read_csv(URL_PM25)
    df.columns = df.columns.str.strip()
    return df

df_pat = load_patient()
df_pm = load_pm25()

# ----------------------------
# ✏️ ฟังก์ชันช่วย: geocode ชื่อ → lat, lon
# ----------------------------
@st.cache_data
def geocode_address(list_of_names):
    geolocator = Nominatim(user_agent="pm25_dashboard")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
    records = []
    for name in list_of_names:
        if not isinstance(name, str) or name.strip() == "":
            records.append({'name': name, 'lat': None, 'lon': None})
            continue
        try:
            loc = geocode(name)
            if loc:
                records.append({'name': name, 'lat': loc.latitude, 'lon': loc.longitude})
            else:
                records.append({'name': name, 'lat': None, 'lon': None})
        except Exception:
            records.append({'name': name, 'lat': None, 'lon': None})
    return pd.DataFrame(records)

# ----------------------------
# 🧭 สร้างพิกัดตำบล
# ----------------------------
if all(col in df_pat.columns for col in ['ตำบล', 'อำเภอ', 'จังหวัด']):
    df_pat['loc_name'] = df_pat.apply(lambda row: f"{row['ตำบล']} {row['อำเภอ']} {row['จังหวัด']}", axis=1)
    distinct_locations = df_pat['loc_name'].dropna().unique().tolist()
    df_geo = geocode_address(distinct_locations)
    df_pat = df_pat.merge(df_geo, left_on='loc_name', right_on='name', how='left')
else:
    df_pat['lat'], df_pat['lon'] = None, None

# ----------------------------
# 🎛 Sidebar filtering
# ----------------------------
st.sidebar.header("ตัวกรอง")

months = sorted(df_pat['เดือน'].dropna().unique().tolist())
gp_list = sorted(df_pat['4 กลุ่มโรคเฝ้าระวัง'].dropna().unique().tolist()) if '4 กลุ่มโรคเฝ้าระวัง' in df_pat.columns else []

month_sel = st.sidebar.selectbox("เลือกเดือน", ['ทั้งหมด'] + months)
gp_sel = st.sidebar.selectbox("เลือกกลุ่มโรค", ['ทั้งหมด'] + gp_list)

dff = df_pat.copy()
if month_sel != 'ทั้งหมด':
    dff = dff[dff['เดือน'] == month_sel]
if gp_sel != 'ทั้งหมด':
    dff = dff[dff['4 กลุ่มโรคเฝ้าระวัง'] == gp_sel]

# ----------------------------
# 📈 กราฟ: ผู้ป่วย 4 กลุ่ม vs PM2.5
# ----------------------------
st.subheader("แนวโน้มผู้ป่วย vs ค่า PM2.5")

if '4 กลุ่มโรคเฝ้าระวัง' in df_pat.columns:
    agg = df_pat.groupby(['เดือน', '4 กลุ่มโรคเฝ้าระวัง']).size().reset_index(name='count')
    df_merge = agg.merge(df_pm, on='เดือน', how='left')

    fig_comb = make_subplots(specs=[[{"secondary_y": True}]])
    for grp in df_merge['4 กลุ่มโรคเฝ้าระวัง'].unique():
        d2 = df_merge[df_merge['4 กลุ่มโรคเฝ้าระวัง'] == grp]
        fig_comb.add_trace(
            go.Scatter(x=d2['เดือน'], y=d2['count'], name=f"ผู้ป่วย {grp}", mode='lines+markers'),
            secondary_y=False
        )

    if 'PM2.5 (ug/m3)' in df_merge.columns:
        fig_comb.add_trace(
            go.Scatter(x=df_merge['เดือน'], y=df_merge['PM2.5 (ug/m3)'], name="PM2.5 (ug/m3)", line=dict(color='black', dash='dash')),
            secondary_y=True
        )

    fig_comb.update_layout(title_text="เปรียบเทียบผู้ป่วย 4 กลุ่มโรค vs PM2.5")
    fig_comb.update_yaxes(title_text="จำนวนผู้ป่วย", secondary_y=False)
    fig_comb.update_yaxes(title_text="PM2.5 (ug/m3)", secondary_y=True)
    st.plotly_chart(fig_comb, use_container_width=True)
else:
    st.warning("ไม่พบคอลัมน์ '4 กลุ่มโรคเฝ้าระวัง' ในข้อมูล")

# ----------------------------
# 🗺️ แผนที่ตำบลผู้ป่วย
# ----------------------------
st.subheader("แผนที่ตำบลผู้ป่วย")
map_df = dff[['lat', 'lon', 'loc_name']].dropna() if 'lat' in dff.columns else pd.DataFrame()
if not map_df.empty:
    st.map(map_df.rename(columns={'lat': 'latitude', 'lon': 'longitude'}))
else:
    st.info("ยังไม่มีข้อมูลพิกัดตำบล หรือไม่สามารถ geocode ได้")

# ----------------------------
# 👥 สัดส่วนกลุ่มเปราะบาง
# ----------------------------
st.subheader("สัดส่วนกลุ่มเปราะบาง")
if 'กลุ่มเปราะบาง' in df_pat.columns:
    sp = df_pat['กลุ่มเปราะบาง'].value_counts().reset_index()
    sp.columns = ['กลุ่ม', 'จำนวน']
    pie = px.pie(sp, values='จำนวน', names='กลุ่ม', title='สัดส่วนกลุ่มเปราะบาง')
    st.plotly_chart(pie, use_container_width=True)
else:
    st.info("ยังไม่มีคอลัมน์ 'กลุ่มเปราะบาง' ในข้อมูล")

# ----------------------------
# 📋 ตารางข้อมูล
# ----------------------------
st.subheader("ข้อมูลผู้ป่วย (กรองแล้ว)")
st.dataframe(dff, use_container_width=True)
