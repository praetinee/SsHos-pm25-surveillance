import pandas as pd
import numpy as np
import streamlit as st
import statsmodels.formula.api as smf
import statsmodels.api as sm
import plotly.graph_objects as go

# ค่าคงที่สำหรับปรับสเกลการวิเคราะห์ (มาตรฐานงานวิจัยฝุ่นคือทุกๆ 10 µg/m³)
PM25_UNIT_SCALE = 10

def format_p_value(p):
    """ฟอร์แมตค่า p-value ให้เป็นทศนิยมที่เหมาะสม"""
    if p < 0.00001:
        return "< 0.00001"
    elif p < 0.001:
        return f"{p:.5f}"  
    else:
        return f"{p:.3f}"  

def perform_poisson_regression(df_sub, df_pm25):
    """
    คำนวณ Quasi-Poisson Regression โดยทำการควบคุม Time Trend และ Seasonality
    เพื่อกรองปัจจัยกวน (Confounding factors) ออกตามหลักระบาดวิทยา
    """
    if df_sub.empty or df_pm25.empty: return None
    
    # 1. ยึดไทม์ไลน์ตามช่วงเวลาจาก PM2.5 เป็นฐาน เพื่อไม่ให้มีเดือนไหนตกหล่นแม้ไม่มีผู้ป่วย
    base_timeline = df_pm25[['Month_Year', 'PM25']].copy()
    
    # 2. นับจำนวนเคสรายเดือนและนำไป Merge กับฐาน
    monthly_cases = df_sub.groupby('Month_Year').size().reset_index(name='case_count')
    merged = pd.merge(base_timeline, monthly_cases, on='Month_Year', how='left').fillna({'case_count': 0})
    
    # 3. จัดเรียงตามเวลาให้ถูกต้อง
    merged = merged.sort_values('Month_Year')
    
    # เพิ่มการตรวจสอบ Sparse Data (ข้อมูลเบาบาง)
    non_zero_months = (merged['case_count'] > 0).sum()
    
    # 4. สร้างตัวแปรควบคุม (Control Variables)
    # 4.1 Time Trend: ควบคุมแนวโน้มระยะยาว (เช่น ผู้ป่วยอาจค่อยๆ เพิ่มขึ้นทุกปี)
    merged['Time_Trend'] = np.arange(1, len(merged) + 1)
    
    # 4.2 Seasonality: สร้างตัวแปรหมวดหมู่ (Categorical) เป็นเดือน 1-12 เพื่อควบคุมผลกระทบจากฤดูกาล
    merged['Month'] = merged['Month_Year'].dt.month.astype(str)
    
    # ต้องมีข้อมูลอย่างน้อยให้พอกับ Degree of Freedom ที่ใช้ไป (12 เดือน + 1 Time + 1 PM2.5)
    # และต้องมี "เดือนที่พบผู้ป่วยจริงๆ" อย่างน้อย 15 เดือน ป้องกันสมการระเบิด
    if len(merged) < 24 or non_zero_months < 15: 
        return None 
    
    try:
        # ใช้ Quasi-Poisson (GLM Poisson with scale='X2') 
        # C(Month) คือการระบุให้ Statsmodels แปลงเดือนเป็น Dummy Variables อัตโนมัติ
        formula = 'case_count ~ PM25 + Time_Trend + C(Month)'
        model = smf.glm(formula=formula, data=merged, family=sm.families.Poisson()).fit(scale='X2')
        
        # คำนวณ Dispersion Ratio ว่าข้อมูลเหวี่ยงมากแค่ไหน (เอาไว้ยืนยันการใช้ Quasi-Poisson)
        dispersion_ratio = model.pearson_chi2 / model.df_resid
        
        coef = model.params['PM25']
        
        # ป้องกันปัญหา Complete Separation ในขั้นสุดท้าย
        # ถ้ายอด Disp ต่ำผิดปกติ หรือค่าตัวคูณเหวี่ยงแรงจนทำให้เปอร์เซ็นต์ทะลุโลก ให้ถือว่าผลลัพธ์ล้มเหลว
        if dispersion_ratio < 0.05 or abs(coef) > 0.5:
            return None
            
        p_val = model.pvalues['PM25']
        conf_int = model.conf_int().loc['PM25']
        
        # คำนวณ IRR (Incidence Rate Ratio) ตามสเกลที่กำหนด (10 µg/m³)
        irr_scaled = np.exp(coef * PM25_UNIT_SCALE)
        irr_lower = np.exp(conf_int[0] * PM25_UNIT_SCALE)
        irr_upper = np.exp(conf_int[1] * PM25_UNIT_SCALE)
        
        # แปลงเป็น % ผู้ป่วยที่เปลี่ยนแปลง
        pct_increase = (irr_scaled - 1) * 100
        pct_lower = (irr_lower - 1) * 100
        pct_upper = (irr_upper - 1) * 100
        
        return {
            "pct": pct_increase, 
            "p": p_val,
            "ci_lower": pct_lower,
            "ci_upper": pct_upper,
            "dispersion": dispersion_ratio
        }
    except Exception as e:
        print(f"Regression Error: {e}") 
        return None

