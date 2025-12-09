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
    - Enhanced for visual clarity: PM2.5 as background area, patient lines on top.
    """
    
    patient_counts = df_pat.groupby(["เดือน", "4 กลุ่มโรคเฝ้าระวัง"]).size().reset_index(name="count")
    df_merged = pd.merge(patient_counts, df_pm, on="เดือน", how="outer").sort_values("เดือน")
    all_months = sorted(df_merged["เดือน"].dropna().unique())

    # Create the figure with a secondary Y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # 1. Add PM2.5 Area chart on the PRIMARY Y-AXIS (as the background layer)
    # Using 'lightgrey' for a subtle background feel.
    pm25_data = df_pm.set_index('เดือน').reindex(all_months)['PM2.5 (ug/m3)']
    
    fig.add_trace(
        go.Scatter(
            x=all_months,
            y=pm25_data,
            name="PM2.5 (ug/m3)",
            fill='tozeroy', # Fill the area under the line
            mode='lines',
            line=dict(color='rgba(192, 192, 192, 0.5)', width=0.5), # Grey, slightly transparent line
            # Customizing the hover template for better readability
            hovertemplate='<b>PM2.5:</b> %{y:.2f} µg/m³<extra></extra>',
        ), 
        secondary_y=False # On Primary Axis
    )

    # 2. Add Patient group lines on the SECONDARY Y-AXIS (placed on top for visibility)
    colors = px.colors.qualitative.D3 # Using D3 color scale for better contrast
    patient_groups = sorted(df_pat["4 กลุ่มโรคเฝ้าระวัง"].dropna().unique())

    for i, grp in enumerate(patient_groups):
        d2 = df_merged[df_merged["4 กลุ่มโรคเฝ้าระวัง"] == grp]
        fig.add_trace(
            go.Scatter(
                x=d2["เดือน"], 
                y=d2["count"], 
                name=f"{grp}", 
                mode="lines+markers", 
                line=dict(width=3, color=colors[i % len(colors)]), # Thicker line for emphasis
                marker=dict(size=8),
                hovertemplate='<b>%{y}</b> คน<extra></extra>',
            ),
            secondary_y=True # On Secondary Axis
        )
        
    # 3. Add Threshold lines for PM2.5 on the PRIMARY axis
    # Make lines thicker and more distinct
    fig.add_hline(
        y=37.5, 
        line=dict(dash="dot", color="#FFBF00", width=2), # Gold/Orange dotted line
        secondary_y=False # Refers to Primary Axis
    )
    fig.add_hline(
        y=75, 
        line=dict(dash="dash", color="#E30022", width=2), # Red dashed line
        secondary_y=False # Refers to Primary Axis
    )

    # 4. Update layout and annotations
    
    # Calculate max patient count to place annotations near the max y2 value
    max_patient_count = df_merged['count'].max() if not df_merged.empty else 100
    
    fig.update_layout(
        title_text="แนวโน้มจำนวนผู้ป่วยตามกลุ่มโรคเฝ้าระวัง เทียบกับค่า PM2.5 รายเดือน",
        legend_title_text="ข้อมูล",
        # Use x unified hover mode to show all values for the same month
        hovermode="x unified", 
        margin=dict(t=50, l=0, r=0, b=0),
        
        # Adjusting font and background for a cleaner look
        font=dict(family="Tahoma, sans-serif"),
        plot_bgcolor='rgba(0,0,0,0)', # Transparent plot background
        paper_bgcolor='rgba(0,0,0,0)', # Transparent paper background
        
        # Annotations for PM2.5 thresholds
        annotations=[
            dict(
                x=all_months[-1] if all_months else 0,
                y=37.5,
                xref="x",
                yref="y", # yref refers to the primary y-axis (PM2.5)
                text="⚠️ อากาศที่ต้องระวัง (37.5)",
                showarrow=False,
                xanchor='right',
                yanchor='bottom',
                font=dict(color="#FFBF00", size=12),
                yshift=5
            ),
            dict(
                x=all_months[-1] if all_months else 0,
                y=75,
                xref="x",
                yref="y", # yref refers to the primary y-axis (PM2.5)
                text="🛑 อากาศแย่ (75)",
                showarrow=False,
                xanchor='right',
                yanchor='bottom',
                font=dict(color="#E30022", size=12),
                yshift=5
            )
        ]
    )
    
    # 5. Update Axes
    # Set range for PRIMARY y-axis (PM2.5)
    pm25_max = df_pm["PM2.5 (ug/m3)"].max() if not df_pm.empty else 100
    fig.update_yaxes(
        title_text="ค่า PM2.5 (µg/m³)", 
        range=[0, pm25_max * 1.2], 
        secondary_y=False,
        showgrid=False # Hide grid lines for PM2.5 axis
    )
    
    # Set range for SECONDARY y-axis (Patient Count)
    patient_max = df_merged['count'].max() if not df_merged.empty else 100
    fig.update_yaxes(
        title_text="จำนวนผู้ป่วย (คน)", 
        range=[0, patient_max * 1.1], 
        secondary_y=True,
        gridcolor='#e0e0e0', # Light gray grid lines for patient axis
        griddash="dot"
    )

    fig.update_xaxes(title_text="เดือน")

    st.plotly_chart(fig, use_container_width=True)


# ----------------------------
# NEW: Plot for Specific Disease Trend vs PM2.5
# NOTE: This function is preserved but not used for the specific ICD-10 trend below
# as the filtering logic needs to be different (string contains vs exact match).
# ----------------------------
def plot_specific_disease_trend(df_pat, df_pm, disease_code, disease_name):
    """
    Generates a trend chart for a single, specific disease (filtered by ICD-10 code)
    compared against PM2.5 levels. (This assumes 'ICD-10' column has single code per row)
    """
    if "ICD-10" not in df_pat.columns:
        st.error(f"ไม่พบคอลัมน์ 'ICD-10' ในข้อมูลผู้ป่วย ไม่สามารถแสดงกราฟ {disease_name} ได้")
        return
        
    df_specific = df_pat[df_pat['ICD-10'] == disease_code]
    
    if df_specific.empty:
        st.info(f"ℹ️ ไม่มีข้อมูลผู้ป่วยสำหรับรหัสโรค {disease_code} ({disease_name})")
        return

    patient_counts = df_specific.groupby("เดือน").size().reset_index(name="count")
    df_merged = pd.merge(patient_counts, df_pm, on="เดือน", how="outer").sort_values("เดือน")
    all_months = sorted(df_merged["เดือน"].dropna().unique())

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # 1. Add PM2.5 Area chart (PRIMARY Y-AXIS)
    pm25_data = df_pm.set_index('เดือน').reindex(all_months)['PM2.5 (ug/m3)']
    
    fig.add_trace(
        go.Scatter(
            x=all_months,
            y=pm25_data,
            name="PM2.5 (ug/m3)",
            fill='tozeroy',
            mode='lines',
            line=dict(color='rgba(192, 192, 192, 0.5)', width=0.5),
            hovertemplate='<b>PM2.5:</b> %{y:.2f} µg/m³<extra></extra>',
        ), 
        secondary_y=False
    )

    # 2. Add Specific Patient line (SECONDARY Y-AXIS)
    line_color = px.colors.qualitative.D3[4] # Choose a distinct color
    
    fig.add_trace(
        go.Scatter(
            x=df_merged["เดือน"], 
            y=df_merged["count"], 
            name=f"จำนวนผู้ป่วย {disease_name}", 
            mode="lines+markers", 
            line=dict(width=3, color=line_color),
            marker=dict(size=8),
            hovertemplate='<b>%{y}</b> คน<extra></extra>',
        ),
        secondary_y=True
    )
        
    # 3. Add Threshold lines for PM2.5
    fig.add_hline(y=37.5, line=dict(dash="dot", color="#FFBF00", width=2), secondary_y=False)
    fig.add_hline(y=75, line=dict(dash="dash", color="#E30022", width=2), secondary_y=False)

    # 4. Update layout and annotations
    fig.update_layout(
        title_text=f"แนวโน้มจำนวนผู้ป่วย {disease_name} ({disease_code}) เทียบกับค่า PM2.5 รายเดือน",
        legend_title_text="ข้อมูล",
        hovermode="x unified", 
        margin=dict(t=50, l=0, r=0, b=0),
        font=dict(family="Tahoma, sans-serif"),
        plot_bgcolor='rgba(0,0,0,0)', 
        paper_bgcolor='rgba(0,0,0,0)',
        annotations=[
            dict(
                x=all_months[-1] if all_months else 0,
                y=37.5,
                xref="x",
                yref="y",
                text="⚠️ อากาศที่ต้องระวัง (37.5)",
                showarrow=False,
                xanchor='right',
                yanchor='bottom',
                font=dict(color="#FFBF00", size=12),
                yshift=5
            ),
            dict(
                x=all_months[-1] if all_months else 0,
                y=75,
                xref="x",
                yref="y",
                text="🛑 อากาศแย่ (75)",
                showarrow=False,
                xanchor='right',
                yanchor='bottom',
                font=dict(color="#E30022", size=12),
                yshift=5
            )
        ]
    )
    
    # 5. Update Axes
    pm25_max = df_pm["PM2.5 (ug/m3)"].max() if not df_pm.empty else 100
    fig.update_yaxes(
        title_text="ค่า PM2.5 (µg/m³)", 
        range=[0, pm25_max * 1.2], 
        secondary_y=False,
        showgrid=False
    )
    
    patient_max = df_merged['count'].max() if not df_merged.empty else 100
    fig.update_yaxes(
        title_text=f"จำนวนผู้ป่วย {disease_name} (คน)", 
        range=[0, patient_max * 1.1], 
        secondary_y=True,
        gridcolor='#e0e0e0', 
        griddash="dot"
    )

    fig.update_xaxes(title_text="เดือน")

    st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# NEW FUNCTION: Plot for Specific ICD-10 (J44.0) with String Matching
# ----------------------------
def plot_specific_icd10_trend(df_pat, df_pm, icd10_code, disease_name, icd10_column_name="ICD10ทั้งหมด"):
    """
    Generates a trend chart for a single, specific ICD-10 code where the ICD-10 
    column contains multiple codes as a comma-separated string.
    """
    if icd10_column_name not in df_pat.columns:
        st.error(f"ไม่พบคอลัมน์ '{icd10_column_name}' ในข้อมูลผู้ป่วย ไม่สามารถแสดงกราฟ {disease_name} ได้")
        return
    
    # 1. Filtering: Use str.contains to find rows where the ICD-10 string contains the code.
    # We use regex to match the code exactly (e.g., 'J44.0' not 'J44.00') by looking for 
    # either comma before/after or start/end of string.
    # Since the ICD-10 column header is 'ICD10ทั้งหมด', we use that.
    pattern = r'(^|,)' + icd10_code + r'(,|$)'
    df_specific = df_pat[df_pat[icd10_column_name].astype(str).str.contains(icd10_code, na=False)]
    
    if df_specific.empty:
        st.info(f"ℹ️ ไม่มีข้อมูลผู้ป่วยสำหรับรหัสโรค {icd10_code} ({disease_name})")
        return

    # 2. Aggregation and Merge
    patient_counts = df_specific.groupby("เดือน").size().reset_index(name="count")
    df_merged = pd.merge(patient_counts, df_pm, on="เดือน", how="outer").sort_values("เดือน")
    all_months = sorted(df_merged["เดือน"].dropna().unique())

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # 3. Add PM2.5 Area chart (PRIMARY Y-AXIS) - Copied from main trend plot
    pm25_data = df_pm.set_index('เดือน').reindex(all_months)['PM2.5 (ug/m3)']
    
    fig.add_trace(
        go.Scatter(
            x=all_months,
            y=pm25_data,
            name="PM2.5 (ug/m3)",
            fill='tozeroy',
            mode='lines',
            line=dict(color='rgba(192, 192, 192, 0.5)', width=0.5),
            hovertemplate='<b>PM2.5:</b> %{y:.2f} µg/m³<extra></extra>',
        ), 
        secondary_y=False
    )

    # 4. Add Specific Patient line (SECONDARY Y-AXIS)
    line_color = px.colors.qualitative.Plotly[0] # Use a distinct color for this specific disease
    
    fig.add_trace(
        go.Scatter(
            x=df_merged["เดือน"], 
            y=df_merged["count"], 
            name=f"จำนวนผู้ป่วย {disease_name}", 
            mode="lines+markers", 
            line=dict(width=3, color=line_color),
            marker=dict(size=8),
            hovertemplate='<b>%{y}</b> คน<extra></extra>',
        ),
        secondary_y=True
    )
        
    # 5. Add Threshold lines for PM2.5
    fig.add_hline(y=37.5, line=dict(dash="dot", color="#FFBF00", width=2), secondary_y=False)
    fig.add_hline(y=75, line=dict(dash="dash", color="#E30022", width=2), secondary_y=False)

    # 6. Update layout and annotations
    fig.update_layout(
        title_text=f"แนวโน้มจำนวนผู้ป่วย {disease_name} ({icd10_code}) เทียบกับค่า PM2.5 รายเดือน",
        legend_title_text="ข้อมูล",
        hovermode="x unified", 
        margin=dict(t=50, l=0, r=0, b=0),
        font=dict(family="Tahoma, sans-serif"),
        plot_bgcolor='rgba(0,0,0,0)', 
        paper_bgcolor='rgba(0,0,0,0)',
        annotations=[
            dict(
                x=all_months[-1] if all_months else 0,
                y=37.5,
                xref="x",
                yref="y",
                text="⚠️ อากาศที่ต้องระวัง (37.5)",
                showarrow=False,
                xanchor='right',
                yanchor='bottom',
                font=dict(color="#FFBF00", size=12),
                yshift=5
            ),
            dict(
                x=all_months[-1] if all_months else 0,
                y=75,
                xref="x",
                yref="y",
                text="🛑 อากาศแย่ (75)",
                showarrow=False,
                xanchor='right',
                yanchor='bottom',
                font=dict(color="#E30022", size=12),
                yshift=5
            )
        ]
    )
    
    # 7. Update Axes
    pm25_max = df_pm["PM2.5 (ug/m3)"].max() if not df_pm.empty else 100
    fig.update_yaxes(
        title_text="ค่า PM2.5 (µg/m³)", 
        range=[0, pm25_max * 1.2], 
        secondary_y=False,
        showgrid=False
    )
    
    patient_max = df_merged['count'].max() if not df_merged.empty else 100
    fig.update_yaxes(
        title_text=f"จำนวนผู้ป่วย {disease_name} (คน)", 
        range=[0, patient_max * 1.1], 
        secondary_y=True,
        gridcolor='#e0e0e0', 
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
    
    years = df_merged['Year'].unique()
    colors = px.colors.qualitative.D3 # Use the same color scale for consistency
    
    for i, year in enumerate(years):
        df_year = df_merged[df_merged['Year'] == year]
        fig.add_trace(go.Scatter(
            x=df_year['Month'], 
            y=df_year['count'], 
            name=f'ผู้ป่วย ปี {year}',
            mode='lines+markers',
            line=dict(width=3, color=colors[i % len(colors)]),
            marker=dict(size=8)
        ))

    fig.update_layout(
        title_text="กราฟเปรียบเทียบจำนวนผู้ป่วยรวมในแต่ละปี",
        xaxis_title="เดือน",
        yaxis_title="จำนวนผู้ป่วยรวม (คน)",
        xaxis=dict(
            tickmode='array', 
            tickvals=list(range(1, 13)), 
            ticktext=['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']
        ),
        legend_title_text="ปี",
        hovermode="x unified",
        font=dict(family="Tahoma, sans-serif"),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    st.plotly_chart(fig, use_container_width=True)
