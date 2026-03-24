import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def create_sidebar_filters(df_patients):
    """สร้างเมนูด้านข้างสำหรับกรองข้อมูล"""
    st.sidebar.header("⚙️ ตัวกรองข้อมูล")
    
    # 1. กรองปี
    if not df_patients.empty:
        years = df_patients['Date'].dt.year.dropna().unique().astype(int)
        selected_year = st.sidebar.multiselect("📅 เลือกปี", options=sorted(years), default=sorted(years))
    else:
        selected_year = []

    # 2. กรองกลุ่มโรค
    disease_groups = df_patients['4 กลุ่มโรคเฝ้าระวัง'].dropna().unique()
    selected_disease = st.sidebar.multiselect("🩺 กลุ่มโรคเฝ้าระวัง", options=disease_groups, default=disease_groups)

    # 3. กรองประเภทการมา รพ.
    st.sidebar.markdown("---")
    st.sidebar.subheader("ตัวกรองเชิงลึก")
    walk_in_filter = st.sidebar.radio(
        "🚨 รูปแบบการเข้ารับบริการ",
        ("ทั้งหมด", "เฉพาะ Walk-in (ไม่ได้นัด)", "เฉพาะมาตามนัด")
    )

    # 4. กรองประเภทผู้ป่วย
    patient_type_filter = st.sidebar.multiselect(
        "👤 ประเภทผู้ป่วย",
        options=["ผู้ป่วยใหม่", "ผู้ป่วยเก่า", "ไม่ระบุ"],
        default=["ผู้ป่วยใหม่", "ผู้ป่วยเก่า", "ไม่ระบุ"]
    )

    return selected_year, selected_disease, walk_in_filter, patient_type_filter

def plot_trend_dual_axis(df_filtered, df_pm25):
    """สร้างกราฟ 2 แกน: แกนซ้าย(แท่ง)=ผู้ป่วย, แกนขวา(เส้น)=PM2.5"""
    if df_filtered.empty or df_pm25.empty:
        st.info("📌 ไม่มีข้อมูลเพียงพอสำหรับสร้างกราฟแสดงแนวโน้ม")
        return

    # แก้ไขจุดที่ 1: กรองข้อมูล PM2.5 ให้ช่วงเวลา (ปี) ตรงกับข้อมูลผู้ป่วยที่ถูกกรองมา
    available_years = df_filtered['Month_Year'].dt.year.unique()
    df_pm25_plot = df_pm25[df_pm25['Month_Year'].dt.year.isin(available_years)].copy()

    # เตรียมข้อมูลนับจำนวนผู้ป่วยรายเดือน
    trend_data = df_filtered.groupby(['Month_Year', 'Is_Walk_in']).size().reset_index(name='Patient_Count')
    
    # แปลง Month_Year กลับเป็น Timestamp สำหรับการพล็อต
    trend_data['Month_Year'] = trend_data['Month_Year'].dt.to_timestamp()
    df_pm25_plot['Month_Year'] = df_pm25_plot['Month_Year'].dt.to_timestamp()

    # สร้างกราฟ 2 แกน
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. เพิ่มแท่งผู้ป่วย (แกนซ้าย)
    for status in trend_data['Is_Walk_in'].unique():
        df_subset = trend_data[trend_data['Is_Walk_in'] == status]
        color = '#ef4444' if 'Walk-in' in status else '#3b82f6' # แดงสำหรับ walk-in, ฟ้าสำหรับนัด
        fig.add_trace(
            go.Bar(x=df_subset['Month_Year'], y=df_subset['Patient_Count'], name=status, marker_color=color),
            secondary_y=False,
        )

    # 2. เพิ่มเส้น PM2.5 (แกนขวา)
    fig.add_trace(
        go.Scatter(x=df_pm25_plot['Month_Year'], y=df_pm25_plot['PM25'], name="PM2.5 (ug/m3)", 
                   mode='lines+markers', line=dict(color='gray', width=3, dash='dot')),
        secondary_y=True,
    )

    fig.update_layout(
        title_text="ความสัมพันธ์ระหว่างจำนวนผู้ป่วยรับบริการและค่าเฉลี่ยฝุ่น PM2.5 รายเดือน",
        barmode='stack', # ให้แท่งซ้อนกัน
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_yaxes(title_text="จำนวนผู้ป่วย (คน)", secondary_y=False)
    fig.update_yaxes(title_text="ค่า PM2.5 (ug/m3)", secondary_y=True)

    st.plotly_chart(fig, use_container_width=True)

def plot_demographics(df_filtered):
    """สร้างกราฟพายและกราฟแท่งสำหรับข้อมูลประชากรศาสตร์และความรุนแรง"""
    # แก้ไขจุดที่ 2: เพิ่มข้อความแจ้งเตือนเมื่อข้อมูลว่างเปล่าแทนการ return ออกไปเฉยๆ
    if df_filtered.empty:
        st.info("📌 ไม่มีข้อมูลประชากรศาสตร์ตรงตามเงื่อนไขที่คุณกรอง")
        return

    col1, col2 = st.columns(2)
    
    with col1:
        # สัดส่วนโรค
        disease_counts = df_filtered['4 กลุ่มโรคเฝ้าระวัง'].value_counts().reset_index()
        disease_counts.columns = ['Disease', 'Count']
        if not disease_counts.empty:
            fig_pie = px.pie(disease_counts, values='Count', names='Disease', title='สัดส่วนกลุ่มโรคที่เข้ารับการรักษา', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("ไม่พบข้อมูลสัดส่วนกลุ่มโรค")

    with col2:
        # ความรุนแรง (Severity)
        sev_counts = df_filtered[df_filtered['Severity'] != 'ไม่ระบุ']['Severity'].value_counts().reset_index()
        sev_counts.columns = ['Severity', 'Count']
        if not sev_counts.empty:
            fig_bar = px.bar(sev_counts, x='Severity', y='Count', title='สถานะความรุนแรง (การจำหน่าย)', color='Severity',
                             color_discrete_map={'รุนแรง (Admit/Refer)': '#ef4444', 'กลับบ้านได้': '#10b981'})
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("ไม่พบข้อมูลความรุนแรง")

def plot_geographic(df_filtered):
    """สร้างกราฟแท่งแนวนอนแสดงพื้นที่ที่พบผู้ป่วยมากที่สุด"""
    # แก้ไขจุดที่ 2 (ต่อ): เพิ่มข้อความแจ้งเตือน
    if df_filtered.empty or 'ตำบล' not in df_filtered.columns:
        st.info("📌 ไม่มีข้อมูลพื้นที่ตรงตามเงื่อนไขที่คุณกรอง")
        return

    # นับจำนวนระดับตำบล (เอาแค่ Top 10)
    geo_data = df_filtered['ตำบล'].value_counts().head(10).reset_index()
    geo_data.columns = ['Sub-district', 'Count']
    
    if not geo_data.empty:
        fig = px.bar(geo_data, y='Sub-district', x='Count', orientation='h', 
                     title='10 อันดับตำบลที่มีผู้ป่วยสูงสุด (ตามตัวกรอง)', 
                     color='Count', color_continuous_scale='Reds')
        fig.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ไม่พบข้อมูลระดับตำบล")
