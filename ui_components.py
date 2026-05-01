import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

@st.cache_data(ttl=3600)
def fetch_icd10_mapping():
    """ดึงข้อมูลคำแปลรหัสโรค ICD-10 จาก Google Sheets"""
    url = "https://docs.google.com/spreadsheets/d/1vvQ8YLChHXvCowQQzcKIeV4PWt0CCt76f5Sj3fNTOV0/export?format=csv&gid=879233407"
    try:
        # อ่านข้อมูลเป็น string เพื่อป้องกันปัญหาแปลง type ผิดพลาด
        df = pd.read_csv(url, dtype=str)
        # ดึงคอลัมน์ B (index 1) เป็นรหัส และคอลัมน์ C (index 2) เป็นคำแปล
        df_valid = df.iloc[:, [1, 2]].dropna()
        mapping = dict(zip(df_valid.iloc[:, 0].str.strip(), df_valid.iloc[:, 1].str.strip()))
        return mapping
    except:
        return {}

def reset_filters():
    """ฟังก์ชันกำหนดค่า session_state กลับเป็นค่าเริ่มต้น เพื่อบังคับรีเซ็ต widget ทุกตัวอย่างสมบูรณ์"""
    for key in st.session_state.keys():
        if key.startswith("year_") or key.startswith("disease_"):
            st.session_state[key] = True  # ค่าเริ่มต้นคือเลือกทั้งหมด
        elif key.startswith("icd_") or key.startswith("vul_") or key == "acute_only":
            st.session_state[key] = False # ค่าเริ่มต้นคือไม่ถูกเลือก
        elif key == "lag_days":
            st.session_state[key] = 0     # ค่าเริ่มต้นของ Lag คือ 0

