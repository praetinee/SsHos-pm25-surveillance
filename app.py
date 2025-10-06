import streamlit as st
import pandas as pd
import plotly.express as px
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# ----------------------------
# 🔧 CONFIG: Google Sheets URL (export to CSV)
# ----------------------------
# สำหรับ sheet “ผู้ป่วย” (tab หลัก)
URL_PATIENT = (
    "https://docs.google.com/spreadsheets/d/1vvQ8YLChHXvCowQQzcKIeV4PWt0CCt76f5Sj3fNTOV0"
    "/export?format=csv&gid=0"
)
# สำหรับ sheet “PM2.5 รายเดือน” (กรณี tab แยก)
URL_PM25 = (
    "https://docs.google.com/spreadsheets/d/1vvQ8YLChHXvCowQQzcKIeV4PWt0CCt76f5Sj3fNTOV0"
    "/export?format=csv&gid=<gid_of_pm25_sheet>"
)

# ----------------------------
# 🔁 โหลดข้อมูล
# ----------------------------
@st.cache_data
def load_patient():
    df = pd.read_csv(URL_PATIENT)
    # ทำความสะอาดชื่อคอลัมน์
    df.columns = df.columns.str.strip()
    # แปลงวันที่ → เดือน (yyyy-MM)
    if 'วันที่เข้ารับบริการ' in df.columns:
        df['วันที่เข้ารับบริการ'] = pd.to_datetime(df['วันที่เข้ารับบริการ'], errors='coerce')
        df['เดือน'] = df['วันที่เข้ารับบริการ'].dt.to_period('M').astype(str)
    return df

@st.cache_data
def load_pm25():
    df = pd.read_csv(URL_PM25)
    df.columns = df.columns.str.strip()
    # สมมติมีคอลัมน์ "เดือน" และ "PM2.5เฉลี่ย"
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
        try:
            loc = geocode(name)
            if loc:
                records.append({'name': name, 'lat': loc.latitude, 'lon': loc.longitude})
            else:
                records.append({'name': name, 'lat': None, 'lon': None})
        except Exception as e:
            records.append({'name': name, 'lat': None, 'lon': None})
    return pd.DataFrame(records)

# ----------------------------
# 🧭 สร้างพิกัดตำบล
# ----------------------------
# สมมติเรรวมชื่อ “ตำบล, อำเภอ, จังหวัด” เป็น string
df_pat['loc_name'] = df_pat.apply(
    lambda row: f\"{row['ตำบล']} {row['อำเภอ']} {row['จังหวัด']}\", axis=1
)
distinct_locations = df_pat['loc_name'].unique().tolist()
df_geo = geocode_address(distinct_locations)
# รวมกับ df_pat
df_pat = df_pat.merge(df_geo, left_on='loc_name', right_on='name', how='left')

# ----------------------------
# 🎛 Sidebar filtering
# ----------------------------
st.sidebar.header("ตัวกรอง")
# ตัวอย่าง filter: เดือน, กลุ่มโรค
months = sorted(df_pat['เดือน'].dropna().unique().tolist())
gp_list = sorted(df_pat['4 กลุ่มโรคเฝ้าระวัง'].dropna().unique().tolist())
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
# สรุปจำนวนผู้ป่วยต่อเดือนแยกกลุ่ม
agg = df_pat.groupby(['เดือน', '4 กลุ่มโรคเฝ้าระวัง']).size().reset_index(name='count')
# รวมกับข้อมูล PM2.5
df_merge = agg.merge(df_pm, on='เดือน', how='left')

fig = px.line(
    df_merge,
    x='เดือน',
    y='count',
    color='4 กลุ่มโรคเฝ้าระวัง',
    markers=True,
    title='จำนวนผู้ป่วยตามกลุ่มโรค',
)
# เพิ่มเส้น PM2.5 เป็นแกน y รอง
fig2 = px.line(
    df_merge,
    x='เดือน',
    y='PM2.5เฉลี่ย',  # ปรับชื่อคอลัมน์ให้ตรง
    markers=True,
    title='PM2.5 เฉลี่ยรายเดือน',
)
# ผสมสองกราฟโดยใช้ secondary_y
from plotly.subplots import make_subplots
import plotly.graph_objs as go

fig_comb = make_subplots(specs=[[{"secondary_y": True}]])
for grp in df_merge['4 กลุ่มโรคเฝ้าระวัง'].unique():
    d2 = df_merge[df_merge['4 กลุ่มโรคเฝ้าระวัง'] == grp]
    fig_comb.add_trace(
        go.Scatter(x=d2['เดือน'], y=d2['count'], name=f"ผู้ป่วย {grp}"),
        secondary_y=False
    )
# PM2.5 trace
fig_comb.add_trace(
    go.Scatter(x=df_merge['เดือน'], y=df_merge['PM2.5เฉลี่ย'], name="PM2.5เฉลี่ย", line=dict(color='black', dash='dash')),
    secondary_y=True
)
fig_comb.update_layout(title_text="เปรียบเทียบผู้ป่วย 4 กลุ่มโรค vs PM2.5")
fig_comb.update_yaxes(title_text="จำนวนผู้ป่วย", secondary_y=False)
fig_comb.update_yaxes(title_text="PM2.5 เฉลี่ย", secondary_y=True)
st.plotly_chart(fig_comb, use_container_width=True)

# ----------------------------
# 🗺️ แผนที่: จุดตำบล / ผู้ป่วย
# ----------------------------
st.subheader("แผนที่ตำบลผู้ป่วย")
map_df = dff[['lat', 'lon', 'loc_name']].dropna()
if not map_df.empty:
    st.map(map_df.rename(columns={'lat':'latitude', 'lon':'longitude'}))
else:
    st.write("ไม่มีพิกัดตำบลสำหรับแสดงแผนที่")

# ----------------------------
# 👥 สัดส่วน “กลุ่มเปราะบาง”
# ----------------------------
st.subheader("สัดส่วนกลุ่มเปราะบาง")
# สมมติคอลัมน์ที่มี: เพศ, อายุ, โรคประจำตัว ฯลฯ
# ตัวอย่าง: ถ้า df_pat มีคอลัมน์ 'กลุ่มเปราะบาง'
if 'กลุ่มเปราะบาง' in df_pat.columns:
    sp = df_pat['กลุ่มเปราะบาง'].value_counts().reset_index()
    sp.columns = ['กลุ่ม', 'จำนวน']
    pie = px.pie(sp, values='จำนวน', names='กลุ่ม', title='สัดส่วนกลุ่มเปราะบาง')
    st.plotly_chart(pie, use_container_width=True)

# ----------------------------
# 📋 ตารางข้อมูลแสดง
# ----------------------------
st.subheader("ข้อมูลผู้ป่วย (กรองแล้ว)")
st.dataframe(dff, use_container_width=True)
