import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def create_sidebar_filters(df_patients):
    """สร้างเมนูด้านข้างสำหรับกรองข้อมูล (เวอร์ชันปรับปรุง UI ให้ใช้งานง่ายขึ้น)"""
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3209/3209935.png", width=60) # ไอคอนตกแต่ง
    st.sidebar.header("⚙️ ตัวกรองข้อมูล")
    
    # 1. กรองปี (Selectbox)
    if not df_patients.empty:
        years = df_patients['Date'].dt.year.dropna().unique().astype(int)
        years_list = ["ทุกปี"] + sorted(years).tolist()
        
        selected_year_input = st.sidebar.selectbox("📅 เลือกช่วงเวลา (ปี)", options=years_list)
        
        if selected_year_input == "ทุกปี":
            selected_year = sorted(years).tolist()
        else:
            selected_year = [selected_year_input]
    else:
        selected_year = []

    st.sidebar.markdown("---")

    # 2. กรองกลุ่มโรค (Checkbox)
    st.sidebar.markdown("**🩺 กลุ่มโรคเฝ้าระวัง**")
    disease_groups = df_patients['4 กลุ่มโรคเฝ้าระวัง'].dropna().unique()
    selected_disease = []
    
    for d in disease_groups:
        if st.sidebar.checkbox(d, value=True):
            selected_disease.append(d)

    st.sidebar.markdown("---")

    # 3. กรองประเภทการมา รพ.
    walk_in_filter = st.sidebar.radio(
        "🚨 รูปแบบการเข้ารับบริการ",
        ("ทั้งหมด", "เฉพาะ Walk-in (ไม่ได้นัด)", "เฉพาะมาตามนัด")
    )

    return selected_year, selected_disease, walk_in_filter

def plot_trend_dual_axis(df_filtered, df_pm25):
    """สร้างกราฟ 2 แกน: แกนซ้าย(แท่ง)=ผู้ป่วย, แกนขวา(เส้น)=PM2.5 (เวอร์ชันดูง่ายและคลีนขึ้น)"""
    if df_filtered.empty or df_pm25.empty:
        st.info("📌 ไม่มีข้อมูลเพียงพอสำหรับสร้างกราฟแสดงแนวโน้ม")
        return

    available_years = df_filtered['Month_Year'].dt.year.unique()
    df_pm25_plot = df_pm25[df_pm25['Month_Year'].dt.year.isin(available_years)].copy()

    trend_data = df_filtered.groupby(['Month_Year', 'Is_Walk_in']).size().reset_index(name='Patient_Count')
    
    trend_data['Month_Year'] = trend_data['Month_Year'].dt.to_timestamp()
    df_pm25_plot['Month_Year'] = df_pm25_plot['Month_Year'].dt.to_timestamp()

    # สร้างกราฟ 2 แกน ปรับดีไซน์ให้มินิมอลและชัดเจน
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. เพิ่มแท่งผู้ป่วย (ปรับสีให้โมเดิร์น)
    for status in trend_data['Is_Walk_in'].unique():
        df_subset = trend_data[trend_data['Is_Walk_in'] == status]
        # โทนสี: ส้มแดงสำหรับ Walk-in (ฉุกเฉิน), น้ำเงินสำหรับนัดมา
        color = '#ff6b6b' if 'Walk-in' in status else '#4ecdc4' 
        fig.add_trace(
            go.Bar(
                x=df_subset['Month_Year'], 
                y=df_subset['Patient_Count'], 
                name=status, 
                marker_color=color,
                opacity=0.85
            ),
            secondary_y=False,
        )

    # 2. เพิ่มเส้น PM2.5 (ปรับให้เส้นเด่นขึ้น)
    fig.add_trace(
        go.Scatter(
            x=df_pm25_plot['Month_Year'], 
            y=df_pm25_plot['PM25'], 
            name="ค่าเฉลี่ย PM2.5 (µg/m³)", 
            mode='lines+markers', 
            line=dict(color='#2d3436', width=3, shape='spline'), # shape='spline' ทำให้เส้นโค้งสวยงาม
            marker=dict(size=8, color='#d63031', line=dict(width=2, color='white'))
        ),
        secondary_y=True,
    )

    fig.update_layout(
        template="plotly_white", # พื้นหลังสีขาวสะอาดตา
        barmode='stack', 
        hovermode="x unified",
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5) # ย้าย Legend ไปตรงกลาง
    )
    
    fig.update_yaxes(title_text="จำนวนผู้ป่วย (คน)", secondary_y=False, showgrid=False)
    fig.update_yaxes(title_text="ค่า PM2.5 (µg/m³)", secondary_y=True, showgrid=True, gridcolor='#f1f2f6')

    st.plotly_chart(fig, use_container_width=True)

def plot_demographics(df_filtered):
    """สร้างกราฟพาย (Donut Chart) ตัดส่วนกราฟความรุนแรงทิ้ง เพื่อความสะอาดตา"""
    if df_filtered.empty:
        st.info("📌 ไม่มีข้อมูลประชากรศาสตร์ตรงตามเงื่อนไข")
        return

    disease_counts = df_filtered['4 กลุ่มโรคเฝ้าระวัง'].value_counts().reset_index()
    disease_counts.columns = ['Disease', 'Count']
    
    if not disease_counts.empty:
        fig_pie = px.pie(
            disease_counts, 
            values='Count', 
            names='Disease', 
            hole=0.5, # ทำให้เป็นทรงโดนัทที่ดูทันสมัย
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label', showlegend=False)
        fig_pie.update_layout(
            template="plotly_white",
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("ไม่พบข้อมูลสัดส่วนกลุ่มโรค")

def plot_geographic(df_filtered):
    """สร้างกราฟแท่งแนวนอน (Bar Chart) แสดงพื้นที่ ปรับให้มีตัวเลขชัดเจน"""
    if df_filtered.empty or 'ตำบล' not in df_filtered.columns:
        st.info("📌 ไม่มีข้อมูลพื้นที่ตรงตามเงื่อนไข")
        return

    geo_data = df_filtered['ตำบล'].value_counts().head(10).reset_index()
    geo_data.columns = ['Sub-district', 'Count']
    
    if not geo_data.empty:
        fig = px.bar(
            geo_data, 
            y='Sub-district', 
            x='Count', 
            orientation='h',
            text='Count', # แสดงตัวเลขบนแท่ง
            color='Count', 
            color_continuous_scale='Reds'
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(
            template="plotly_white",
            yaxis={'categoryorder':'total ascending'},
            xaxis_title="จำนวนผู้ป่วย (คน)",
            yaxis_title="",
            margin=dict(l=20, r=20, t=20, b=20),
            coloraxis_showscale=False # ซ่อนแถบสีด้านขวาให้ดูคลีนขึ้น
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ไม่พบข้อมูลระดับตำบล")
