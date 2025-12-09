import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def plot_patient_timeline(df_pat, df_pm, selected_hn):
    """
    Generates a timeline plot for a single patient (HN), showing their visit dates 
    (ICD-10 complexity) overlaid on the monthly PM2.5 trend.
    
    Args:
        df_pat (pd.DataFrame): Patient data (must contain 'HN', 'วันที่เข้ารับบริการ', 'ICD10ทั้งหมด').
        df_pm (pd.DataFrame): PM2.5 data (must contain 'เดือน' and 'PM2.5 (ug/m3)').
        selected_hn (str): The Hospital Number (HN) to plot.
    """
    
    required_cols = ['HN', 'วันที่เข้ารับบริการ', 'ICD10ทั้งหมด']
    if not all(col in df_pat.columns for col in required_cols):
        st.error("ℹ️ ข้อมูลผู้ป่วยขาดคอลัมน์ที่จำเป็น ('HN', 'วันที่เข้ารับบริการ', หรือ 'ICD10ทั้งหมด')")
        return

    # 1. Filter data for the selected patient
    df_patient = df_pat[df_pat['HN'] == selected_hn].copy()
    
    if df_patient.empty:
        st.warning(f"ℹ️ ไม่พบข้อมูลการเข้ารับบริการสำหรับ HN: {selected_hn}")
        return

    # Ensure 'วันที่เข้ารับบริการ' is datetime and sort by it
    df_patient['วันที่เข้ารับบริการ'] = pd.to_datetime(df_patient['วันที่เข้ารับบริการ'])
    df_patient = df_patient.sort_values('วันที่เข้ารับบริการ')

    # 2. Prepare visit complexity (marker size)
    # Calculate the number of ICD-10 codes per visit
    def count_icd10(icd_str):
        if pd.isna(icd_str) or icd_str == '':
            return 0
        return len(str(icd_str).split(','))

    df_patient['ICD10_Count'] = df_patient['ICD10ทั้งหมด'].apply(count_icd10)
    
    # 3. Prepare PM2.5 data
    # Use 'เดือน' for PM2.5 trend
    df_merged = pd.merge(
        df_patient[['เดือน', 'วันที่เข้ารับบริการ', 'ICD10ทั้งหมด', 'ICD10_Count', '4 กลุ่มโรคเฝ้าระวัง']],
        df_pm,
        on='เดือน',
        how='left'
    )
    
    # Get all unique months in the PM2.5 dataset for the background trend line
    pm_months = sorted(df_pm["เดือน"].dropna().unique())
    pm_data_full = df_pm.set_index('เดือน').reindex(pm_months)['PM2.5 (ug/m3)']

    # 4. Create Plotly Figure (Dual Axis)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # --- PRIMARY Y-AXIS: PM2.5 TREND (Background) ---
    fig.add_trace(
        go.Scatter(
            x=[pd.to_datetime(m) for m in pm_months], # Convert month string to datetime for smooth plotting
            y=pm_data_full,
            name="PM2.5 รายเดือน",
            fill='tozeroy',
            mode='lines',
            line=dict(color='rgba(192, 192, 192, 0.5)', width=0.5),
            hovertemplate='<b>PM2.5:</b> %{y:.2f} µg/m³<extra></extra>',
        ), 
        secondary_y=False
    )
    
    # --- SECONDARY Y-AXIS: PATIENT VISITS (Timeline Markers) ---
    
    # Map disease groups to colors
    disease_colors = {
        'โรคระบบทางเดินหายใจ': 'red',
        'โรคหัวใจและหลอดเลือด': 'blue',
        'โรคตาอักเสบ': 'green',
        'โรคผิวหนังอักเสบ': 'orange',
        'แพทย์วินิจฉัยโรคร่วมด้วย Z58.1': 'purple',
    }
    
    # Group visits by the main disease category for plotting
    for group, color in disease_colors.items():
        df_group = df_merged[df_merged['4 กลุ่มโรคเฝ้าระวัง'] == group]
        if not df_group.empty:
            fig.add_trace(
                go.Scatter(
                    x=df_group['วันที่เข้ารับบริการ'],
                    y=[1] * len(df_group), # Use a placeholder Y-axis value (1) for simplicity
                    name=f"การเข้ารับบริการ: {group}",
                    mode='markers',
                    marker=dict(
                        size=df_group['ICD10_Count'] * 5 + 10, # Marker size scales with ICD-10 count
                        color=color,
                        opacity=0.8,
                        line=dict(width=1, color='Black')
                    ),
                    hovertemplate=(
                        f"<b>วันที่:</b> %{{x|%d %b %Y}}<br>" +
                        f"<b>กลุ่มโรค:</b> {group}<br>" +
                        "<b>PM2.5 (เดือนนี้):</b> %{customdata[0]:.2f} µg/m³<br>" +
                        "<b>จำนวน ICD-10 (ความซับซ้อน):</b> %{customdata[1]} รหัส<br>" +
                        "<b>ICD-10 ทั้งหมด:</b> %{customdata[2]}<extra></extra>"
                    ),
                    customdata=df_group[['PM2.5 (ug/m3)', 'ICD10_Count', 'ICD10ทั้งหมด']],
                ),
                secondary_y=True # Visits on the Secondary Axis
            )

    # 5. Update Layout and Axes
    fig.update_layout(
        title_text=f"เส้นเวลาการเข้ารับบริการของ HN: {selected_hn} เทียบกับแนวโน้ม PM2.5",
        hovermode="x unified", 
        font=dict(family="Tahoma, sans-serif"),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    
    # Primary Y-axis (PM2.5)
    pm25_max = df_pm["PM2.5 (ug/m3)"].max() if not df_pm.empty else 100
    fig.update_yaxes(
        title_text="ค่า PM2.5 (µg/m³)", 
        range=[0, pm25_max * 1.2], 
        secondary_y=False,
        showgrid=True,
        gridcolor='#e0e0e0',
    )
    
    # Secondary Y-axis (Visits Timeline) - We hide the axis line and ticks, only use markers
    fig.update_yaxes(
        title_text="การเข้ารับบริการ (แต่ละจุดคือ 1 Visit)", 
        secondary_y=True,
        showgrid=False,
        showticklabels=False,
        range=[0, 2] # Fixed range to keep markers visible at a constant height
    )

    fig.update_xaxes(title_text="วันที่เข้ารับบริการ")

    st.plotly_chart(fig, use_container_width=True)
