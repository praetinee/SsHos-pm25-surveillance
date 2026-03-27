import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def create_sidebar_filters(df_patients):
    """สร้างเมนูด้านข้างสำหรับกรองข้อมูล (เวอร์ชันปรับปรุง UI ให้ใช้งานง่ายขึ้น)"""
    # เปลี่ยน URL ของรูปภาพเป็นไอคอนรูปเมฆและลม
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/1163/1163661.png", width=65) 
    st.sidebar.header("⚙️ ตัวกรองข้อมูล")
    
    # 1. กรองปี (Selectbox)
    if not df_patients.empty:
        years = df_patients['Date'].dt.year.dropna().unique().astype(int)
        
        # แก้ไขจุด Error: sorted(years) เป็น list อยู่แล้ว จึงไม่ต้องใช้ .tolist()
        years_list = ["ทุกปี"] + sorted(years)
        
        selected_year_input = st.sidebar.selectbox("📅 เลือกช่วงเวลา (ปี)", options=years_list)
        
        if selected_year_input == "ทุกปี":
            selected_year = sorted(years)
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
        # เปลี่ยนข้อความแสดงผลเฉพาะหน้า UI (Sidebar)
        display_name = "โรคร่วม Z58.1" if d == "ไม่จัดอยู่ใน 4 กลุ่มโรค" else d
        if st.sidebar.checkbox(display_name, value=True):
            selected_disease.append(d)

    st.sidebar.markdown("---")
    
    # 3. กรองกลุ่มเปราะบาง (Multiselect)
    st.sidebar.markdown("**🛡️ กลุ่มเปราะบาง**")
    if 'กลุ่มเปราะบาง' in df_patients.columns:
        # ดึงค่าที่ไม่ซ้ำกัน และกรองคำว่า 'ข้อมูลอายุไม่ถูกต้อง' ทิ้งไป
        raw_groups = df_patients['กลุ่มเปราะบาง'].dropna().unique()
        vulnerable_groups = [g for g in raw_groups if g != "ข้อมูลอายุไม่ถูกต้อง"]
        
        selected_vulnerable = st.sidebar.multiselect(
            "เลือกกลุ่มเปราะบาง",
            options=vulnerable_groups,
            default=[] # ตั้งค่าเริ่มต้นให้เป็นช่องว่าง (ยังไม่เลือกอันไหน)
        )
    else:
        selected_vulnerable = []

    st.sidebar.markdown("---")

    # 4. กรองประเภทการมา รพ.
    walk_in_filter = st.sidebar.radio(
        "🚨 รูปแบบการเข้ารับบริการ",
        ("ทั้งหมด", "เฉพาะ Walk-in (ไม่ได้นัด)", "เฉพาะมาตามนัด")
    )

    # ส่งค่า selected_vulnerable กลับไปด้วย (เป็นตัวแปรที่ 4)
    return selected_year, selected_disease, walk_in_filter, selected_vulnerable

