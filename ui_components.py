import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def create_sidebar_filters(df_patients):
    """สร้างเมนูด้านข้าง ปีเป็น Checkbox, มีปุ่มรีเซ็ต, มี Scrollbar กลุ่มเปราะบาง"""
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/1163/1163661.png", width=65) 
    st.sidebar.header("⚙️ ตัวกรองข้อมูล")
    
    # --- ปุ่มรีเซ็ตตัวกรอง ---
    if st.sidebar.button("🔄 ล้างตัวกรองทั้งหมด", use_container_width=True):
        for key in st.session_state.keys():
            del st.session_state[key]
        try:
            st.rerun()
        except AttributeError:
            st.experimental_rerun()

    st.sidebar.markdown("---")
    
    # 1. เลือกช่วงเวลา (ปรับกลับเป็น Checkbox)
    st.sidebar.markdown("**📅 เลือกช่วงเวลา (ปี)**")
    selected_year = []
    if not df_patients.empty:
        years = df_patients['Date'].dt.year.dropna().unique().astype(int)
        for y in sorted(years):
            # แสดงผลเป็น พ.ศ. แต่เก็บค่าเป็น ค.ศ.
            if st.sidebar.checkbox(str(y + 543), value=True, key=f"year_{y}"):
                selected_year.append(y)

    st.sidebar.markdown("---")

    # 2. กลุ่มโรคเฝ้าระวัง (Checkbox)
    st.sidebar.markdown("**🩺 กลุ่มโรคเฝ้าระวัง**")
    selected_disease = []
    if '4 กลุ่มโรคเฝ้าระวัง' in df_patients.columns:
        disease_groups = df_patients['4 กลุ่มโรคเฝ้าระวัง'].dropna().unique()
        for d in disease_groups:
            display_name = "โรคร่วม Z58.1" if d == "ไม่จัดอยู่ใน 4 กลุ่มโรค" else d
            if st.sidebar.checkbox(display_name, value=True, key=f"disease_{d}"):
                selected_disease.append(d)

    st.sidebar.markdown("---")
    
    # 3. การคัดกรองพิเศษ (กล่อง Scrollbar + Checkbox)
    st.sidebar.markdown("**🌟 การคัดกรองพิเศษ**")
    selected_vulnerable = []
    
    with st.sidebar.container(height=300):
        st.markdown("**กลุ่มเปราะบาง**")
        if 'กลุ่มเปราะบาง' in df_patients.columns:
            raw_groups = df_patients['กลุ่มเปราะบาง'].dropna().unique()
            vulnerable_groups = [g for g in raw_groups if g != "ข้อมูลอายุไม่ถูกต้อง"]
            for v in vulnerable_groups:
                if st.checkbox(str(v), value=False, key=f"vul_{v}"):
                    selected_vulnerable.append(v)
        else:
            st.caption("⚠️ ไม่พบคอลัมน์ 'กลุ่มเปราะบาง'")

    st.sidebar.markdown("---")

    return selected_year, selected_disease, selected_vulnerable

def plot_trend_dual_axis(df_filtered, df_pm25):
    if df_filtered.empty or df_pm25.empty:
        st.info("📌 ไม่มีข้อมูลเพียงพอสำหรับสร้างกราฟแสดงแนวโน้ม")
        return

    available_years = df_filtered['Month_Year'].dt.year.unique()
    df_pm25_plot = df_pm25[df_pm25['Month_Year'].dt.year.isin(available_years)].copy()

    trend_data = df_filtered.groupby(['Month_Year']).size().reset_index(name='Patient_Count')
    trend_data['Month_Year'] = trend_data['Month_Year'].dt.to_timestamp()
    df_pm25_plot['Month_Year'] = df_pm25_plot['Month_Year'].dt.to_timestamp()

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=trend_data['Month_Year'], 
            y=trend_data['Patient_Count'], 
            name="จำนวนผู้ป่วยทั้งหมด", 
            marker_color='#ff6b6b',
            opacity=0.85
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df_pm25_plot['Month_Year'], 
            y=df_pm25_plot['PM25'], 
            name="ค่าเฉลี่ย PM2.5 (µg/m³)", 
            mode='lines+markers', 
            line=dict(color='#2d3436', width=3, shape='spline'),
            marker=dict(size=8, color='#d63031', line=dict(width=2, color='white'))
        ),
        secondary_y=True,
    )

    fig.update_layout(
        font_family="'Sarabun', 'Segoe UI', 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji', sans-serif",
        template="plotly_white", barmode='group', hovermode="x unified",
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5)
    )
    fig.update_yaxes(title_text="จำนวนผู้ป่วย (คน)", secondary_y=False, showgrid=False)
    fig.update_yaxes(title_text="ค่า PM2.5 (µg/m³)", secondary_y=True, showgrid=True, gridcolor='#f1f2f6')
    st.plotly_chart(fig, use_container_width=True)

