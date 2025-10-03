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
                <p style="font-size: 0.9em; color: #888; margin-top: 15px;">โรงพยาบาลสันทราย</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("ไม่สามารถแสดงข้อมูล PM2.5 Real-time ได้ในขณะนี้")

