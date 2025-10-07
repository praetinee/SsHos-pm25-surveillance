import streamlit as st
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import numpy as np

# ----------------------------
# Plot 1: Original Trend Chart (Updated)
# ----------------------------
def plot_patient_vs_pm25(df_pat, df_pm):
    # This function is now deprecated and will call the new function for consistency.
    # We keep it for backward compatibility in case other parts of the app call it.
    plot_main_dashboard_chart(df_pat, df_pm)

def plot_main_dashboard_chart(df_pat, df_pm):
    """
    Generates the main dashboard chart showing patient trends vs. PM2.5 levels.
    - Swapped axes to ensure patient lines (secondary_y) are drawn on top of the PM2.5 area (primary_y).
    """
    # st.header("แนวโน้มผู้ป่วยเทียบกับค่า PM2.5") # REMOVED: This header was redundant
    
    patient_counts = df_pat.groupby(["เดือน", "4 กลุ่มโรคเฝ้าระวัง"]).size().reset_index(name="count")
    df_merged = pd.merge(patient_counts, df_pm, on="เดือน", how="outer").sort_values("เดือน")
    all_months = sorted(df_merged["เดือน"].dropna().unique())

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # 1. Add PM2.5 Area chart on the PRIMARY Y-AXIS (so it's in the background)
    fig.add_trace(
        go.Scatter(
            x=all_months,
            y=df_pm.set_index('เดือน').reindex(all_months)['PM2.5 (ug/m3)'],
            name="PM2.5 (ug/m3)",
            fill='tozeroy',
            mode='lines',
            line=dict(color='lightgrey')
        ), 
        secondary_y=False # On Primary Axis
    )

    # 2. Add Patient group lines on the SECONDARY Y-AXIS (so they are on top)
    colors = px.colors.qualitative.Plotly
    patient_groups = sorted(df_pat["4 กลุ่มโรคเฝ้าระวัง"].dropna().unique())

    for i, grp in enumerate(patient_groups):
        d2 = df_merged[df_merged["4 กลุ่มโรคเฝ้าระวัง"] == grp]
        fig.add_trace(
            go.Scatter(
                x=d2["เดือน"], 
                y=d2["count"], 
                name=f"{grp}", 
                mode="lines+markers", 
                line=dict(width=2.5, color=colors[i % len(colors)])
            ),
            secondary_y=True # On Secondary Axis
        )
        
    # 3. Add Threshold lines for PM2.5 on the PRIMARY axis
    fig.add_hline(
        y=37.5, 
        line_dash="dash", 
        line_color="orange", 
        secondary_y=False # Refers to Primary Axis
    )
    fig.add_hline(
        y=75, 
        line_dash="dash", 
        line_color="red", 
        secondary_y=False # Refers to Primary Axis
    )

    # 4. Update layout: Swap axis titles and update annotation references
    fig.update_layout(
        legend_title_text="ข้อมูล",
        yaxis_title="PM2.5 (ug/m3)", # Primary axis title
        yaxis2_title="จำนวนผู้ป่วย (คน)", # Secondary axis title
        hovermode="x unified",
        margin=dict(t=30, l=0, r=0, b=0),
        annotations=[
            dict(
                x=all_months[-1] if all_months else 0,
                y=37.5,
                xref="x",
                yref="y", # yref refers to the primary y-axis
                text="อากาศที่ต้องระวัง (37.5)",
                showarrow=False,
                xanchor='right',
                yanchor='bottom',
                font=dict(color="orange")
            ),
            dict(
                x=all_months[-1] if all_months else 0,
                y=75,
                xref="x",
                yref="y", # yref refers to the primary y-axis
                text="อากาศแย่ (75)",
                showarrow=False,
                xanchor='right',
                yanchor='bottom',
                font=dict(color="red")
            )
        ]
    )
    
    # Set range for PRIMARY y-axis (PM2.5)
    fig.update_yaxes(range=[0, df_pm["PM2.5 (ug/m3)"].max() * 1.2 if not df_pm.empty else 100], secondary_y=False)
    st.plotly_chart(fig, use_container_width=True)


