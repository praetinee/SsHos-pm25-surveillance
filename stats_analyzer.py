import pandas as pd
import numpy as np
import streamlit as st
import statsmodels.formula.api as smf

# ค่าคงที่สำหรับปรับสเกลการวิเคราะห์ (มาตรฐานงานวิจัยฝุ่นคือทุกๆ 10 µg/m³)
PM25_UNIT_SCALE = 10

def format_p_value(p):
    """ฟอร์แมตค่า p-value ให้เป็นทศนิยมที่เหมาะสม ไม่แสดง 0.000 ถ้าค่าไม่ใช่ศูนย์"""
    if p < 0.00001:
        return "< 0.00001"
    elif p < 0.001:
        return f"{p:.5f}"  # แสดง 5 ตำแหน่งสำหรับค่าน้อยๆ เพื่อให้เห็นตัวเลขที่ไม่ใช่ศูนย์
    else:
        return f"{p:.3f}"  # มาตรฐาน 3 ตำแหน่ง

def perform_poisson_regression(df_sub, df_pm25):
    """คำนวณ Poisson Regression เพื่อหาค่าความเสี่ยงสะสม (IRR)"""
    if df_sub.empty or df_pm25.empty: return None
    
    # รวมกลุ่มข้อมูลรายเดือน
    monthly_cases = df_sub.groupby('Month_Year').size().reset_index(name='case_count')
    merged = pd.merge(monthly_cases, df_pm25, on='Month_Year', how='inner').dropna()
    
    if len(merged) < 6: return None
    
    try:
        # รัน Model: ln(count) = beta0 + beta1 * PM25
        model = smf.poisson('case_count ~ PM25', data=merged).fit(disp=0)
        coef = model.params['PM25']
        p_val = model.pvalues['PM25']
        
        # คำนวณความเสี่ยงสัมพัทธ์ (IRR) ต่อการเพิ่มขึ้นของฝุ่นตาม SCALE ที่กำหนด
        # IRR = exp(beta * scale)
        irr_scaled = np.exp(coef * PM25_UNIT_SCALE)
        
        # แปลงเป็นเปอร์เซ็นต์การเพิ่มขึ้น
        pct_increase = (irr_scaled - 1) * 100
        
        return {"pct": pct_increase, "p": p_val}
    except:
        return None

