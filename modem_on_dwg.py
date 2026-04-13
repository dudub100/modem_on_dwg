import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- App Configuration ---
st.set_page_config(page_title="DWG Analyzer: Professional Mode", layout="wide")
st.title("DWG Analysis: IEEE PAM-4 vs. Customizable Coherent")

# --- Sidebar Inputs ---
st.sidebar.header("1. Material Physics")
dwg_atten_base = st.sidebar.number_input("Measured Attenuation (dB/m)", value=2.0, step=0.1)
f_meas_ghz = st.sidebar.number_input("at Measurement Frequency (GHz)", value=140.0, step=10.0)
epsilon_r = st.sidebar.number_input("Relative Permittivity (εr)", value=2.1)

# --- Physics Derivations ---
c = 299792458 
f_hz = f_meas_ghz * 1e9
tan_delta = (dwg_atten_base * c) / (8.686 * np.pi * f_hz * np.sqrt(epsilon_r))
dwg_slope_mhz_m = dwg_atten_base / (f_meas_ghz * 1000)

# --- Updated Sidebar Display (Using Metrics for better visibility) ---
st.sidebar.subheader("Calculated Material Specs")
# Metrics work better across different screen sizes/browsers
st.sidebar.metric(label="Tan Delta (δ)", value=f"{tan_delta:.6f}")
st.sidebar.metric(label="Slope (dB/MHz/m)", value=f"{dwg_slope_mhz_m:.8f}")

st.sidebar.divider()
# ... rest of your sidebar code ...

# --- Sidebar: Coherent Config ---
st.sidebar.header("2. Coherent Configuration")
coh_mod_options = {
    "QPSK": {"bits": 2, "snr": 7.0},
    "8-QAM": {"bits": 3, "snr": 10.0},
    "16-QAM": {"bits": 4, "snr": 12.5},
    "32-QAM": {"bits": 5, "snr": 15.5},
    "64-QAM": {"bits": 6, "snr": 18.5}
}
selected_mod = st.sidebar.selectbox("Coherent Modulation Level", list(coh_mod_options.keys()), index=2)
bits_per_symbol_coh = coh_mod_options[selected_mod]["bits"]
snr_threshold_coh = coh_mod_options[selected_mod]["snr"]

# Dynamic Display of Coherent SNR Requirement
st.sidebar.info(f"**Coherent SNR Threshold:** {snr_threshold_coh} dB")

st.sidebar.divider()

# --- Sidebar: PAM-4 Config ---
st.sidebar.header("3. IEEE PAM-4 Configuration")
snr_threshold_pam = 15.8
st.sidebar.info(f"**PAM-4 SNR Threshold:** {snr_threshold_pam} dB")
st.sidebar.caption("Based on typical IEEE 802.3 pre-FEC limits.")

st.sidebar.divider()

# --- Sidebar: Link Parameters ---
st.sidebar.header("4. Link Parameters")
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

# Common Bit Rate with FEC
total_bit_rate_fec = capacity_gbps * (1 + fec_overhead)

# 1. PAM-4 (IEEE Multi-lane)
num_lanes_pam = int(capacity_gbps / lane_rate_pam)
symbol_rate_pam = (lane_rate_pam * (1 + fec_overhead)) / 2  
bw_per_carrier_pam = symbol_rate_pam * (1 + roll_off)       
total_bw_pam = num_lanes_pam * (bw_per_carrier_pam * 1.15)  

# 2. Coherent SP
symbol_rate_coh_sp = total_bit_rate_fec / bits_per_symbol_coh
total_bw_coh_sp = symbol_rate_coh_sp * (1 + roll_off)

# 3. Coherent DP
symbol_rate_coh_dp = total_bit_rate_fec / (2 * bits_per_symbol_coh)
total_bw_coh_dp = symbol_rate_coh_dp * (1 + roll_off)

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
        "SNR Thr (dB)": snr_threshold_pam,
        "Flatness (dB)": round(dwg_slope_mhz_m * (total_bw_pam * 1000) * dwg_length, 2),
        "Sens (dBm)": round(calc_sensitivity(symbol_rate_pam, snr_threshold_pam), 2)
    },
    {
        "Solution": "Coherent SP",
        "Modulation": selected_mod,
        "Pol": "Single",
        "Sym Rate (Gbaud)": round(symbol_rate_coh_sp, 2),
        "SNR Thr (dB)": snr_threshold_coh,
        "Flatness (dB)": round(dwg_slope_mhz_m * (total_bw_coh_sp * 1000) * dwg_length, 2),
        "Sens (dBm)": round(calc_sensitivity(symbol_rate_coh_sp, snr_threshold_coh), 2)
    },
    {
        "Solution": "Coherent DP",
        "Modulation": selected_mod,
        "Pol": "Dual",
        "Sym Rate (Gbaud)": round(symbol_rate_coh_dp, 2),
        "SNR Thr (dB)": snr_threshold_coh,
        "Flatness (dB)": round(dwg_slope_mhz_m * (total_bw_coh_dp * 1000) * dwg_length, 2),
        "Sens (dBm)": round(calc_sensitivity(symbol_rate_coh_dp, snr_threshold_coh), 2)
    }
]

df = pd.DataFrame(results)
df["Margin (dB)"] = round(prx_base - df["Sens (dBm)"], 2)

# --- UI & Graphs ---
st.subheader(f"System Comparison for {capacity_gbps} Gbps")
st.table(df)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Link Margin (dB)")
    fig_margin = px.bar(df, x="Solution", y="Margin (dB)", color="Solution", text="Margin (dB)")
    fig_margin.add_hline(y=0, line_dash="dash", line_color="black")
    st.plotly_chart(fig_margin, use_container_width=True)

with col2:
    st.subheader("Spectral Occupancy & Tilt")
    max_bw = max(total_bw_pam, total_bw_coh_sp)
    x_range = max_bw * 1.3 / 2
    freq = np.linspace(-x_range, x_range, 800)
    loss_curve = -(dwg_slope_mhz_m * (freq * 1000) * dwg_length)
    
    fig_spec = go.Figure()
    fig_spec.add_trace(go.Scatter(x=freq, y=np.where(np.abs(freq) < (total_bw_coh_sp/2), 0, -30) + loss_curve, name=f"Coherent SP ({selected_mod})"))
    fig_spec.add_trace(go.Scatter(x=freq, y=np.where(np.abs(freq) < (total_bw_coh_dp/2), -2, -30) + loss_curve, name=f"Coherent DP ({selected_mod})", line=dict(dash='dot')))
    
    pam_spec = np.full_like(freq, -30.0)
    offsets = np.linspace(-(total_bw_pam/2) + (bw_per_carrier_pam/2), (total_bw_pam/2) - (bw_per_carrier_pam/2), num_lanes_pam)
    for off in offsets:
        pam_spec = np.maximum(pam_spec, np.where(np.abs(freq - off) < (bw_per_carrier_pam/2), -5, -30))
    fig_spec.add_trace(go.Scatter(x=freq, y=pam_spec + loss_curve, name="PAM-4 (4-Lane)"))

    fig_spec.update_layout(xaxis_title="Freq Offset (GHz)", yaxis_title="Rel. Power (dB)", yaxis_range=[-40, 5])
    st.plotly_chart(fig_spec, use_container_width=True)