# -------------------------------------
# Plot 2: Year-over-Year Comparison
# -------------------------------------
def plot_yearly_comparison(df_pat, df_pm):
    df_merged = pd.merge(
        df_pat.groupby('เดือน').size().reset_index(name='count'), 
        df_pm, on='เดือน', how='inner'
    )
    df_merged['Year'] = pd.to_datetime(df_merged['เดือน']).dt.year
    df_merged['Month'] = pd.to_datetime(df_merged['เดือน']).dt.month

    fig = go.Figure()
    
    years = df_merged['Year'].unique()
    for year in years:
        df_year = df_merged[df_merged['Year'] == year]
        fig.add_trace(go.Scatter(
            x=df_year['Month'], 
            y=df_year['count'], 
            name=f'ผู้ป่วย ปี {year}',
            mode='lines+markers'
        ))

    fig.update_layout(
        title_text="กราฟเปรียบเทียบจำนวนผู้ป่วยรวมในแต่ละปี",
        xaxis_title="เดือน",
        yaxis_title="จำนวนผู้ป่วยรวม (คน)",
        xaxis=dict(tickmode='array', tickvals=list(range(1, 13)), ticktext=['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']),
        legend_title_text="ปี"
    )
    st.plotly_chart(fig, use_container_width=True)

# -------------------------------------
# Plot 3: Calendar Heatmap
# -------------------------------------
def plot_calendar_heatmap(df_pat, df_pm):
    df_merged = pd.merge(
        df_pat.groupby('เดือน').size().reset_index(name='count'), 
        df_pm, on='เดือน', how='inner'
    )
    df_merged['Year'] = pd.to_datetime(df_merged['เดือน']).dt.year
    df_merged['Month'] = pd.to_datetime(df_merged['เดือน']).dt.month
    
    # Pivot data for heatmap
    years = sorted(df_merged['Year'].unique(), reverse=True)
    months = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']
    
    z_data = [] # PM2.5 for color
    text_data = [] # Patient count for text

    for year in years:
        row_z = []
        row_text = []
        for month_num in range(1, 13):
            cell = df_merged[(df_merged['Year'] == year) & (df_merged['Month'] == month_num)]
            if not cell.empty:
                row_z.append(cell['PM2.5 (ug/m3)'].iloc[0])
                row_text.append(f"{int(cell['count'].iloc[0])}")
            else:
                row_z.append(np.nan)
                row_text.append("")
        z_data.append(row_z)
        text_data.append(row_text)

    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        x=months,
        y=[str(y) for y in years],
        text=text_data,
        texttemplate="%{text}",
        textfont={"size":12},
        colorscale='OrRd',
        hovertemplate='<b>ปี %{y}, เดือน %{x}</b><br>PM2.5: %{z:.2f}<br>ผู้ป่วย: %{text} คน<extra></extra>'
    ))

    fig.update_layout(
        title='ปฏิทินแสดงค่า PM2.5 (สี) และจำนวนผู้ป่วย (ตัวเลข)'
    )
    st.plotly_chart(fig, use_container_width=True)