def render_forest_plot(significant_results):
    """สร้างกราฟ Forest Plot สำหรับผลลัพธ์ที่มีนัยสำคัญทางสถิติ"""
    if not significant_results:
        return
    
    sorted_res = sorted(significant_results, key=lambda x: x['pct'])
    labels = [f"{r['group']} - {r['disease']}" for r in sorted_res]
    pcts = [r['pct'] for r in sorted_res]
    error_minus = [r['pct'] - r['ci_lower'] for r in sorted_res]
    error_plus = [r['ci_upper'] - r['pct'] for r in sorted_res]
    colors = ['#ef4444' if p > 0 else '#22c55e' for p in pcts]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pcts, y=labels, mode='markers',
        marker=dict(color=colors, size=12, symbol='square'),
        error_x=dict(
            type='data', symmetric=False, array=error_plus, arrayminus=error_minus,
            color='#64748b', thickness=1.5, width=5
        ),
        text=[f"{p:+.1f}% (95% CI: {r['ci_lower']:+.1f} ถึง {r['ci_upper']:+.1f}, p={format_p_value(r['p'])})" for p, r in zip(pcts, sorted_res)],
        hoverinfo='text'
    ))
    
    fig.add_vline(x=0, line_width=2, line_dash="dash", line_color="#94a3b8")
    fig.update_layout(
        font=dict(family="TH SarabunPSK, sans-serif", size=18),
        title="Forest Plot: ความเสี่ยงการเกิดโรคที่เปลี่ยนแปลงต่อฝุ่น PM2.5 ที่เพิ่ม 10 µg/m³ (p < 0.05)",
        xaxis_title="ร้อยละความเสี่ยง (Percentage Change %)", yaxis_title="",
        height=max(400, len(labels) * 50), margin=dict(l=20, r=20, t=50, b=20),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)', zeroline=False, fixedrange=True),
        yaxis=dict(fixedrange=True)
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True, 'displaylogo': False})

