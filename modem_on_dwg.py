import streamlit as st
import pandas as pd
import numpy as np

# --- App Configuration ---
st.set_page_config(page_title="IEEE PAM-4 vs Coherent Comparison", layout="wide")
st.title("Waveguide Comparison: IEEE Multi-Lane PAM-4 vs. Coherent QAM")

# --- Sidebar Inputs ---
st.sidebar.header("Design Parameters")
capacity_gbps = st.sidebar.slider("Target Capacity (Gbps)", 100, 400, 200, 50)
fec_overhead = st.sidebar.slider("FEC Overhead (%)", 7, 25, 15) / 100
waveguide_length = st.sidebar.slider("Waveguide Length (m)", 10, 30, 20)

# Constants
lane_rate_pam = 50  # IEEE Standard 50G per PAM4 carrier
bits_per_symbol_pam = 2

# --- Logic: PAM-4 (IEEE Multi-Lane) ---
num_lanes_pam = int(capacity_gbps / lane_rate_pam)
# Bit rate per lane including FEC
bit_rate_per_lane_pam = lane_rate_pam * (1 + fec_overhead)
symbol_rate_pam = bit_rate_per_lane_pam / bits_per_symbol_pam
snr_threshold_pam = 15.8  # Standard target for PAM4

# --- Logic: Coherent (Single Carrier) ---
# We'll assume 16-QAM (4 bits/sym) for 200G, 64-QAM (6 bits/sym) for 400G
mod_scheme = "16-QAM" if capacity_gbps <= 200 else "64-QAM"
bits_per_symbol_coh = 4 if mod_scheme == "16-QAM" else 6
snr_threshold_coh = 12.5 if mod_scheme == "16-QAM" else 18.5

# Total bit rate with FEC
total_bit_rate_fec = capacity_gbps * (1 + fec_overhead)

# Case 1: Single Polarization (SP)
symbol_rate_coh_sp = total_bit_rate_fec / bits_per_symbol_coh

# Case 2: Dual Polarization (DP)
symbol_rate_coh_dp = total_bit_rate_fec / (2 * bits_per_symbol_coh)

# --- Comparison Table ---
data = [
    {
        "Solution": "PAM-4 (IEEE Multi-lane)",
        "Modulation": "PAM-4",
        "Polarization": "Single",
        "No. of Carriers": num_lanes_pam,
        "Symbol Rate / Carrier (Gbaud)": round(symbol_rate_pam, 2),
        "SNR Threshold (dB)": snr_threshold_pam,
        "Total Bandwidth Needs": "High (Requires WDM or Multi-core)"
    },
    {
        "Solution": "Coherent QAM (SP)",
        "Modulation": mod_scheme,
        "Polarization": "Single",
        "No. of Carriers": 1,
        "Symbol Rate / Carrier (Gbaud)": round(symbol_rate_coh_sp, 2),
        "SNR Threshold (dB)": snr_threshold_coh,
        "Total Bandwidth Needs": "Very High (Single Channel)"
    },
    {
        "Solution": "Coherent QAM (DP)",
        "Modulation": mod_scheme,
        "Polarization": "Dual",
        "No. of Carriers": 1,
        "Symbol Rate / Carrier (Gbaud)": round(symbol_rate_coh_dp, 2),
        "SNR Threshold (dB)": snr_threshold_coh,
        "Total Bandwidth Needs": "Moderate (Efficient)"
    }
]

df = pd.DataFrame(data)

# --- Display Results ---
st.subheader(f"Engineering Analysis: {capacity_gbps} Gbps over {waveguide_length}m")
st.table(df)

st.divider()

# --- Technical Breakdown ---
col1, col2 = st.columns(2)

with col1:
    st.markdown("### Symbol Rate Formula")
    st.latex(r"R_s = \frac{C \cdot (1 + FEC)}{n \cdot P}")
    st.write("""
    Where:
    - **C**: Capacity per carrier
    - **n**: Bits per symbol
    - **P**: Number of polarizations
    """)

with col2:
    st.markdown("### Key Observation")
    if capacity_gbps == 200:
        st.success("""
        **The 28 Gbaud Parity:** Notice that at 200 Gbps, both the **IEEE 4-lane PAM-4** and the **Dual-Pol 16-QAM Coherent** solution 
        run at approximately **28.75 Gbaud**. 
        
        The difference is physical: PAM-4 requires 4 separate channels (lanes), while Coherent 
        fits everything into a single channel using phase and polarization.
        """)