# -------------------------------------
# Plot 4: Correlation Scatter Plot (REBUILT WITH ENHANCED INTERPRETATION)
# -------------------------------------
def plot_correlation_scatter(df_pat, df_pm):
    """
    Overhauled function to provide deeper correlation insights with enhanced, dynamic interpretation.
    """
    
    # --- Part 1: Overall Correlation ---
    st.subheader("1. ความสัมพันธ์ภาพรวม: ผู้ป่วยทั้งหมด vs PM2.5")
    
    df_merged_all = pd.merge(
        df_pat.groupby('เดือน').size().reset_index(name='จำนวนผู้ป่วย'), 
        df_pm, on='เดือน', how='inner'
    )
    
    if not df_merged_all.empty and df_merged_all.shape[0] > 1:
        fig = px.scatter(
            df_merged_all,
            x="PM2.5 (ug/m3)",
            y="จำนวนผู้ป่วย",
            trendline="ols",
            trendline_color_override="red",
            title="ความสัมพันธ์ระหว่าง PM2.5 และ จำนวนผู้ป่วยทั้งหมด",
            labels={"PM2.5 (ug/m3)": "ค่า PM2.5 (µg/m³)", "จำนวนผู้ป่วย": "จำนวนผู้ป่วยรวม (คน)"},
            hover_data=['เดือน']
        )
        st.plotly_chart(fig, use_container_width=True)
        
        try:
            results = px.get_trendline_results(fig)
            model = results.iloc[0]["px_fit_results"]
            r_squared = model.rsquared
            slope = model.params[1]

            st.metric("R-squared", f"{r_squared:.4f}")
            
            interpretation = f"""
            **คำอธิบาย:**
            สมมติว่ามีปัจจัย 100 อย่างที่ทำให้จำนวนผู้ป่วยทั้งหมดในแต่ละเดือน **'มากขึ้น'** หรือ **'น้อยลง'** (ความผันผวน),
            ค่า R-squared ที่ **{r_squared:.2f}** กำลังบอกเราว่า **การเปลี่ยนแปลงของค่า PM2.5** เป็นปัจจัยที่เกี่ยวข้องกับการเพิ่มขึ้น/ลดลงของผู้ป่วยอยู่ประมาณ **{r_squared*100:.1f} ส่วน จากทั้งหมด 100 ส่วน**
            
            ส่วนที่เหลืออีก **{100 - (r_squared*100):.1f}%** คืออิทธิพลจากปัจจัยอื่นๆ เช่น สภาพอากาศ, การระบาดของโรคตามฤดูกาล, หรือพฤติกรรมของประชาชน
            """
            if slope > 0:
                interpretation += "\n\n**แนวโน้ม:** เส้นกราฟที่ชันขึ้น บ่งชี้ถึง **ความสัมพันธ์เชิงบวก** หมายความว่า เมื่อค่า PM2.5 สูงขึ้น จำนวนผู้ป่วยก็มีแนวโน้มสูงขึ้นตามไปด้วย"
            else:
                interpretation += "\n\n**แนวโน้ม:** เส้นกราฟที่ลาดลง บ่งชี้ถึง **ความสัมพันธ์เชิงลบ** หมายความว่า เมื่อค่า PM2.5 สูงขึ้น จำนวนผู้ป่วยกลับมีแนวโน้มลดลง"
            st.info(interpretation)

        except (KeyError, IndexError):
            st.warning("ไม่สามารถคำนวณและแปลผลค่าทางสถิติได้")
    else:
        st.info("ข้อมูลไม่เพียงพอที่จะวิเคราะห์ความสัมพันธ์ภาพรวม")

    st.divider()

    # --- Part 2: Correlation by Disease Group ---
    st.subheader("2. เจาะลึกรายกลุ่มโรค")
    
    if "4 กลุ่มโรคเฝ้าระวัง" in df_pat.columns:
        all_groups = sorted(df_pat["4 กลุ่มโรคเฝ้าระวัง"].dropna().unique())
        selected_group = st.selectbox("เลือกกลุ่มโรคเพื่อดูความสัมพันธ์", all_groups)
        
        if selected_group:
            df_pat_group = df_pat[df_pat["4 กลุ่มโรคเฝ้าระวัง"] == selected_group]
            df_merged_group = pd.merge(
                df_pat_group.groupby('เดือน').size().reset_index(name=f'จำนวนผู้ป่วย ({selected_group})'), 
                df_pm, on='เดือน', how='inner'
            )
            
            if not df_merged_group.empty and df_merged_group.shape[0] > 1:
                fig_group = px.scatter(
                    df_merged_group,
                    x="PM2.5 (ug/m3)",
                    y=f'จำนวนผู้ป่วย ({selected_group})',
                    trendline="ols",
                    trendline_color_override="darkblue",
                    title=f"ความสัมพันธ์สำหรับกลุ่ม: {selected_group}",
                    labels={"PM2.5 (ug/m3)": "ค่า PM2.5 (µg/m³)"}
                )
                st.plotly_chart(fig_group, use_container_width=True)
                
                try:
                    results_group = px.get_trendline_results(fig_group)
                    model_group = results_group.iloc[0]["px_fit_results"]
                    r_squared_group = model_group.rsquared
                    
                    st.metric(f"R-squared (กลุ่ม {selected_group})", f"{r_squared_group:.4f}")
                    
                    interpretation_group = f"""
                    **คำอธิบายสำหรับกลุ่ม '{selected_group}':**

                    ค่า R-squared ที่ **{r_squared_group:.2f}** บ่งชี้ว่า จากปัจจัยทั้งหมดที่ส่งผลต่อจำนวนผู้ป่วยในกลุ่มนี้, การเปลี่ยนแปลงของค่า PM2.5 มีความเกี่ยวข้องอยู่ประมาณ **{r_squared_group*100:.1f}%**

                    - **ถ้าค่านี้สูง (เข้าใกล้ 100%):** หมายความว่าฝุ่น PM2.5 เป็นปัจจัยที่มีความสัมพันธ์กับผู้ป่วยกลุ่มนี้ค่อนข้างมาก
                    - **ถ้าค่านี้ต่ำ (เข้าใกล้ 0%):** หมายความว่าอาจมีปัจจัยอื่นที่สำคัญกว่า (เช่น เชื้อโรค, ฤดูกาล) ที่ส่งผลต่อผู้ป่วยกลุ่มนี้
                    """
                    st.info(interpretation_group)

                except (KeyError, IndexError):
                    st.warning("ไม่สามารถคำนวณค่า R-squared สำหรับกลุ่มนี้ได้")
            else:
                st.info(f"ข้อมูลไม่เพียงพอที่จะวิเคราะห์ความสัมพันธ์สำหรับกลุ่ม '{selected_group}'")
    else:
        st.warning("ไม่พบคอลัมน์ '4 กลุ่มโรคเฝ้าระวัง' สำหรับการวิเคราะห์รายกลุ่มโรค")

    st.divider()

    # --- Part 3: Lag Analysis (Simple) ---
    st.subheader("3. การวิเคราะห์ผลกระทบย้อนหลัง (Lag Analysis)")

    try:
        patient_monthly = df_pat.groupby('เดือน').size().reset_index(name='จำนวนผู้ป่วย')
        patient_monthly['เดือน'] = pd.to_datetime(patient_monthly['เดือน'])

        pm_monthly = df_pm[['เดือน', 'PM2.5 (ug/m3)']].copy()
        pm_monthly['เดือน'] = pd.to_datetime(pm_monthly['เดือน'])

        pm_monthly_lagged = pm_monthly.copy()
        pm_monthly_lagged.rename(columns={'PM2.5 (ug/m3)': 'PM2.5 (เดือนก่อนหน้า)'}, inplace=True)
        pm_monthly_lagged['เดือน'] = pm_monthly_lagged['เดือน'] + pd.DateOffset(months=1)

        df_merged_lag = pd.merge(patient_monthly, pm_monthly, on='เดือน', how='inner')
        df_merged_lag = pd.merge(df_merged_lag, pm_monthly_lagged, on='เดือน', how='inner')

        if not df_merged_lag.empty:
            corr_same_month = df_merged_lag['จำนวนผู้ป่วย'].corr(df_merged_lag['PM2.5 (ug/m3)'])
            corr_lagged = df_merged_lag['จำนวนผู้ป่วย'].corr(df_merged_lag['PM2.5 (เดือนก่อนหน้า)'])
            
            col1, col2 = st.columns(2)
            col1.metric("ความสัมพันธ์ ณ เดือนเดียวกัน", f"{corr_same_month:.4f}" if pd.notna(corr_same_month) else "N/A")
            col2.metric("ความสัมพันธ์แบบล่าช้า 1 เดือน", f"{corr_lagged:.4f}" if pd.notna(corr_lagged) else "N/A")
            
            interpretation_lag = ""
            if pd.notna(corr_same_month) and pd.notna(corr_lagged):
                if abs(corr_lagged) > abs(corr_same_month):
                    interpretation_lag = """
                    💡 **ข้อสังเกต:** ค่าความสัมพันธ์แบบ **'ล่าช้า 1 เดือน'** มีค่า **สูงกว่า**

                    **นี่อาจหมายความว่า:** ผลกระทบจากฝุ่นอาจไม่ได้เกิดขึ้นทันที แต่อาจใช้เวลาสะสมในร่างกายประมาณ 1 เดือน ก่อนที่จะแสดงอาการป่วยออกมาอย่างชัดเจน
                    """
                else:
                    interpretation_lag = """
                    💡 **ข้อสังเกต:** ค่าความสัมพันธ์ ณ **'เดือนเดียวกัน'** มีค่า **สูงกว่า**

                    **นี่อาจหมายความว่า:** ผลกระทบจากฝุ่นต่อสุขภาพมีแนวโน้มที่จะเกิดขึ้นค่อนข้างเร็ว ผู้คนอาจเริ่มแสดงอาการป่วยภายในเดือนเดียวกันกับที่ได้รับฝุ่นในปริมาณสูง
                    """
            if interpretation_lag:
                st.info(interpretation_lag)

        else:
            st.info("ข้อมูลไม่เพียงพอสำหรับ Lag Analysis")

    except Exception:
        st.error("เกิดข้อผิดพลาดในการทำ Lag Analysis")

    st.divider()

    # --- Part 4: Methodology Explanation ---
    with st.expander("ℹ️ หลักการทางสถิติและการคำนวณที่ใช้ในหน้านี้"):
        st.markdown("""
        หน้านี้ใช้หลักการทางสถิติหลายอย่างเพื่อวิเคราะห์และแสดงภาพความสัมพันธ์ระหว่างค่า PM2.5 และจำนวนผู้ป่วย:

        #### 1. กราฟการกระจาย (Scatter Plot)
        - **คืออะไร:** เป็นกราฟที่ใช้แสดงข้อมูลของตัวแปร 2 ตัว โดยแต่ละจุดบนกราฟแทนข้อมูล 1 คู่ (ในที่นี้คือ PM2.5 และจำนวนผู้ป่วยในแต่ละเดือน)
        - **ทำไมถึงใช้:** เหมาะสำหรับการดูกระจายตัวและแนวโน้มความสัมพันธ์ของข้อมูลด้วยสายตา ว่ามีความสัมพันธ์กันในทิศทางใดหรือไม่

        #### 2. การวิเคราะห์การถดถอยเชิงเส้น (Linear Regression - OLS)
        - **คืออะไร:** เป็นเทคนิคทางสถิติที่ใช้วาด "เส้นแนวโน้ม" (Trendline) ที่ลากผ่านกลางกลุ่มข้อมูลในกราฟ Scatter Plot ให้เหมาะสมที่สุด
        - **ทำไมถึงใช้:** เพื่อสรุปแนวโน้มของข้อมูลทั้งหมดให้อยู่ในรูปของเส้นตรง ทำให้ง่ายต่อการตีความว่าความสัมพันธ์โดยรวมเป็นไปในทิศทางใด (ชันขึ้น = สัมพันธ์เชิงบวก, ลาดลง = สัมพันธ์เชิงลบ)

        #### 3. R-squared (สัมประสิทธิ์การตัดสินใจ)
        - **คืออะไร:** เป็นค่าที่วัดว่าแบบจำลองเส้นตรง (เส้นแนวโน้ม) ของเรา สามารถอธิบายความผันผวนของข้อมูลได้ดีแค่ไหน มีค่าระหว่าง 0 ถึง 1
        - **ทำไมถึงใช้:** เพื่อวัด "ความน่าเชื่อถือ" ของความสัมพันธ์ **ค่า R-squared ที่สูง (เข้าใกล้ 1)** หมายความว่าค่า PM2.5 สามารถอธิบายการเปลี่ยนแปลงของจำนวนผู้ป่วยได้ดี ในทางกลับกัน **ค่าที่ต่ำ (เข้าใกล้ 0)** หมายความว่าอาจมีปัจจัยอื่นๆ อีกมากที่ส่งผลต่อจำนวนผู้ป่วย ไม่ใช่แค่ PM2.5 เพียงอย่างเดียว

        #### 4. สัมประสิทธิ์สหสัมพันธ์ (Correlation Coefficient)
        - **คืออะไร:** เป็นค่าที่ใช้วัดความสัมพันธ์ "เชิงเส้น" ระหว่างตัวแปร 2 ตัว มีค่าตั้งแต่ -1 ถึง +1 (ใช้ใน Lag Analysis)
        - **ทำไมถึงใช้:** เพื่อดูทั้ง "ทิศทาง" และ "ความแรง" ของความสัมพันธ์
            - **ค่าเข้าใกล้ +1:** สัมพันธ์กันในทิศทางเดียวกันอย่างมาก (PM2.5 สูง, ผู้ป่วยสูง)
            - **ค่าเข้าใกล้ -1:** สัมพันธ์กันในทิศทางตรงกันข้ามอย่างมาก (PM2.5 สูง, ผู้ป่วยต่ำ)
            - **ค่าเข้าใกล้ 0:** แทบไม่มีความสัมพันธ์เชิงเส้นต่อกัน

        > **⚠️ ข้อควรระวังที่สำคัญ:** การวิเคราะห์ทั้งหมดนี้แสดงให้เห็นถึง **ความสัมพันธ์ (Correlation)** เท่านั้น แต่ **ไม่ได้พิสูจน์ความเป็นเหตุเป็นผล (Causation)** หมายความว่า แม้ค่า PM2.5 และจำนวนผู้ป่วยจะสูงขึ้นพร้อมกัน ก็ยังไม่สามารถสรุปได้ 100% ว่า PM2.5 เป็น "สาเหตุ" เพียงอย่างเดียวที่ทำให้เกิดผู้ป่วยเพิ่มขึ้น แต่อาจมีปัจจัยอื่นร่วมด้วย การวิเคราะห์นี้เป็นเพียงเครื่องมือชี้เป้าเพื่อการเฝ้าระวังและศึกษาเพิ่มเติมต่อไป
        """)

