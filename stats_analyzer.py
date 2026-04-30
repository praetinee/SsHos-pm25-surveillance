import pandas as pd
import numpy as np
import streamlit as st

def get_correlation_insight(corr):
    """ฟังก์ชันสำหรับแปลผลค่า Correlation ให้อ่านง่าย"""
    if pd.isna(corr):
        return "ข้อมูลไม่เพียงพอ", "#cbd5e1", "⚪", "ไม่มีข้อมูลประมวลผล"
    
    if corr >= 0.7:
        return "ระดับสูงมาก", "#ef4444", "🚨", "ความสัมพันธ์ชัดเจน ควรเฝ้าระวังสูงสุด"
    elif corr >= 0.5:
        return "ระดับปานกลาง", "#f97316", "⚠️", "มีผลกระทบในระดับที่สังเกตได้"
    elif corr >= 0.3:
        return "ระดับต่ำ", "#eab308", "📊", "มีผลกระทบเล็กน้อย หรือมีปัจจัยอื่นร่วม"
    elif corr > -0.3:
        return "ไม่ชัดเจน", "#64748b", "❔", "ไม่พบความสัมพันธ์ทางสถิติที่ชัดเจน"
    else:
        return "เชิงลบ", "#3b82f6", "📉", "ข้อมูลแปรผกผัน (อาจเกิดจากปัจจัยอื่น)"

def analyze_disease_correlation(df, df_pm25):
    """คำนวณความสัมพันธ์แยกตามกลุ่มโรค"""
    monthly_disease = df.groupby(['Month_Year', '4 กลุ่มโรคเฝ้าระวัง']).size().reset_index(name='Count')
    merged = pd.merge(monthly_disease, df_pm25, on='Month_Year', how='inner')
    
    disease_corrs = {}
    for disease in merged['4 กลุ่มโรคเฝ้าระวัง'].unique():
        sub = merged[merged['4 กลุ่มโรคเฝ้าระวัง'] == disease]
        if len(sub) > 2:
            r = sub['Count'].corr(sub['PM25'])
            if not pd.isna(r):
                disease_corrs[disease] = r
                
    if not disease_corrs:
        return None, None
        
    top_disease = max(disease_corrs, key=disease_corrs.get)
    max_corr = disease_corrs[top_disease]
    return top_disease, max_corr

def analyze_vulnerable_impact(df, df_pm25):
    """วิเคราะห์ผลกระทบต่อกลุ่มเปราะบาง (Threshold 37.5)"""
    THRESHOLD = 37.5 
    df_pm25_high = df_pm25[df_pm25['PM25'] > THRESHOLD]['Month_Year']
    df_pm25_low = df_pm25[df_pm25['PM25'] <= THRESHOLD]['Month_Year']
    
    focus_groups = ['เด็ก', 'ผู้สูงอายุ', 'หญิงตั้งครรภ์']
    if 'กลุ่มเปราะบาง' not in df.columns: return None
        
    vul_data = df[df['กลุ่มเปราะบาง'].isin(focus_groups)]
    high_cases = vul_data[vul_data['Month_Year'].isin(df_pm25_high)].shape[0]
    low_cases = vul_data[vul_data['Month_Year'].isin(df_pm25_low)].shape[0]
    
    months_high = len(df_pm25_high)
    months_low = len(df_pm25_low)
    
    avg_high = (high_cases / months_high) if months_high > 0 else 0
    avg_low = (low_cases / months_low) if months_low > 0 else 0
    
    increase_pct = ((avg_high - avg_low) / avg_low) * 100 if avg_low > 0 else (0 if avg_high == 0 else 100)
    return increase_pct, avg_high, avg_low

def render_smart_insights(df_filtered, df_pm25, lag_days=0):
    """วาด UI สำหรับ Smart Insight Dashboard พร้อมข้อมูล Lag Analysis"""
    if df_filtered.empty or df_pm25.empty:
        return

    st.markdown(f"### 🧠 Smart Insights: วิเคราะห์เชิงลึก (Lag: {lag_days} วัน)")
    
    # 1. คำนวณ Overall Correlation
    monthly_cases = df_filtered.groupby('Month_Year').size().reset_index(name='Patient_Count')
    merged_stats = pd.merge(monthly_cases, df_pm25, on='Month_Year', how='inner')
    
    overall_corr = np.nan
    if len(merged_stats) > 1:
        overall_corr = merged_stats['Patient_Count'].corr(merged_stats['PM25'])
        
    level, color, icon, desc = get_correlation_insight(overall_corr)
    
    # 2. คำนวณ Disease Correlation
    top_disease, top_corr = analyze_disease_correlation(df_filtered, df_pm25)
    
    # 3. คำนวณ Vulnerable Impact
    vul_result = analyze_vulnerable_impact(df_filtered, df_pm25)

    c1, c2, c3 = st.columns(3)
    
    # Card 1: ความสัมพันธ์ภาพรวม
    with c1:
        corr_val = f"{overall_corr:.2f}" if not pd.isna(overall_corr) else "N/A"
        st.markdown(f"""
        <div style="background-color: #f8fafc; padding: 15px; border-radius: 10px; border-top: 4px solid {color}; height: 100%;">
            <h5 style="color: #475569; margin: 0; font-family: 'Sarabun', sans-serif;">ความสัมพันธ์ที่พิจารณา Lag {icon}</h5>
            <h3 style="color: {color}; margin: 0; font-family: 'Sarabun', sans-serif;">{level} <span style="font-size: 1rem; color: #94a3b8;">(r={corr_val})</span></h3>
            <p style="font-size: 0.85rem; color: #64748b; margin-top: 5px;">ค่าความสัมพันธ์เทียบกับฝุ่นเมื่อย้อนไป {lag_days} วัน</p>
        </div>
        """, unsafe_allow_html=True)
        
    # Card 2: โรคที่อ่อนไหวที่สุด
    with c2:
        if top_disease and top_corr >= 0.3:
            st.markdown(f"""
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 10px; border-top: 4px solid #8b5cf6; height: 100%;">
                <h5 style="color: #475569; margin: 0; font-family: 'Sarabun', sans-serif;">กลุ่มโรคที่อ่อนไหวสุด 💨</h5>
                <h4 style="color: #8b5cf6; margin: 0; font-family: 'Sarabun', sans-serif;">{top_disease}</h4>
                <p style="font-size: 0.85rem; color: #64748b; margin-top: 5px;">มีความสัมพันธ์สูงสุดที่ Lag นี้ (r={top_corr:.2f})</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("<div style='background-color: #f8fafc; padding: 15px; border-radius: 10px; border-top: 4px solid #cbd5e1; height: 100%;'>ยังไม่พบความสัมพันธ์ชัดเจน</div>", unsafe_allow_html=True)

    # Card 3: ผลกระทบต่อกลุ่มเปราะบาง
    with c3:
        if vul_result:
            increase_pct, avg_high, avg_low = vul_result
            status_color = "#ef4444" if increase_pct > 0 else "#22c55e"
            st.markdown(f"""
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 10px; border-top: 4px solid {status_color}; height: 100%;">
                <h5 style="color: #475569; margin: 0; font-family: 'Sarabun', sans-serif;">ภัยคุกคามกลุ่มเปราะบาง 🛡️</h5>
                <h3 style="color: {status_color}; margin: 0;">{"+" if increase_pct > 0 else ""}{increase_pct:.1f}%</h3>
                <p style="font-size: 0.85rem; color: #64748b; margin-top: 5px;">อัตราการเพิ่มขึ้นในเดือนที่ฝุ่นเกินมาตรฐาน</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