def render_descriptive_stats(df_filtered, df_pm25):
    """
    สร้างตารางสถิติเชิงพรรณนา 12 เดือน เพื่อปูพื้นฐานงานวิจัย
    แสดงให้เห็นการเปลี่ยนแปลงรายเดือน (Seasonality) ของทั้ง PM2.5 และผู้ป่วย
    """
    st.markdown("### 📊 ตารางแสดงค่าเฉลี่ยรายเดือน (Baseline Descriptive Statistics)")
    st.caption("ตารางที่ 1 แสดงการเปรียบเทียบค่าเฉลี่ยฝุ่น PM2.5 และผู้ป่วยในแต่ละเดือน (ม.ค.-ธ.ค.) ตามช่วงปีที่เลือก เพื่อพิจารณาแนวโน้มตามฤดูกาล")
    
    if df_filtered.empty or df_pm25.empty:
        st.info("ไม่มีข้อมูลเพียงพอสำหรับแสดงผล")
        return

    thai_months = ['มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 'พฤษภาคม', 'มิถุนายน', 
                   'กรกฎาคม', 'สิงหาคม', 'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม']
                   
    disease_cols = {
        "ภาพรวม 4 กลุ่มโรค": None,
        "กลุ่มโรคตาอักเสบ": "กลุ่มโรคตาอักเสบ",
        "กลุ่มโรคทางเดินหายใจ": "กลุ่มโรคทางเดินหายใจ",
        "กลุ่มโรคผิวหนังอักเสบ": "กลุ่มโรคผิวหนังอักเสบ",
        "กลุ่มโรคหัวใจและหลอดเลือด": "กลุ่มโรคหัวใจและหลอดเลือด"
    }

    # คำนวณค่าสถิติ PM2.5 แยกตาม 12 เดือนตลอด 5 ปี
    base_pm = df_pm25.copy()
    base_pm['Month'] = base_pm['Month_Year'].dt.month
    pm_stats = base_pm.groupby('Month')['PM25'].agg(['mean', 'std']).reindex(range(1, 13), fill_value=0)

    html_table = """
    <div style="overflow-x: auto; margin-bottom: 1rem;">
    <table style="width:100%; min-width: 700px; border-collapse: collapse; text-align: center; font-family: 'TH SarabunPSK', sans-serif; font-size: 18px;">
        <thead>
            <tr style="background-color: rgba(59, 130, 246, 0.1); border-bottom: 2px solid rgba(59, 130, 246, 0.3);">
                <th style="padding: 12px; border: 1px solid rgba(128, 128, 128, 0.2);">เดือน</th>
                <th style="padding: 12px; border: 1px solid rgba(128, 128, 128, 0.2);">PM2.5 (µg/m³)<br><span style="font-size:14px; font-weight:normal;">Mean ± SD</span></th>
    """
    
    for col_name in disease_cols.keys():
        html_table += f'<th style="padding: 12px; border: 1px solid rgba(128, 128, 128, 0.2);">{col_name}<br><span style="font-size:14px; font-weight:normal;">Mean ± SD</span></th>'
    html_table += "</tr></thead><tbody>"

    for i, m_name in enumerate(thai_months, 1):
        bg_color = "background-color: rgba(128, 128, 128, 0.05);" if i % 2 == 0 else ""
        html_table += f'<tr style="border-bottom: 1px solid rgba(128, 128, 128, 0.2); {bg_color}">'
        html_table += f'<td style="padding: 10px; border: 1px solid rgba(128, 128, 128, 0.2); font-weight: bold; text-align: left;">{m_name}</td>'
        
        # คอลัมน์ PM2.5
        pm_m = pm_stats.loc[i, 'mean']
        pm_s = pm_stats.loc[i, 'std']
        if pd.isna(pm_s): pm_s = 0.0
        # ไฮไลต์สีแดงให้สังเกตง่าย
        html_table += f'<td style="padding: 10px; border: 1px solid rgba(128, 128, 128, 0.2); font-weight:bold; color:#ef4444;">{pm_m:.1f} ± {pm_s:.1f}</td>'
        
        # คอลัมน์โรคต่างๆ
        for col_name, disease_name in disease_cols.items():
            if disease_name is None:
                sub = df_filtered.copy()
            else:
                sub = df_filtered[df_filtered['4 กลุ่มโรคเฝ้าระวัง'] == disease_name].copy()
                
            # ต้องกรุ๊ปตาม เดือน_ปี ทั้งหมดก่อนเพื่อนับยอด จากนั้นเติม 0 ในเดือนที่ไม่มีเคส แล้วค่อยหาค่าเฉลี่ย
            monthly_c = sub.groupby('Month_Year').size().reset_index(name='count')
            merged = pd.merge(df_pm25[['Month_Year']], monthly_c, on='Month_Year', how='left').fillna({'count': 0})
            merged['Month'] = merged['Month_Year'].dt.month
            
            stats = merged.groupby('Month')['count'].agg(['mean', 'std']).reindex(range(1, 13), fill_value=0)
            
            d_m = stats.loc[i, 'mean']
            d_s = stats.loc[i, 'std']
            if pd.isna(d_s): d_s = 0.0
            
            html_table += f'<td style="padding: 10px; border: 1px solid rgba(128, 128, 128, 0.2);">{d_m:.1f} ± {d_s:.1f}</td>'
            
        html_table += "</tr>"
        
    html_table += "</tbody></table></div>"
    st.markdown(html_table, unsafe_allow_html=True)

