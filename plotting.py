import pandas as pd
import plotly.express as px

def create_time_series_chart(filtered_patients, pm25_df, start_date, end_date):
    """สร้างกราฟแนวโน้มผู้ป่วยเทียบกับค่า PM2.5"""
    # เตรียมข้อมูลสำหรับกราฟ
    daily_admissions = filtered_patients.groupby(filtered_patients['admission_date'].dt.date).size().reset_index(name='patient_count')
    daily_admissions['admission_date'] = pd.to_datetime(daily_admissions['admission_date'])
    pm25_filtered = pm25_df[(pm25_df['date'] >= start_date) & (pm25_df['date'] <= end_date)]

    # รวมข้อมูล 2 ชุด
    plot_df = pd.merge(daily_admissions, pm25_filtered, left_on='admission_date', right_on='date', how='left')

    fig = px.line(plot_df, x='admission_date', y='patient_count', title='',
                  labels={'admission_date': 'วันที่', 'patient_count': 'จำนวนผู้ป่วย'},
                  markers=True, template='plotly_white')

    # เพิ่มแกน Y ที่สองสำหรับ PM2.5
    fig.add_bar(x=plot_df['date'], y=plot_df['pm25_level'], name='PM2.5 Level (µg/m³)',
                marker_color='lightcoral', opacity=0.6)

    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def create_diagnosis_pie_chart(filtered_patients):
    """สร้างกราฟวงกลมแสดงสัดส่วนกลุ่มโรค"""
    if filtered_patients.empty:
        return None

    diagnosis_counts = filtered_patients['diagnosis'].value_counts()
    fig = px.pie(values=diagnosis_counts.values, names=diagnosis_counts.index,
                 hole=0.3, color_discrete_sequence=px.colors.sequential.RdBu)
    fig.update_traces(textposition='inside', textinfo='percent+label')
    return fig

def create_age_gender_bar_chart(filtered_patients):
    """สร้างกราฟแท่งแสดงผู้ป่วยตามกลุ่มอายุและเพศ"""
    if filtered_patients.empty:
        return None

    # ทำสำเนาเพื่อหลีกเลี่ยง SettingWithCopyWarning
    df = filtered_patients.copy()

    age_bins = [0, 10, 20, 30, 40, 50, 60, 70, 100]
    age_labels = ['0-10', '11-20', '21-30', '31-40', '41-50', '51-60', '61-70', '70+']
    df['age_group'] = pd.cut(df['age'], bins=age_bins, labels=age_labels, right=False)

    age_gender_df = df.groupby(['age_group', 'gender']).size().reset_index(name='count')
    fig = px.bar(age_gender_df, x='age_group', y='count', color='gender',
                 barmode='group', labels={'age_group': 'กลุ่มอายุ', 'count': 'จำนวนผู้ป่วย', 'gender': 'เพศ'},
                 template='plotly_white', color_discrete_map={'ชาย': 'cornflowerblue', 'หญิง': 'lightcoral'})
    return fig
