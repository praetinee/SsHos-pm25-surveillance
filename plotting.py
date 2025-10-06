import plotly.express as px
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import pandas as pd
import streamlit as st

def plot_patient_vs_pm25(df_pat, df_pm):
    """
    Generates and displays line charts for patient counts vs a background-highlighted
    area chart for PM2.5 levels, with multiple thresholds.
    """
    st.subheader("📊 แนวโน้มผู้ป่วย 4 กลุ่มโรคเทียบกับค่าฝุ่น PM2.5")

    # --- Data validation ---
    if "เดือน" not in df_pat.columns or "4 กลุ่มโรคเฝ้าระวัง" not in df_pat.columns:
        st.warning("ไม่สามารถสร้างกราฟแนวโน้มได้ เนื่องจากขาดคอลัมน์ 'เดือน' หรือ '4 กลุ่มโรคเฝ้าระวัง'")
        return

    # --- Prepare patient data ---
    agg = df_pat.groupby(["เดือน", "4 กลุ่มโรคเฝ้าระวัง"]).size().reset_index(name="count")
    patient_pivot = agg.pivot(index="เดือน", columns="4 กลุ่มโรคเฝ้าระวัง", values="count").fillna(0)
    patient_pivot = patient_pivot.sort_index()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # --- Prepare combined data for x-axis and PM2.5 ---
    all_months_list = sorted(list(set(list(patient_pivot.index) + list(df_pm['เดือน'].unique()))))
    all_months_df = pd.DataFrame({'เดือน': all_months_list})
    df_merged_pm = pd.merge(all_months_df, df_pm, on="เดือน", how="left").sort_values('เดือน')
    
    # --- Define Thresholds and Plotting Range ---
    PM25_MODERATE = 37.5
    PM25_UNHEALTHY = 75.0
    max_pm_val = df_merged_pm["PM2.5 (ug/m3)"].max()
    plot_max_y = max(PM25_UNHEALTHY, max_pm_val if pd.notna(max_pm_val) else 0) * 1.15

    # --- Add Threshold Highlighting Zones (as background) ---
    # Zone 1: Moderate/Cautious (Yellow)
    fig.add_shape(
        type="rect", xref="paper", yref="y2",
        x0=0, y0=PM25_MODERATE, x1=1, y1=PM25_UNHEALTHY,
        fillcolor="rgba(255, 217, 102, 0.2)", line_width=0, layer="below"
    )
    # Zone 2: Unhealthy (Red)
    fig.add_shape(
        type="rect", xref="paper", yref="y2",
        x0=0, y0=PM25_UNHEALTHY, x1=1, y1=plot_max_y,
        fillcolor="rgba(255, 82, 82, 0.2)", line_width=0, layer="below"
    )

    # --- Plot PM2.5 as an Area Chart ---
    if not df_merged_pm.empty and "PM2.5 (ug/m3)" in df_merged_pm.columns:
        fig.add_trace(
            go.Scatter(
                x=df_merged_pm["เดือน"],
                y=df_merged_pm["PM2.5 (ug/m3)"],
                name="PM2.5 (ug/m3)",
                fill='tozeroy',
                mode='lines',
                line=dict(color="rgba(0, 0, 0, 0.5)", width=1.5)
            ),
            secondary_y=True
        )

        # --- Add Threshold Lines with Labels ---
        fig.add_hline(
            y=PM25_MODERATE, line_dash="dot",
            line_color="orange",
            annotation_text=f"เกณฑ์ควรระวัง ({PM25_MODERATE})",
            annotation_position="bottom right",
            secondary_y=True
        )
        fig.add_hline(
            y=PM25_UNHEALTHY, line_dash="dot",
            line_color="red",
            annotation_text=f"เกณฑ์อันตราย ({PM25_UNHEALTHY})",
            annotation_position="top right",
            secondary_y=True
        )
    
    # --- Plot line charts for patient groups ---
    colors = px.colors.qualitative.Plotly
    for i, group in enumerate(patient_pivot.columns):
        fig.add_trace(
            go.Scatter(
                x=patient_pivot.index,
                y=patient_pivot[group],
                name=group,
                mode='lines+markers',
                line=dict(width=2, color=colors[i % len(colors)]),
            ),
            secondary_y=False
        )

    # --- Finalize Layout ---
    fig.update_layout(
        title_text="แนวโน้มผู้ป่วยเทียบกับระดับค่าฝุ่น PM2.5",
        legend_title_text="ข้อมูล",
        hovermode="x unified"
    )
    fig.update_yaxes(title_text="จำนวนผู้ป่วย (คน)", secondary_y=False)
    fig.update_yaxes(title_text="PM2.5 (ug/m3)", secondary_y=True, range=[0, plot_max_y])
    st.plotly_chart(fig, use_container_width=True)


def plot_vulnerable_pie(df, month_filter):
    """Generates and displays a pie chart of vulnerable groups."""
    st.subheader("👥 สัดส่วนกลุ่มเปราะบาง")

    if "กลุ่มเปราะบาง" in df.columns:
        if df["กลุ่มเปราะบาง"].dropna().empty:
            st.info("ไม่มีข้อมูลกลุ่มเปราะบางในข้อมูลที่เลือก")
            return
            
        sp = df["กลุ่มเปราะบาง"].value_counts().reset_index()
        sp.columns = ["กลุ่ม", "จำนวน"]
        title = f"สัดส่วนกลุ่มเปราะบาง (เดือน: {month_filter})"
        fig = px.pie(sp, values="จำนวน", names="กลุ่ม", title=title)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ℹ️ ไม่มีคอลัมน์ 'กลุ่มเปราะบาง' ในข้อมูล")