def render_statistical_matrix(df_filtered, df_pm25):
    """สร้างตารางสรุปสถิติเชิงอนุมานด้วย Quasi-Poisson และกล่องคำอธิบายเชิงวิชาการสำหรับ อวช."""
    st.markdown("### 🧪 ตารางสถิติเชิงอนุมาน (Quasi-Poisson Regression Matrix)")
    st.caption(f"ตารางที่ 2 แสดงค่าความเสี่ยงของร้อยละผู้ป่วยที่เพิ่มขึ้น/ลดลง ต่อปริมาณ PM2.5 ที่ขยับขึ้นทุกๆ {PM25_UNIT_SCALE} µg/m³ (P-value)")
    
    age_groups = ["ทุกเพศทุกวัย", "ผู้สูงอายุ", "วัยผู้ใหญ่", "วัยเรียนและวัยรุ่น", "เด็ก", "หญิงตั้งครรภ์"]
    disease_cols = {
        "ภาพรวม 4 กลุ่มโรค": None,
        "กลุ่มโรคตาอักเสบ": "กลุ่มโรคตาอักเสบ",
        "กลุ่มโรคทางเดินหายใจ": "กลุ่มโรคทางเดินหายใจ",
        "กลุ่มโรคผิวหนังอักเสบ": "กลุ่มโรคผิวหนังอักเสบ",
        "กลุ่มโรคหัวใจและหลอดเลือด": "กลุ่มโรคหัวใจและหลอดเลือด"
    }

    csv_data = []
    significant_results = []

    html_table = """
    <div style="overflow-x: auto; margin-bottom: 1rem;">
    <table style="width:100%; min-width: 700px; border-collapse: collapse; text-align: center; font-family: 'TH SarabunPSK', sans-serif; font-size: 18px;">
        <thead>
            <tr style="background-color: rgba(128, 128, 128, 0.1); border-bottom: 2px solid rgba(128, 128, 128, 0.3);">
                <th style="padding: 12px; border: 1px solid rgba(128, 128, 128, 0.2);">กลุ่มเป้าหมาย</th>
    """
    
    for col_name in disease_cols.keys():
        html_table += f'<th style="padding: 12px; border: 1px solid rgba(128, 128, 128, 0.2);">{col_name}</th>'
    html_table += "</tr></thead><tbody>"

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
                
                model_tag = f"<br><span style='font-size: 0.75em; color: rgba(128, 128, 128, 0.7);'>(Disp: {res['dispersion']:.2f})</span>"
                cell_content = f"<span style='color: {color}; font-weight: {'bold' if is_significant else 'normal'};'>{res['pct']:+.1f}%</span> <br> <span style='font-size: 0.85em; color: rgba(128, 128, 128, 0.8);'>(p={p_text}){significance}</span>{model_tag}"
                
                csv_val = ""
                if res['pct'] > 0:
                    csv_val = f"เพิ่ม {abs(res['pct']):.1f}% (p={p_text})"
                elif res['pct'] < 0:
                    csv_val = f"ลด {abs(res['pct']):.1f}% (p={p_text})"
                else:
                    csv_val = f"0.0% (p={p_text})"
                
                csv_row[col_name] = f"{csv_val} [Disp: {res['dispersion']:.2f}]"
            else:
                cell_content = "<span style='color: rgba(128, 128, 128, 0.5);'>n/a</span>"
                csv_row[col_name] = "n/a"
            
            html_table += f'<td style="padding: 10px; border: 1px solid rgba(128, 128, 128, 0.2);">{cell_content}</td>'
            
        html_table += "</tr>"
        csv_data.append(csv_row)
        
    html_table += "</tbody></table></div>"
    st.markdown(html_table, unsafe_allow_html=True)
    
    if significant_results:
        st.markdown("---")
        render_forest_plot(significant_results)
        st.caption("กราฟ Forest Plot แสดงช่วงความเชื่อมั่น 95% (95% CI) ของกลุ่มที่มีนัยสำคัญทางสถิติ สามารถบันทึกรูปภาพโดยกดไอคอนกล้องถ่ายรูปมุมขวาบนของกราฟ")
    
    df_csv = pd.DataFrame(csv_data)
    csv_bytes = df_csv.to_csv(index=False).encode('utf-8-sig')
    
    st.download_button(
        label="📥 ดาวน์โหลดข้อมูลสำหรับ Google Sheets (CSV)",
        data=csv_bytes,
        file_name="statistical_matrix_pm25.csv",
        mime="text/csv"
    )
    
    st.markdown("---")
    
    st.markdown("#### 📚 คำอธิบายระเบียบวิธีวิจัยและสถิติที่ใช้ (สำหรับการเขียน อวช.)")
    st.info(
        "การศึกษานี้วิเคราะห์ความสัมพันธ์ระหว่างระดับฝุ่น PM2.5 กับจำนวนผู้ป่วยตามช่วงเวลาที่ศึกษา โดยมีขั้นตอนและระเบียบวิธีทางสถิติดังนี้:\n\n"
        
        "**1. การนำเสนอสถิติเชิงพรรณนารายเดือน (12-Month Baseline Analysis)**\n"
        "ในการทำความเข้าใจพฤติกรรมข้อมูลเบื้องต้น ได้มีการจัดกลุ่มข้อมูลและหาค่าเฉลี่ยแบบแยก 12 เดือน (ม.ค. - ธ.ค.) ตามช่วงปีที่กำหนด "
        "การนำเสนอในรูปแบบนี้ช่วยให้เห็นความสอดคล้องตามธรรมชาติระหว่าง 'ช่วงฤดูฝุ่น (High Season)' กับ 'แนวโน้มยอดผู้ป่วยที่เพิ่มขึ้น' "
        "ได้อย่างชัดเจน (อ้างอิงจากตารางที่ 1)\n\n"
        
        "**2. การวิเคราะห์ผลกระทบด้วยสมการถดถอยควาไซ-ปัวซง (Quasi-Poisson Regression)**\n"
        "ตัวแปรตาม (จำนวนผู้ป่วย) เป็นข้อมูลแจงนับ (Count Data) หากใช้ Linear Regression (OLS) ทั่วไปจะทำให้ได้ผลลัพธ์ที่ผิดพลาด "
        "และข้อมูลทางระบาดวิทยามักมีภาวะความแปรปรวนสูง (Overdispersion) การเลือกใช้โมเดล Quasi-Poisson จึงเหมาะสมที่สุด "
        "เพราะมีการเพิ่มค่า Dispersion Parameter (อักษรย่อ Disp ในตาราง) เข้ามาปรับช่วงความเชื่อมั่นให้กว้างขึ้น เพื่อป้องกันการเกิด 'นัยสำคัญหลอก (False Positive)'\n\n"
        
        "**3. การควบคุมตัวแปรกวน (Controlling for Confounders)**\n"
        "เพื่อให้ผลลัพธ์เปอร์เซ็นต์ความเสี่ยงมาจาก PM2.5 อย่างแท้จริง ภายใต้ข้อจำกัดของข้อมูล ผู้วิจัยได้นำตัวแปร 2 ตัวเข้าสู่สมการเพื่อทำหน้าที่ควบคุม:\n"
        "   - **Time Trend (ลำดับเวลาเดือนที่วิเคราะห์):** ป้องกันอคติจากจำนวนผู้ป่วยที่อาจเพิ่มสูงขึ้นทุกปีตามการเติบโตของประชากร\n"
        "   - **Seasonality (ตัวแปรหุ่นระบุเดือน 1-12):** กรองผลกระทบด้านฤดูกาลออก เนื่องจากผู้ป่วยมักเพิ่มในฤดูหนาวตามธรรมชาติอยู่แล้ว\n\n"
        
        "**4. การประเมินและแปลผล (Interpretation)**\n"
        "ความน่าเชื่อถือของโมเดลถูกประเมินจาก P-value (< 0.05) และค่า Dispersion Parameter (> 1.0 ยืนยันว่าต้องใช้ Quasi-Poisson) "
        "โดยตัวเลขแสดงผลเป็นค่า Incidence Rate Ratio (IRR) ที่ถูกแปลงเป็นร้อยละ (%) ซึ่งอธิบายได้ว่า หากค่าฝุ่นขยับสูงขึ้น 10 µg/m³ จำนวนผู้ป่วยจะเพิ่มหรือลดร้อยละเท่าใด"
    )

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
