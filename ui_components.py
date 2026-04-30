import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def create_sidebar_filters(df_patients):
    """สร้างเมนูด้านข้างสำหรับกรองข้อมูล พร้อมตัวเลือกอาการเฉียบพลัน"""
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/1163/1163661.png", width=65) 
    st.sidebar.header("⚙️ ตัวกรองข้อมูล")
    
    # 1. กรองปี
    if not df_patients.empty:
        years = df_patients['Date'].dt.year.dropna().unique().astype(int)
        years_list = ["ทุกปี"] + sorted(years)
        selected_year_input = st.sidebar.selectbox("📅 เลือกช่วงเวลา (ปี)", options=years_list)
        selected_year = sorted(years) if selected_year_input == "ทุกปี" else [selected_year_input]
    else:
        selected_year = []

    st.sidebar.markdown("---")

    # 2. กรองกลุ่มโรค
    st.sidebar.markdown("**🩺 กลุ่มโรคเฝ้าระวัง**")
    disease_groups = df_patients['4 กลุ่มโรคเฝ้าระวัง'].dropna().unique()
    selected_disease = []
    for d in disease_groups:
        if st.sidebar.checkbox(d, value=True):
            selected_disease.append(d)

    st.sidebar.markdown("---")
    
    # 3. [NEW] กรองอาการเฉียบพลัน (Toggle)
    st.sidebar.markdown("**🚨 การคัดกรองพิเศษ**")
    acute_only = st.sidebar.toggle("วิเคราะห์เฉพาะเคสเฉียบพลัน", value=False, help="สแกนหาคำว่า 'เฉียบพลัน/Acute' ในบันทึกการวินิจฉัย")

    # 4. กรองกลุ่มเปราะบาง
    st.sidebar.markdown("**🛡️ กลุ่มเปราะบาง**")
    if 'กลุ่มเปราะบาง' in df_patients.columns:
        raw_groups = df_patients['กลุ่มเปราะบาง'].dropna().unique()
        vulnerable_groups = [g for g in raw_groups if g != "ข้อมูลอายุไม่ถูกต้อง"]
        selected_vulnerable = st.sidebar.multiselect("เลือกกลุ่มเปราะบาง", options=vulnerable_groups, default=[])
    else:
        selected_vulnerable = []

    return selected_year, selected_disease, selected_vulnerable, acute_only

def plot_trend_dual_axis(df_filtered, df_pm25):
    """สร้างกราฟ 2 แกน แสดงสัดส่วนอาการเฉียบพลันเทียบกับ PM2.5"""
    if df_filtered.empty or df_pm25.empty:
        st.info("📌 ไม่มีข้อมูลเพียงพอสำหรับสร้างกราฟแสดงแนวโน้ม")
        return

    available_years = df_filtered['Month_Year'].dt.year.unique()
    df_pm25_plot = df_pm25[df_pm25['Month_Year'].dt.year.isin(available_years)].copy()

    # นับจำนวนแยกตามประเภทเฉียบพลัน
    trend_data = df_filtered.groupby(['Month_Year', 'Acute_Label']).size().reset_index(name='Patient_Count')
    trend_data['Month_Year'] = trend_data['Month_Year'].dt.to_timestamp()
    df_pm25_plot['Month_Year'] = df_pm25_plot['Month_Year'].dt.to_timestamp()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. แท่งผู้ป่วยแยกสี (Stacked Bar)
    labels = trend_data['Acute_Label'].unique()
    colors = {'อาการเฉียบพลัน': '#ef4444', 'อาการทั่วไป': '#94a3b8'}
    
    for label in labels:
        df_sub = trend_data[trend_data['Acute_Label'] == label]
        fig.add_trace(
            go.Bar(
                x=df_sub['Month_Year'], 
                y=df_sub['Patient_Count'], 
                name=label, 
                marker_color=colors.get(label, '#4ecdc4'),
                opacity=0.85
            ),
            secondary_y=False,
        )

    # 2. เส้น PM2.5
    fig.add_trace(
        go.Scatter(
            x=df_pm25_plot['Month_Year'], y=df_pm25_plot['PM25'], 
            name="ค่าเฉลี่ย PM2.5 (µg/m³)", mode='lines+markers', 
            line=dict(color='#2d3436', width=3, shape='spline'), 
            marker=dict(size=8, color='#d63031', line=dict(width=2, color='white'))
        ),
        secondary_y=True,
    )

    fig.update_layout(
        font_family="'Sarabun', sans-serif", template="plotly_white", barmode='stack',
        hovermode="x unified", margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5)
    )
    
    fig.update_yaxes(title_text="จำนวนผู้ป่วย (คน)", secondary_y=False, showgrid=False)
    fig.update_yaxes(title_text="ค่า PM2.5 (µg/m³)", secondary_y=True, showgrid=True, gridcolor='#f1f2f6')

    st.plotly_chart(fig, use_container_width=True)

# ... (ฟังก์ชันอื่นๆ ยังคงเดิม) ...
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
