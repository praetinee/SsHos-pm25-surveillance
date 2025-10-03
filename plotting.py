import plotly.graph_objects as go
from plotly.subplots import make_subplots

def plot_main_chart(df, disease_groups):
    """
    สร้างกราฟหลักที่แสดงจำนวนผู้ป่วยในแต่ละกลุ่มโรคเทียบกับค่าฝุ่น PM2.5
    """
    # สร้างกราฟที่มีแกน Y 2 แกน
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # กำหนดชุดสี
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']

    # 1. เพิ่มกราฟเส้นสำหรับจำนวนผู้ป่วยในแต่ละกลุ่มโรค
    for i, disease in enumerate(disease_groups):
        fig.add_trace(
            go.Scatter(
                x=df['date'], 
                y=df[disease], 
                name=disease,
                mode='lines+markers',
                line=dict(color=colors[i % len(colors)])
            ),
            secondary_y=False,
        )

    # 2. เพิ่มกราฟแท่งสำหรับค่าฝุ่น PM2.5
    fig.add_trace(
        go.Bar(
            x=df['date'], 
            y=df['pm25_level'], 
            name='PM2.5 (ug/m3)',
            marker_color='lightgray',
            opacity=0.6
        ),
        secondary_y=True,
    )

    # --- ตั้งค่า Layout และแกนต่างๆ ---
    fig.update_layout(
        title_text="จำนวนผู้ป่วยรายเดือนเทียบกับค่าเฉลี่ย PM2.5",
        xaxis_title="เดือน",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # ตั้งชื่อแกน Y หลัก (ซ้าย)
    fig.update_yaxes(
        title_text="<b>จำนวนผู้ป่วย (คน)</b>", 
        secondary_y=False,
        showgrid=True, 
        gridwidth=1, 
        gridcolor='LightGray'
    )
    
    # ตั้งชื่อแกน Y รอง (ขวา)
    fig.update_yaxes(
        title_text="<b>ระดับฝุ่น PM2.5 (ug/m3)</b>", 
        secondary_y=True,
        showgrid=False
    )
    
    return fig

