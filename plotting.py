import plotly.express as px
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import pandas as pd
import streamlit as st

def plot_patient_vs_pm25(df_pat, df_pm):
    """
    Generates and displays a stacked area chart for patient counts 
    vs a line chart for PM2.5 levels, with a threshold highlight.
    """
    st.subheader("📊 สัดส่วนผู้ป่วยเทียบกับค่า PM2.5 และเกณฑ์มาตรฐาน")

    # --- Data validation ---
    if "เดือน" not in df_pat.columns or "4 กลุ่มโรคเฝ้าระวัง" not in df_pat.columns:
        st.warning("ไม่สามารถสร้างกราฟแนวโน้มได้ เนื่องจากขาดคอลัมน์ 'เดือน' หรือ '4 กลุ่มโรคเฝ้าระวัง'")
        return

    # --- Prepare patient data for stacked area chart ---
    agg = df_pat.groupby(["เดือน", "4 กลุ่มโรคเฝ้าระวัง"]).size().reset_index(name="count")
    patient_pivot = agg.pivot(index="เดือน", columns="4 กลุ่มโรคเฝ้าระวัง", values="count").fillna(0)
    patient_pivot = patient_pivot.sort_index()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # --- Plot stacked area chart for patient groups ---
    colors = px.colors.qualitative.Plotly
    for i, group in enumerate(patient_pivot.columns):
        fig.add_trace(
            go.Scatter(
                x=patient_pivot.index, 
                y=patient_pivot[group], 
                name=group,
                hoverinfo='x+y',
                mode='lines',
                line=dict(width=0.5, color=colors[i % len(colors)]),
                stackgroup='one' # This creates the stacked area chart
            ),
            secondary_y=False
        )

    # --- Prepare and plot PM2.5 line ---
    if not df_pm.empty and all(col in df_pm.columns for col in ["เดือน", "PM2.5 (ug/m3)"]):
        all_months_list = sorted(list(set(list(patient_pivot.index) + list(df_pm['เดือน'].unique()))))
        all_months_df = pd.DataFrame({'เดือน': all_months_list})
        df_merged_pm = pd.merge(all_months_df, df_pm, on="เดือน", how="left").sort_values('เดือน')

        fig.add_trace(
            go.Scatter(
                x=df_merged_pm["เดือน"], 
                y=df_merged_pm["PM2.5 (ug/m3)"], 
                name="PM2.5 (ug/m3)", 
                line=dict(color="rgba(0, 0, 0, 0.7)", width=2.5)
            ),
            secondary_y=True
        )

        # --- Add Threshold Highlighting ---
        PM25_THRESHOLD = 37.5
        fig.add_hline(
            y=PM25_THRESHOLD, 
            line_dash="dash", 
            line_color="red", 
            annotation_text="เกณฑ์มาตรฐาน (37.5)", 
            annotation_position="bottom right",
            secondary_y=True
        )
        
        max_pm_val = df_merged_pm["PM2.5 (ug/m3)"].max()
        if pd.notna(max_pm_val) and max_pm_val > PM25_THRESHOLD:
            fig.add_shape(
                type="rect",
                xref="paper", yref="y2",
                x0=0, y0=PM25_THRESHOLD,
                x1=1, y1=max_pm_val * 1.1,
                fillcolor="rgba(255, 82, 82, 0.15)",
                line_width=0,
                layer="below"
            )
        fig.update_yaxes(title_text="PM2.5 (ug/m3)", secondary_y=True, range=[0, max_pm_val * 1.15])
    else:
        st.info("ℹ️ ไม่ได้แสดงข้อมูล PM2.5 เนื่องจากไม่พบข้อมูลหรือคอลัมน์ที่จำเป็น")

    # --- Finalize Layout ---
    fig.update_layout(
        title_text="แนวโน้มผู้ป่วย 4 กลุ่มโรคเทียบกับค่า PM2.5",
        legend_title_text="ข้อมูล",
        hovermode="x unified"
    )
    fig.update_yaxes(title_text="จำนวนผู้ป่วยสะสม (คน)", secondary_y=False)
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

