import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def create_sidebar_filters(df_patients):
    """สร้างเมนูด้านข้างสำหรับกรองข้อมูล พร้อมระบบเลือกวัน Lag"""
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/1163/1163661.png", width=65) 
    st.sidebar.header("⚙️ ตัวกรองและตั้งค่า")
    
    # 1. กรองปี (เปลี่ยนเป็น Checkbox)
    st.sidebar.markdown("**📅 เลือกช่วงเวลา (ปี)**")
    selected_year = []
    if not df_patients.empty:
        years = sorted(df_patients['Date'].dt.year.dropna().unique().astype(int))
        for y in years:
            if st.sidebar.checkbox(str(y), value=True, key=f"year_{y}"):
                selected_year.append(y)

    st.sidebar.markdown("---")

    # 2. ตั้งค่า Lag Analysis (หัวใจสำคัญใหม่)
    st.sidebar.markdown("**⏳ วิเคราะห์ผลกระทบย้อนหลัง (Lag)**")
    lag_days = st.sidebar.slider(
        "จำนวนวัน Lag (Exposure Lag)", 
        min_value=0, 
        max_value=14, 
        value=0,
        help="การคำนวณผลกระทบของฝุ่นย้อนไปกี่วัน (ตัวอย่าง: เลือก 3 วัน คือคำนวณผลฝุ่นเมื่อ 3 วันก่อนต่อคนไข้ที่มาวันนี้)"
    )

    st.sidebar.markdown("---")

    # 3. กรองกลุ่มโรค
    st.sidebar.markdown("**🩺 กลุ่มโรคเฝ้าระวัง**")
    disease_groups = df_patients['4 กลุ่มโรคเฝ้าระวัง'].dropna().unique()
    selected_disease = []
    for d in disease_groups:
        if st.sidebar.checkbox(d, value=True):
            selected_disease.append(d)

    st.sidebar.markdown("---")
    
    # 3.5 กรองรหัสโรค ICD-10 (ขึ้นต้นด้วยรหัสที่กำหนด) แบบ Checkbox
    st.sidebar.markdown("**📌 รหัสโรค ICD-10**")
    st.sidebar.caption("(เลื่อนเพื่อดูรหัสทั้งหมด, เว้นว่างเพื่อดูทุกรหัสโรค)")
    target_icd10 = [
        "I21.0", "I21.1", "I21.2", "I21.3", "I21.4", "I21.9", "I22.0", "I22.1", "I22.8", "I22.9",
        "I24.0", "I24.1", "I24.8", "I24.9", "H10.0", "H10.1", "H10.2", "H10.3", "H10.4", "H10.5",
        "H10.8", "H10.9", "J45.0", "J45.1", "J45.2", "J45.3", "J45.4", "J44.2", "J44.0", "J44.1",
        "J44.8", "J44.9", "L30.9", "L50.0", "L50.1", "L50.2", "L50.3", "L50.4", "L50.5", "L50.6",
        "L50.8", "L50.9", "Y96", "Y97", "Z58.1"
    ]
    
    selected_icd10 = []
    # ใช้ container กำหนดความสูงเพื่อให้เกิด Scrollbar แทน expander
    with st.sidebar.container(height=250):
        for icd in target_icd10:
            if st.checkbox(icd, value=False, key=f"icd_{icd}"):
                selected_icd10.append(icd)

    st.sidebar.markdown("---")

    # 4. กรองอาการเฉียบพลัน
    st.sidebar.markdown("**🚨 การคัดกรองพิเศษ**")
    acute_only = st.sidebar.toggle("วิเคราะห์เฉพาะเคสเฉียบพลัน", value=False)

    # 5. กรองกลุ่มเปราะบาง (เปลี่ยนเป็น Checkbox)
    st.sidebar.markdown("**🛡️ กลุ่มเปราะบาง**")
    selected_vulnerable = []
    if 'กลุ่มเปราะบาง' in df_patients.columns:
        raw_groups = df_patients['กลุ่มเปราะบาง'].dropna().unique()
        vulnerable_groups = [g for g in raw_groups if g != "ข้อมูลอายุไม่ถูกต้อง"]
        for vg in vulnerable_groups:
            if st.sidebar.checkbox(vg, value=False, key=f"vul_{vg}"):
                selected_vulnerable.append(vg)

    return selected_year, selected_disease, selected_vulnerable, acute_only, lag_days, selected_icd10

