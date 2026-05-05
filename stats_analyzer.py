import pandas as pd
import numpy as np
import streamlit as st
import statsmodels.formula.api as smf

def format_p_value(p):
    """ฟอร์แมตค่า p-value: ถ้าเล็กกว่า 0.001 ให้แสดงเป็นเลขยกกำลัง"""
    if p < 0.001:
        # แปลงจาก 1.23e-05 เป็น 1.23x10⁻⁵
        formatted = f"{p:.2e}".replace("e-0", "x10⁻").replace("e-", "x10⁻")
        # เปลี่ยนตัวเลขยกกำลังธรรมดาเป็นตัวยก (Superscript) เพื่อความสวยงาม
        superscript_map = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
        parts = formatted.split("⁻")
        if len(parts) > 1:
            return f"{parts[0]}x10⁻{parts[1].translate(superscript_map)}"
        return formatted
    return f"{p:.3f}"

def perform_poisson_regression(df_sub, df_pm25):
    """คำนวณ Poisson Regression สำหรับกลุ่มย่อย"""
    if df_sub.empty or df_pm25.empty: return None
    
    monthly_cases = df_sub.groupby('Month_Year').size().reset_index(name='case_count')
    merged = pd.merge(monthly_cases, df_pm25, on='Month_Year', how='inner').dropna()
    
    if len(merged) < 6: return None # ข้อมูลต้องมีอย่างน้อย 6 จุดเวลา
    
    try:
        model = smf.poisson('case_count ~ PM25', data=merged).fit(disp=0)
        coef = model.params['PM25']
        p_val = model.pvalues['PM25']
        irr_10 = np.exp(coef * 10)
        pct = (irr_10 - 1) * 100
        return {"pct": pct, "p": p_val}
    except:
        return None

def render_statistical_matrix(df_filtered, df_pm25):
    """สร้างตารางสรุปสถิติแยกตามกลุ่มโรคและกลุ่มอายุ"""
    st.markdown("### 🧪 ตารางวิเคราะห์ความเสี่ยงเชิงระบาดวิทยา (Poisson Regression Matrix)")
    st.caption("แสดงค่า % ผู้ป่วยที่เพิ่มขึ้นต่อ PM2.5 ทุกๆ 10 µg/m³ (ค่า P-value)")
    
    # นิยามแถวและคอลัมน์
    age_groups = ["ทุกเพศทุกวัย", "ผู้สูงอายุ", "วัยผู้ใหญ่", "วัยเรียนและวัยรุ่น", "เด็ก", "หญิงตั้งครรภ์"]
    disease_cols = {
        "ภาพรวม 4 กลุ่มโรค": None,
        "กลุ่มโรคตาอักเสบ": "กลุ่มโรคตาอักเสบ",
        "กลุ่มโรคทางเดินหายใจ": "กลุ่มโรคทางเดินหายใจ",
        "กลุ่มโรคผิวหนังอักเสบ": "กลุ่มโรคผิวหนังอักเสบ",
        "กลุ่มโรคหัวใจและหลอดเลือด": "กลุ่มโรคหัวใจและหลอดเลือด"
    }

    matrix_data = []

    for age in age_groups:
        row = {"กลุ่มเป้าหมาย": age}
        # กรองตามอายุ
        df_age = df_filtered if age == "ทุกเพศทุกวัย" else df_filtered[df_filtered['กลุ่มเปราะบาง'] == age]
        
        for col_name, disease_name in disease_cols.items():
            # กรองตามโรค
            df_target = df_age if disease_name is None else df_age[df_age['4 กลุ่มโรคเฝ้าระวัง'] == disease_name]
            
            res = perform_poisson_regression(df_target, df_pm25)
            if res:
                significance = "⭐" if res['p'] < 0.05 else ""
                p_text = format_p_value(res['p'])
                row[col_name] = f"{res['pct']:+.1f}% (p={p_text}){significance}"
            else:
                row[col_name] = "n/a"
        
        matrix_data.append(row)

    df_matrix = pd.DataFrame(matrix_data)
    
    # แสดงผลตารางแบบสวยงาม
    st.dataframe(
        df_matrix.set_index("กลุ่มเป้าหมาย"),
        use_container_width=True,
        column_config={col: st.column_config.TextColumn(col, help="เปอร์เซ็นต์ที่เพิ่มขึ้น (นัยสำคัญทางสถิติ)") for col in disease_cols.keys()}
    )
    st.info("💡 หมายเหตุ: ⭐ หมายถึงมีนัยสำคัญทางสถิติ (p < 0.05), n/a หมายถึงข้อมูลไม่เพียงพอในการคำนวณ")

