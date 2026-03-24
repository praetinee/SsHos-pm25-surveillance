import streamlit as st
import pandas as pd
import pydeck as pdk

def plot_patient_map(dff_filtered, df_lat_lon):
    """
    Generates a bubble map of patient distribution based on pre-loaded lat/lon data.
    """
    if 'ตำบล' not in dff_filtered.columns:
        st.warning("ข้อมูลผู้ป่วยขาดคอลัมน์ 'ตำบล' ที่จำเป็นสำหรับการสร้างแผนที่")
        return

    # Prepare data for mapping
    patient_locations = dff_filtered['ตำบล'].value_counts().reset_index()
    patient_locations.columns = ['ตำบล', 'จำนวนผู้ป่วย']

    # Merge patient counts with coordinates
    # Using a left merge to ensure we only map locations present in the filtered patient data
    map_data = pd.merge(patient_locations, df_lat_lon, on='ตำบล', how='inner')

    if map_data.empty:
        st.info("ℹ️ ไม่มีข้อมูลผู้ป่วยที่ตรงกับพิกัดในพื้นที่ที่เลือก")
        return

    # Setting the initial view state for the map (centered on Chiang Mai)
    view_state = pdk.ViewState(
        latitude=18.7883,
        longitude=98.9853,
        zoom=8,
        pitch=50,
    )

    # Creating the scatter plot layer for the map
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_data,
        get_position="[lon, lat]",
        get_color="[200, 30, 0, 160]",
        get_radius="จำนวนผู้ป่วย * 100",  # Radius scales with patient count
        pickable=True,
        auto_highlight=True,
    )

    # Tooltip configuration
    tooltip = {
        "html": "<b>ตำบล:</b> {ตำบล}<br/><b>จำนวนผู้ป่วย:</b> {จำนวนผู้ป่วย} คน",
        "style": {"backgroundColor": "steelblue", "color": "white"},
    }

    # Render the map
    st.pydeck_chart(
        pdk.Deck(
            map_style="mapbox://styles/mapbox/light-v9",
            initial_view_state=view_state,
            layers=[layer],
            tooltip=tooltip,
        )
    )