def render_statistical_matrix(df_filtered, df_pm25):
    """สร้างตารางสรุปสถิติแยกตามกลุ่มโรคและกลุ่มอายุ แบบ Static HTML (รองรับ Responsive & Themes)"""
    st.markdown("### 🧪 ตารางวิเคราะห์ความเสี่ยงเชิงระบาดวิทยา (Poisson Regression Matrix)")
    st.caption(f"แสดงค่า % ผู้ป่วยที่เพิ่มขึ้นต่อ PM2.5 ทุกๆ {PM25_UNIT_SCALE} µg/m³ (ค่า P-value)")
    
    age_groups = ["ทุกเพศทุกวัย", "ผู้สูงอายุ", "วัยผู้ใหญ่", "วัยเรียนและวัยรุ่น", "เด็ก", "หญิงตั้งครรภ์"]
    disease_cols = {
        "ภาพรวม 4 กลุ่มโรค": None,
        "กลุ่มโรคตาอักเสบ": "กลุ่มโรคตาอักเสบ",
        "กลุ่มโรคทางเดินหายใจ": "กลุ่มโรคทางเดินหายใจ",
        "กลุ่มโรคผิวหนังอักเสบ": "กลุ่มโรคผิวหนังอักเสบ",
        "กลุ่มโรคหัวใจและหลอดเลือด": "กลุ่มโรคหัวใจและหลอดเลือด"
    }

    # สร้างโครงสร้าง HTML สำหรับตาราง ครอบด้วย div ให้เลื่อนซ้ายขวาได้ในจอมือถือ
    html_table = """
    <div style="overflow-x: auto; margin-bottom: 1rem;">
    <table style="width:100%; min-width: 700px; border-collapse: collapse; text-align: center; font-family: 'Sarabun', sans-serif;">
        <thead>
            <tr style="background-color: rgba(128, 128, 128, 0.1); border-bottom: 2px solid rgba(128, 128, 128, 0.3);">
                <th style="padding: 12px; border: 1px solid rgba(128, 128, 128, 0.2);">กลุ่มเป้าหมาย</th>
    """
    
    # เพิ่มส่วนหัวคอลัมน์
    for col_name in disease_cols.keys():
        html_table += f'<th style="padding: 12px; border: 1px solid rgba(128, 128, 128, 0.2);">{col_name}</th>'
    html_table += "</tr></thead><tbody>"

    # สร้างเนื้อหาแต่ละแถว
    for age in age_groups:
        bg_color = "background-color: rgba(128, 128, 128, 0.05);" if age_groups.index(age) % 2 != 0 else ""
        html_table += f'<tr style="border-bottom: 1px solid rgba(128, 128, 128, 0.2); {bg_color}">'
        html_table += f'<td style="padding: 10px; border: 1px solid rgba(128, 128, 128, 0.2); font-weight: bold; text-align: left;">{age}</td>'
        
        df_age = df_filtered if age == "ทุกเพศทุกวัย" else df_filtered[df_filtered['กลุ่มเปราะบาง'] == age]
        
        for col_name, disease_name in disease_cols.items():
            df_target = df_age if disease_name is None else df_age[df_age['4 กลุ่มโรคเฝ้าระวัง'] == disease_name]
            
            res = perform_poisson_regression(df_target, df_pm25)
            if res:
                significance = " ⭐" if res['p'] < 0.05 else ""
                # ใช้ inherit เพื่อให้สีกลมกลืนไปกับธีม หากผลไม่มีนัยสำคัญ
                color = "#ef4444" if res['pct'] > 0 and res['p'] < 0.05 else ("#22c55e" if res['pct'] < 0 and res['p'] < 0.05 else "inherit")
                p_text = format_p_value(res['p'])
                cell_content = f"<span style='color: {color}; font-weight: {'bold' if res['p'] < 0.05 else 'normal'};'>{res['pct']:+.1f}%</span> <br> <span style='font-size: 0.85em; color: rgba(128, 128, 128, 0.8);'>(p={p_text}){significance}</span>"
            else:
                cell_content = "<span style='color: rgba(128, 128, 128, 0.5);'>n/a</span>"
            
            html_table += f'<td style="padding: 10px; border: 1px solid rgba(128, 128, 128, 0.2);">{cell_content}</td>'
            
        html_table += "</tr>"
        
    html_table += "</tbody></table></div>"

    # แสดงผล HTML
    st.markdown(html_table, unsafe_allow_html=True)
    st.info(f"💡 หมายเหตุ: ค่า % คำนวณจากการเพิ่มขึ้นของฝุ่นทุก {PM25_UNIT_SCALE} µg/m³ โดยใช้ Poisson Regression Model. \n ⭐ หมายถึงมีนัยสำคัญทางสถิติ (p < 0.05)")

def get_correlation_insight(corr):
    if pd.isna(corr): return "ข้อมูลไม่เพียงพอ", "rgba(128,128,128,0.5)", "⚪", ""
    if corr >= 0.7: return "ระดับสูงมาก", "#ef4444", "🚨", "r >= 0.7"
    elif corr >= 0.5: return "ระดับปานกลาง", "#f97316", "⚠️", "r >= 0.5"
    elif corr >= 0.3: return "ระดับต่ำ", "#eab308", "📊", "r >= 0.3"
    elif corr > -0.3: return "ไม่ชัดเจน", "inherit", "❔", ""
    else: return "เชิงลบ", "#3b82f6", "📉", "แปรผกผัน"

def analyze_disease_correlation(df, df_pm25):
    monthly_disease = df.groupby(['Month_Year', '4 กลุ่มโรคเฝ้าระวัง']).size().reset_index(name='Count')
    merged = pd.merge(monthly_disease, df_pm25, on='Month_Year', how='inner')
    disease_corrs = {}
    for disease in merged['4 กลุ่มโรคเฝ้าระวัง'].unique():
        sub = merged[merged['4 กลุ่มโรคเฝ้าระวัง'] == disease]
        if len(sub) > 2:
            r = sub['Count'].corr(sub['PM25'])
            if not pd.isna(r): disease_corrs[disease] = r
    if not disease_corrs: return None, None
    top_disease = max(disease_corrs, key=disease_corrs.get)
    return top_disease, disease_corrs[top_disease]

