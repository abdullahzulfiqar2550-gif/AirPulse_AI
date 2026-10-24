import sys
import sklearn._loss
try:
    from sklearn._loss import _loss as cy_loss
    sys.modules['_loss'] = cy_loss
    if hasattr(cy_loss, 'CyHalfSquaredError'):
        sklearn._loss.CyHalfSquaredError = cy_loss.CyHalfSquaredError
except Exception:
    pass

import streamlit as st
import pandas as pd
import numpy as np
import joblib
import os
import plotly.graph_objects as go

# 1. Page Configuration
st.set_page_config(
    page_title="AirPulse AI - Pakistan PM2.5 Smog Forecasting",
    page_icon="🌫️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Model Loading with Caching
@st.cache_resource
def load_model():
    # Check both paths: inside src or in root
    possible_paths = [
        os.path.join("..", "models", "best_pm25_pipeline.joblib"),
        os.path.join("models", "best_pm25_pipeline.joblib"),
        os.path.join(os.path.dirname(__file__), "..", "models", "best_pm25_pipeline.joblib")
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return joblib.load(path)
    return None

pipeline = load_model()

# City Geographic Coordinates
CITY_COORDINATES = {
    "Lahore": {"lat": 31.5204, "lon": 74.3587},
    "Karachi": {"lat": 24.8607, "lon": 67.0011},
    "Islamabad": {"lat": 33.6844, "lon": 73.0479},
    "Peshawar": {"lat": 34.0151, "lon": 71.5249},
    "Rawalpindi": {"lat": 33.5651, "lon": 73.0169}
}

# 3. Sidebar - Input Controls
st.sidebar.title("AirPulse AI Controls")
st.sidebar.markdown("Configure current sensor readings to forecast next-hour PM2.5 smog severity.")

selected_city = st.sidebar.selectbox("Select Pakistan City", list(CITY_COORDINATES.keys()), index=0)
lat = CITY_COORDINATES[selected_city]["lat"]
lon = CITY_COORDINATES[selected_city]["lon"]

st.sidebar.subheader("Temporal Context")
selected_hour = st.sidebar.slider("Current Hour of Day (0-23)", 0, 23, 19)
selected_month = st.sidebar.slider("Current Month (1-12)", 1, 12, 11)

st.sidebar.subheader("Current & Past PM2.5 Readings (µg/m³)")
current_pm25 = st.sidebar.number_input("Current PM2.5", min_value=1.0, max_value=800.0, value=145.0, step=1.0)
lag_1 = st.sidebar.number_input("PM2.5 Reading 1 Hour Ago", min_value=1.0, max_value=800.0, value=138.0, step=1.0)
lag_2 = st.sidebar.number_input("PM2.5 Reading 2 Hours Ago", min_value=1.0, max_value=800.0, value=125.0, step=1.0)
roll_6h = st.sidebar.number_input("6-Hour Rolling Average", min_value=1.0, max_value=800.0, value=130.0, step=1.0)

# 4. Prepare Feature DataFrame for Inference
input_data = pd.DataFrame([{
    "pm25_value": current_pm25,
    "pm25_lag_1": lag_1,
    "pm25_lag_2": lag_2,
    "pm25_roll_mean_6h": roll_6h,
    "hour": selected_hour,
    "month": selected_month,
    "latitude": lat,
    "longitude": lon
}])

# 5. Main Screen Header
st.title("AirPulse AI — Pakistan PM2.5 Smog Early Warning System")
st.markdown(f"**Live Model Forecasting for:** `{selected_city}` | Lat: `{lat}`, Lon: `{lon}`")

if pipeline is None:
    st.error("Model file `models/best_pm25_pipeline.joblib` not found. Please ensure the trained pipeline is in the models folder.")
    st.stop()

# Perform Inference
predicted_pm25 = float(pipeline.predict(input_data)[0])
delta_change = predicted_pm25 - current_pm25

# 6. AQI Risk Assessment Helper
def get_aqi_details(val):
    if val <= 30:
        return "Good (Safe)", "#2ecc71", "Air quality is satisfactory and poses little or no risk.", "No precautions needed."
    elif val <= 60:
        return "Moderate", "#f1c40f", "Acceptable quality; sensitive individuals may experience minor symptoms.", "Sensitive groups limit prolonged outdoor exertion."
    elif val <= 90:
        return "Unhealthy for Sensitive Groups", "#e67e22", "Members of sensitive groups may experience health effects.", "Wear a mask if sensitive; avoid heavy outdoor work."
    elif val <= 120:
        return "Unhealthy", "#e74c3c", "Everyone may begin to experience health effects.", "N95 mask recommended for all outdoor commute."
    elif val <= 250:
        return "Very Unhealthy", "#8e44ad", "Health alert: risk of serious health effects for everyone.", "Avoid all non-essential outdoor activity."
    else:
        return "Hazardous / Severe Smog", "#78281f", "Emergency conditions. Entire population is severely affected.", "Stay indoors with air purification. Smog Emergency Protocol."

category, color, description, advisory = get_aqi_details(predicted_pm25)

# 7. Dashboard Layout: 2 Columns
col1, col2 = st.columns([1, 1.4])

with col1:
    st.subheader("Next-Hour Forecast & Alert")
    
    # Top KPI Metric Card
    st.metric(
        label="Predicted PM2.5 (Next 1 Hour)",
        value=f"{predicted_pm25:.1f} µg/m³",
        delta=f"{delta_change:+.1f} µg/m³ vs Current",
        delta_color="inverse"
    )
    
    # Severity Banner
    st.markdown(
        f"""
        <div style="background-color: {color}; padding: 14px; border-radius: 8px; color: white; margin-top: 10px;">
            <h4 style="margin: 0; padding: 0;">Category: {category}</h4>
            <p style="margin: 6px 0 0 0; font-size: 14px;">{description}</p>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    st.markdown("#### Health Advisory & Action Plan")
    st.info(f"**Recommendation:** {advisory}")
    
    # Model Metadata card
    st.markdown("---")
    st.markdown("**Production Model:** `HistGradientBoostingRegressor` (Tuned Pipeline)")
    st.markdown("**Benchmark Score:** Test $R^2 = 0.9279$ | Test RMSE $= 23.94\ \\mu\\text{g/m}^3$")

with col2:
    st.subheader("Smog Trend & Trajectory Curve")
    
    # Plotly Visual
    time_points = ["2 Hours Ago", "1 Hour Ago", "Current Reading", "Next Hour (Predicted)"]
    pm25_points = [lag_2, lag_1, current_pm25, predicted_pm25]
    
    fig = go.Figure()
    
    # Historical Observed line
    fig.add_trace(go.Scatter(
        x=time_points[:3],
        y=pm25_points[:3],
        mode="lines+markers",
        name="Observed Readings",
        line=dict(color="#3498db", width=3),
        marker=dict(size=8)
    ))
    
    # Forecast line
    fig.add_trace(go.Scatter(
        x=time_points[2:],
        y=pm25_points[2:],
        mode="lines+markers",
        name="AI Forecast",
        line=dict(color="#e74c3c", width=3, dash="dot"),
        marker=dict(size=10, symbol="star")
    ))
    
    # WHO Guidelines Threshold line
    fig.add_hline(
        y=15, 
        line_dash="dash", 
        line_color="#27ae60", 
        annotation_text="WHO 24h Guideline (15 µg/m³)",
        annotation_position="bottom right"
    )
    
    fig.update_layout(
        title=f"PM2.5 Trajectory for {selected_city}",
        xaxis_title="Time Horizon",
        yaxis_title="PM2.5 Concentration (µg/m³)",
        template="plotly_white",
        height=380,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    st.plotly_chart(fig, use_container_width=True)

# 8. Input Feature Verification Expander
with st.expander("View Input Features Sent to Pipeline"):
    st.dataframe(input_data)