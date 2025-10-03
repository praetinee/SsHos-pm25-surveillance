import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils import get_aqi_details # Import from our new utils module

def display_pm25_gauge(timestamp, pm25_value):
    """Displays the real-time PM2.5 gauge."""
    if timestamp and pm25_value is not None:
        aqi_text, color, text_color = get_aqi_details(pm25_value)
        
        col1, col2, col3 = st.columns([1, 1.5, 1])

        with col2:
            st.markdown(f"""
            <div style="text-align: center; margin-top: 20px;">
                <div style="
                    margin: auto;
                    width: 280px;
                    height: 280px;
                    background-color: {color};
                    border-radius: 50%;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    color: {text_color};
                    box-shadow: 0 4px 12px 0 rgba(0, 0, 0, 0.18);
                    border: 6px solid rgba(255, 255, 255, 0.5);
                    ">
                    <div style="font-size: 1em; font-weight: bold;">ระดับ PM2.5</div>
                    <div style="font-size: 7em; font-weight: 900; line-height: 1.1;">{pm25_value:.0f}</div>
                    <div style="font-size: 1em;">μg/m³</div>
                    <div style="font-size: 0.8em; margin-top: 5px;">{timestamp.strftime('%d %b %Y %H:%M')}</div>
                </div>
                <h2 style="color:{color}; margin-top: 15px; font-weight: bold;">{aqi_text}</h2>
                <p style="font-size: 0.9em; color: #888;">โรงพยาบาลสันทราย</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("ไม่สามารถแสดงข้อมูล PM2.5 Real-time ได้ในขณะนี้")

def display_historical_chart(df, selected_groups):
    """Displays the dual-axis chart for historical data."""
    if df.empty or not selected_groups:
        st.warning("ไม่มีข้อมูลให้แสดงผล กรุณาตรวจสอบตัวกรอง")
        return

    # Aggregate data by month for plotting
    df['Month'] = df['Date'].dt.to_period('M').astype(str)
    monthly_agg = df.groupby('Month').agg({
        'PM2.5': 'mean',
        **{group: 'sum' for group in selected_groups}
    }).reset_index()

    monthly_agg['Total Patients'] = monthly_agg[selected_groups].sum(axis=1)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(x=monthly_agg['Month'], y=monthly_agg['Total Patients'], name="จำนวนผู้ป่วยรวม", marker_color='cornflowerblue'),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(x=monthly_agg['Month'], y=monthly_agg['PM2.5'], name="ค่าเฉลี่ย PM2.5", mode='lines+markers', line=dict(color='firebrick', width=3)),
        secondary_y=True,
    )

    fig.update_layout(
        title_text="กราฟแสดงจำนวนผู้ป่วยรวมเทียบกับค่า PM2.5 เฉลี่ยรายเดือน",
        xaxis_title="เดือน-ปี",
        legend=dict(x=0, y=1.1, traceorder="normal", orientation="h")
    )
    fig.update_yaxes(title_text="<b>จำนวนผู้ป่วย (คน)</b>", secondary_y=False)
    fig.update_yaxes(title_text="<b>ค่า PM2.5 เฉลี่ย (μg/m³)</b>", secondary_y=True)

    st.plotly_chart(fig, use_container_width=True)

    with st.expander("แสดงข้อมูลตารางแบบสรุปรายเดือน"):
        st.dataframe(monthly_agg)