def get_correlation_insight(corr):
    if pd.isna(corr): return "ข้อมูลไม่เพียงพอ", "#cbd5e1", "⚪", ""
    if corr >= 0.7: return "ระดับสูงมาก", "#ef4444", "🚨", "r >= 0.7"
    elif corr >= 0.5: return "ระดับปานกลาง", "#f97316", "⚠️", "r >= 0.5"
    elif corr >= 0.3: return "ระดับต่ำ", "#eab308", "📊", "r >= 0.3"
    elif corr > -0.3: return "ไม่ชัดเจน", "#64748b", "❔", ""
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
            st.markdown(f'<div style="background-color: #f8fafc; padding: 15px; border-radius: 10px; border-top: 4px solid {color}; height: 100%;"><h5 style="color: #475569; margin: 0;">ความเสี่ยงรวม 🚨</h5><h3 style="color: {color}; margin: 0;">{val:+.1f}%</h3><p style="font-size: 0.85rem; color: #64748b; margin-top: 5px;">ผู้ป่วยเพิ่มขึ้นต่อทุก 10 µg/m³ (p={p_text})</p></div>', unsafe_allow_html=True)
        else:
            monthly_cases = df_filtered.groupby('Month_Year').size().reset_index(name='Patient_Count')
            merged_stats = pd.merge(monthly_cases, df_pm25, on='Month_Year', how='inner')
            overall_corr = merged_stats['Patient_Count'].corr(merged_stats['PM25']) if len(merged_stats) > 1 else np.nan
            level, color, icon, _ = get_correlation_insight(overall_corr)
            st.markdown(f'<div style="background-color: #f8fafc; padding: 15px; border-radius: 10px; border-top: 4px solid {color}; height: 100%;"><h5 style="color: #475569; margin: 0;">ความสัมพันธ์ภาพรวม {icon}</h5><h3 style="color: {color}; margin: 0;">{level}</h3><p style="font-size: 0.85rem; color: #64748b; margin-top: 5px;">r = {overall_corr:.2f} (Lag: {lag_days} วัน)</p></div>', unsafe_allow_html=True)
    with c2:
        if top_disease:
            st.markdown(f'<div style="background-color: #f8fafc; padding: 15px; border-radius: 10px; border-top: 4px solid #8b5cf6; height: 100%;"><h5 style="color: #475569; margin: 0;">กลุ่มโรคที่อ่อนไหวสุด 💨</h5><h4 style="color: #8b5cf6; margin: 0;">{top_disease}</h4><p style="font-size: 0.85rem; color: #64748b; margin-top: 5px;">r = {top_corr:.2f}</p></div>', unsafe_allow_html=True)
    with c3:
        if vul_result:
            increase_pct, _, _ = vul_result
            st.markdown(f'<div style="background-color: #f8fafc; padding: 15px; border-radius: 10px; border-top: 4px solid #ef4444; height: 100%;"><h5 style="color: #475569; margin: 0;">ภัยคุกคามกลุ่มเปราะบาง 🛡️</h5><h3 style="color: #ef4444; margin: 0;">{increase_pct:+.1f}%</h3><p style="font-size: 0.85rem; color: #64748b; margin-top: 5px;">อัตราเพิ่มในเดือนที่ฝุ่นเกินมาตรฐาน</p></div>', unsafe_allow_html=True)
