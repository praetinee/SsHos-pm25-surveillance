import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy.stats import pearsonr

def calculate_kpis(df):
    """คำนวณสถิติพื้นฐานสำหรับหน้า Dashboard"""
    total_patients = len(df)
    unique_patients = df['HN'].nunique() if 'HN' in df.columns else 0
    top_disease = df['4 กลุ่มโรคเฝ้าระวัง'].mode()[0] if not df['4 กลุ่มโรคเฝ้าระวัง'].empty else "N/A"
    
    return total_patients, unique_patients, top_disease

def get_pm_color(pm_value):
    """กำหนดสีตามมาตรฐานระดับฝุ่น"""
    if pm_value <= 15: return "🟢 ดีมาก"
    elif pm_value <= 25: return "🟡 ดี"
    elif pm_value <= 37.5: return "🟠 ปานกลาง"
    elif pm_value <= 75: return "🔴 เริ่มมีผลกระทบ"
    else: return "🟤 มีผลกระทบ (อันตราย)"

def plot_dual_axis(df, pm_df):
    """สร้างกราฟเทียบยอดผู้ป่วยกับค่า PM2.5 (Dual-axis)"""
    # รวมจำนวนผู้ป่วยรายเดือน
    monthly_cases = df.groupby('Month_Year').size().reset_index(name='Cases')
    
    # Merge กับข้อมูลฝุ่น
    merged = pd.merge(monthly_cases, pm_df, on='Month_Year', how='inner')
    merged['Month_Str'] = merged['Month_Year'].astype(str)
    
    # คำนวณ Correlation
    r_val, _ = pearsonr(merged['PM2.5'], merged['Cases'])
    
    fig = go.Figure()
    # กราฟแท่งจำนวนผู้ป่วย
    fig.add_trace(go.Bar(x=merged['Month_Str'], y=merged['Cases'], name="จำนวนผู้ป่วย (คน)", yaxis="y1", marker_color='lightblue'))
    # กราฟเส้น PM2.5
    fig.add_trace(go.Scatter(x=merged['Month_Str'], y=merged['PM2.5'], name="PM2.5 (µg/m³)", yaxis="y2", mode='lines+markers', line=dict(color='red', width=3)))
    
    fig.update_layout(
        title=f"ความสัมพันธ์จำนวนผู้ป่วยและ PM2.5 (r = {r_val:.2f})",
        yaxis=dict(title="จำนวนผู้ป่วย"),
        yaxis2=dict(title="PM2.5 (µg/m³)", overlaying="y", side="right"),
        legend=dict(x=0.01, y=0.99),
        margin=dict(l=0, r=0, t=40, b=0)
    )
    return fig, r_val

def plot_disease_breakdown(df):
    """กราฟวงกลมแสดงสัดส่วน 4 กลุ่มโรค"""
    disease_counts = df['4 กลุ่มโรคเฝ้าระวัง'].value_counts().reset_index()
    disease_counts.columns = ['Disease Group', 'Count']
    fig = px.pie(disease_counts, values='Count', names='Disease Group', hole=0.4, title="สัดส่วนผู้ป่วยตามกลุ่มโรค")
    fig.update_traces(textposition='inside', textinfo='percent+label')
    return fig

def plot_walkin_vs_appt(df):
    """เปรียบเทียบผู้ป่วยนัด vs Walk-in (ฉุกเฉิน)"""
    # ตีความว่าถ้าช่องมีคำว่า 'นัด' คือนัด นอกนั้นถือเป็น Walk-in
    df['Status'] = df['ผู้ป่วยนัด'].apply(lambda x: 'ผู้ป่วยนัด' if 'นัด' in str(x) else 'Walk-in (ฉุกเฉิน)')
    counts = df['Status'].value_counts().reset_index()
    fig = px.bar(counts, x='Status', y='count', color='Status', title="ปริมาณผู้ป่วยแยกตามประเภทการเข้ารับบริการ")
    return fig

def plot_new_old_opd(df):
    """สัดส่วนผู้ป่วยใหม่และเก่า (ดึงจากคอลัมน์ COPD+Asthma at OPD)"""
    if 'COPD+Asthma at OPD' not in df.columns:
        return None
        
    valid_cases = df[df['COPD+Asthma at OPD'].notna() & (df['COPD+Asthma at OPD'] != '-')]
    if valid_cases.empty:
        return None
        
    # ตัดข้อความเอาเฉพาะ 'ผู้ป่วยเก่า' หรือ 'ผู้ป่วยใหม่'
    valid_cases['Type'] = valid_cases['COPD+Asthma at OPD'].apply(
        lambda x: 'ผู้ป่วยใหม่' if 'ใหม่' in str(x) else ('ผู้ป่วยเก่า' if 'เก่า' in str(x) else 'อื่นๆ')
    )
    counts = valid_cases['Type'].value_counts().reset_index()
    fig = px.pie(counts, values='count', names='Type', title="อุบัติการณ์ผู้ป่วยโรคเรื้อรัง (เก่า vs ใหม่)")
    return fig
