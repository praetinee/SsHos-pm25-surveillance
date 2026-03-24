import streamlit as st
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go

def plot_reattendance_rate(df_pat, df_pm, lookback_days=30):
    """
    Analyzes and plots the re-attendance rate of patients (visits within a specified lookback period)
    against monthly PM2.5 levels.
    
    Args:
        df_pat (pd.DataFrame): Patient data (must contain 'HN' and 'วันที่เข้ารับบริการ').
        df_pm (pd.DataFrame): PM2.5 data (must contain 'เดือน' and 'PM2.5 (ug/m3)').
        lookback_days (int): The number of days used to define a 're-attendance' event.
    """
    
    required_cols = ['HN', 'วันที่เข้ารับบริการ']
    if not all(col in df_pat.columns for col in required_cols):
        st.error("ℹ️ ข้อมูลผู้ป่วยขาดคอลัมน์ที่จำเป็น ('HN' หรือ 'วันที่เข้ารับบริการ') สำหรับการวิเคราะห์การมาซ้ำ")
        return

    st.subheader(f"อัตราการมาซ้ำ (Re-attendance) ภายใน {lookback_days} วัน")
    
    # Ensure data types are correct
    df_pat = df_pat.sort_values(by=['HN', 'วันที่เข้ารับบริการ'])
    
    # 1. Calculate Time Difference (Interval between visits for the same patient)
    # Group by HN and calculate the difference in days between the current visit and the previous visit.
    df_pat['Previous_Visit_Date'] = df_pat.groupby('HN')['วันที่เข้ารับบริการ'].shift(1)
    df_pat['Time_Diff_Days'] = (df_pat['วันที่เข้ารับบริการ'] - df_pat['Previous_Visit_Date']).dt.days
    
    # 2. Identify Re-attendance Visits
    # A visit is considered 're-attendance' if the time difference is <= lookback_days AND the visit is not the first visit (Time_Diff_Days is not NaN)
    df_pat['Is_Reattendance'] = (
        (df_pat['Time_Diff_Days'] > 0) & 
        (df_pat['Time_Diff_Days'] <= lookback_days)
    )
    
    # 3. Aggregate Re-attendance Counts by Month
    df_revisit_monthly = df_pat[df_pat['Is_Reattendance']].groupby('เดือน').size().reset_index(name='จำนวนการมาซ้ำ')
    
    # Get total unique patients (or total visits) per month for rate calculation base (optional, but counts are clearer)
    # For simplicity, we just plot the raw count of re-attendance events.
    
    # 4. Merge with PM2.5 data
    df_merged = pd.merge(df_revisit_monthly, df_pm, on='เดือน', how='inner').sort_values('เดือน')
    all_months = sorted(df_merged["เดือน"].dropna().unique())

    if df_merged.empty:
        st.info("ℹ️ ไม่มีข้อมูลการมาซ้ำในช่วงเวลาที่กำหนด หรือข้อมูล PM2.5 ไม่สอดคล้องกัน")
        return

    # 5. Plotting (Dual Axis)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Add PM2.5 Area chart (Primary Y-Axis)
    pm25_data = df_pm.set_index('เดือน').reindex(all_months)['PM2.5 (ug/m3)']
    fig.add_trace(
        go.Scatter(
            x=all_months,
            y=pm25_data,
            name="PM2.5 (ug/m3)",
            fill='tozeroy',
            mode='lines',
            line=dict(color='rgba(192, 192, 192, 0.5)', width=0.5),
        ), 
        secondary_y=False
    )
    
    # Add Re-attendance Count line (Secondary Y-Axis)
    fig.add_trace(
        go.Scatter(
            x=df_merged["เดือน"], 
            y=df_merged["จำนวนการมาซ้ำ"], 
            name=f"จำนวนการมาซ้ำภายใน {lookback_days} วัน", 
            mode="lines+markers", 
            line=dict(width=3, color=px.colors.qualitative.Plotly[1]),
            marker=dict(size=8),
        ),
        secondary_y=True
    )

    # Update Layout
    fig.update_layout(
        title_text=f"แนวโน้มการมาซ้ำของผู้ป่วย เทียบกับค่า PM2.5 รายเดือน ({lookback_days} วัน)",
        legend_title_text="ข้อมูล",
        hovermode="x unified",
        font=dict(family="Tahoma, sans-serif"),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    
    # Update Axes
    pm25_max = df_pm["PM2.5 (ug/m3)"].max() if not df_pm.empty else 100
    revisit_max = df_merged['จำนวนการมาซ้ำ'].max() if not df_merged.empty else 100
    
    fig.update_yaxes(
        title_text="ค่า PM2.5 (µg/m³)", 
        range=[0, pm25_max * 1.2], 
        secondary_y=False,
        showgrid=False
    )
    fig.update_yaxes(
        title_text="จำนวนการมาซ้ำ (ครั้ง)", 
        range=[0, revisit_max * 1.1], 
        secondary_y=True,
        gridcolor='#e0e0e0', 
        griddash="dot"
    )

    fig.update_xaxes(title_text="เดือน")

    st.plotly_chart(fig, use_container_width=True)
