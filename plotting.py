import streamlit as st
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import numpy as np

# ----------------------------
# Plot 1: Original Trend Chart (Updated)
# ----------------------------
def plot_patient_vs_pm25(df_pat, df_pm):
    # This function is now deprecated and will call the new function for consistency.
    # We keep it for backward compatibility in case other parts of the app call it.
    plot_main_dashboard_chart(df_pat, df_pm)

def plot_main_dashboard_chart(df_pat, df_pm):
    """
    Generates the main dashboard chart showing patient trends vs. PM2.5 levels.
    - Patient data as line charts in the foreground.
    - PM2.5 data as a grey area chart in the background.
    - Correctly aligned threshold annotations.
    """
    st.header("แนวโน้มผู้ป่วยเทียบกับค่า PM2.5")
    
    patient_counts = df_pat.groupby(["เดือน", "4 กลุ่มโรคเฝ้าระวัง"]).size().reset_index(name="count")
    # Use an outer join to ensure all months from both datasets are included
    df_merged = pd.merge(patient_counts, df_pm, on="เดือน", how="outer").sort_values("เดือน")
    
    # Get a complete list of months for the x-axis, ensuring both graphs share the same scale
    all_months = sorted(df_merged["เดือน"].dropna().unique())

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # 1. Add PM2.5 Area chart as a grey background FIRST
    fig.add_trace(
        go.Scatter(
            x=all_months,
            y=df_pm.set_index('เดือน').reindex(all_months)['PM2.5 (ug/m3)'],
            name="PM2.5 (ug/m3)",
            fill='tozeroy',
            mode='lines',
            line=dict(color='lightgrey')
        ), secondary_y=True
    )

    # 2. Add Patient group lines on top SECOND
    colors = px.colors.qualitative.Plotly
    patient_groups = sorted(df_pat["4 กลุ่มโรคเฝ้าระวัง"].dropna().unique())

    for i, grp in enumerate(patient_groups):
        d2 = df_merged[df_merged["4 กลุ่มโรคเฝ้าระวัง"] == grp]
        fig.add_trace(
            go.Scatter(
                x=d2["เดือน"], 
                y=d2["count"], 
                name=f"{grp}", 
                mode="lines+markers", 
                line=dict(width=2.5, color=colors[i % len(colors)])
            ),
            secondary_y=False
        )
        
    # 3. Add Threshold lines WITHOUT built-in annotations
    fig.add_hline(
        y=37.5, 
        line_dash="dash", 
        line_color="orange", 
        secondary_y=True
    )
    fig.add_hline(
        y=75, 
        line_dash="dash", 
        line_color="red", 
        secondary_y=True
    )

    # 4. Update layout with MANUAL annotations for precise positioning
    fig.update_layout(
        legend_title_text="ข้อมูล",
        yaxis_title="จำนวนผู้ป่วย (คน)",
        yaxis2_title="PM2.5 (ug/m3)",
        hovermode="x unified",
        margin=dict(t=30, l=0, r=0, b=0), # Reduce top margin
        annotations=[
            dict(
                x=all_months[-1] if all_months else 0,
                y=37.5,
                xref="x",
                yref="y2",
                text="อากาศที่ต้องระวัง (37.5)",
                showarrow=False,
                xanchor='right',
                yanchor='bottom',
                font=dict(color="orange")
            ),
            dict(
                x=all_months[-1] if all_months else 0,
                y=75,
                xref="x",
                yref="y2",
                text="อากาศแย่ (75)",
                showarrow=False,
                xanchor='right',
                yanchor='bottom',
                font=dict(color="red")
            )
        ]
    )
    
    # Set range for secondary y-axis to give more space at the top
    fig.update_yaxes(range=[0, df_pm["PM2.5 (ug/m3)"].max() * 1.2 if not df_pm.empty else 100], secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)


