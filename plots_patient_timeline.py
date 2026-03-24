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
    # Re-conversion is key for robustness
    df_patient['วันที่เข้ารับบริการ'] = pd.to_datetime(df_patient['วันที่เข้ารับบริการ'], errors='coerce')
    df_patient = df_patient.dropna(subset=['วันที่เข้ารับบริการ']).sort_values('วันที่เข้ารับบริการ')

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
    # FIX: Explicitly convert month strings to Datetime objects using the known format
    try:
        pm_dates = pd.to_datetime(pm_months, format='%Y-%m', errors='coerce').dropna()
    except Exception:
        pm_dates = pd.to_datetime(pm_months, errors='coerce').dropna()

    if pm_dates.empty:
        st.error("ไม่สามารถสร้างแกนเวลา PM2.5 ได้ ข้อมูลเดือน PM2.5 อาจไม่ถูกต้อง")
        return

    fig.add_trace(
        go.Scatter(
            x=pm_dates, # Use the converted Datetime objects
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
        'โรคอื่นๆ/ไม่ระบุ': 'gray' # NEW: Added fallback group
    }
    
    # Identify visits not belonging to the main surveillance groups
    surveillance_groups = list(disease_colors.keys())[:-1] # Exclude 'โรคอื่นๆ/ไม่ระบุ'
    
    df_merged['Plot_Group'] = df_merged['4 กลุ่มโรคเฝ้าระวัง'].apply(
        lambda x: x if x in surveillance_groups else 'โรคอื่นๆ/ไม่ระบุ'
    )
    
    # Group visits by the main disease category for plotting
    data_plotted = False
    for group in disease_colors.keys():
        color = disease_colors[group]
        df_group = df_merged[df_merged['Plot_Group'] == group]
        
        if not df_group.empty:
            data_plotted = True
            
            # The group name in hover must be the actual '4 กลุ่มโรคเฝ้าระวัง' value
            # For 'โรคอื่นๆ/ไม่ระบุ', we just use the group name
            
            # Prepare hovertext using the actual '4 กลุ่มโรคเฝ้าระวัง' column
            hover_group_name = group if group != 'โรคอื่นๆ/ไม่ระบุ' else 'โรคอื่นๆ/ไม่ระบุ'
            
            fig.add_trace(
                go.Scatter(
                    x=df_group['วันที่เข้ารับบริการ'],
                    y=[1] * len(df_group), # Use a placeholder Y-axis value (1) for simplicity
                    name=f"การเข้ารับบริการ: {hover_group_name}",
                    mode='markers',
                    marker=dict(
                        size=df_group['ICD10_Count'] * 5 + 10, # Marker size scales with ICD-10 count
                        color=color,
                        opacity=0.8,
                        line=dict(width=1, color='Black')
                    ),
                    hovertemplate=(
                        f"<b>วันที่:</b> %{{x|%d %b %Y}}<br>" +
                        "<b>กลุ่มโรค:</b> %{customdata[3]}<br>" + # Use the original group name for detail
                        "<b>PM2.5 (เดือนนี้):</b> %{customdata[0]:.2f} µg/m³<br>" +
                        "<b>จำนวน ICD-10 (ความซับซ้อน):</b> %{customdata[1]} รหัส<br>" +
                        "<b>ICD-10 ทั้งหมด:</b> %{customdata[2]}<extra></extra>"
                    ),
                    customdata=df_group[['PM2.5 (ug/m3)', 'ICD10_Count', 'ICD10ทั้งหมด', '4 กลุ่มโรคเฝ้าระวัง']],
                ),
                secondary_y=True # Visits on the Secondary Axis
            )

    # If no patient data was plotted (but PM2.5 was), give a warning
    # We can now simplify this warning since we have a catch-all 'โรคอื่นๆ/ไม่ระบุ' group.
    if not data_plotted and selected_hn != "default":
        st.warning(f"ℹ️ HN: {selected_hn} มีข้อมูลผู้ป่วย แต่ไม่สามารถจับคู่กับกลุ่มโรคเฝ้าระวังได้ หรือวันที่ไม่ถูกต้อง")


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
