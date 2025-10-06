import plotly.express as px
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import pandas as pd
import streamlit as st

def plot_patient_vs_pm25(df_pat, df_pm):
    """Generates and displays a combination chart of patient counts vs PM2.5 levels."""
    st.subheader("📊 แนวโน้มผู้ป่วย 4 กลุ่มโรคเทียบกับค่า PM2.5")

    if "เดือน" not in df_pat.columns or "4 กลุ่มโรคเฝ้าระวัง" not in df_pat.columns:
        st.warning("ไม่สามารถสร้างกราฟแนวโน้มได้ เนื่องจากขาดคอลัมน์ 'เดือน' หรือ '4 กลุ่มโรคเฝ้าระวัง'")
        return

    agg = df_pat.groupby(["เดือน", "4 กลุ่มโรคเฝ้าระวัง"]).size().reset_index(name="count")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add patient data
    for grp in sorted(agg["4 กลุ่มโรคเฝ้าระวัง"].unique()):
        d2 = agg[agg["4 กลุ่มโรคเฝ้าระวัง"] == grp]
        fig.add_trace(
            go.Scatter(x=d2["เดือน"], y=d2["count"], name=f"ผู้ป่วย {grp}", mode="lines+markers"),
            secondary_y=False
        )

    # Add PM2.5 data if available
    if not df_pm.empty and all(col in df_pm.columns for col in ["เดือน", "PM2.5 (ug/m3)"]):
        df_merge = pd.merge(agg[['เดือน']].drop_duplicates(), df_pm, on="เดือน", how="left")
        fig.add_trace(
            go.Scatter(x=df_merge["เดือน"], y=df_merge["PM2.5 (ug/m3)"], name="PM2.5 (ug/m3)", line=dict(color="black", dash="dash")),
            secondary_y=True
        )
        fig.update_yaxes(title_text="PM2.5 (ug/m3)", secondary_y=True)
    else:
        st.info("ℹ️ ไม่ได้แสดงข้อมูล PM2.5 เนื่องจากไม่พบข้อมูลหรือคอลัมน์ที่จำเป็น")

    fig.update_layout(
        title_text="แนวโน้มผู้ป่วย 4 กลุ่มโรคเทียบกับค่า PM2.5",
        legend_title_text="ข้อมูล"
    )
    fig.update_yaxes(title_text="จำนวนผู้ป่วย (คน)", secondary_y=False)
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
