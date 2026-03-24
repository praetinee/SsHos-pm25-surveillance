import streamlit as st
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# ----------------------------
# NEW: Vulnerable Groups Dashboard
# ----------------------------
def plot_vulnerable_dashboard(df_pat, df_pm, dff_filtered):
    """
    Creates a comprehensive dashboard for vulnerable groups analysis.
    """
    if "กลุ่มเปราะบาง" not in df_pat.columns or "4 กลุ่มโรคเฝ้าระวัง" not in df_pat.columns:
        st.info("ℹ️ ไม่สามารถวิเคราะห์ได้ เนื่องจากขาดคอลัมน์ 'กลุ่มเปราะบาง' หรือ '4 กลุ่มโรคเฝ้าระวัง'")
        return

    df_vul = df_pat.dropna(subset=['กลุ่มเปราะบาง'])
    df_vul = df_vul[df_vul['กลุ่มเปราะบาง'] != 'วัยผู้ใหญ่']
    
    # --- 1. Pie Chart (based on current filters) ---
    st.subheader("1. สัดส่วนกลุ่มเปราะบาง (ตามตัวกรองปัจจุบัน)")
    if not dff_filtered.empty:
        df_vul_filtered = dff_filtered.dropna(subset=['กลุ่มเปราะบาง'])
        df_vul_filtered = df_vul_filtered[df_vul_filtered['กลุ่มเปราะบาง'] != 'วัยผู้ใหญ่']
        if not df_vul_filtered.empty:
            sp = df_vul_filtered["กลุ่มเปราะบาง"].value_counts().reset_index()
            sp.columns = ["กลุ่ม", "จำนวน"]
            pie = px.pie(sp, values="จำนวน", names="กลุ่ม", title="สัดส่วนกลุ่มเปราะบางที่เลือก")
            st.plotly_chart(pie, use_container_width=True)
        else:
            st.info("ℹ️ ไม่มีข้อมูลกลุ่มเปราะบางในข้อมูลที่กรอง")
    else:
        st.info("ℹ️ ไม่มีข้อมูลกลุ่มเปราะบางสำหรับเดือนที่เลือก")

    st.divider()

    # --- 2. Vulnerable Groups vs PM2.5 (all data) ---
    st.subheader("2. เปรียบเทียบแนวโน้มผู้ป่วยกลุ่มเปราะบางกับค่า PM2.5 (ข้อมูลทั้งหมด)")
    trend_data = df_vul.groupby(['เดือน', 'กลุ่มเปราะบาง']).size().reset_index(name='จำนวน')
    trend_data_vs_pm = pd.merge(trend_data, df_pm, on="เดือน", how="left")
    all_months = sorted(trend_data_vs_pm["เดือน"].dropna().unique())
    
    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Add PM2.5 trace
    fig2.add_trace(
        go.Scatter(
            x=all_months,
            y=df_pm.set_index('เดือน').reindex(all_months)['PM2.5 (ug/m3)'],
            name="PM2.5 (ug/m3)",
            fill='tozeroy',
            mode='lines',
            line=dict(color='lightgrey')
        ), 
        secondary_y=False
    )
    
    # Add vulnerable group traces
    colors = px.colors.qualitative.Plotly
    vulnerable_groups = sorted(df_vul["กลุ่มเปราะบาง"].dropna().unique())
    for i, grp in enumerate(vulnerable_groups):
        d2 = trend_data_vs_pm[trend_data_vs_pm["กลุ่มเปราะบาง"] == grp]
        fig2.add_trace(
            go.Scatter(
                x=d2["เดือน"], 
                y=d2["จำนวน"], 
                name=f"{grp}", 
                mode="lines+markers",
                line=dict(color=colors[i % len(colors)])
            ),
            secondary_y=True
        )
    
    fig2.update_layout(
        legend_title_text="ข้อมูล",
        yaxis_title="PM2.5 (ug/m3)",
        yaxis2_title="จำนวนผู้ป่วย (คน)",
        hovermode="x unified",
        title_text="แนวโน้มผู้ป่วยกลุ่มเปราะบางเทียบกับ PM2.5"
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # --- 3. Disease Breakdown by Vulnerable Group (all data) ---
    st.subheader("3. กลุ่มโรคที่พบในแต่ละกลุ่มเปราะบาง (ข้อมูลทั้งหมด)")
    breakdown_data = df_vul.groupby(['กลุ่มเปราะบาง', '4 กลุ่มโรคเฝ้าระวัง']).size().reset_index(name='จำนวน')
    if not breakdown_data.empty:
        fig3 = px.bar(
            breakdown_data, 
            x='กลุ่มเปราะบาง', 
            y='จำนวน', 
            color='4 กลุ่มโรคเฝ้าระวัง', 
            barmode='group', 
            title="จำแนกกลุ่มโรคที่พบในแต่ละกลุ่มเปราะบาง",
            labels={'จำนวน': 'จำนวนผู้ป่วย (คน)', 'กลุ่มเปราะบาง': 'กลุ่มเปราะบาง', '4 กลุ่มโรคเฝ้าระวัง': 'กลุ่มโรคเฝ้าระวัง'}
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("ℹ️ ไม่มีข้อมูลเพียงพอสำหรับจำแนกกลุ่มโรค")