def plot_trend_dual_axis(df_filtered, df_pm25):
    """สร้างกราฟ 2 แกน: แกนซ้าย(แท่ง)=ผู้ป่วย, แกนขวา(เส้น)=PM2.5 พร้อมสลับมุมมองโรคเด่น"""
    if df_filtered.empty or df_pm25.empty:
        st.info("📌 ไม่มีข้อมูลเพียงพอสำหรับสร้างกราฟแสดงแนวโน้ม")
        return

    # 1. ระบบสแกนหาคอลัมน์ชื่อโรคอัตโนมัติ (เพื่อใช้ในฟีเจอร์ใหม่)
    possible_cols = ['ชื่อโรค', 'โรค', 'โรค(ชื่อ)', 'โรคหลัก', 'ICD10_Name', 'icd10_name', 'รหัสโรค', 'ICD10', 'pdx', 'Diag', 'Diagnosis']
    disease_col = next((col for col in possible_cols if col in df_filtered.columns), None)

    # 2. สร้าง UI ตัวเลือกเหนือกราฟ (ไม่ไปกวน Sidebar)
    view_mode = "Walk-in"
    if disease_col:
        # ใช้ columns เพื่อจัด layout ให้สวยงาม ไม่กินพื้นที่
        c1, c2 = st.columns([1.5, 3])
        with c1:
            st.markdown("<p style='font-size: 0.95rem; font-weight: 600; color: #475569; margin-bottom: 0px;'>⚙️ จัดกลุ่มแท่งกราฟตาม:</p>", unsafe_allow_html=True)
            selected_view = st.radio(
                "ซ่อน Label",
                ["รูปแบบการมารพ. (Walk-in / นัด)", "5 อันดับโรคเด่น (Top Diseases)"],
                label_visibility="collapsed",
                horizontal=False
            )
            if selected_view == "5 อันดับโรคเด่น (Top Diseases)":
                view_mode = "Diseases"

    # 3. เตรียมข้อมูลแกนเวลา
    available_years = df_filtered['Month_Year'].dt.year.unique()
    df_pm25_plot = df_pm25[df_pm25['Month_Year'].dt.year.isin(available_years)].copy()
    df_pm25_plot['Month_Year'] = df_pm25_plot['Month_Year'].dt.to_timestamp()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 4. ลอจิกการสร้างแท่งกราฟ (แยกตามมุมมองที่ผู้ใช้เลือก)
    if view_mode == "Walk-in":
        # --- มุมมองปกติ: แบ่งตาม Walk-in ---
        trend_data = df_filtered.groupby(['Month_Year', 'Is_Walk_in']).size().reset_index(name='Patient_Count')
        trend_data['Month_Year'] = trend_data['Month_Year'].dt.to_timestamp()
        
        for status in trend_data['Is_Walk_in'].unique():
            df_subset = trend_data[trend_data['Is_Walk_in'] == status]
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
    else:
        # --- มุมมองใหม่: แบ่งตาม 5 อันดับโรคเด่น ---
        # หา 5 อันดับแรก
        top_5 = df_filtered[disease_col].value_counts().nlargest(5).index.tolist()
        
        # จัดกลุ่มข้อมูลที่เหลือเป็น 'อื่นๆ' เพื่อรักษายอดรวมให้เท่าเดิม
        df_plot = df_filtered.copy()
        df_plot['Plot_Group'] = df_plot[disease_col].apply(lambda x: x if x in top_5 else 'อื่นๆ (โรคทั่วไป)')
        
        trend_data = df_plot.groupby(['Month_Year', 'Plot_Group']).size().reset_index(name='Patient_Count')
        trend_data['Month_Year'] = trend_data['Month_Year'].dt.to_timestamp()
        
        # กำหนดสีทันสมัย 5 สี + สีเทาสำหรับกลุ่มอื่นๆ
        plot_groups = top_5 + ['อื่นๆ (โรคทั่วไป)']
        colors = ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#cbd5e1']
        color_map = dict(zip(plot_groups, colors))

        # วาดแท่งกราฟทีละกลุ่มตามลำดับ
        for group in plot_groups:
            if group in trend_data['Plot_Group'].unique():
                df_subset = trend_data[trend_data['Plot_Group'] == group]
                # ตัดข้อความชื่อโรคให้ไม่ยาวเกินไปใน Legend
                display_name = (group[:30] + '..') if len(group) > 30 else group
                fig.add_trace(
                    go.Bar(
                        x=df_subset['Month_Year'], 
                        y=df_subset['Patient_Count'], 
                        name=display_name, 
                        marker_color=color_map.get(group, '#cbd5e1'),
                        opacity=0.85
                    ),
                    secondary_y=False,
                )

    # 5. เพิ่มเส้น PM2.5 (ทำเหมือนเดิม)
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
        template="plotly_white",
        barmode='stack', 
        hovermode="x unified",
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5)
    )
    
    fig.update_yaxes(title_text="จำนวนผู้ป่วย (คน)", secondary_y=False, showgrid=False)
    fig.update_yaxes(title_text="ค่า PM2.5 (µg/m³)", secondary_y=True, showgrid=True, gridcolor='#f1f2f6')

    st.plotly_chart(fig, use_container_width=True)