def plot_trend_dual_axis(df_filtered, df_pm25):
    """สร้างกราฟ 2 แกน แสดงสัดส่วนอาการเฉียบพลันเทียบกับ PM2.5"""
    if df_filtered.empty or df_pm25.empty:
        st.info("📌 ไม่มีข้อมูลเพียงพอสำหรับสร้างกราฟแสดงแนวโน้ม")
        return

    available_years = df_filtered['Month_Year'].dt.year.unique()
    df_pm25_plot = df_pm25[df_pm25['Month_Year'].dt.year.isin(available_years)].copy()

    trend_data = df_filtered.groupby(['Month_Year', 'Acute_Label']).size().reset_index(name='Patient_Count')
    trend_data['Month_Year'] = trend_data['Month_Year'].dt.to_timestamp()
    df_pm25_plot['Month_Year'] = df_pm25_plot['Month_Year'].dt.to_timestamp()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    labels = trend_data['Acute_Label'].unique()
    colors = {'อาการเฉียบพลัน': '#ef4444', 'อาการทั่วไป': '#94a3b8'}
    
    for label in labels:
        df_sub = trend_data[trend_data['Acute_Label'] == label]
        fig.add_trace(go.Bar(x=df_sub['Month_Year'], y=df_sub['Patient_Count'], name=label, marker_color=colors.get(label, '#4ecdc4'), opacity=0.85), secondary_y=False)

    fig.add_trace(go.Scatter(x=df_pm25_plot['Month_Year'], y=df_pm25_plot['PM25'], name="ค่าเฉลี่ย PM2.5 (µg/m³)", mode='lines+markers', line=dict(color='#2d3436', width=3, shape='spline'), marker=dict(size=8, color='#d63031', line=dict(width=2, color='white'))), secondary_y=True)

    fig.update_layout(font_family="'Sarabun', sans-serif", template="plotly_white", barmode='stack', hovermode="x unified", margin=dict(l=20, r=20, t=30, b=20), legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5))
    fig.update_yaxes(title_text="จำนวนผู้ป่วย (คน)", secondary_y=False, showgrid=False)
    fig.update_yaxes(title_text="ค่า PM2.5 (µg/m³)", secondary_y=True, showgrid=True, gridcolor='#f1f2f6')

    st.plotly_chart(fig, use_container_width=True)

def plot_icd10_trend(df_icd, df_pm25, icd_name):
    if df_icd.empty or df_pm25.empty: return
    trend_data = df_icd.groupby('Month_Year').size().reset_index(name='Patient_Count')
    trend_data['Month_Year'] = trend_data['Month_Year'].dt.to_timestamp()
    df_pm_p = df_pm25[df_pm25['Month_Year'].dt.year.isin(df_icd['Month_Year'].dt.year.unique())].copy()
    df_pm_p['Month_Year'] = df_pm_p['Month_Year'].dt.to_timestamp()
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=trend_data['Month_Year'], y=trend_data['Patient_Count'], name=f"ผู้ป่วยรหัส {icd_name}", marker_color='#8b5cf6'), secondary_y=False)
    fig.add_trace(go.Scatter(x=df_pm_p['Month_Year'], y=df_pm_p['PM25'], name="ค่า PM2.5", mode='lines+markers', line=dict(color='#ef4444')), secondary_y=True)
    fig.update_layout(font_family="'Sarabun', sans-serif", template="plotly_white", margin=dict(l=20, r=20, t=30, b=20), height=400)
    st.plotly_chart(fig, use_container_width=True)

def plot_demographics(df_filtered):
    if df_filtered.empty: return
    disease_counts = df_filtered['4 กลุ่มโรคเฝ้าระวัง'].value_counts().reset_index()
    disease_counts.columns = ['Disease', 'Count']
    fig_pie = px.pie(disease_counts, values='Count', names='Disease', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
    fig_pie.update_layout(font_family="'Sarabun', sans-serif", margin=dict(l=20, r=20, t=10, b=10), height=300)
    st.plotly_chart(fig_pie, use_container_width=True)
    if 'กลุ่มเปราะบาง' in df_filtered.columns:
        focus_groups = ['เด็ก', 'ผู้สูงอายุ', 'หญิงตั้งครรภ์']
        vul_data = df_filtered[df_filtered['กลุ่มเปราะบาง'].isin(focus_groups)]
        if not vul_data.empty:
            vul_counts = vul_data['กลุ่มเปราะบาง'].value_counts().reset_index()
            vul_counts.columns = ['Vulnerable Group', 'Count']
            fig_vul = px.bar(vul_counts, y='Vulnerable Group', x='Count', orientation='h', text='Count', color='Vulnerable Group', color_discrete_map={'ผู้สูงอายุ': '#ff9f43', 'เด็ก': '#00d2d3', 'หญิงตั้งครรภ์': '#ff9ff3'})
            fig_vul.update_layout(font_family="'Sarabun', sans-serif", showlegend=False, height=180, margin=dict(l=10, r=40, t=10, b=10))
            st.plotly_chart(fig_vul, use_container_width=True)

def plot_geographic(df_filtered):
    if df_filtered.empty or 'ตำบล' not in df_filtered.columns: return
    geo_data = df_filtered['ตำบล'].value_counts().head(10).reset_index()
    geo_data.columns = ['Sub-district', 'Count']
    fig = px.bar(geo_data, y='Sub-district', x='Count', orientation='h', text='Count', color='Count', color_continuous_scale='Reds')
    fig.update_layout(font_family="'Sarabun', sans-serif", yaxis={'categoryorder':'total ascending'}, margin=dict(l=20, r=20, t=20, b=20), coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)
