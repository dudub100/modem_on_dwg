import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- App Configuration ---
st.set_page_config(page_title="DWG Link Budget: Physics-Based Model", layout="wide")
st.title("DWG Analysis: IEEE PAM-4 vs. Coherent (SP & DP)")

# --- Sidebar Inputs ---
st.sidebar.header("1. Material & Physical Layer")
# Measurement inputs to derive Tan Delta and Slope
dwg_atten_base = st.sidebar.number_input("Measured Attenuation (dB/m)", value=2.0, step=0.1)
f_meas_ghz = st.sidebar.number_input("at Measurement Frequency (GHz)", value=140.0, step=10.0)
epsilon_r = st.sidebar.number_input("Relative Permittivity (εr)", value=2.1, help="2.1 for PTFE, 2.3 for PE")

# Physics Calculations
c = 299792458 # Speed of light
# 1. Derive Tan Delta: tan_d = (alpha_db * c) / (8.686 * pi * f * sqrt(er))
f_hz = f_meas_ghz * 1e9
tan_delta = (dwg_atten_base * c) / (8.686 * np.pi * f_hz * np.sqrt(epsilon_r))

# 2. Derive Slope (dB/MHz/m) assuming linear dielectric loss
# S = Atten / Frequency_in_MHz
dwg_slope_mhz_m = dwg_atten_base / (f_meas_ghz * 1000)

st.sidebar.markdown(f"**Estimated Tan Delta:** `{tan_delta:.6f}`")
st.sidebar.markdown(f"**Calculated Slope:** `{dwg_slope_mhz_m:.8f}` dB/MHz/m")

st.sidebar.divider()
st.sidebar.header("2. Link Config")
tx_power_dbm = st.sidebar.number_input("Tx Power per Carrier (dBm)", value=0.0)
dwg_length = st.sidebar.slider("DWG Length (meters)", 1, 50, 20)
capacity_gbps = st.sidebar.slider("Target Capacity (Gbps)", 100, 400, 200, 50)
fec_overhead = st.sidebar.slider("FEC Overhead (%)", 7, 25, 15) / 100

# Constants
lane_rate_pam = 50  
roll_off = 0.25     
noise_figure = 7.0  
thermal_noise_floor = -174  

# --- Engineering Calculations ---

# 1. PAM-4 (IEEE Multi-lane)
num_lanes_pam = int(capacity_gbps / lane_rate_pam)
symbol_rate_pam = (lane_rate_pam * (1 + fec_overhead)) / 2  # Gbaud
bw_per_carrier_pam = symbol_rate_pam * (1 + roll_off)       
total_bw_pam = num_lanes_pam * (bw_per_carrier_pam * 1.15)  

# 2. Coherent (16QAM for 200G, 64QAM for 400G)
mod_scheme_coh = "16-QAM" if capacity_gbps <= 200 else "64-QAM"
bits_per_symbol_coh = 4 if mod_scheme_coh == "16-QAM" else 6
total_bit_rate_fec = capacity_gbps * (1 + fec_overhead)

# Coherent SP vs DP
symbol_rate_coh_sp = total_bit_rate_fec / bits_per_symbol_coh
total_bw_coh_sp = symbol_rate_coh_sp * (1 + roll_off)

symbol_rate_coh_dp = total_bit_rate_fec / (2 * bits_per_symbol_coh)
total_bw_coh_dp = symbol_rate_coh_dp * (1 + roll_off)

# Sensitivity Helper
def calc_sensitivity(baud_rate, snr_db):
    noise_power = thermal_noise_floor + 10 * np.log10(baud_rate * 1e9)
    return noise_power + noise_figure + snr_db

# --- Result Compilation ---
total_loss_base = dwg_atten_base * dwg_length
prx_base = tx_power_dbm - total_loss_base

results = [
    {
        "Solution": "PAM-4 (IEEE)",
        "Modulation": "PAM-4",
        "Pol": "Single",
        "Sym Rate (Gbaud)": round(symbol_rate_pam, 2),
        "SNR Thr (dB)": 15.8,
        "Flatness (dB)": round(dwg_slope_mhz_m * (total_bw_pam * 1000) * dwg_length, 2),
        "Sens (dBm)": round(calc_sensitivity(symbol_rate_pam, 15.8), 2)
    },
    {
        "Solution": "Coherent SP",
        "Modulation": mod_scheme_coh,
        "Pol": "Single",
        "Sym Rate (Gbaud)": round(symbol_rate_coh_sp, 2),
        "SNR Thr (dB)": 12.5 if mod_scheme_coh == "16-QAM" else 18.5,
        "Flatness (dB)": round(dwg_slope_mhz_m * (total_bw_coh_sp * 1000) * dwg_length, 2),
        "Sens (dBm)": round(calc_sensitivity(symbol_rate_coh_sp, 12.5 if mod_scheme_coh == "16-QAM" else 18.5), 2)
    },
    {
        "Solution": "Coherent DP",
        "Modulation": mod_scheme_coh,
        "Pol": "Dual",
        "Sym Rate (Gbaud)": round(symbol_rate_coh_dp, 2),
        "SNR Thr (dB)": 12.5 if mod_scheme_coh == "16-QAM" else 18.5,
        "Flatness (dB)": round(dwg_slope_mhz_m * (total_bw_coh_dp * 1000) * dwg_length, 2),
        "Sens (dBm)": round(calc_sensitivity(symbol_rate_coh_dp, 12.5 if mod_scheme_coh == "16-QAM" else 18.5), 2)
    }
]

df = pd.DataFrame(results)
df["Margin (dB)"] = round(prx_base - df["Sens (dBm)"], 2)

# --- Visuals ---
st.subheader("Physical Layer Engineering Comparison")
st.table(df)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Link Margin (dB)")
    fig_margin = px.bar(df, x="Solution", y="Margin (dB)", color="Solution", text="Margin (dB)")
    fig_margin.add_hline(y=0, line_dash="dash", line_color="black")
    st.plotly_chart(fig_margin, use_container_width=True)

with col2:
    st.subheader("Spectrum Impact (Centered on f_meas)")
    max_bw = max(total_bw_pam, total_bw_coh_sp)
    x_range = max_bw * 1.3 / 2
    freq = np.linspace(-x_range, x_range, 800)
    
    # Loss curve relative to center frequency
    loss_curve = -(dwg_slope_mhz_m * (freq * 1000) * dwg_length)
    
    fig_spec = go.Figure()
    # Coherent SP
    fig_spec.add_trace(go.Scatter(x=freq, y=np.where(np.abs(freq) < (total_bw_coh_sp/2), 0, -30) + loss_curve, name="Coherent SP"))
    # Coherent DP
    fig_spec.add_trace(go.Scatter(x=freq, y=np.where(np.abs(freq) < (total_bw_coh_dp/2), -2, -30) + loss_curve, name="Coherent DP"))
    # PAM-4 Lanes
    pam_spec = np.full_like(freq, -30.0)
    offsets = np.linspace(-(total_bw_pam/2) + (bw_per_carrier_pam/2), (total_bw_pam/2) - (bw_per_carrier_pam/2), num_lanes_pam)
    for off in offsets:
        pam_spec = np.maximum(pam_spec, np.where(np.abs(freq - off) < (bw_per_carrier_pam/2), -5, -30))
    fig_spec.add_trace(go.Scatter(x=freq, y=pam_spec + loss_curve, name="PAM-4 (4-Lane)"))

    fig_spec.update_layout(xaxis_title="Freq Offset from Center (GHz)", yaxis_title="Rel. Power (dB)", yaxis_range=[-40, 5])
    st.plotly_chart(fig_spec, use_container_width=True)
