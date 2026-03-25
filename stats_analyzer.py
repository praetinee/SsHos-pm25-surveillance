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
    """คำนวณความสัมพันธ์แยกตามกลุ่มโรค และหาโรคที่สัมพันธ์สูงสุด"""
    monthly_disease = df.groupby(['Month_Year', '4 กลุ่มโรคเฝ้าระวัง']).size().reset_index(name='Count')
    merged = pd.merge(monthly_disease, df_pm25, on='Month_Year', how='inner')
    
    disease_corrs = {}
    for disease in merged['4 กลุ่มโรคเฝ้าระวัง'].unique():
        sub = merged[merged['4 กลุ่มโรคเฝ้าระวัง'] == disease]
        if len(sub) > 2: # ต้องมีข้อมูลอย่างน้อย 3 เดือนถึงจะหา correlation ได้
            r = sub['Count'].corr(sub['PM25'])
            if not pd.isna(r):
                disease_corrs[disease] = r
                
    if not disease_corrs:
        return None, None
        
    # หาโรคที่มีค่า r สูงสุด
    top_disease = max(disease_corrs, key=disease_corrs.get)
    max_corr = disease_corrs[top_disease]
    return top_disease, max_corr

def analyze_vulnerable_impact(df, df_pm25):
    """
    วิเคราะห์ผลกระทบต่อกลุ่มเปราะบาง 
    โดยเทียบเดือนที่ฝุ่นเกินมาตรฐาน (> 37.5) vs เดือนที่ฝุ่นปกติ
    """
    # เกณฑ์มาตรฐาน PM2.5 ของไทย (ค่าเฉลี่ย 24 ชม. ปรับใช้กับรายเดือนเพื่อเป็น Threshold เบื้องต้น)
    THRESHOLD = 37.5 
    
    df_pm25_high = df_pm25[df_pm25['PM25'] > THRESHOLD]['Month_Year']
    df_pm25_low = df_pm25[df_pm25['PM25'] <= THRESHOLD]['Month_Year']
    
    focus_groups = ['เด็ก', 'ผู้สูงอายุ', 'หญิงตั้งครรภ์']
    if 'กลุ่มเปราะบาง' not in df.columns:
        return None
        
    vul_data = df[df['กลุ่มเปราะบาง'].isin(focus_groups)]
    
    # นับจำนวนผู้ป่วยในเดือนที่ฝุ่นสูง vs ต่ำ
    high_cases = vul_data[vul_data['Month_Year'].isin(df_pm25_high)].shape[0]
    low_cases = vul_data[vul_data['Month_Year'].isin(df_pm25_low)].shape[0]
    
    # หาค่าเฉลี่ยต่อเดือน (เพราะจำนวนเดือนที่ฝุ่นสูงกับต่ำอาจไม่เท่ากัน)
    months_high = len(df_pm25_high)
    months_low = len(df_pm25_low)
    
    avg_high = (high_cases / months_high) if months_high > 0 else 0
    avg_low = (low_cases / months_low) if months_low > 0 else 0
    
    # คำนวณเปอร์เซ็นต์ที่เพิ่มขึ้น
    if avg_low > 0:
        increase_pct = ((avg_high - avg_low) / avg_low) * 100
    else:
        increase_pct = 0 if avg_high == 0 else 100 # ถ้าปกติไม่มีคนป่วยเลย แต่ฝุ่นสูงมีคนป่วย ถือว่าเพิ่ม 100%
        
    return increase_pct, avg_high, avg_low

