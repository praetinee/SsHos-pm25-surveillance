import pandas as pd
import numpy as np
import streamlit as st
import statsmodels.formula.api as smf
import plotly.graph_objects as go

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
    """คำนวณ Poisson Regression เพื่อหาค่าความเสี่ยงสะสม (IRR) และ 95% CI"""
    if df_sub.empty or df_pm25.empty: return None
    
    monthly_cases = df_sub.groupby('Month_Year').size().reset_index(name='case_count')
    merged = pd.merge(monthly_cases, df_pm25, on='Month_Year', how='inner').dropna()
    
    if len(merged) < 6: return None
    
    try:
        model = smf.poisson('case_count ~ PM25', data=merged).fit(disp=0)
        coef = model.params['PM25']
        p_val = model.pvalues['PM25']
        conf_int = model.conf_int().loc['PM25']
        
        # คำนวณ IRR และ 95% CI ตาม SCALE ที่กำหนด
        irr_scaled = np.exp(coef * PM25_UNIT_SCALE)
        irr_lower = np.exp(conf_int[0] * PM25_UNIT_SCALE)
        irr_upper = np.exp(conf_int[1] * PM25_UNIT_SCALE)
        
        # แปลงเป็นเปอร์เซ็นต์การเพิ่มขึ้น/ลดลง
        pct_increase = (irr_scaled - 1) * 100
        pct_lower = (irr_lower - 1) * 100
        pct_upper = (irr_upper - 1) * 100
        
        return {
            "pct": pct_increase, 
            "p": p_val,
            "ci_lower": pct_lower,
            "ci_upper": pct_upper
        }
    except:
        return None

