import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURATION & DATA ---
st.set_page_config(page_title="IITKGP Solar Cooling Framework", layout="wide")

# Solar Data (kWh/day) from Phase 1
solar_data = {
    'January': 14947.80, 'February': 18678.17, 'March': 19303.15, 'April': 20573.28,
    'May': 20605.78, 'June': 17866.55, 'July': 15839.19, 'August': 14271.71,
    'September': 15995.65, 'October': 15879.08, 'November': 16283.02, 'December': 13876.31
}

# Hostel Database from Phase 4
hostels = {
    'Azad': 424, 'BC Roy': 162, 'BRH': 1390, 'Gokhale': 54, 'HJB': 163,
    'JCB': 262, 'Nehru': 331, 'LBS': 650, 'LLR': 334, 'MMM': 789,
    'MS': 397, 'MT': 164, 'SNVH': 81, 'Patel': 328, 'RK': 421,
    'RLB': 250, 'RP': 489, 'SNIG': 249, 'VS': 335, 'SBP-1': 450, 'SBP-2': 450
}

# Engineering Constants
TR_PER_ROOM = 0.6
KW_PER_TR = 1.1
KW_PER_ROOM = TR_PER_ROOM * KW_PER_TR

# --- SIDEBAR INPUTS ---
st.sidebar.header("Control Panel")
selected_month = st.sidebar.selectbox("Select Scenario Month", list(solar_data.keys()))
x_factor = st.sidebar.slider("Storage Scaling Factor (X%)", 0.1, 1.0, 0.6, 0.05)

# NEW FEATURE: Selective Hostel Dispatch
st.sidebar.subheader("Hostel Selection")
all_hostels = sorted(list(hostels.keys()))
active_hostels = st.sidebar.multiselect(
    "Select Hostels to Provide AC Supply",
    options=all_hostels,
    default=all_hostels
)

# --- CALCULATIONS ---
tier_list = []
for name, rooms in hostels.items():
    # Only process hostels that are selected in the multiselect
    if name in active_hostels:
        if rooms < 270:
            tier, duration = "Small", 4
        elif 270 <= rooms <= 600:
            tier, duration = "Medium", 3
        else:
            tier, duration = "Large", 2
        
        power = rooms * KW_PER_ROOM
        energy = power * duration
        tier_list.append({'Hostel': name, 'Rooms': rooms, 'Tier': tier, 
                          'Duration': duration, 'Power (kW)': power, 'Energy (kWh)': energy})

# Check if any hostels are selected to avoid empty dataframe errors
if len(tier_list) > 0:
    df_halls = pd.DataFrame(tier_list)

    theoretical_energy = df_halls['Energy (kWh)'].sum()
    design_storage = theoretical_energy * x_factor
    available_solar = solar_data[selected_month]
    solar_utilization = (design_storage / available_solar) * 100

    # --- DASHBOARD LAYOUT ---
    st.title("☀️ IIT Kharagpur: Solar-to-Cooling Framework")
    st.markdown("### Data-Driven Scheduling with Selective Dispatch")

    # Top Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Daily Solar Yield", "{:,.0f} kWh".format(available_solar))
    m2.metric("Design Storage Capacity", "{:,.1f} kWh".format(design_storage))
    m3.metric("Storage Scaling (X)", "{:.0f}%".format(x_factor*100))
    m4.metric("Solar Utilization", "{:.1f}%".format(solar_utilization))

    st.markdown("---")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Active Cooling Schedule")
        fig = px.bar(df_halls, x="Duration", y="Hostel", color="Tier",
                     orientation='h',
                     title="Hours of Supply (Starting from 12 AM)",
                     category_orders={"Tier": ["Small", "Medium", "Large"]})
        fig.update_layout(xaxis_title="Hours", yaxis_title="Hostel Name")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Active Load Distribution")
        pie_fig = px.pie(df_halls, values='Power (kW)', names='Tier', hole=0.4,
                         title="Power Demand of Selected Halls")
        st.plotly_chart(pie_fig, use_container_width=True)

    # Grid vs Storage Analysis
    st.subheader("Power Supply Analysis")
    p_solar = design_storage / 4 
    p_grid = (df_halls['Power (kW)'].sum()) - p_solar 

    supply_fig = go.Figure(data=[
        go.Bar(name='Solar-Storage Contribution', x=['Power Blending'], y=[p_solar]),
        go.Bar(name='Grid Supplement', x=['Power Blending'], y=[max(0, p_grid)])
    ])
    supply_fig.update_layout(barmode='stack', title="Instantaneous Power Source for Selected Load (kW)")
    st.plotly_chart(supply_fig, use_container_width=True)

    with st.expander("View Active Hostel Stats"):
        st.dataframe(df_halls.sort_values(by='Rooms', ascending=False))

else:
    st.warning("Please select at least one hostel from the sidebar to view the analysis.")

st.caption("Final Outcome: Framework for equitable cooling with manual dispatch control.")