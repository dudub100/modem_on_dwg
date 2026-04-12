import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- App Configuration ---
st.set_page_config(page_title="DWG Link Budget & Spectrum Analyzer", layout="wide")
st.title("DWG Analysis: Link Margin & Spectral Flatness")

# --- Sidebar Inputs ---
st.sidebar.header("User Inputs")

# 1, 2, 3: Basic Link Parameters
tx_power_dbm = st.sidebar.number_input("Transmit Power per Carrier (dBm)", value=0.0, step=1.0)
dwg_atten_base = st.sidebar.number_input("DWG Base Attenuation (dB/m)", value=1.5, step=0.1)
dwg_length = st.sidebar.slider("DWG Length (meters)", 1, 50, 20)

# 5: Slope Model
# Typical DWG slope might be in the range of 0.0001 to 0.001 dB/MHz/m
dwg_slope_mhz_m = st.sidebar.number_input("DWG Slope (dB/MHz/meter)", value=0.0001, format="%.6f")

st.sidebar.divider()
capacity_gbps = st.sidebar.slider("Target Capacity (Gbps)", 100, 400, 200, 50)
fec_overhead = st.sidebar.slider("FEC Overhead (%)", 7, 25, 15) / 100

# Constants
lane_rate_pam = 50  # IEEE Standard
roll_off = 0.25     # RRC Filter factor
noise_figure = 7.0  # dB (Receiver LNA/Frontend)
thermal_noise_floor = -174  # dBm/Hz

# --- Engineering Calculations ---

# Calculations for PAM-4 (4 Carriers for 200G)
num_lanes_pam = int(capacity_gbps / lane_rate_pam)
symbol_rate_pam = (lane_rate_pam * (1 + fec_overhead)) / 2  # Gbaud
bw_per_carrier_pam = symbol_rate_pam * (1 + roll_off)       # GHz
total_bw_pam = num_lanes_pam * (bw_per_carrier_pam * 1.2)   # Including 20% guard bands

# Calculations for Coherent (Single Carrier, Dual Pol)
mod_scheme = "16-QAM" if capacity_gbps <= 200 else "64-QAM"
bits_per_symbol_coh = 4 if mod_scheme == "16-QAM" else 6
symbol_rate_coh_dp = (capacity_gbps * (1 + fec_overhead)) / (2 * bits_per_symbol_coh)
total_bw_coh = symbol_rate_coh_dp * (1 + roll_off) # GHz

# Sensitivity Model (Simplified)
# Sensitivity = Thermal Noise + 10log10(BW_Hz) + NF + SNR_Required
def calc_sensitivity(bw_ghz, snr_db):
    noise_power = thermal_noise_floor + 10 * np.log10(bw_ghz * 1e9)
    return noise_power + noise_figure + snr_db

sens_pam = calc_sensitivity(symbol_rate_pam / 1e9, 15.8)
sens_coh = calc_sensitivity(symbol_rate_coh_dp / 1e9, 12.5 if mod_scheme == "16-QAM" else 18.5)

# Margin Calculation
total_loss_base = dwg_atten_base * dwg_length
prx_per_carrier = tx_power_dbm - total_loss_base
margin_pam = prx_per_carrier - sens_pam
margin_coh = tx_power_dbm - total_loss_base - sens_coh

# 6: Flatness / Slope Calculation
# Total Flatness (dB) = Slope (dB/MHz/m) * Bandwidth (MHz) * Length (m)
flatness_pam = dwg_slope_mhz_m * (total_bw_pam * 1000) * dwg_length
flatness_coh = dwg_slope_mhz_m * (total_bw_coh * 1000) * dwg_length

# --- Table & Metrics ---
st.subheader("System Summary")
col_a, col_b, col_c = st.columns(3)
col_a.metric("Total Base Loss", f"{round(total_loss_base, 2)} dB")
col_b.metric("PAM-4 Flatness (Tilt)", f"{round(flatness_pam, 2)} dB")
col_c.metric("Coherent Flatness (Tilt)", f"{round(flatness_coh, 2)} dB")

data = [
    {"Solution": "PAM-4 (4x50G)", "Symbol Rate": f"{round(symbol_rate_pam, 2)} Gbaud", "Margin": round(margin_pam, 2), "Flatness": round(flatness_pam, 2)},
    {"Solution": "Coherent (DP)", "Symbol Rate": f"{round(symbol_rate_coh_dp, 2)} Gbaud", "Margin": round(margin_coh, 2), "Flatness": round(flatness_coh, 2)}
]
st.table(pd.DataFrame(data))

# --- Graphs ---
st.divider()
col1, col2 = st.columns(2)

with col1:
    st.subheader("Link Margin Comparison")
    fig_margin = px.bar(data, x="Solution", y="Margin", color="Solution", 
                        color_discrete_sequence=["#EF553B", "#636EFA"])
    fig_margin.add_hline(y=0, line_dash="dash", line_color="black", annotation_text="Limit")
    st.plotly_chart(fig_margin, use_container_width=True)

with col2:
    st.subheader("Relative Spectrum & Waveguide Slope")
    
    # Spectrum Simulation
    freq = np.linspace(-total_bw_pam, total_bw_pam, 500)
    
    # DWG Loss Curve (Slope)
    loss_curve = -(dwg_slope_mhz_m * (freq * 1000) * dwg_length)
    
    fig_spec = go.Figure()
    
    # Coherent Spectrum (One wide pulse)
    coh_spec = np.where(np.abs(freq) < (total_bw_coh/2), 0, -30)
    fig_spec.add_trace(go.Scatter(x=freq, y=coh_spec + loss_curve, name="Coherent Spectrum", line=dict(color='blue', width=3)))
    
    # PAM-4 Spectrum (4 narrow pulses)
    pam_spec = np.full_like(freq, -30)
    offsets = np.linspace(-total_bw_pam/2, total_bw_pam/2, 4)
    for off in offsets:
        pam_spec = np.maximum(pam_spec, np.where(np.abs(freq - off) < (bw_per_carrier_pam/2), -5, -30))
    
    fig_spec.add_trace(go.Scatter(x=freq, y=pam_spec + loss_curve, name="PAM-4 (4-Lane) Spectrum", line=dict(color='red', dash='dash')))
    
    fig_spec.update_layout(xaxis_title="Relative Frequency (GHz)", yaxis_title="Relative Power (dBm)", yaxis_range=[-40, 5])
    st.plotly_chart(fig_spec, use_container_width=True)
