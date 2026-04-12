import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- App Configuration ---
st.set_page_config(page_title="Waveguide Modem Comparison", layout="wide")
st.title("Dielectric Waveguide Link: Coherent QAM vs. PAM-4")
st.markdown("Comparing a DSP-heavy Coherent architecture against an IEEE-based direct-detect PAM-4 architecture over flexible waveguide.")

# --- Sidebar Inputs ---
st.sidebar.header("System Parameters")

length_m = st.sidebar.slider("Waveguide Length (meters)", min_value=10, max_value=30, value=20, step=1)
capacity_gbps = st.sidebar.slider("Target Capacity (Gbps)", min_value=100, max_value=400, value=200, step=50)

st.sidebar.markdown("---")
st.sidebar.subheader("Physical Layer Settings")
tx_power_dbm = st.sidebar.number_input("Tx Power (dBm)", value=5.0)
waveguide_loss_per_m = st.sidebar.number_input("Waveguide Loss (dB/m)", value=1.5, step=0.1)

# --- Engineering Model Calculations ---
total_loss_db = length_m * waveguide_loss_per_m
received_power_dbm = tx_power_dbm - total_loss_db

# 1. Coherent Solution (QAM + Simple FEC)
# High spectral efficiency, better sensitivity, higher power and cost.
coh_base_sens = -45.0 # dBm (Baseline sensitivity at 200 Gbps)
coh_sens_penalty = 10 * np.log10(capacity_gbps / 200) # Noise penalty for scaling capacity
coh_rx_sens = coh_base_sens + coh_sens_penalty

coh_margin = received_power_dbm - coh_rx_sens
coh_power_w = 25 + (capacity_gbps * 0.05) # Heavier DSP means higher power scaling
coh_cost = 1200 + (capacity_gbps * 2.5)

# 2. PAM-4 Solution (IEEE standard-based)
# Simpler architecture, worse sensitivity (requires ~15dB better SNR than coherent), low power, low cost.
pam_base_sens = -30.0 # dBm (Baseline sensitivity at 200 Gbps)
pam_sens_penalty = 10 * np.log10(capacity_gbps / 200)
pam_rx_sens = pam_base_sens + pam_sens_penalty

pam_margin = received_power_dbm - pam_rx_sens
pam_power_w = 8 + (capacity_gbps * 0.015) # Lightweight direct-detect
pam_cost = 350 + (capacity_gbps * 0.5)

# --- Data Structuring ---
data = {
    "Architecture": ["Coherent (QAM + FEC)", "PAM-4 (IEEE Based)"],
    "Rx Sensitivity (dBm)": [round(coh_rx_sens, 2), round(pam_rx_sens, 2)],
    "Link Margin (dB)": [round(coh_margin, 2), round(pam_margin, 2)],
    "Est. Power (W)": [round(coh_power_w, 2), round(pam_power_w, 2)],
    "Relative Cost Index": [round(coh_cost, 0), round(pam_cost, 0)]
}
df = pd.DataFrame(data)

# Status indicators (Link is down if margin < 0)
df["Status"] = df["Link Margin (dB)"].apply(lambda x: "🟢 Link UP" if x >= 0 else "🔴 Link DOWN")

# --- Dashboard Layout ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("System Performance Summary")
    st.markdown(f"**Total Waveguide Attenuation:** {round(total_loss_db, 2)} dB")
    st.markdown(f"**Received Power:** {round(received_power_dbm, 2)} dBm")
    
    # Display table with dynamic coloring for the Link Margin
    st.dataframe(df.style.map(lambda x: 'color: red' if 'DOWN' in str(x) else 'color: green', subset=['Status']))

with col2:
    st.subheader("Link Margin over Distance")
    
    # Visualizing Margin (crucial for showing when PAM-4 drops out)
    fig1 = px.bar(
        df, 
        x="Architecture", 
        y="Link Margin (dB)", 
        color="Architecture",
        color_discrete_map={"Coherent (QAM + FEC)": "#1f77b4", "PAM-4 (IEEE Based)": "#ff7f0e"}
    )
    # Add a horizontal line at 0 dB to show the failure threshold
    fig1.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Failure Threshold (0 dB)")
    st.plotly_chart(fig1, use_container_width=True)

st.divider()

# --- Secondary Metrics: Cost & Power ---
st.subheader("Trade-off Analysis: Power vs. Cost")
col3, col4 = st.columns(2)

with col3:
    fig2 = px.bar(df, x="Architecture", y="Est. Power (W)", color="Architecture",
                  title=f"Power Consumption at {capacity_gbps} Gbps",
                  color_discrete_map={"Coherent (QAM + FEC)": "#1f77b4", "PAM-4 (IEEE Based)": "#ff7f0e"})
    st.plotly_chart(fig2, use_container_width=True)

with col4:
    fig3 = px.bar(df, x="Architecture", y="Relative Cost Index", color="Architecture",
                  title=f"Cost Scaling at {capacity_gbps} Gbps",
                  color_discrete_map={"Coherent (QAM + FEC)": "#1f77b4", "PAM-4 (IEEE Based)": "#ff7f0e"})
    st.plotly_chart(fig3, use_container_width=True)