def render_smart_insights(df_filtered, df_pm25):
    """วาด UI สำหรับ Smart Insight Dashboard พร้อมระบบ Tooltip Hover สุดฉลาด"""
    if df_filtered.empty or df_pm25.empty:
        return

    # --- CSS สำหรับทำ Hover Tooltip สวยๆ และบังคับฟอนต์ Sarabun + Fallback Emoji ---
    tooltip_css = """
    <style>
    .smart-tooltip {
        position: relative;
        display: inline-block;
        cursor: help;
        color: #94a3b8;
        font-size: 0.95rem;
        margin-left: 6px;
    }
    .smart-tooltip .tooltip-text {
        visibility: hidden;
        width: 280px;
        background-color: #1e293b;
        color: #f8fafc;
        text-align: left;
        border-radius: 8px;
        padding: 12px 14px;
        position: absolute;
        z-index: 1000;
        bottom: 130%;
        left: 50%;
        margin-left: -140px;
        opacity: 0;
        transition: opacity 0.3s;
        font-family: 'Sarabun', 'Segoe UI', 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji', sans-serif !important;
        font-size: 0.8rem;
        font-weight: 300;
        line-height: 1.5;
        box-shadow: 0px 8px 16px rgba(0,0,0,0.15);
    }
    .smart-tooltip .tooltip-text::after {
        content: "";
        position: absolute;
        top: 100%;
        left: 50%;
        margin-left: -6px;
        border-width: 6px;
        border-style: solid;
        border-color: #1e293b transparent transparent transparent;
    }
    .smart-tooltip:hover .tooltip-text {
        visibility: visible;
        opacity: 1;
    }
    .tooltip-title {
        color: #38bdf8;
        font-weight: bold;
        display: block;
        margin-bottom: 4px;
        font-size: 0.85rem;
    }
    </style>
    """
    st.markdown(tooltip_css, unsafe_allow_html=True)

    st.markdown("### 🧠 Smart Insights: วิเคราะห์ข้อมูลเชิงลึกทางสถิติ")
    
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

    # --- วาด UI แบ่ง 3 คอลัมน์ ---
    c1, c2, c3 = st.columns(3)
    
    # Card 1: ความสัมพันธ์ภาพรวม
    with c1:
        corr_val = f"{overall_corr:.2f}" if not pd.isna(overall_corr) else "N/A"
        st.markdown(f"""
        <div style="background-color: #f8fafc; padding: 15px; border-radius: 10px; border-top: 4px solid {color}; height: 100%;">
            <div style="display: flex; align-items: center; margin-bottom: 5px;">
                <h5 style="color: #475569; margin: 0; font-family: 'Sarabun', sans-serif;">ภาพรวมความสัมพันธ์ {icon}</h5>
                <div class="smart-tooltip">ℹ️
                    <span class="tooltip-text">
                        <span class="tooltip-title">📊 สถิติที่ใช้: Pearson Correlation (r)</span>
                        เหมาะสมที่สุดในการตอบคำถามว่า 'เมื่อฝุ่นเพิ่มขึ้น ผู้ป่วยเพิ่มตามหรือไม่' เป็นมาตรฐานสากลในการหาความสัมพันธ์เชิงเส้น ซึ่งตอบโจทย์สาธารณสุขได้ตรงจุดและเข้าใจง่าย
                    </span>
                </div>
            </div>
            <h3 style="color: {color}; margin: 0; font-family: 'Sarabun', sans-serif;">{level} <span style="font-size: 1rem; color: #94a3b8;">(r={corr_val})</span></h3>
            <p style="font-size: 0.85rem; color: #64748b; margin-top: 5px; font-family: 'Sarabun', sans-serif;">{desc}</p>
        </div>
        """, unsafe_allow_html=True)
        
    # Card 2: โรคที่อ่อนไหวที่สุด
    with c2:
        if top_disease and top_corr >= 0.3:
            st.markdown(f"""
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 10px; border-top: 4px solid #8b5cf6; height: 100%;">
                <div style="display: flex; align-items: center; margin-bottom: 5px;">
                    <h5 style="color: #475569; margin: 0; font-family: 'Sarabun', sans-serif;">โรคที่อ่อนไหวต่อฝุ่นที่สุด 💨</h5>
                    <div class="smart-tooltip">ℹ️
                        <span class="tooltip-text">
                            <span class="tooltip-title">🔍 กระบวนการ: Comparative Sensitivity</span>
                            ช่วยให้แพทย์จัดลำดับความสำคัญ (Prioritization) ได้ทันที ว่าโรคใดทำปฏิกิริยากับฝุ่นไวที่สุด เพื่อบริหารทรัพยากรเตียงและยาเตรียมรับมือได้ล่วงหน้า
                        </span>
                    </div>
                </div>
                <h4 style="color: #8b5cf6; margin: 0; font-family: 'Sarabun', sans-serif;">{top_disease}</h4>
                <p style="font-size: 0.85rem; color: #64748b; margin-top: 5px; font-family: 'Sarabun', sans-serif;">มีความสัมพันธ์กับฝุ่นสูงสุด (r={top_corr:.2f})</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 10px; border-top: 4px solid #cbd5e1; height: 100%;">
                <h5 style="color: #475569; margin-bottom: 5px; font-family: 'Sarabun', sans-serif;">โรคที่อ่อนไหวต่อฝุ่นที่สุด 💨</h5>
                <p style="font-size: 0.9rem; color: #64748b; margin-top: 5px; font-family: 'Sarabun', sans-serif;">ยังไม่พบกลุ่มโรคที่มีความสัมพันธ์กับฝุ่นอย่างชัดเจน</p>
            </div>
            """, unsafe_allow_html=True)

    # Card 3: ผลกระทบต่อกลุ่มเปราะบาง
    with c3:
        if vul_result:
            increase_pct, avg_high, avg_low = vul_result
            if increase_pct > 0:
                st.markdown(f"""
                <div style="background-color: #fef2f2; padding: 15px; border-radius: 10px; border-top: 4px solid #ef4444; height: 100%;">
                    <div style="display: flex; align-items: center; margin-bottom: 5px;">
                        <h5 style="color: #475569; margin: 0; font-family: 'Sarabun', sans-serif;">ภัยคุกคามกลุ่มเปราะบาง 🛡️</h5>
                        <div class="smart-tooltip">ℹ️
                            <span class="tooltip-text">
                                <span class="tooltip-title">📈 สถิติที่ใช้: Percentage Change</span>
                                การใช้ 'ร้อยละการเปลี่ยนแปลง' เหมาะสมต่อการนำเสนอผู้บริหาร เพราะสะท้อน 'ขนาดภาระงานที่เพิ่มขึ้นจริง' (Magnitude) ออกมาเป็นตัวเลขที่จับต้องได้ สื่อสารได้ทรงพลังกว่าค่า P-Value
                            </span>
                        </div>
                    </div>
                    <h3 style="color: #ef4444; margin: 0; font-family: 'Sarabun', sans-serif;">+{increase_pct:.1f}%</h3>
                    <p style="font-size: 0.85rem; color: #64748b; margin-top: 5px; font-family: 'Sarabun', sans-serif;">
                        ผู้ป่วยเด็ก/ผู้สูงอายุ/คนท้อง <b>เพิ่มขึ้น</b> ในเดือนที่ฝุ่นเกินมาตรฐาน (>37.5 µg/m³) <br>
                        <span style="font-size: 0.75rem;">(เฉลี่ย {avg_high:.0f} คน/เดือน เทียบกับปกติ {avg_low:.0f} คน)</span>
                    </p>
                </div>
                """, unsafe_allow_html=True)
            else:
                 st.markdown(f"""
                <div style="background-color: #f0fdf4; padding: 15px; border-radius: 10px; border-top: 4px solid #22c55e; height: 100%;">
                    <h5 style="color: #475569; margin-bottom: 5px; font-family: 'Sarabun', sans-serif;">ภัยคุกคามกลุ่มเปราะบาง 🛡️</h5>
                    <h3 style="color: #22c55e; margin: 0; font-family: 'Sarabun', sans-serif;">ทรงตัว</h3>
                    <p style="font-size: 0.85rem; color: #64748b; margin-top: 5px; font-family: 'Sarabun', sans-serif;">ไม่พบการเพิ่มขึ้นของกลุ่มเปราะบางในเดือนที่ฝุ่นเกินมาตรฐาน</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 10px; border-top: 4px solid #cbd5e1; height: 100%;">
                <h5 style="color: #475569; margin-bottom: 5px; font-family: 'Sarabun', sans-serif;">ภัยคุกคามกลุ่มเปราะบาง 🛡️</h5>
                <p style="font-size: 0.85rem; color: #64748b; margin-top: 5px; font-family: 'Sarabun', sans-serif;">ไม่มีข้อมูลกลุ่มเปราะบางให้วิเคราะห์</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
