import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- App Configuration ---
st.set_page_config(page_title="DWG Link Budget: IEEE vs Coherent", layout="wide")
st.title("DWG Analysis: IEEE PAM-4 vs. Coherent (SP & DP)")

# --- Sidebar Inputs ---
st.sidebar.header("User Inputs")
tx_power_dbm = st.sidebar.number_input("Transmit Power per Carrier (dBm)", value=0.0, step=1.0)
dwg_atten_base = st.sidebar.number_input("DWG Base Attenuation (dB/m)", value=1.5, step=0.1)
dwg_length = st.sidebar.slider("DWG Length (meters)", 1, 50, 20)
dwg_slope_mhz_m = st.sidebar.number_input("DWG Slope (dB/MHz/meter)", value=0.0001, format="%.6f")

st.sidebar.divider()
capacity_gbps = st.sidebar.slider("Target Capacity (Gbps)", 100, 400, 200, 50)
fec_overhead = st.sidebar.slider("FEC Overhead (%)", 7, 25, 15) / 100

# Constants
lane_rate_pam = 50  # IEEE Standard
roll_off = 0.25     
noise_figure = 7.0  
thermal_noise_floor = -174  

# --- Engineering Calculations ---

# 1. PAM-4 (IEEE Multi-lane: 4x50G for 200G)
num_lanes_pam = int(capacity_gbps / lane_rate_pam)
symbol_rate_pam = (lane_rate_pam * (1 + fec_overhead)) / 2  # Gbaud
bw_per_carrier_pam = symbol_rate_pam * (1 + roll_off)       # GHz
total_bw_pam = num_lanes_pam * (bw_per_carrier_pam * 1.15)  # 15% guard bands between lanes

# 2. Coherent Modulation Selection (16QAM for 200G, 64QAM for higher)
mod_scheme_coh = "16-QAM" if capacity_gbps <= 200 else "64-QAM"
bits_per_symbol_coh = 4 if mod_scheme_coh == "16-QAM" else 6
total_bit_rate_fec = capacity_gbps * (1 + fec_overhead)

# Coherent SP
symbol_rate_coh_sp = total_bit_rate_fec / bits_per_symbol_coh
total_bw_coh_sp = symbol_rate_coh_sp * (1 + roll_off)

# Coherent DP
symbol_rate_coh_dp = total_bit_rate_fec / (2 * bits_per_symbol_coh)
total_bw_coh_dp = symbol_rate_coh_dp * (1 + roll_off)

# Sensitivity Helper
def calc_sensitivity(baud_rate, snr_db):
    # Bandwidth in Hz for noise power calculation
    noise_power = thermal_noise_floor + 10 * np.log10(baud_rate * 1e9)
    return noise_power + noise_figure + snr_db

# --- Comparison Metrics Construction ---
total_loss_base = dwg_atten_base * dwg_length
prx_base = tx_power_dbm - total_loss_base

results = [
    {
        "Solution": "PAM-4 (IEEE)",
        "Modulation": "PAM-4",
        "Pol": "Single",
        "Lanes": num_lanes_pam,
        "Sym Rate (Gbaud)": round(symbol_rate_pam, 2),
        "SNR Thr (dB)": 15.8,
        "Flatness (dB)": round(dwg_slope_mhz_m * (total_bw_pam * 1000) * dwg_length, 2),
        "Sens (dBm)": calc_sensitivity(symbol_rate_pam, 15.8)
    },
    {
        "Solution": "Coherent SP",
        "Modulation": mod_scheme_coh,
        "Pol": "Single",
        "Lanes": 1,
        "Sym Rate (Gbaud)": round(symbol_rate_coh_sp, 2),
        "SNR Thr (dB)": 12.5 if mod_scheme_coh == "16-QAM" else 18.5,
        "Flatness (dB)": round(dwg_slope_mhz_m * (total_bw_coh_sp * 1000) * dwg_length, 2),
        "Sens (dBm)": calc_sensitivity(symbol_rate_coh_sp, 12.5 if mod_scheme_coh == "16-QAM" else 18.5)
    },
    {
        "Solution": "Coherent DP",
        "Modulation": mod_scheme_coh,
        "Pol": "Dual",
        "Lanes": 1,
        "Sym Rate (Gbaud)": round(symbol_rate_coh_dp, 2),
        "SNR Thr (dB)": 12.5 if mod_scheme_coh == "16-QAM" else 18.5,
        "Flatness (dB)": round(dwg_slope_mhz_m * (total_bw_coh_dp * 1000) * dwg_length, 2),
        "Sens (dBm)": calc_sensitivity(symbol_rate_coh_dp, 12.5 if mod_scheme_coh == "16-QAM" else 18.5)
    }
]

df = pd.DataFrame(results)
df["Margin (dB)"] = round(prx_base - df["Sens (dBm)"], 2)

# --- UI Layout ---
st.subheader(f"Engineering Summary: {capacity_gbps} Gbps over {dwg_length}m DWG")
st.table(df[["Solution", "Modulation", "Pol", "Sym Rate (Gbaud)", "SNR Thr (dB)", "Flatness (dB)", "Margin (dB)"]])

# --- Graphs ---
st.divider()
col1, col2 = st.columns(2)

with col1:
    st.subheader("Link Margin Comparison")
    fig_margin = px.bar(df, x="Solution", y="Margin (dB)", color="Solution", text="Margin (dB)")
    fig_margin.add_hline(y=0, line_dash="dash", line_color="black")
    st.plotly_chart(fig_margin, use_container_width=True)

with col2:
    st.subheader("Spectrum & DWG Slope Impact")
    
    # Determine relevant frequency range (Max BW + 20% margin)
    max_bw = max(total_bw_pam, total_bw_coh_sp)
    x_range = max_bw * 1.2 / 2
    freq = np.linspace(-x_range, x_range, 800)
    
    # DWG Loss Curve
    loss_curve = -(dwg_slope_mhz_m * (freq * 1000) * dwg_length)
    
    fig_spec = go.Figure()

    # 1. Coherent SP Spectrum
    coh_sp_spec = np.where(np.abs(freq) < (total_bw_coh_sp / 2), 0, -30)
    fig_spec.add_trace(go.Scatter(x=freq, y=coh_sp_spec + loss_curve, name="Coherent SP", line=dict(color='blue')))

    # 2. Coherent DP Spectrum
    coh_dp_spec = np.where(np.abs(freq) < (total_bw_coh_dp / 2), -2, -30) # Offset for visibility
    fig_spec.add_trace(go.Scatter(x=freq, y=coh_dp_spec + loss_curve, name="Coherent DP", line=dict(color='cyan', dash='dot')))

    # 3. PAM-4 Spectrum (IEEE Multi-lane)
    pam_spec = np.full_like(freq, -30.0)
    offsets = np.linspace(-(total_bw_pam/2) + (bw_per_carrier_pam/2), (total_bw_pam/2) - (bw_per_carrier_pam/2), num_lanes_pam)
    for off in offsets:
        lane = np.where(np.abs(freq - off) < (bw_per_carrier_pam / 2), -5, -30)
        pam_spec = np.maximum(pam_spec, lane)
    fig_spec.add_trace(go.Scatter(x=freq, y=pam_spec + loss_curve, name="PAM-4 (4-Lane)", line=dict(color='red', width=1)))

    fig_spec.update_layout(
        xaxis_title="Frequency (GHz)", 
        yaxis_title="Rel. Power (dBm)",
        xaxis=dict(range=[-x_range, x_range]),
        yaxis=dict(range=[-45, 5])
    )
    st.plotly_chart(fig_spec, use_container_width=True)
