import streamlit as st
import pandas as pd
import plotly.express as px

# =============================
# 🔹 CONFIG
# =============================
SHEET_URL = 'https://docs.google.com/spreadsheets/d/1vvQ8YLChHXvCowQQzcKIeV4PWt0CCt76f5Sj3fNTOV0/export?format=csv&id=1vvQ8YLChHXvCowQQzcKIeV4PWt0CCt76f5Sj3fNTOV0&gid=795124395'

st.set_page_config(page_title="PM2.5 Dashboard", layout="wide")

# =============================
# 🔹 LOAD DATA
# =============================
@st.cache_data
def load_data():
    df = pd.read_csv(SHEET_URL)
    df.columns = df.columns.str.strip()

    # แปลงวันที่ให้เป็น datetime
    if 'วันที่เข้ารับบริการ' in df.columns:
        df['วันที่เข้ารับบริการ'] = pd.to_datetime(df['วันที่เข้ารับบริการ'], errors='coerce', dayfirst=True)
        df['เดือน'] = df['วันที่เข้ารับบริการ'].dt.to_period('M').astype(str)

    return df

df = load_data()

st.title('📊 การเฝ้าระวังโรคที่อาจมีผลกระทบจาก PM2.5 ในผู้เข้ารับบริการโรงพยาบาลสันทราย')

# =============================
# 🔹 FILTER SIDEBAR
# =============================
with st.sidebar:
    st.header('🔍 ตัวกรองข้อมูล')

    province_list = ['ทั้งหมด'] + sorted(df['จังหวัด'].dropna().unique().tolist()) if 'จังหวัด' in df.columns else []
    amphoe_list = ['ทั้งหมด'] + sorted(df['อำเภอ'].dropna().unique().tolist()) if 'อำเภอ' in df.columns else []
    tambon_list = ['ทั้งหมด'] + sorted(df['ตำบล'].dropna().unique().tolist()) if 'ตำบล' in df.columns else []
    gender_list = ['ทั้งหมด'] + sorted(df['เพศ'].dropna().unique().tolist()) if 'เพศ' in df.columns else []

    province = st.selectbox('เลือกจังหวัด', province_list)
    amphoe = st.selectbox('เลือกอำเภอ', amphoe_list)
    tambon = st.selectbox('เลือกตำบล', tambon_list)
    gender = st.selectbox('เลือกเพศ', gender_list)

# กรองข้อมูล
filtered_df = df.copy()
if province != 'ทั้งหมด' and 'จังหวัด' in df.columns:
    filtered_df = filtered_df[filtered_df['จังหวัด'] == province]
if amphoe != 'ทั้งหมด' and 'อำเภอ' in df.columns:
    filtered_df = filtered_df[filtered_df['อำเภอ'] == amphoe]
if tambon != 'ทั้งหมด' and 'ตำบล' in df.columns:
    filtered_df = filtered_df[filtered_df['ตำบล'] == tambon]
if gender != 'ทั้งหมด' and 'เพศ' in df.columns:
    filtered_df = filtered_df[filtered_df['เพศ'] == gender]

# =============================
# 🔹 VISUALIZATION 1: แนวโน้มผู้ป่วยตามเดือน
# =============================
if 'เดือน' in filtered_df.columns:
    st.subheader('📈 แนวโน้มจำนวนผู้เข้ารับบริการตามเดือน')
    month_df = filtered_df.groupby('เดือน').size().reset_index(name='จำนวนผู้ป่วย')
    line_fig = px.line(
        month_df,
        x='เดือน',
        y='จำนวนผู้ป่วย',
        markers=True,
        title='จำนวนผู้ป่วยรายเดือน'
    )
    st.plotly_chart(line_fig, use_container_width=True)

# =============================
# 🔹 VISUALIZATION 2: ผู้ป่วยรายตำบล
# =============================
if 'ตำบล' in filtered_df.columns:
    st.subheader('📊 จำนวนผู้ป่วยในแต่ละตำบล (Top 10)')
    sub_df = (
        filtered_df.groupby('ตำบล')
        .size()
        .reset_index(name='จำนวนผู้ป่วย')
        .sort_values('จำนวนผู้ป่วย', ascending=False)
    )
    bar_fig = px.bar(sub_df.head(10), x='ตำบล', y='จำนวนผู้ป่วย', text='จำนวนผู้ป่วย', title='Top 10 ตำบลที่มีผู้ป่วยมากที่สุด')
    bar_fig.update_traces(textposition='outside')
    st.plotly_chart(bar_fig, use_container_width=True)

# =============================
# 🔹 VISUALIZATION 3: สัดส่วนเพศผู้ป่วย
# =============================
if 'เพศ' in filtered_df.columns:
    st.subheader('🧍‍♀️ สัดส่วนผู้ป่วยตามเพศ')
    pie_df = filtered_df['เพศ'].value_counts().reset_index()
    pie_df.columns = ['เพศ', 'จำนวน']
    pie_fig = px.pie(pie_df, values='จำนวน', names='เพศ', title='สัดส่วนเพศของผู้ป่วย', hole=0.3)
    st.plotly_chart(pie_fig, use_container_width=True)

# =============================
# 🔹 VISUALIZATION 4: โรคที่พบบ่อยที่สุด
# =============================
if 'โรคหลัก' in filtered_df.columns:
    st.subheader('🩺 10 อันดับโรคที่พบบ่อยที่สุด')
    disease_df = (
        filtered_df['โรคหลัก']
        .value_counts()
        .reset_index()
        .rename(columns={'index': 'โรคหลัก', 'โรคหลัก': 'จำนวน'})
        .head(10)
    )
    disease_fig = px.bar(disease_df, x='โรคหลัก', y='จำนวน', text='จำนวน', title='10 อันดับโรคที่พบบ่อยที่สุด')
    disease_fig.update_traces(textposition='outside')
    st.plotly_chart(disease_fig, use_container_width=True)

# =============================
# 🔹 ตารางข้อมูลดิบ
# =============================
st.subheader('📋 ข้อมูลดิบ')
st.dataframe(filtered_df, use_container_width=True)

st.caption('ข้อมูลจาก Google Sheet: PM2.5 Surveillance Dashboard | อัปเดตอัตโนมัติ')