def create_sidebar_filters(df_patients):
    """สร้างเมนูด้านข้างสำหรับกรองข้อมูล พร้อมระบบนับจำนวนสัมพันธ์กัน (Cascading Filters)"""
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/1163/1163661.png", width=65) 
    st.sidebar.header("⚙️ ตัวกรองและตั้งค่า")
    
    # เพิ่มปุ่มรีเซ็ต
    st.sidebar.button("🔄 รีเซ็ตค่าเริ่มต้น", on_click=reset_filters, type="primary", use_container_width=True)
    st.sidebar.markdown("---")

    # ดึง Data คำแปลรอไว้
    icd_mapping = fetch_icd10_mapping()

    # สร้าง df_temp เพื่อใช้คำนวณจำนวนเคสแบบเรียลไทม์ตามตัวกรองที่ถูกเลือก
    df_temp = df_patients.copy()
    
    # 1. กรองปี
    st.sidebar.markdown("**📅 เลือกช่วงเวลา (ปี)**")
    selected_year = []
    if not df_patients.empty:
        years = sorted(df_patients['Date'].dt.year.dropna().unique().astype(int))
        for y in years:
            # คำนวณจำนวนทั้งหมดของปีนั้นๆ (อิงจากข้อมูลตั้งต้นเสมอ)
            count = len(df_patients[df_patients['Date'].dt.year == y])
            if st.sidebar.checkbox(f"{y} ({count:,} เคส)", value=True, key=f"year_{y}"):
                selected_year.append(y)
                
    # อัปเดต df_temp ตามปีที่เลือก เพื่อให้ตัวกรองด้านล่างนับจำนวนได้สอดคล้องกัน
    if selected_year:
        df_temp = df_temp[df_temp['Date'].dt.year.isin(selected_year)]
    else:
        df_temp = pd.DataFrame(columns=df_temp.columns)

    st.sidebar.markdown("---")

    # 2. ตั้งค่า Lag Analysis
    st.sidebar.markdown("**⏳ วิเคราะห์ผลกระทบย้อนหลัง (Lag)**")
    lag_days = st.sidebar.slider(
        "จำนวนวัน Lag (Exposure Lag)", 
        min_value=0, 
        max_value=14, 
        value=0,
        key="lag_days",
        help="การคำนวณผลกระทบของฝุ่นย้อนไปกี่วัน (ตัวอย่าง: เลือก 3 วัน คือคำนวณผลฝุ่นเมื่อ 3 วันก่อนต่อคนไข้ที่มาวันนี้)"
    )

    st.sidebar.markdown("---")

    # 3. กรองกลุ่มโรค (จำนวนเคสจะผันแปรตาม "ปี" ที่เลือกด้านบน)
    st.sidebar.markdown("**🩺 กลุ่มโรคเฝ้าระวัง**")
    disease_groups = df_patients['4 กลุ่มโรคเฝ้าระวัง'].dropna().unique()
    selected_disease = []
    for d in disease_groups:
        count = len(df_temp[df_temp['4 กลุ่มโรคเฝ้าระวัง'] == d])
        if st.sidebar.checkbox(f"{d} ({count:,})", value=True, key=f"disease_{d}"):
            selected_disease.append(d)

    # อัปเดต df_temp ตามกลุ่มโรคที่เลือก เพื่อส่งผลไปยังการนับรหัส ICD-10
    if selected_disease:
        df_temp = df_temp[df_temp['4 กลุ่มโรคเฝ้าระวัง'].isin(selected_disease)]
    else:
        df_temp = pd.DataFrame(columns=df_temp.columns)

    st.sidebar.markdown("---")
    
    # 3.5 กรองรหัสโรค ICD-10 (จำนวนเคสจะผันแปรตาม "ปี" และ "กลุ่มโรค" ที่เลือกด้านบน)
    st.sidebar.markdown("**📌 รหัสโรค ICD-10**")
    st.sidebar.caption("(เว้นว่างเพื่อดูทุกรหัสโรคที่เกี่ยวข้อง)")
    target_icd10 = [
        "I21.0", "I21.1", "I21.2", "I21.3", "I21.4", "I21.9", "I22.0", "I22.1", "I22.8", "I22.9",
        "I24.0", "I24.1", "I24.8", "I24.9", "H10.0", "H10.1", "H10.2", "H10.3", "H10.4", "H10.5",
        "H10.8", "H10.9", "J45.0", "J45.1", "J45.2", "J45.3", "J45.4", "J44.2", "J44.0", "J44.1",
        "J44.8", "J44.9", "L30.9", "L50.0", "L50.1", "L50.2", "L50.3", "L50.4", "L50.5", "L50.6",
        "L50.8", "L50.9", "Y96", "Y97", "Z58.1"
    ]
    
    selected_icd10 = []
    
    # คำนวณจำนวนรหัส ICD-10 ล่วงหน้าเพื่อความรวดเร็ว
    icd_counts = {icd: 0 for icd in target_icd10}
    if not df_temp.empty and 'ICD10_โรคเฝ้าระวัง' in df_temp.columns:
        val_counts = df_temp['ICD10_โรคเฝ้าระวัง'].dropna().astype(str).value_counts().to_dict()
        for icd in target_icd10:
            icd_counts[icd] = sum(count for key, count in val_counts.items() if key.startswith(icd))

    # เพิ่มความสูง container เป็น 400 เพื่อให้มีพื้นที่พอแสดงคำแปลโรคที่ยาวขึ้น
    with st.sidebar.container(height=400):
        for icd in target_icd10:
            count = icd_counts.get(icd, 0)
            
            # ดึงคำแปล ถ้ารหัสเต็มไม่มีให้ใช้ 3 ตัวแรก (เช่น J45 จาก J45.0)
            desc = icd_mapping.get(icd)
            if not desc:
                desc = icd_mapping.get(icd[:3], "ไม่พบข้อมูลคำแปล")
            
            # แสดงรหัส - คำแปล (จำนวนเคส)
            label = f"{icd} - {desc} ({count:,})"
            if st.checkbox(label, value=False, key=f"icd_{icd}"):
                selected_icd10.append(icd)
                
    # อัปเดต df_temp ตาม ICD-10 เพื่อส่งผลไปยังการนับกลุ่มเปราะบาง
    if selected_icd10:
        df_temp = df_temp[df_temp['ICD10_โรคเฝ้าระวัง'].astype(str).str.startswith(tuple(selected_icd10), na=False)]

    st.sidebar.markdown("---")

    # 4. กรองอาการเฉียบพลัน
    st.sidebar.markdown("**🚨 การคัดกรองพิเศษ**")
    acute_count = len(df_temp[df_temp['Is_Acute'] == True]) if not df_temp.empty and 'Is_Acute' in df_temp.columns else 0
    acute_only = st.sidebar.toggle(f"วิเคราะห์เฉพาะเคสเฉียบพลัน ({acute_count:,})", value=False, key="acute_only")
    
    if acute_only:
        df_temp = df_temp[df_temp['Is_Acute'] == True]

    # 5. กรองกลุ่มเปราะบาง
    st.sidebar.markdown("**🛡️ กลุ่มเปราะบาง**")
    selected_vulnerable = []
    if 'กลุ่มเปราะบาง' in df_patients.columns:
        raw_groups = df_patients['กลุ่มเปราะบาง'].dropna().unique()
        vulnerable_groups = [g for g in raw_groups if g != "ข้อมูลอายุไม่ถูกต้อง"]
        for vg in vulnerable_groups:
            count = len(df_temp[df_temp['กลุ่มเปราะบาง'] == vg])
            if st.sidebar.checkbox(f"{vg} ({count:,})", value=False, key=f"vul_{vg}"):
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