def render_forest_plot(significant_results):
    """สร้างกราฟ Forest Plot สำหรับผลลัพธ์ที่มีนัยสำคัญทางสถิติ"""
    if not significant_results:
        return
    
    # จัดเรียงข้อมูลจากน้อยไปมากตามค่า pct
    sorted_res = sorted(significant_results, key=lambda x: x['pct'])
    
    labels = [f"{r['group']} - {r['disease']}" for r in sorted_res]
    pcts = [r['pct'] for r in sorted_res]
    error_minus = [r['pct'] - r['ci_lower'] for r in sorted_res]
    error_plus = [r['ci_upper'] - r['pct'] for r in sorted_res]
    colors = ['#ef4444' if p > 0 else '#22c55e' for p in pcts] # แดง=เสี่ยงเพิ่ม, เขียว=เสี่ยงลด
    
    fig = go.Figure()
    
    # เพิ่มจุดและหนวดกุ้ง (Error Bars)
    fig.add_trace(go.Scatter(
        x=pcts,
        y=labels,
        mode='markers',
        marker=dict(color=colors, size=12, symbol='square'),
        error_x=dict(
            type='data',
            symmetric=False,
            array=error_plus,
            arrayminus=error_minus,
            color='#64748b',
            thickness=1.5,
            width=5
        ),
        text=[f"{p:+.1f}% (95% CI: {r['ci_lower']:+.1f} ถึง {r['ci_upper']:+.1f}, p={format_p_value(r['p'])})" for p, r in zip(pcts, sorted_res)],
        hoverinfo='text'
    ))
    
    # เพิ่มเส้นอ้างอิงที่ 0 (ไม่มีผลกระทบ)
    fig.add_vline(x=0, line_width=2, line_dash="dash", line_color="#94a3b8")
    
    fig.update_layout(
        font=dict(family="TH SarabunPSK, sans-serif", size=18), # ปรับฟอนต์เป็น TH SarabunPSK
        title="Forest Plot: การเปลี่ยนแปลงความเสี่ยงต่อฝุ่น PM2.5 (เฉพาะที่มีนัยสำคัญ p < 0.05)",
        xaxis_title="เปอร์เซ็นต์ความเสี่ยงที่เปลี่ยนแปลงต่อฝุ่น 10 µg/m³",
        yaxis_title="",
        height=max(400, len(labels) * 50), # ปรับความสูงตามจำนวนข้อมูล
        margin=dict(l=20, r=20, t=50, b=20),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)', zeroline=False, fixedrange=True), # fixedrange=True ล็อกไม่ให้ซูมแกน X
        yaxis=dict(fixedrange=True) # fixedrange=True ล็อกไม่ให้ซูมแกน Y
    )
    
    # config={'displayModeBar': False} เพื่อซ่อนแถบเครื่องมือด้านบน ทำให้ล็อกตายตัว
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

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

    csv_data = []
    significant_results = [] # เก็บข้อมูลสำหรับวาดกราฟ

    html_table = """
    <div style="overflow-x: auto; margin-bottom: 1rem;">
    <table style="width:100%; min-width: 700px; border-collapse: collapse; text-align: center; font-family: 'TH SarabunPSK', sans-serif; font-size: 18px;">
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
        csv_row = {"กลุ่มเป้าหมาย": age}
        
        for col_name, disease_name in disease_cols.items():
            df_target = df_age if disease_name is None else df_age[df_age['4 กลุ่มโรคเฝ้าระวัง'] == disease_name]
            
            res = perform_poisson_regression(df_target, df_pm25)
            if res:
                is_significant = res['p'] < 0.05
                significance = " ⭐" if is_significant else ""
                
                # เก็บข้อมูลสำหรับกราฟ Forest Plot (เฉพาะอันที่มีนัยสำคัญ)
                if is_significant:
                    significant_results.append({
                        "group": age,
                        "disease": col_name,
                        "pct": res['pct'],
                        "ci_lower": res['ci_lower'],
                        "ci_upper": res['ci_upper'],
                        "p": res['p']
                    })

                color = "#ef4444" if res['pct'] > 0 and is_significant else ("#22c55e" if res['pct'] < 0 and is_significant else "inherit")
                p_text = format_p_value(res['p'])
                cell_content = f"<span style='color: {color}; font-weight: {'bold' if res['p'] < 0.05 else 'normal'};'>{res['pct']:+.1f}%</span> <br> <span style='font-size: 0.85em; color: rgba(128, 128, 128, 0.8);'>(p={p_text}){significance}</span>"
                
                # ฟอร์แมตข้อมูลสำหรับ CSV (ป้องกัน Error ใน Google Sheets)
                if res['pct'] > 0:
                    csv_row[col_name] = f"เพิ่ม {abs(res['pct']):.1f}% (p={p_text})"
                elif res['pct'] < 0:
                    csv_row[col_name] = f"ลด {abs(res['pct']):.1f}% (p={p_text})"
                else:
                    csv_row[col_name] = f"0.0% (p={p_text})"
            else:
                cell_content = "<span style='color: rgba(128, 128, 128, 0.5);'>n/a</span>"
                csv_row[col_name] = "n/a"
            
            html_table += f'<td style="padding: 10px; border: 1px solid rgba(128, 128, 128, 0.2);">{cell_content}</td>'
    # แสดงผล HTML ตาราง
    st.markdown(html_table, unsafe_allow_html=True)
    
    # แสดงกราฟ Forest Plot ใต้ตาราง
    if significant_results:
        st.markdown("---")
        render_forest_plot(significant_results)
        st.caption("กราฟ Forest Plot แสดงช่วงความเชื่อมั่น 95% (95% CI) ของกลุ่มที่มีนัยสำคัญทางสถิติ สามารถบันทึกรูปภาพโดยกดไอคอนกล้องถ่ายรูปมุมขวาบนของกราฟ")
    
    # แสดงปุ่มดาวน์โหลด CSV
    df_csv = pd.DataFrame(csv_data)
    # ใช้ utf-8-sig เพื่อให้ Google Sheets และ Excel อ่านภาษาไทยได้สมบูรณ์
    csv_bytes = df_csv.to_csv(index=False).encode('utf-8-sig')
    
    st.download_button(
        label="📥 ดาวน์โหลดข้อมูลสำหรับ Google Sheets (CSV)",
        data=csv_bytes,
        file_name="statistical_matrix_pm25.csv",
        mime="text/csv",
        help="ดาวน์โหลดตารางนี้เป็นไฟล์ CSV ที่ปรับฟอร์แมตเครื่องหมายบวกลบ เพื่อไม่ให้เกิด Error เมื่อนำไปวางใน Google Sheets"
    )
    
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
            st.markdown(f'<div style="font-family: \'TH SarabunPSK\', sans-serif; background-color: rgba(128, 128, 128, 0.05); padding: 15px; border-radius: 10px; border-top: 4px solid {color}; height: 100%;"><h5 style="margin: 0; opacity: 0.8; font-size: 20px;">ความเสี่ยงรวม 🚨</h5><h3 style="color: {color}; margin: 0; font-size: 28px;">{val:+.1f}%</h3><p style="font-size: 16px; opacity: 0.7; margin-top: 5px;">ผู้ป่วยเพิ่มขึ้นต่อทุก {PM25_UNIT_SCALE} µg/m³ (p={p_text})</p></div>', unsafe_allow_html=True)
        else:
            monthly_cases = df_filtered.groupby('Month_Year').size().reset_index(name='Patient_Count')
            merged_stats = pd.merge(monthly_cases, df_pm25, on='Month_Year', how='inner')
            overall_corr = merged_stats['Patient_Count'].corr(merged_stats['PM25']) if len(merged_stats) > 1 else np.nan
            level, color, icon, _ = get_correlation_insight(overall_corr)
            st.markdown(f'<div style="font-family: \'TH SarabunPSK\', sans-serif; background-color: rgba(128, 128, 128, 0.05); padding: 15px; border-radius: 10px; border-top: 4px solid {color}; height: 100%;"><h5 style="margin: 0; opacity: 0.8; font-size: 20px;">ความสัมพันธ์ภาพรวม {icon}</h5><h3 style="color: {color}; margin: 0; font-size: 28px;">{level}</h3><p style="font-size: 16px; opacity: 0.7; margin-top: 5px;">r = {overall_corr:.2f} (Lag: {lag_days} วัน)</p></div>', unsafe_allow_html=True)
            
    with c2:
        if top_disease:
            st.markdown(f'<div style="font-family: \'TH SarabunPSK\', sans-serif; background-color: rgba(128, 128, 128, 0.05); padding: 15px; border-radius: 10px; border-top: 4px solid #8b5cf6; height: 100%;"><h5 style="margin: 0; opacity: 0.8; font-size: 20px;">กลุ่มโรคที่อ่อนไหวสุด 💨</h5><h4 style="color: #8b5cf6; margin: 0; font-size: 24px;">{top_disease}</h4><p style="font-size: 16px; opacity: 0.7; margin-top: 5px;">r = {top_corr:.2f}</p></div>', unsafe_allow_html=True)
            
    with c3:
        if vul_result:
            increase_pct, _, _ = vul_result
            st.markdown(f'<div style="font-family: \'TH SarabunPSK\', sans-serif; background-color: rgba(128, 128, 128, 0.05); padding: 15px; border-radius: 10px; border-top: 4px solid #ef4444; height: 100%;"><h5 style="margin: 0; opacity: 0.8; font-size: 20px;">ภัยคุกคามกลุ่มเปราะบาง 🛡️</h5><h3 style="color: #ef4444; margin: 0; font-size: 28px;">{increase_pct:+.1f}%</h3><p style="font-size: 16px; opacity: 0.7; margin-top: 5px;">อัตราเพิ่มในเดือนที่ฝุ่นเกินมาตรฐาน</p></div>', unsafe_allow_html=True)
