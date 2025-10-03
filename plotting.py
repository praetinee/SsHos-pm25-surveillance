import plotly.graph_objects as go
from plotly.subplots import make_subplots

def plot_main_chart(df, disease_groups):
    """
    Creates the main chart showing patient counts vs. PM2.5 levels.
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']

    # 1. Add line traces for each disease group
    for i, disease in enumerate(disease_groups):
        fig.add_trace(
            go.Scatter(
                x=df['date'], 
                y=df[disease], 
                name=disease,
                mode='lines+markers',
                line=dict(color=colors[i % len(colors)], width=2.5),
                marker=dict(size=6)
            ),
            secondary_y=False,
        )

    # 2. Add a bar trace for PM2.5 levels
    fig.add_trace(
        go.Bar(
            x=df['date'], 
            y=df['pm25_level'], 
            name='PM2.5 (ug/m3)',
            marker_color='lightgray',
            opacity=0.7
        ),
        secondary_y=True,
    )

    # --- Update Layout and Axes ---
    fig.update_layout(
        title_text="จำนวนผู้ป่วยรายเดือนเทียบกับค่าเฉลี่ย PM2.5",
        xaxis_title="เดือน",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white"
    )

    # Configure the primary Y-axis (Patient Count)
    fig.update_yaxes(
        title_text="<b>จำนวนผู้ป่วย (คน)</b>", 
        secondary_y=False,
        showgrid=True,
        gridcolor='lightgrey'
    )
    
    # Configure the secondary Y-axis (PM2.5 Level)
    fig.update_yaxes(
        title_text="<b>ระดับฝุ่น PM2.5 (ug/m3)</b>", 
        secondary_y=True,
        showgrid=False
    )
    
    return fig

