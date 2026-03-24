import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy.stats import pearsonr, spearmanr

def plot_correlation_scatter(df_pat, df_pm):
    """
    Overhauled function to provide correlation insights across all disease and vulnerable groups.
    """
    st.subheader("📊 ตารางสรุปความสัมพันธ์ (Correlation Summary)")
    st.markdown("ตารางด้านล่างแสดงค่าความสัมพันธ์ระหว่างปริมาณ PM2.5 กับจำนวนผู้ป่วยในกลุ่มต่างๆ โดยเรียงลำดับจากกลุ่มที่มีความสัมพันธ์มากที่สุดไปน้อยที่สุด")

    # ฟังก์ชันช่วยคำนวณความสัมพันธ์
    def calculate_correlation(df_grouped, group_name):
        df_analysis = pd.merge(
            df_grouped.groupby('เดือน').size().reset_index(name='จำนวนผู้ป่วย'), 
            df_pm, on='เดือน', how='inner'
        )
        if len(df_analysis) >= 3:
            pearson_r, pearson_p = pearsonr(df_analysis['PM2.5 (ug/m3)'], df_analysis['จำนวนผู้ป่วย'])
            spearman_rho, spearman_p = spearmanr(df_analysis['PM2.5 (ug/m3)'], df_analysis['จำนวนผู้ป่วย'])
            
            # เลือกค่าที่ดีที่สุด (มีนัยสำคัญและค่าสูงกว่า)
            if pearson_p < 0.05 and spearman_p < 0.05:
                if abs(spearman_rho) > abs(pearson_r):
                    return spearman_rho, spearman_p, "Spearman"
                else:
                    return pearson_r, pearson_p, "Pearson"
            elif pearson_p < 0.05:
                return pearson_r, pearson_p, "Pearson"
            elif spearman_p < 0.05:
                return spearman_rho, spearman_p, "Spearman"
            else:
                # ถ้าไม่มีนัยสำคัญ ให้ส่งค่า Pearson ไปโชว์เป็นค่าตั้งต้น
                return pearson_r, pearson_p, "ไม่พบนัยสำคัญ"
        return None, None, "ข้อมูลไม่พอ"

    results = []

    # 1. ความสัมพันธ์ภาพรวม
    r, p, t = calculate_correlation(df_pat, "ผู้ป่วยทั้งหมด")
    if r is not None:
        results.append({
            "หมวดหมู่": "ภาพรวม",
            "กลุ่ม": "ผู้ป่วยทั้งหมด",
            "ค่าความสัมพันธ์ (r/ρ)": r,
            "p-value": p,
            "ประเภทสถิติ": t,
            "นัยสำคัญ": "✅" if p < 0.05 else "❌"
        })

    # 2. ความสัมพันธ์รายกลุ่มโรค
    if "4 กลุ่มโรคเฝ้าระวัง" in df_pat.columns:
        for group in df_pat["4 กลุ่มโรคเฝ้าระวัง"].dropna().unique():
            df_group = df_pat[df_pat["4 กลุ่มโรคเฝ้าระวัง"] == group]
            r, p, t = calculate_correlation(df_group, group)
            if r is not None:
                results.append({
                    "หมวดหมู่": "กลุ่มโรค",
                    "กลุ่ม": group,
                    "ค่าความสัมพันธ์ (r/ρ)": r,
                    "p-value": p,
                    "ประเภทสถิติ": t,
                    "นัยสำคัญ": "✅" if p < 0.05 else "❌"
                })

    # 3. ความสัมพันธ์รายกลุ่มเปราะบาง
    if "กลุ่มเปราะบาง" in df_pat.columns:
        for group in df_pat["กลุ่มเปราะบาง"].dropna().unique():
            df_group = df_pat[df_pat["กลุ่มเปราะบาง"] == group]
            r, p, t = calculate_correlation(df_group, group)
            if r is not None:
                results.append({
                    "หมวดหมู่": "กลุ่มเปราะบาง",
                    "กลุ่ม": group,
                    "ค่าความสัมพันธ์ (r/ρ)": r,
                    "p-value": p,
                    "ประเภทสถิติ": t,
                    "นัยสำคัญ": "✅" if p < 0.05 else "❌"
                })

    if results:
        df_results = pd.DataFrame(results)
        # เรียงลำดับจากค่าความสัมพันธ์มากไปน้อย (Absolute value)
        df_results = df_results.reindex(df_results['ค่าความสัมพันธ์ (r/ρ)'].abs().sort_values(ascending=False).index)
        
        # จัดรูปแบบตัวเลขให้สวยงาม
        df_results_display = df_results.copy()
        df_results_display['ค่าความสัมพันธ์ (r/ρ)'] = df_results_display['ค่าความสัมพันธ์ (r/ρ)'].apply(lambda x: f"{x:.4f}")
        df_results_display['p-value'] = df_results_display['p-value'].apply(lambda x: f"{x:.4f}")
        
        st.dataframe(df_results_display, use_container_width=True, hide_index=True)

        # สร้างกราฟแท่งเปรียบเทียบ
        st.markdown("---")
        st.subheader("📉 กราฟเปรียบเทียบค่าความสัมพันธ์")
        
        # เพิ่มคอลัมน์สำหรับการแสดงผลในกราฟ
        df_results['สี'] = df_results.apply(lambda row: 'มีความนัยสำคัญ' if row['p-value'] < 0.05 else 'ไม่มีนัยสำคัญ', axis=1)
        
        fig_bar = px.bar(
            df_results,
            y="กลุ่ม",
            x="ค่าความสัมพันธ์ (r/ρ)",
            color="หมวดหมู่",
            orientation='h',
            text=df_results['ค่าความสัมพันธ์ (r/ρ)'].round(2),
            title="ค่าความสัมพันธ์ (ยิ่งเข้าใกล้ 1 ยิ่งสัมพันธ์กันมาก)",
            category_orders={"กลุ่ม": df_results["กลุ่ม"].tolist()} # เรียงตาม dataframe
        )
        
        # ใส่รูปแบบเส้นประให้กับแท่งที่ไม่มีนัยสำคัญ
        fig_bar.update_traces(
            textposition='outside',
            marker_line_width=1.5,
            marker_line_color='black',
        )
        for i, row in df_results.iterrows():
            if row['p-value'] >= 0.05:
                # ทำให้สีจางลงสำหรับตัวที่ไม่มีนัยสำคัญ
                fig_bar.data[0].marker.opacity = 0.5
        
        fig_bar.update_layout(
             paper_bgcolor='rgba(0,0,0,0)', 
             plot_bgcolor='rgba(0,0,0,0)',
             font=dict(family="Kanit, sans-serif"),
             xaxis_title="ค่าความสัมพันธ์ (r/ρ)",
             yaxis_title="กลุ่ม",
             margin=dict(l=0, r=20, t=40, b=0)
        )
        # เติมเส้นตรงที่ 0
        fig_bar.add_vline(x=0, line_width=2, line_dash="dash", line_color="black")
        
        st.plotly_chart(fig_bar, use_container_width=True)

    else:
        st.info("ข้อมูลไม่เพียงพอที่จะวิเคราะห์ความสัมพันธ์ภาพรวม")

    st.divider()

    # --- Part 4: Methodology Explanation ---
    with st.expander("ℹ️ หลักการทางสถิติและการคำนวณที่ใช้ในหน้านี้"):
        st.markdown("""
        หน้านี้ใช้หลักการทางสถิติเพื่อวิเคราะห์และแสดงภาพความสัมพันธ์ระหว่างค่า PM2.5 และจำนวนผู้ป่วย:

        #### สัมประสิทธิ์สหสัมพันธ์ (Correlation Coefficient)
        - **คืออะไร:** เป็นค่าที่ใช้วัดความสัมพันธ์ "เชิงเส้น" และ "แบบลำดับ" ระหว่างตัวแปร 2 ตัว มีค่าตั้งแต่ -1 ถึง +1 
        - **ทำไมถึงใช้:** เพื่อดูทั้ง "ทิศทาง" และ "ความแรง" ของความสัมพันธ์
            - **ค่าเข้าใกล้ +1:** สัมพันธ์กันในทิศทางเดียวกันอย่างมาก (PM2.5 สูง, ผู้ป่วยสูง)
            - **ค่าเข้าใกล้ -1:** สัมพันธ์กันในทิศทางตรงกันข้ามอย่างมาก (PM2.5 สูง, ผู้ป่วยต่ำ)
            - **ค่าเข้าใกล้ 0:** แทบไม่มีความสัมพันธ์ต่อกัน
        
        #### ประเภทสถิติที่แสดง
        - **Pearson (r):** วัดการเปลี่ยนแปลงที่เป็นสัดส่วนคงที่ (เส้นตรง)
        - **Spearman (ρ):** วัดทิศทางร่วมกันโดยไม่สนใจว่าต้องเป็นสัดส่วนคงที่ (ทนต่อข้อมูลที่มีค่ากระโดด)
        *ระบบจะเลือกค่าที่เหมาะสมและมีนัยสำคัญ (p < 0.05) มาแสดงให้โดยอัตโนมัติ*

        > **⚠️ ข้อควรระวังที่สำคัญ:** การวิเคราะห์ทั้งหมดนี้แสดงให้เห็นถึง **ความสัมพันธ์ (Correlation)** เท่านั้น แต่ **ไม่ได้พิสูจน์ความเป็นเหตุเป็นผล (Causation)** หมายความว่า แม้ค่า PM2.5 และจำนวนผู้ป่วยจะสูงขึ้นพร้อมกัน ก็ยังไม่สามารถสรุปได้ 100% ว่า PM2.5 เป็น "สาเหตุ" เพียงอย่างเดียวที่ทำให้เกิดผู้ป่วยเพิ่มขึ้น แต่อาจมีปัจจัยอื่นร่วมด้วย
        """)
