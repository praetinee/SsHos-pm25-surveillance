import pandas as pd
import requests
import streamlit as st

@st.cache_data(show_spinner="กำลังดึงพิกัดจาก Google Maps...")
def _geocode_single_address(address):
    """Geocodes a single address string."""
    if not isinstance(address, str) or not address.strip():
        return None, None
    
    try:
        api_key = st.secrets["google_maps"]["api_key"]
    except (KeyError, FileNotFoundError):
        st.error("❌ ไม่พบ API Key ของ Google Maps ใน secrets.toml")
        return None, None

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": api_key, "language": "th"}
    
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        data = r.json()

        if data.get("status") == "OK" and data.get("results"):
            loc = data["results"][0]["geometry"]["location"]
            return loc.get("lat"), loc.get("lng")
        return None, None
            
    except requests.exceptions.RequestException:
        # Avoid flooding the UI with errors for connection issues
        return None, None
    except (KeyError, IndexError):
        # Handle cases where the JSON response is not as expected
        return None, None

def add_coordinates_to_dataframe(df):
    """Adds 'lat' and 'lon' columns to the dataframe by geocoding addresses."""
    if not all(col in df.columns for col in ["ตำบล", "อำเภอ", "จังหวัด"]):
        st.warning("⚠️ ไม่พบคอลัมน์ 'ตำบล', 'อำเภอ', 'จังหวัด' สำหรับ Geocoding")
        df['lat'] = None
        df['lon'] = None
        return df

    st.info("🔍 กำลังประมวลผลพิกัดตำบล ... (ระบบจะ cache ผลลัพธ์เพื่อความรวดเร็ว)")
    
    df["full_address"] = df.apply(
        lambda r: f"{r['ตำบล']} {r['อำเภอ']} {r['จังหวัด']}", axis=1
    )
    
    # Create a list of unique addresses to geocode, avoiding redundant API calls
    unique_addresses = df["full_address"].unique()
    
    lat_lon_map = {}
    progress_bar = st.progress(0, text="กำลังแปลงที่อยู่เป็นพิกัด...")
    
    for i, address in enumerate(unique_addresses):
        lat, lon = _geocode_single_address(address)
        lat_lon_map[address] = {"lat": lat, "lon": lon}
        progress_bar.progress((i + 1) / len(unique_addresses), text=f"กำลังแปลงที่อยู่... ({i+1}/{len(unique_addresses)})")
    
    progress_bar.empty()
    
    # Map the results back to the original dataframe
    mapped_coords = df['full_address'].map(lat_lon_map).apply(pd.Series)
    df['lat'] = mapped_coords['lat']
    df['lon'] = mapped_coords['lon']

    return df