# ----------------------------
# NEW: Vulnerable Groups Dashboard
# ----------------------------
def plot_vulnerable_dashboard(df_pat, df_pm, dff_filtered):
    """
    Creates a comprehensive dashboard for vulnerable groups analysis.
    """
    if "กลุ่มเปราะบาง" not in df_pat.columns or "4 กลุ่มโรคเฝ้าระวัง" not in df_pat.columns:
        st.info("ℹ️ ไม่สามารถวิเคราะห์ได้ เนื่องจากขาดคอลัมน์ 'กลุ่มเปราะบาง' หรือ '4 กลุ่มโรคเฝ้าระวัง'")
        return

    df_vul = df_pat.dropna(subset=['กลุ่มเปราะบาง'])
    
    # --- 1. Pie Chart (based on current filters) ---
    st.subheader("1. สัดส่วนกลุ่มเปราะบาง (ตามตัวกรองปัจจุบัน)")
    if not dff_filtered.empty:
        df_vul_filtered = dff_filtered.dropna(subset=['กลุ่มเปราะบาง'])
        if not df_vul_filtered.empty:
            sp = df_vul_filtered["กลุ่มเปราะบาง"].value_counts().reset_index()
            sp.columns = ["กลุ่ม", "จำนวน"]
            pie = px.pie(sp, values="จำนวน", names="กลุ่ม", title="สัดส่วนกลุ่มเปราะบางที่เลือก")
            st.plotly_chart(pie, use_container_width=True)
        else:
            st.info("ℹ️ ไม่มีข้อมูลกลุ่มเปราะบางในข้อมูลที่กรอง")
    else:
        st.info("ℹ️ ไม่มีข้อมูลกลุ่มเปราะบางสำหรับเดือนที่เลือก")

    st.divider()

    # --- 2. Vulnerable Groups vs PM2.5 (all data) ---
    st.subheader("2. เปรียบเทียบแนวโน้มผู้ป่วยกลุ่มเปราะบางกับค่า PM2.5 (ข้อมูลทั้งหมด)")
    trend_data = df_vul.groupby(['เดือน', 'กลุ่มเปราะบาง']).size().reset_index(name='จำนวน')
    trend_data_vs_pm = pd.merge(trend_data, df_pm, on="เดือน", how="left")
    all_months = sorted(trend_data_vs_pm["เดือน"].dropna().unique())
    
    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Add PM2.5 trace
    fig2.add_trace(
        go.Scatter(
            x=all_months,
            y=df_pm.set_index('เดือน').reindex(all_months)['PM2.5 (ug/m3)'],
            name="PM2.5 (ug/m3)",
            fill='tozeroy',
            mode='lines',
            line=dict(color='lightgrey')
        ), 
        secondary_y=False
    )
    
    # Add vulnerable group traces
    colors = px.colors.qualitative.Plotly
    vulnerable_groups = sorted(df_vul["กลุ่มเปราะบาง"].dropna().unique())
    for i, grp in enumerate(vulnerable_groups):
        d2 = trend_data_vs_pm[trend_data_vs_pm["กลุ่มเปราะบาง"] == grp]
        fig2.add_trace(
            go.Scatter(
                x=d2["เดือน"], 
                y=d2["จำนวน"], 
                name=f"{grp}", 
                mode="lines+markers",
                line=dict(color=colors[i % len(colors)])
            ),
            secondary_y=True
        )
    
    fig2.update_layout(
        legend_title_text="ข้อมูล",
        yaxis_title="PM2.5 (ug/m3)",
        yaxis2_title="จำนวนผู้ป่วย (คน)",
        hovermode="x unified",
        title_text="แนวโน้มผู้ป่วยกลุ่มเปราะบางเทียบกับ PM2.5"
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # --- 3. Disease Breakdown by Vulnerable Group (all data) ---
    st.subheader("3. กลุ่มโรคที่พบในแต่ละกลุ่มเปราะบาง (ข้อมูลทั้งหมด)")
    breakdown_data = df_vul.groupby(['กลุ่มเปราะบาง', '4 กลุ่มโรคเฝ้าระวัง']).size().reset_index(name='จำนวน')
    if not breakdown_data.empty:
        fig3 = px.bar(
            breakdown_data, 
            x='กลุ่มเปราะบาง', 
            y='จำนวน', 
            color='4 กลุ่มโรคเฝ้าระวัง', 
            barmode='group', 
            title="จำแนกกลุ่มโรคที่พบในแต่ละกลุ่มเปราะบาง",
            labels={'จำนวน': 'จำนวนผู้ป่วย (คน)', 'กลุ่มเปราะบาง': 'กลุ่มเปราะบาง', '4 กลุ่มโรคเฝ้าระวัง': 'กลุ่มโรคเฝ้าระวัง'}
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("ℹ️ ไม่มีข้อมูลเพียงพอสำหรับจำแนกกลุ่มโรค")

