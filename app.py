import streamlit as st
import pandas as pd

# นำเข้าฟังก์ชันจากไฟล์โมดูลที่เราแยกไว้
from data_processor import load_and_prep_data
from ui_components import create_sidebar_filters, plot_trend_dual_axis, plot_demographics, plot_geographic

def main():
    # 1. ตั้งค่าหน้าเพจ (ต้องอยู่บรรทัดแรก)
    st.set_page_config(page_title="PM2.5 Health Surveillance", page_icon="🌬️", layout="wide")
    
    # --- Custom CSS เพื่อให้ UI ดูทันสมัยและฉลาดขึ้น ---
    st.markdown("""
        <style>
        /* ตกแต่งกล่อง Metric ให้เป็น Card ดูมีมิติ */
        div[data-testid="metric-container"] {
            background-color: #ffffff;
            border: 1px solid #f0f2f6;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        }
        /* เปลี่ยนสีหัวข้อของ Metric */
        div[data-testid="metric-container"] > div > div > div > div > p {
            font-size: 1rem;
            color: #64748b;
            font-weight: 500;
        }
        /* เปลี่ยนสีตัวเลขของ Metric */
        div[data-testid="metric-container"] > div > div > div > div:nth-child(2) > p {
            font-size: 2rem;
            color: #0f172a;
            font-weight: 700;
        }
        </style>
    """, unsafe_allow_html=True)

    # 2. ส่วนหัวของ Dashboard
    st.title("🌬️ ระบบเฝ้าระวังผลกระทบทางสุขภาพจาก PM2.5")
    st.markdown("<p style='font-size: 1.1rem; color: #64748b;'>วิเคราะห์ความสัมพันธ์ระหว่างคุณภาพอากาศ และการเข้ารับบริการที่โรงพยาบาลแบบเรียลไทม์</p>", unsafe_allow_html=True)
    st.markdown("---")

    # 3. โหลดข้อมูล
    with st.spinner('กำลังประมวลผลข้อมูลสาธารณสุข...'):
        df_patients, df_pm25 = load_and_prep_data()

    if df_patients.empty:
        st.warning("⚠️ ไม่สามารถดำเนินการต่อได้ กรุณาอัปโหลดหรือตรวจสอบไฟล์ข้อมูลต้นทาง")
        st.stop()

    # 4. สร้าง Sidebar และรับค่าตัวกรอง
    selected_year, selected_disease, walk_in_filter = create_sidebar_filters(df_patients)

    # --- 5. การประยุกต์ใช้ตัวกรองข้อมูล ---
    df_filtered = df_patients.copy()
    
    if selected_year:
        df_filtered = df_filtered[df_filtered['Date'].dt.year.isin(selected_year)]
    
    if selected_disease:
        df_filtered = df_filtered[df_filtered['4 กลุ่มโรคเฝ้าระวัง'].isin(selected_disease)]

    if walk_in_filter == "เฉพาะ Walk-in (ไม่ได้นัด)":
        df_filtered = df_filtered[df_filtered['Is_Walk_in'] == 'Walk-in (ไม่ได้นัด)']
    elif walk_in_filter == "เฉพาะมาตามนัด":
        df_filtered = df_filtered[df_filtered['Is_Walk_in'] == 'Appointment (นัดมา)']

    # --- 6. การแสดงผล KPI Cards ข้อมูลสรุป ---
    total_cases = len(df_filtered)
    walk_in_count = len(df_filtered[df_filtered['Is_Walk_in'] == 'Walk-in (ไม่ได้นัด)'])
    walk_in_percent = (walk_in_count / total_cases * 100) if total_cases > 0 else 0
    
    max_pm = "-"
    if not df_pm25.empty and selected_year:
        max_pm_val = df_pm25[df_pm25['Month_Year'].dt.year.isin(selected_year)]['PM25'].max()
        max_pm = f"{max_pm_val:.1f}"

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    with kpi1:
        st.metric(label="👥 จำนวนผู้ป่วยสะสม (เคส)", value=f"{total_cases:,}")
    
    with kpi2:
        st.metric(label="🚨 ผู้ป่วยฉุกเฉิน (Walk-in)", value=f"{walk_in_count:,}")
        
    with kpi3:
        st.metric(label="📊 สัดส่วน Walk-in (%)", value=f"{walk_in_percent:.1f}%")
        
    with kpi4:
        st.metric(label="🌫️ ค่า PM2.5 สูงสุด (µg/m³)", value=max_pm)

    st.markdown("<br>", unsafe_allow_html=True) # เว้นบรรทัด

    # --- 6.5 Smart Statistical Insight (เพิ่มใหม่) ---
    if not df_filtered.empty and not df_pm25.empty:
        # เตรียมข้อมูลสำหรับหาความสัมพันธ์ (Correlation)
        monthly_cases = df_filtered.groupby('Month_Year').size().reset_index(name='Patient_Count')
        merged_stats = pd.merge(monthly_cases, df_pm25, on='Month_Year', how='inner')
        
        if len(merged_stats) > 1:
            corr = merged_stats['Patient_Count'].corr(merged_stats['PM25'])
            
            if not pd.isna(corr):
                # กำหนดข้อความ สี และไอคอน ตามระดับความสัมพันธ์ทางสถิติ
                if corr >= 0.7:
                    level, color, icon = "ระดับสูงมาก", "#ef4444", "🚨" # สีแดง
                    desc = "ผู้ป่วยมีแนวโน้มเพิ่มขึ้นตามปริมาณฝุ่นอย่างชัดเจน ควรเฝ้าระวังและเตรียมทรัพยากรรับมือ"
                elif corr >= 0.5:
                    level, color, icon = "ระดับปานกลาง", "#f97316", "⚠️" # สีส้ม
                    desc = "ปริมาณฝุ่นมีผลต่อจำนวนผู้ป่วยในระดับที่สังเกตได้"
                elif corr >= 0.3:
                    level, color, icon = "ระดับต่ำ", "#eab308", "📊" # สีเหลือง
                    desc = "ฝุ่นอาจมีผลต่อจำนวนผู้ป่วยเพียงเล็กน้อย หรือมีปัจจัยฤดูกาลอื่นร่วมด้วย"
                elif corr > -0.3:
                    level, color, icon = "ไม่ชัดเจน", "#64748b", "❔" # สีเทา
                    desc = "ไม่พบความสัมพันธ์ทางสถิติที่ชัดเจนระหว่างฝุ่นและจำนวนผู้ป่วยในช่วงเวลา/เงื่อนไขนี้"
                else:
                    level, color, icon = "เชิงลบ", "#3b82f6", "📉" # สีฟ้า
                    desc = "ข้อมูลมีความสัมพันธ์แบบผกผัน ซึ่งอาจเกิดจากปัจจัยการลงข้อมูลหรือปัจจัยแทรกซ้อนอื่น"

                # แสดงกล่องข้อความแบบสวยงามทันสมัย
                st.markdown(f"""
                <div style="background: linear-gradient(to right, #ffffff, #f8fafc); border: 1px solid #e2e8f0; border-left: 5px solid {color}; padding: 18px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); margin-bottom: 25px;">
                    <div style="display: flex; align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 1.4rem; margin-right: 10px;">{icon}</span>
                        <h4 style="margin:0; color: #1e293b; font-weight: 600;">Smart Insight: วิเคราะห์ความสัมพันธ์ทางสถิติ</h4>
                    </div>
                    <p style="margin: 0 0 0 38px; font-size: 1.05rem; color: #475569;">
                        จากเงื่อนไขที่กรอง พบความสัมพันธ์เชิงสถิติ (Correlation) <b>{level} (r = {corr:.2f})</b> <br>
                        <span style="color: {color}; font-weight: 500;">💡 สรุปผล:</span> {desc}
                    </p>
                </div>
                """, unsafe_allow_html=True)

    # --- 7. แสดงผลกราฟหลัก (Trend) ---
    st.markdown("### 📈 แนวโน้มการรับบริการเทียบกับระดับ PM2.5")
    plot_trend_dual_axis(df_filtered, df_pm25)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 8. แสดงผลกราฟรอง แบ่ง 2 คอลัมน์ให้ดูสวยงาม ---
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🩺 สัดส่วนกลุ่มโรคที่ได้รับผลกระทบ")
        plot_demographics(df_filtered)
        
    with col2:
        st.markdown("### 📍 10 อันดับพื้นที่เฝ้าระวัง (ระดับตำบล)")
        plot_geographic(df_filtered)

# จุดเริ่มต้นการทำงานของสคริปต์
if __name__ == "__main__":
    main()
