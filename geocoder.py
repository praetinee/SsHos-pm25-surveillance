import streamlit as st
import pandas as pd
import requests
from time import sleep

def _geocode_single_address(address, api_key):
    """Return (lat, lon) using Google Maps Geocoding API for a single address."""
    if not isinstance(address, str) or address.strip() == "":
        return None, None
    
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": api_key, "language": "th"}
    
    try:
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status() # Raises an exception for bad status codes (4xx or 5xx)
        data = r.json()
        if data.get("status") == "OK":
            loc = data["results"][0]["geometry"]["location"]
            return loc["lat"], loc["lng"]
        else:
            return None, None
    except requests.exceptions.RequestException as e:
        st.warning(f"เกิดข้อผิดพลาดในการเชื่อมต่อเพื่อ Geocode ที่อยู่: {address} ({e})")
        return None, None

def geocode_addresses(df):
    """
    Processes a DataFrame to add 'lat' and 'lon' columns by geocoding addresses.
    Uses caching to avoid re-processing and re-calling the API.
    """
    required_cols = ["ตำบล", "อำเภอ", "จังหวัด"]
    if not all(col in df.columns for col in required_cols):
        st.info("ℹ️ ไม่สามารถ Geocode ได้ เนื่องจากขาดคอลัมน์ ตำบล, อำเภอ, หรือ จังหวัด")
        return df

    # --- API Key Handling ---
    api_key = None
    if "google_maps" in st.secrets and "api_key" in st.secrets["google_maps"] and st.secrets["google_maps"]["api_key"]:
        api_key = st.secrets["google_maps"]["api_key"]
    else:
        st.error("❌ ไม่พบ Google Maps API Key. กรุณาตั้งค่าในไฟล์ `.streamlit/secrets.toml` หรือในหน้าตั้งค่า Secrets ของ Streamlit Cloud")
        return df

    df["full_address"] = df.apply(lambda r: f"ต.{r['ตำบล']} อ.{r['อำเภอ']} จ.{r['จังหวัด']}", axis=1)
    
    unique_addresses = df["full_address"].dropna().unique()
    
    progress_bar = st.progress(0, text="กำลังประมวลผลพิกัด...")
    
    # Use a dictionary for an efficient cache-like lookup
    coord_map = {}

    for i, address in enumerate(unique_addresses):
        lat, lon = _geocode_single_address(address, api_key)
        coord_map[address] = (lat, lon)
        sleep(0.01) # Small delay to prevent hitting API rate limits too quickly
        progress_bar.progress((i + 1) / len(unique_addresses), text=f"ประมวลผล: {address}")

    progress_bar.empty()
    st.success("✅ ประมวลผลพิกัดสำเร็จ!")
    
    df[["lat", "lon"]] = df["full_address"].map(coord_map).apply(pd.Series)
    return df

