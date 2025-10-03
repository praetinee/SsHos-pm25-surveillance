import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from utils import get_aqi_details

def display_pm25_gauge(timestamp, pm25_value):
    """Displays the real-time PM2.5 gauge."""
    if timestamp and pm25_value is not None:
        aqi_text, color, text_color = get_aqi_details(pm25_value)
        
        st.markdown(f"""
        <div style="text-align: center; margin-top: -30px;">
            <div style="
                margin: auto;
                width: 200px;
                height: 200px;
                background-color: {color};
                border-radius: 50%;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                color: {text_color};
                box-shadow: 0 4px 12px 0 rgba(0, 0, 0, 0.15);
                border: 4px solid rgba(255, 255, 255, 0.4);
                ">
                <div style="font-size: 0.8em; font-weight: bold;">PM2.5</div>
                <div style="font-size: 5em; font-weight: 900; line-height: 1.1;">{pm25_value:.0f}</div>
                <div style="font-size: 0.9em;">μg/m³</div>
            </div>
            <div style="font-size: 0.8em; color: #888; margin-top: 5px;">{timestamp.strftime('%d %b %Y, %H:%M')} | รพ.สันทราย</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("ไม่สามารถโหลดข้อมูล PM2.5 ได้")

def display_historical_chart(df):
    """Displays the dual-axis chart for patients and PM2.5."""
    if df.empty:
        st.warning("ไม่มีข้อมูลตามตัวกรองที่เลือก")
        return

    # Aggregate data by month
    monthly_df = df.set_index('visit_date').resample('M').agg(
        patient_count=('disease_group', 'count'),
        avg_pm25=('pm25_value', 'mean')
    ).reset_index()
    monthly_df['month_str'] = monthly_df['visit_date'].dt.strftime('%b %y')

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Bar chart for patient count
    fig.add_trace(
        go.Bar(
            x=monthly_df['month_str'], 
            y=monthly_df['patient_count'], 
            name='จำนวนผู้ป่วย',
            marker_color='#3498DB',
            opacity=0.7
        ),
        secondary_y=False,
    )

    # Line chart for PM2.5
    fig.add_trace(
        go.Scatter(
            x=monthly_df['month_str'], 
            y=monthly_df['avg_pm25'], 
            name='ค่าเฉลี่ย PM2.5',
            mode='lines+markers',
            line=dict(color='#E74C3C', width=3)
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title_text='<b>สถานการณ์ PM2.5 และจำนวนผู้เข้ารับการรักษา (รายเดือน)</b>',
        xaxis_title=None,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="sans-serif"),
        margin=dict(l=20, r=20, t=60, b=20)
    )
    fig.update_yaxes(title_text="จำนวนผู้ป่วย (คน)", secondary_y=False)
    fig.update_yaxes(title_text="ค่าเฉลี่ย PM2.5 (μg/m³)", secondary_y=True)
    
    st.plotly_chart(fig, use_container_width=True)

def display_district_barchart(df):
    """Displays a bar chart of patient counts by district."""
    st.markdown("<h6>จำนวนผู้ป่วยในแต่ละอำเภอ</h6>", unsafe_allow_html=True)
    if df.empty:
        st.warning("ไม่มีข้อมูล")
        return
        
    district_counts = df['district'].value_counts().sort_values(ascending=True)
    fig = px.bar(
        district_counts, 
        x=district_counts.values, 
        y=district_counts.index, 
        orientation='h',
        labels={'x': 'จำนวนผู้ป่วย', 'y': 'อำเภอ'},
        text=district_counts.values
    )
    fig.update_traces(marker_color='#2ECC71', textposition='outside')
    fig.update_layout(
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=10, b=10),
        height=300
    )
    st.plotly_chart(fig, use_container_width=True)

def display_patient_group_chart(df):
    """Displays a donut chart for patient group distribution."""
    st.markdown("<h6>สัดส่วนกลุ่มผู้เข้ารับบริการ</h6>", unsafe_allow_html=True)
    if df.empty:
        st.warning("ไม่มีข้อมูล")
        return

    group_counts = df['patient_group'].value_counts()
    fig = go.Figure(data=[go.Pie(
        labels=group_counts.index, 
        values=group_counts.values, 
        hole=.5,
        marker_colors=px.colors.qualitative.Pastel
    )])
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=10, b=10),
        height=300
    )
    st.plotly_chart(fig, use_container_width=True)