# -------------------------------------
# Plot 2: Year-over-Year Comparison
# -------------------------------------
def plot_yearly_comparison(df_pat, df_pm):
    df_merged = pd.merge(
        df_pat.groupby('เดือน').size().reset_index(name='count'), 
        df_pm, on='เดือน', how='inner'
    )
    df_merged['Year'] = pd.to_datetime(df_merged['เดือน']).dt.year
    df_merged['Month'] = pd.to_datetime(df_merged['เดือน']).dt.month

    fig = go.Figure()
    
    years = df_merged['Year'].unique()
    for year in years:
        df_year = df_merged[df_merged['Year'] == year]
        fig.add_trace(go.Scatter(
            x=df_year['Month'], 
            y=df_year['count'], 
            name=f'ผู้ป่วย ปี {year}',
            mode='lines+markers'
        ))

    fig.update_layout(
        title_text="กราฟเปรียบเทียบจำนวนผู้ป่วยรวมในแต่ละปี",
        xaxis_title="เดือน",
        yaxis_title="จำนวนผู้ป่วยรวม (คน)",
        xaxis=dict(tickmode='array', tickvals=list(range(1, 13)), ticktext=['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']),
        legend_title_text="ปี"
    )
    st.plotly_chart(fig, use_container_width=True)

# -------------------------------------
# Plot 3: Calendar Heatmap
# -------------------------------------
def plot_calendar_heatmap(df_pat, df_pm):
    df_merged = pd.merge(
        df_pat.groupby('เดือน').size().reset_index(name='count'), 
        df_pm, on='เดือน', how='inner'
    )
    df_merged['Year'] = pd.to_datetime(df_merged['เดือน']).dt.year
    df_merged['Month'] = pd.to_datetime(df_merged['เดือน']).dt.month
    
    # Pivot data for heatmap
    years = sorted(df_merged['Year'].unique(), reverse=True)
    months = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']
    
    z_data = [] # PM2.5 for color
    text_data = [] # Patient count for text

    for year in years:
        row_z = []
        row_text = []
        for month_num in range(1, 13):
            cell = df_merged[(df_merged['Year'] == year) & (df_merged['Month'] == month_num)]
            if not cell.empty:
                row_z.append(cell['PM2.5 (ug/m3)'].iloc[0])
                row_text.append(f"{int(cell['count'].iloc[0])}")
            else:
                row_z.append(np.nan)
                row_text.append("")
        z_data.append(row_z)
        text_data.append(row_text)

    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        x=months,
        y=[str(y) for y in years],
        text=text_data,
        texttemplate="%{text}",
        textfont={"size":12},
        colorscale='OrRd',
        hovertemplate='<b>ปี %{y}, เดือน %{x}</b><br>PM2.5: %{z:.2f}<br>ผู้ป่วย: %{text} คน<extra></extra>'
    ))

    fig.update_layout(
        title='ปฏิทินแสดงค่า PM2.5 (สี) และจำนวนผู้ป่วย (ตัวเลข)'
    )
    st.plotly_chart(fig, use_container_width=True)


# -------------------------------------
# Plot 4: Correlation Scatter Plot
# -------------------------------------
def plot_correlation_scatter(df_pat, df_pm):
    df_merged = pd.merge(
        df_pat.groupby('เดือน').size().reset_index(name='จำนวนผู้ป่วย'), 
        df_pm, on='เดือน', how='inner'
    )
    
    fig = px.scatter(
        df_merged,
        x="PM2.5 (ug/m3)",
        y="จำนวนผู้ป่วย",
        trendline="ols",
        trendline_color_override="red",
        title="ความสัมพันธ์ระหว่าง PM2.5 และ จำนวนผู้ป่วย",
        labels={"PM2.5 (ug/m3)": "ค่า PM2.5 (µg/m³)", "จำนวนผู้ป่วย": "จำนวนผู้ป่วยรวม (คน)"},
        hover_data=['เดือน']
    )
    
    st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# Original Pie Chart
# ----------------------------
def plot_vulnerable_pie(df, month_sel):
    st.subheader("สัดส่วนกลุ่มเปราะบาง")
    if "กลุ่มเปราะบาง" in df.columns:
        if not df.empty:
            sp = df["กลุ่มเปราะบาง"].value_counts().reset_index()
            sp.columns = ["กลุ่ม", "จำนวน"]
            pie = px.pie(sp, values="จำนวน", names="กลุ่ม", title=f"สัดส่วนกลุ่มเปราะบาง (เดือน: {month_sel})")
            st.plotly_chart(pie, use_container_width=True)
        else:
            st.info("ℹ️ ไม่มีข้อมูลกลุ่มเปราะบางสำหรับเดือนที่เลือก")
    else:
        st.info("ℹ️ ยังไม่มีคอลัมน์ 'กลุ่มเปราะบาง' ในข้อมูล")

