import streamlit as st
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import numpy as np

# ----------------------------
# Plot 1: Original Trend Chart (Updated with Lag/Lead)
# ----------------------------
def plot_patient_vs_pm25(df_pat, df_pm, lag_months=0):
    """
    This function is now deprecated and will call the new function for consistency.
    It is updated to pass the lag_months parameter.
    """
    plot_main_dashboard_chart(df_pat, df_pm, lag_months)

def plot_main_dashboard_chart(df_pat, df_pm, lag_months=0):
    """
    Generates the main dashboard chart showing patient trends vs. PM2.5 levels.
    """
    
    # --- Lag/Lead Processing Start ---
    df_pm_lagged = df_pm.copy()
    
    df_pm_lagged['Date'] = pd.to_datetime(df_pm_lagged['เดือน'])
    df_pm_lagged.set_index('Date', inplace=True)

    if lag_months != 0: # ปรับให้รองรับทั้งบวกและลบ
        df_pm_lagged['PM2.5 (ug/m3)'] = df_pm_lagged['PM2.5 (ug/m3)'].shift(periods=lag_months)
        df_pm_lagged.reset_index(inplace=True)
        df_pm_current = df_pm[['เดือน', 'PM2.5 (ug/m3)']].copy() 
        df_pm = df_pm_lagged[['เดือน', 'PM2.5 (ug/m3)']].copy() 
    else:
        df_pm_current = df_pm[['เดือน', 'PM2.5 (ug/m3)']].copy()
        df_pm = df_pm[['เดือน', 'PM2.5 (ug/m3)']].copy()
        
    # --- Lag Processing End ---
    
    patient_counts = df_pat.groupby(["เดือน", "4 กลุ่มโรคเฝ้าระวัง"]).size().reset_index(name="count")
    df_merged = pd.merge(patient_counts, df_pm, on="เดือน", how="outer").sort_values("เดือน")
    all_months = sorted(df_merged["เดือน"].dropna().unique())

    # Create the figure with a secondary Y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # 1. Add PM2.5 Area chart on the PRIMARY Y-AXIS
    pm25_data = df_pm.set_index('เดือน').reindex(all_months)['PM2.5 (ug/m3)']
    
    # สร้างข้อความ Label ให้กราฟรองรับอดีต/อนาคต
    if lag_months > 0:
        pm25_name_suffix = f" (ก่อนหน้า {lag_months} เดือน)"
    elif lag_months < 0:
        pm25_name_suffix = f" (ให้หลัง {abs(lag_months)} เดือน)"
    else:
        pm25_name_suffix = " (เดือนเดียวกัน)"
    
    fig.add_trace(
        go.Scatter(
            x=all_months,
            y=pm25_data,
            name=f"PM2.5{pm25_name_suffix}", 
            fill='tozeroy', 
            mode='lines',
            # Use semi-transparent grey that works on both dark/light backgrounds
            line=dict(color='rgba(160, 160, 160, 0.5)', width=0), 
            fillcolor='rgba(160, 160, 160, 0.2)',
            hovertemplate='<b>PM2.5:</b> %{y:.2f} µg/m³<extra></extra>',
        ), 
        secondary_y=False 
    )

    # 2. Add Patient group lines on the SECONDARY Y-AXIS
    colors = px.colors.qualitative.Bold # Using Bold for better visibility
    patient_groups = sorted(df_pat["4 กลุ่มโรคเฝ้าระวัง"].dropna().unique())

    for i, grp in enumerate(patient_groups):
        d2 = df_merged[df_merged["4 กลุ่มโรคเฝ้าระวัง"] == grp]
        fig.add_trace(
            go.Scatter(
                x=d2["เดือน"], 
                y=d2["count"], 
                name=f"{grp}", 
                mode="lines+markers", 
                line=dict(width=2.5, color=colors[i % len(colors)]),
                marker=dict(size=6, symbol='circle'),
                hovertemplate='<b>%{y}</b> คน<extra></extra>',
            ),
            secondary_y=True
        )
        
    # 3. Add Threshold lines for PM2.5
    fig.add_hline(
        y=37.5, 
        line=dict(dash="dot", color="#FFBF00", width=1.5), 
        secondary_y=False 
    )
    fig.add_hline(
        y=75, 
        line=dict(dash="dash", color="#E30022", width=1.5), 
        secondary_y=False 
    )

    # 4. Update layout and annotations
    if lag_months > 0:
        title_suffix = f" (PM2.5 ก่อนหน้า {lag_months} เดือน)"
    elif lag_months < 0:
        title_suffix = f" (PM2.5 ให้หลัง {abs(lag_months)} เดือน)"
    else:
        title_suffix = ""
    
    fig.update_layout(
        # Remove hardcoded template to allow Streamlit theme to shine through
        # template='plotly_white', 
        paper_bgcolor='rgba(0,0,0,0)', # Transparent background
        plot_bgcolor='rgba(0,0,0,0)', # Transparent plot area
        
        title=dict(
            text=f"<b>แนวโน้มจำนวนผู้ป่วยเทียบกับค่า PM2.5</b>{title_suffix}",
            font=dict(size=18, family="Kanit, sans-serif")
        ),
        legend=dict(
            orientation="h", # Horizontal legend
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode="x unified", 
        margin=dict(t=80, l=10, r=10, b=20), # Reduced side margins for mobile
        font=dict(family="Kanit, sans-serif"),
        
        # Annotations for PM2.5 thresholds
        annotations=[
            dict(
                x=0.01,
                xref="paper",
                y=37.5,
                yref="y",
                text="⚠️ 37.5",
                showarrow=False,
                xanchor='left',
                yanchor='bottom',
                font=dict(color="#FFBF00", size=10),
            ),
            dict(
                x=0.01,
                xref="paper",
                y=75,
                yref="y",
                text="🛑 75",
                showarrow=False,
                xanchor='left',
                yanchor='bottom',
                font=dict(color="#E30022", size=10),
            )
        ]
    )
    
    # 5. Update Axes
    pm25_max = df_pm["PM2.5 (ug/m3)"].max() if not df_pm.empty else 100
    
    # Common axis style
    grid_style = dict(showgrid=True, gridcolor='rgba(128, 128, 128, 0.2)', griddash="dot")
    
    fig.update_yaxes(
        title_text="ค่า PM2.5 (µg/m³)", 
        range=[0, pm25_max * 1.2], 
        secondary_y=False,
        showgrid=False,
        # Remove hardcoded colors so it adapts to Light/Dark mode
    )
    
    patient_max = df_merged['count'].max() if not df_merged.empty else 100
    fig.update_yaxes(
        title_text="จำนวนผู้ป่วย (คน)", 
        range=[0, patient_max * 1.1], 
        secondary_y=True,
        **grid_style # Use adaptive grid
    )

    fig.update_xaxes(title_text="เดือน", showgrid=False)

    st.plotly_chart(fig, use_container_width=True)


# ----------------------------
# NEW FUNCTION: Plot for Specific ICD-10 (J44.0)
# ----------------------------
def plot_specific_icd10_trend(df_pat, df_pm, icd10_code, disease_name, icd10_column_name="ICD10ทั้งหมด"):
    """
    Generates a trend chart for a single, specific ICD-10 code.
    """
    if icd10_column_name not in df_pat.columns:
        st.error(f"ไม่พบคอลัมน์ '{icd10_column_name}' ในข้อมูลผู้ป่วย ไม่สามารถแสดงกราฟ {disease_name} ได้")
        return
    
    pattern = r'(^|,)' + icd10_code + r'(,|$)'
    df_specific = df_pat[df_pat[icd10_column_name].astype(str).str.contains(icd10_code, na=False)]
    
    if df_specific.empty:
        st.info(f"ℹ️ ไม่มีข้อมูลผู้ป่วยสำหรับรหัสโรค {icd10_code} ({disease_name})")
        return

    # Aggregation
    patient_counts = df_specific.groupby("เดือน").size().reset_index(name="count")
    df_merged = pd.merge(patient_counts, df_pm, on="เดือน", how="outer").sort_values("เดือน")
    all_months = sorted(df_merged["เดือน"].dropna().unique())

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # PM2.5 Area chart
    pm25_data = df_pm.set_index('เดือน').reindex(all_months)['PM2.5 (ug/m3)']
    
    fig.add_trace(
        go.Scatter(
            x=all_months,
            y=pm25_data,
            name="PM2.5",
            fill='tozeroy',
            mode='lines',
            line=dict(color='rgba(160, 160, 160, 0.5)', width=0),
            fillcolor='rgba(160, 160, 160, 0.2)',
            hovertemplate='<b>PM2.5:</b> %{y:.2f} µg/m³<extra></extra>',
        ), 
        secondary_y=False
    )

    # Specific Patient line
    line_color = '#E91E63' # Distinct Pink color
    
    fig.add_trace(
        go.Scatter(
            x=df_merged["เดือน"], 
            y=df_merged["count"], 
            name=f"ผู้ป่วย {disease_name}", 
            mode="lines+markers", 
            line=dict(width=3, color=line_color),
            marker=dict(size=8),
            hovertemplate='<b>%{y}</b> คน<extra></extra>',
        ),
        secondary_y=True
    )
        
    # Threshold lines
    fig.add_hline(y=37.5, line=dict(dash="dot", color="#FFBF00", width=1.5), secondary_y=False)
    fig.add_hline(y=75, line=dict(dash="dash", color="#E30022", width=1.5), secondary_y=False)

    # Layout
    fig.update_layout(
        # template='plotly_white', # Removed for theme adaptability
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        
        title=dict(
             text=f"<b>แนวโน้มผู้ป่วย {disease_name} ({icd10_code}) vs PM2.5</b>",
             font=dict(size=18, family="Kanit, sans-serif")
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified", 
        margin=dict(t=80, l=10, r=10, b=20),
        font=dict(family="Kanit, sans-serif"),
    )
    
    # Axes
    pm25_max = df_pm["PM2.5 (ug/m3)"].max() if not df_pm.empty else 100
    fig.update_yaxes(title_text="ค่า PM2.5", range=[0, pm25_max * 1.2], secondary_y=False, showgrid=False)
    
    patient_max = df_merged['count'].max() if not df_merged.empty else 100
    fig.update_yaxes(
        title_text="จำนวนผู้ป่วย (คน)", 
        range=[0, patient_max * 1.1], 
        secondary_y=True, 
        gridcolor='rgba(128, 128, 128, 0.2)', # Adaptive grid color
        griddash="dot"
    )

    fig.update_xaxes(title_text="เดือน")

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
    
    years = sorted(df_merged['Year'].unique())
    colors = px.colors.sequential.Viridis # Use sequential for years usually looks nice
    
    for i, year in enumerate(years):
        df_year = df_merged[df_merged['Year'] == year]
        fig.add_trace(go.Scatter(
            x=df_year['Month'], 
            y=df_year['count'], 
            name=f'{year}',
            mode='lines+markers',
            line=dict(width=3),
            marker=dict(size=8)
        ))

    fig.update_layout(
        # template='plotly_white', # Removed
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        
        title=dict(
            text="<b>เปรียบเทียบจำนวนผู้ป่วยรวมในแต่ละปี (Year-over-Year)</b>",
            font=dict(size=18, family="Kanit, sans-serif")
        ),
        xaxis_title="เดือน",
        yaxis_title="จำนวนผู้ป่วยรวม (คน)",
        xaxis=dict(
            tickmode='array', 
            tickvals=list(range(1, 13)), 
            ticktext=['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']
        ),
        legend_title_text="ปี",
        hovermode="x unified",
        font=dict(family="Kanit, sans-serif"),
        margin=dict(t=80, l=10, r=10, b=20),
        
        # Add adaptive grid
        yaxis=dict(gridcolor='rgba(128, 128, 128, 0.2)', griddash="dot"),
        # xaxis=dict(gridcolor='rgba(128, 128, 128, 0.2)', griddash="dot") # Optional for X-axis
    )
    st.plotly_chart(fig, use_container_width=True)
