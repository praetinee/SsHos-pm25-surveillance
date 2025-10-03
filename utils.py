import pandas as pd

def get_aqi_details(pm_value):
    """Returns AQI level text, background color, and text color based on PM2.5 value."""
    if pm_value is None or pd.isna(pm_value):
        return "ไม่มีข้อมูล", "#cccccc", "black" # Grey for missing data
    # Adjusted thresholds and colors based on Thailand's AQI for PM2.5
    if pm_value <= 15:
        return "คุณภาพอากาศดีมาก", "#3498DB", "white" # Blue
    if pm_value <= 25:
        return "คุณภาพอากาศดี", "#2ECC71", "white" # Green
    if pm_value <= 37:
        return "คุณภาพอากาศปานกลาง", "#F1C40F", "black" # Yellow
    if pm_value <= 75:
        return "เริ่มมีผลกระทบต่อสุขภาพ", "#E67E22", "white" # Orange
    return "มีผลกระทบต่อสุขภาพ", "#E74C3C", "white" # Red