def plot_demographics(df_filtered):
    """สร้างกราฟพาย (Donut Chart) สัดส่วนโรค และเพิ่มการนำเสนอข้อมูลกลุ่มเปราะบางแบบอัจฉริยะ พร้อมสรุปโรคเด่น"""
    if df_filtered.empty:
        st.info("📌 ไม่มีข้อมูลประชากรศาสตร์ตรงตามเงื่อนไข")
        return

    # --- ส่วนที่ 1: กราฟสัดส่วนโรค ---
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
            font_family="'Sarabun', 'Segoe UI', 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji', sans-serif",
            template="plotly_white",
            margin=dict(l=20, r=20, t=10, b=10),
            height=300 # ควบคุมความสูงไม่ให้กินพื้นที่มากไป
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("ไม่พบข้อมูลสัดส่วนกลุ่มโรค")

    # --- ส่วนที่ 2: การนำเสนอข้อมูล "กลุ่มเปราะบาง" (Smart Presentation) ---
    if 'กลุ่มเปราะบาง' in df_filtered.columns:
        st.markdown("<h5 style='text-align: center; color: #64748b; margin-top: 15px;'>🛡️ กลุ่มเปราะบางที่ต้องเฝ้าระวังพิเศษ</h5>", unsafe_allow_html=True)
        
        # คัดกรองเฉพาะกลุ่มที่สนใจ (เด็ก, ผู้สูงอายุ, หญิงตั้งครรภ์)
        focus_groups = ['เด็ก', 'ผู้สูงอายุ', 'หญิงตั้งครรภ์']
        vul_data = df_filtered[df_filtered['กลุ่มเปราะบาง'].isin(focus_groups)]
        
        if not vul_data.empty:
            vul_counts = vul_data['กลุ่มเปราะบาง'].value_counts().reset_index()
            vul_counts.columns = ['Vulnerable Group', 'Count']
            
            # คำนวณเปอร์เซ็นต์แบบอัจฉริยะเทียบกับ "ผู้ป่วยทั้งหมดในช่วงเวลานั้น"
            total_patients = len(df_filtered)
            vul_counts['Percent'] = (vul_counts['Count'] / total_patients * 100).round(1)
            
            # สร้างข้อความสำหรับแสดงบนแท่งกราฟให้อ่านง่าย เช่น "150 คน (30%)"
            vul_counts['Display_Text'] = vul_counts['Count'].astype(str) + " คน (" + vul_counts['Percent'].astype(str) + "%)"
            
            # สร้างกราฟแท่งแนวนอน (มินิมอล)
            fig_vul = px.bar(
                vul_counts, 
                y='Vulnerable Group', 
                x='Count', 
                orientation='h',
                text='Display_Text', 
                color='Vulnerable Group',
                color_discrete_map={
                    'ผู้สูงอายุ': '#ff9f43',   # สีส้มอบอุ่น
                    'เด็ก': '#00d2d3',         # สีฟ้าสดใส
                    'หญิงตั้งครรภ์': '#ff9ff3' # สีชมพู
                }
            )
            # ตั้งค่าให้ข้อความอยู่ตรงปลายแท่งกราฟ และซ่อนแกน X เพื่อความสะอาดตา
            fig_vul.update_traces(textposition='outside', textfont_size=13)
            fig_vul.update_layout(
                font_family="'Sarabun', 'Segoe UI', 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji', sans-serif",
                template="plotly_white",
                showlegend=False,
                xaxis_title="",
                yaxis_title="",
                xaxis_visible=False, # ซ่อนแกน X
                yaxis={'categoryorder':'total ascending'},
                margin=dict(l=10, r=40, t=10, b=10),
                height=180 # ปรับความสูงให้กำลังดีเมื่อวางซ้อนกับ Donut chart
            )
            st.plotly_chart(fig_vul, use_container_width=True)

            # สรุป Insight ด้านล่าง (ตัวอักษรเน้นสีแดง)
            total_vul = vul_counts['Count'].sum()
            vul_percent_total = (total_vul / total_patients * 100).round(1)
            st.markdown(f"<p style='text-align: center; font-size: 0.95rem; color: #ef4444; background-color: #fef2f2; padding: 10px; border-radius: 8px;'><b>⚠️ พบผู้ป่วยกลุ่มเปราะบางรวม {total_vul:,} คน (คิดเป็น {vul_percent_total}% ของผู้ป่วยทั้งหมด)</b></p>", unsafe_allow_html=True)
            
        else:
            st.info("ไม่พบผู้ป่วยในกลุ่มเปราะบาง (เด็ก, ผู้สูงอายุ, หญิงตั้งครรภ์) ตามเงื่อนไขที่เลือก")

    # --- ส่วนที่ 3: โรคเด่นของแต่ละกลุ่มโรค (Top Diseases) ---
    disease_col = None
    # ระบบจะสแกนหาคอลัมน์ที่มักใช้เก็บชื่อโรคหรือรหัสโรคย่อยโดยอัตโนมัติ
    possible_cols = ['ชื่อโรค', 'โรค', 'โรค(ชื่อ)', 'โรคหลัก', 'ICD10_Name', 'icd10_name', 'รหัสโรค', 'ICD10', 'pdx', 'Diag', 'Diagnosis']
    for col in possible_cols:
        if col in df_filtered.columns:
            disease_col = col
            break
            
    if disease_col:
        st.markdown("<h5 style='text-align: center; color: #64748b; margin-top: 25px;'>🦠 3 อันดับโรคเด่น แยกตามกลุ่มโรค</h5>", unsafe_allow_html=True)
        
        groups = df_filtered['4 กลุ่มโรคเฝ้าระวัง'].dropna().unique()
        for group in groups:
            group_data = df_filtered[df_filtered['4 กลุ่มโรคเฝ้าระวัง'] == group]
            if not group_data.empty:
                # ดึง 3 อันดับโรคย่อยที่พบมากที่สุดในกลุ่มนั้นๆ
                top_diseases = group_data[disease_col].value_counts().head(3)
                
                # ถ้าชื่อกลุ่มโรคเป็น 'ไม่จัดอยู่ใน 4 กลุ่มโรค' ให้ปรับการแสดงผลเพื่อความสวยงาม
                display_group_name = "โรคร่วม Z58.1" if group == "ไม่จัดอยู่ใน 4 กลุ่มโรค" else group
                
                # เปลี่ยนวิธีการต่อสตริงเพื่อไม่ให้ Markdown มองเป็น Code Block (เอาช่องว่างตอนขึ้นบรรทัดใหม่ออก)
                html_content = (
                    f"<div style='background-color: #ffffff; border: 1px solid #e2e8f0; border-left: 4px solid #3b82f6; padding: 12px; margin-bottom: 10px; border-radius: 6px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>"
                    f"<strong style='color: #0f172a; font-size: 0.95rem;'>{display_group_name}</strong>"
                )
                
                for disease, count in top_diseases.items():
                    pct = (count / len(group_data)) * 100
                    html_content += (
                        f"<div style='display: flex; justify-content: space-between; font-size: 0.85rem; color: #475569; margin-top: 6px; border-bottom: 1px dashed #f1f5f9; padding-bottom: 4px;'>"
                        f"<span style='width: 70%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;' title='{disease}'>• {disease}</span>"
                        f"<span style='font-weight: 500;'>{count:,} <span style='color: #94a3b8; font-size: 0.75rem;'>({pct:.1f}%)</span></span>"
                        f"</div>"
                    )
                html_content += "</div>"
                st.markdown(html_content, unsafe_allow_html=True)


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
            font_family="'Sarabun', 'Segoe UI', 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji', sans-serif",
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
