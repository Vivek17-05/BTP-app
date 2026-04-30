import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURATION & DATA ---
st.set_page_config(page_title="IITKGP Solar Cooling Framework", layout="wide")

# Solar Data (kWh/day) from Phase 1 Analysis [cite: 787]
solar_data = {
    'January': 14947.80, 'February': 18678.17, 'March': 19303.15, 'April': 20573.28,
    'May': 20605.78, 'June': 17866.55, 'July': 15839.19, 'August': 14271.71,
    'September': 15995.65, 'October': 15879.08, 'November': 16283.02, 'December': 13876.31
}

# Campus Hostel Database from Phase 4 Scaling [cite: 787]
hostels = {
    'Azad': 424, 'BC Roy': 162, 'BRH': 1390, 'Gokhale': 54, 'HJB': 163,
    'JCB': 262, 'Nehru': 331, 'LBS': 650, 'LLR': 334, 'MMM': 789,
    'MS': 397, 'MT': 164, 'SNVH': 81, 'Patel': 328, 'RK': 421,
    'RLB': 250, 'RP': 489, 'SNIG': 249, 'VS': 335, 'SBP-1': 450, 'SBP-2': 450
}

# --- SIDEBAR INPUTS ---
st.sidebar.header("1. Environmental & Storage Config")
selected_month = st.sidebar.selectbox("Select Scenario Month", list(solar_data.keys()))

# NEW FEATURE: Dynamic CoP Controller (Baseline 3.2) [cite: 827, 831]
cop_value = st.sidebar.select_slider(
    "Chiller Efficiency (CoP)",
    options=[2.0, 2.5, 3.2, 4.0, 5.0],
    value=3.2,
    help="Higher CoP means more efficient chillers (standard is ~3.2)"
)

# Convert CoP to kW per TR 
# Formula: kW_elec = 3.517 / CoP
dynamic_kw_per_tr = 3.517 / cop_value 

# Dynamic Load Configuration [cite: 808, 809]
tr_per_room = st.sidebar.slider("Cooling Intensity (TR/Room)", 0.0, 1.0, 0.6, 0.05)
kw_per_room = tr_per_room * dynamic_kw_per_tr 
x_factor = st.sidebar.slider("Storage Scaling Factor (X%)", 0.1, 1.0, 0.6, 0.05)

st.sidebar.markdown("---")
st.sidebar.header("2. Hostel Selection")
all_hostels = sorted(list(hostels.keys()))
active_hostels = st.sidebar.multiselect(
    "Active Halls",
    options=all_hostels,
    default=all_hostels
)

st.sidebar.markdown("---")
st.sidebar.header("3. Scheduling Mode")
sched_mode = st.sidebar.radio(
    "Select Scheduling Strategy",
    ("Auto-Tiered (2-3-4 hrs)", "Manual Override (0-24 hrs)")
)

manual_durations = {}
if sched_mode == "Manual Override (0-24 hrs)":
    with st.sidebar.expander("Configure Individual Hall Hours"):
        for name in active_hostels:
            manual_durations[name] = st.slider(f"Hours for {name}", 0, 24, 4)

# --- CALCULATIONS ---
tier_list = []
for name, rooms in hostels.items():
    if name in active_hostels:
        if sched_mode == "Auto-Tiered (2-3-4 hrs)":
            # Multi-tiered logic [cite: 800]
            if rooms < 270:
                tier, duration = "Small", 4
            elif 270 <= rooms <= 600:
                tier, duration = "Medium", 3
            else:
                tier, duration = "Large", 2
        else:
            tier, duration = "Manual", manual_durations.get(name, 4)
        
        power = rooms * kw_per_room
        energy = power * duration
        tier_list.append({
            'Hostel': name, 'Rooms': rooms, 'Tier': tier, 
            'Duration': duration, 'Power (kW)': power, 'Energy (kWh)': energy
        })

if len(tier_list) > 0:
    df_halls = pd.DataFrame(tier_list)
    theoretical_energy = df_halls['Energy (kWh)'].sum()
    design_storage = theoretical_energy * x_factor
    available_solar = solar_data[selected_month]
    solar_utilization = (design_storage / available_solar) * 100

    # --- DASHBOARD LAYOUT ---
    st.title("☀️ IIT Kharagpur: Solar-to-Cooling Framework")
    st.markdown("### Operational Mode: " + sched_mode)

    # Metrics Section
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Daily Solar Yield", "{:,.0f} kWh".format(available_solar))
    m2.metric("Design Storage Capacity", "{:,.1f} kWh".format(design_storage))
    m3.metric("System Efficiency (CoP)", "{:.1f}".format(cop_value))
    m4.metric("Solar Utilization", "{:.1f}%".format(solar_utilization))

    st.markdown("---") 

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Configured Cooling Schedule")
        fig = px.bar(df_halls, x="Duration", y="Hostel", color="Tier" if sched_mode == "Auto-Tiered (2-3-4 hrs)" else None,
                     orientation='h',
                     title="Cooling Window Lengths",
                     category_orders={"Tier": ["Small", "Medium", "Large", "Manual"]})
        fig.update_layout(xaxis_title="Duration (Hours)", yaxis_title="Hostel Name")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Active Load Distribution")
        pie_fig = px.pie(df_halls, values='Power (kW)', names='Hostel' if sched_mode == "Manual Override (0-24 hrs)" else 'Tier',
                         title="Power Demand Distribution")
        st.plotly_chart(pie_fig, use_container_width=True)

    # Hybrid Power Supply Analysis [cite: 804]
    st.subheader("Power Supply Analysis")
    total_inst_power = df_halls['Power (kW)'].sum()
    p_solar_discharge = design_storage / (df_halls['Duration'].max() if df_halls['Duration'].max() > 0 else 1)
    p_grid_supplement = total_inst_power - p_solar_discharge 

    supply_fig = go.Figure(data=[
        go.Bar(name='Solar-Storage Contribution', x=['Power Blending'], y=[p_solar_discharge]),
        go.Bar(name='Grid Supplement', x=['Power Blending'], y=[max(0, p_grid_supplement)])
    ])
    supply_fig.update_layout(barmode='stack', title="Instantaneous Power Source Blend (kW)")
    st.plotly_chart(supply_fig, use_container_width=True)

    with st.expander("Detailed Dispatch Data"):
        st.write(f"**Calculated System Power Rating:** {dynamic_kw_per_tr:.3f} kW/TR")
        st.dataframe(df_halls.sort_values(by='Power (kW)', ascending=False))
else:
    st.warning("Please select at least one hostel to begin the simulation.")

st.caption("Final Outcome: Dynamic multi-modal software framework for equitable campus cooling.")