def plot_demographics(df_filtered):
    if df_filtered.empty:
        st.info("📌 ไม่มีข้อมูลประชากรศาสตร์ตรงตามเงื่อนไข")
        return

    disease_counts = df_filtered['4 กลุ่มโรคเฝ้าระวัง'].value_counts().reset_index()
    disease_counts.columns = ['Disease', 'Count']
    if not disease_counts.empty:
        fig_pie = px.pie(disease_counts, values='Count', names='Disease', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_pie.update_traces(textposition='inside', textinfo='percent+label', showlegend=False)
        fig_pie.update_layout(
            font_family="'Sarabun', 'Segoe UI', 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji', sans-serif",
            template="plotly_white", margin=dict(l=20, r=20, t=10, b=10), height=300
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("ไม่พบข้อมูลสัดส่วนกลุ่มโรค")

    if 'กลุ่มเปราะบาง' in df_filtered.columns:
        st.markdown("<h5 style='text-align: center; color: #64748b; margin-top: 15px;'>🛡️ กลุ่มเปราะบางที่ต้องเฝ้าระวังพิเศษ</h5>", unsafe_allow_html=True)
        focus_groups = ['เด็ก', 'ผู้สูงอายุ', 'หญิงตั้งครรภ์']
        vul_data = df_filtered[df_filtered['กลุ่มเปราะบาง'].isin(focus_groups)]
        if not vul_data.empty:
            vul_counts = vul_data['กลุ่มเปราะบาง'].value_counts().reset_index()
            vul_counts.columns = ['Vulnerable Group', 'Count']
            total_patients = len(df_filtered)
            vul_counts['Percent'] = (vul_counts['Count'] / total_patients * 100).round(1)
            vul_counts['Display_Text'] = vul_counts['Count'].astype(str) + " คน (" + vul_counts['Percent'].astype(str) + "%)"
            
            fig_vul = px.bar(
                vul_counts, y='Vulnerable Group', x='Count', orientation='h', text='Display_Text', color='Vulnerable Group',
                color_discrete_map={'ผู้สูงอายุ': '#ff9f43', 'เด็ก': '#00d2d3', 'หญิงตั้งครรภ์': '#ff9ff3'}
            )
            fig_vul.update_traces(textposition='outside', textfont_size=13)
            fig_vul.update_layout(
                font_family="'Sarabun', 'Segoe UI', 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji', sans-serif",
                template="plotly_white", showlegend=False, xaxis_title="", yaxis_title="", xaxis_visible=False,
                yaxis={'categoryorder':'total ascending'}, margin=dict(l=10, r=40, t=10, b=10), height=180
            )
            st.plotly_chart(fig_vul, use_container_width=True)
            
            total_vul = vul_counts['Count'].sum()
            vul_percent_total = (total_vul / total_patients * 100).round(1)
            st.markdown(f"<p style='text-align: center; font-size: 0.95rem; color: #ef4444; background-color: #fef2f2; padding: 10px; border-radius: 8px;'><b>⚠️ พบผู้ป่วยกลุ่มเปราะบางรวม {total_vul:,} คน (คิดเป็น {vul_percent_total}% ของผู้ป่วยทั้งหมด)</b></p>", unsafe_allow_html=True)
        else:
            st.info("ไม่พบผู้ป่วยในกลุ่มเปราะบาง (เด็ก, ผู้สูงอายุ, หญิงตั้งครรภ์) ตามเงื่อนไขที่เลือก")

def plot_geographic(df_filtered):
    if df_filtered.empty or 'ตำบล' not in df_filtered.columns:
        st.info("📌 ไม่มีข้อมูลพื้นที่ตรงตามเงื่อนไข")
        return

    geo_data = df_filtered['ตำบล'].value_counts().head(10).reset_index()
    geo_data.columns = ['Sub-district', 'Count']
    if not geo_data.empty:
        fig = px.bar(geo_data, y='Sub-district', x='Count', orientation='h', text='Count', color='Count', color_continuous_scale='Reds')
        fig.update_traces(textposition='outside')
        fig.update_layout(
            font_family="'Sarabun', 'Segoe UI', 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji', sans-serif",
            template="plotly_white", yaxis={'categoryorder':'total ascending'}, xaxis_title="จำนวนผู้ป่วย (คน)",
            yaxis_title="", margin=dict(l=20, r=20, t=20, b=20), coloraxis_showscale=False
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ไม่พบข้อมูลระดับตำบล")