def analyze_vulnerable_impact(df, df_pm25):
    THRESHOLD = 37.5 
    df_pm25_high = df_pm25[df_pm25['PM25'] > THRESHOLD]['Month_Year']
    df_pm25_low = df_pm25[df_pm25['PM25'] <= THRESHOLD]['Month_Year']
    focus_groups = ['เด็ก', 'ผู้สูงอายุ', 'หญิงตั้งครรภ์']
    if 'กลุ่มเปราะบาง' not in df.columns: return None
    vul_data = df[df['กลุ่มเปราะบาง'].isin(focus_groups)]
    high_cases = vul_data[vul_data['Month_Year'].isin(df_pm25_high)].shape[0]
    low_cases = vul_data[vul_data['Month_Year'].isin(df_pm25_low)].shape[0]
    avg_high = (high_cases / len(df_pm25_high)) if len(df_pm25_high) > 0 else 0
    avg_low = (low_cases / len(df_pm25_low)) if len(df_pm25_low) > 0 else 0
    increase_pct = ((avg_high - avg_low) / avg_low) * 100 if avg_low > 0 else 0
    return increase_pct, avg_high, avg_low

def render_smart_insights(df_filtered, df_pm25, lag_days=0):
    if df_filtered.empty or df_pm25.empty: return
    st.markdown(f"### 🧠 Smart Insights: วิเคราะห์เชิงลึก (Lag: {lag_days} วัน)")
    poisson_res = perform_poisson_regression(df_filtered, df_pm25)
    top_disease, top_corr = analyze_disease_correlation(df_filtered, df_pm25)
    vul_result = analyze_vulnerable_impact(df_filtered, df_pm25)
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        if poisson_res and poisson_res['p'] < 0.05:
            val = poisson_res['pct']
            p_text = format_p_value(poisson_res['p'])
            color = "#ef4444" if val > 0 else "#22c55e"
            st.markdown(f'<div style="background-color: rgba(128, 128, 128, 0.05); padding: 15px; border-radius: 10px; border-top: 4px solid {color}; height: 100%;"><h5 style="margin: 0; opacity: 0.8;">ความเสี่ยงรวม 🚨</h5><h3 style="color: {color}; margin: 0;">{val:+.1f}%</h3><p style="font-size: 0.85rem; opacity: 0.7; margin-top: 5px;">ผู้ป่วยเพิ่มขึ้นต่อทุก {PM25_UNIT_SCALE} µg/m³ (p={p_text})</p></div>', unsafe_allow_html=True)
        else:
            monthly_cases = df_filtered.groupby('Month_Year').size().reset_index(name='Patient_Count')
            merged_stats = pd.merge(monthly_cases, df_pm25, on='Month_Year', how='inner')
            overall_corr = merged_stats['Patient_Count'].corr(merged_stats['PM25']) if len(merged_stats) > 1 else np.nan
            level, color, icon, _ = get_correlation_insight(overall_corr)
            st.markdown(f'<div style="background-color: rgba(128, 128, 128, 0.05); padding: 15px; border-radius: 10px; border-top: 4px solid {color}; height: 100%;"><h5 style="margin: 0; opacity: 0.8;">ความสัมพันธ์ภาพรวม {icon}</h5><h3 style="color: {color}; margin: 0;">{level}</h3><p style="font-size: 0.85rem; opacity: 0.7; margin-top: 5px;">r = {overall_corr:.2f} (Lag: {lag_days} วัน)</p></div>', unsafe_allow_html=True)
            
    with c2:
        if top_disease:
            st.markdown(f'<div style="background-color: rgba(128, 128, 128, 0.05); padding: 15px; border-radius: 10px; border-top: 4px solid #8b5cf6; height: 100%;"><h5 style="margin: 0; opacity: 0.8;">กลุ่มโรคที่อ่อนไหวสุด 💨</h5><h4 style="color: #8b5cf6; margin: 0;">{top_disease}</h4><p style="font-size: 0.85rem; opacity: 0.7; margin-top: 5px;">r = {top_corr:.2f}</p></div>', unsafe_allow_html=True)
            
    with c3:
        if vul_result:
            increase_pct, _, _ = vul_result
            st.markdown(f'<div style="background-color: rgba(128, 128, 128, 0.05); padding: 15px; border-radius: 10px; border-top: 4px solid #ef4444; height: 100%;"><h5 style="margin: 0; opacity: 0.8;">ภัยคุกคามกลุ่มเปราะบาง 🛡️</h5><h3 style="color: #ef4444; margin: 0;">{increase_pct:+.1f}%</h3><p style="font-size: 0.85rem; opacity: 0.7; margin-top: 5px;">อัตราเพิ่มในเดือนที่ฝุ่นเกินมาตรฐาน</p></div>', unsafe_allow_html=True)
