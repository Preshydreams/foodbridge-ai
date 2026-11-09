import streamlit as st
import pandas as pd
import plotly.express as px
import pulp
from io import BytesIO

st.set_page_config(page_title="FOODBRIDGE AI", page_icon="ðŸ¥«", layout="wide")

# ---------- Styling ----------
st.markdown(""" <style> .block-container {padding-top: 1.4rem; padding-bottom: 2rem;} [data-testid="stMetric"] {background: #f5f8f6; border: 1px solid #e2ebe5; padding: 14px; border-radius: 12px;} section[data-testid="stSidebar"] {background: #f4f7f5;} </style> """, unsafe_allow_html=True)

st.title("ðŸ¥« FOODBRIDGE AI")
st.caption("Intelligent food rescue â€¢ Fair allocation â€¢ Transparent decisions")
st.info("A human-supervised decision-support prototype for allocating donated food. Always verify food safety and operational feasibility before dispatch.")

# ---------- Sample scenario ----------
def sample_data():
    donations = pd.DataFrame([
        {"food": "Rice", "available_kg": 500, "days_to_expiry": 180},
        {"food": "Beans", "available_kg": 260, "days_to_expiry": 120},
        {"food": "Vegetables", "available_kg": 180, "days_to_expiry": 3},
        {"food": "Tomatoes", "available_kg": 140, "days_to_expiry": 2},
    ])
    centres = pd.DataFrame([
        {"centre": "Makwari Community Hub", "capacity_kg": 360, "priority": 1.30},
        {"centre": "Riverside Relief Centre", "capacity_kg": 300, "priority": 1.15},
        {"centre": "Central Food Support", "capacity_kg": 420, "priority": 1.00},
    ])
    demand = pd.DataFrame([
        {"centre": "Makwari Community Hub", "food": "Rice", "demand_kg": 180, "distance_km": 8},
        {"centre": "Makwari Community Hub", "food": "Beans", "demand_kg": 100, "distance_km": 8},
        {"centre": "Makwari Community Hub", "food": "Vegetables", "demand_kg": 70, "distance_km": 8},
        {"centre": "Makwari Community Hub", "food": "Tomatoes", "demand_kg": 45, "distance_km": 8},
        {"centre": "Riverside Relief Centre", "food": "Rice", "demand_kg": 150, "distance_km": 14},
        {"centre": "Riverside Relief Centre", "food": "Beans", "demand_kg": 90, "distance_km": 14},
        {"centre": "Riverside Relief Centre", "food": "Vegetables", "demand_kg": 60, "distance_km": 14},
        {"centre": "Riverside Relief Centre", "food": "Tomatoes", "demand_kg": 55, "distance_km": 14},
        {"centre": "Central Food Support", "food": "Rice", "demand_kg": 220, "distance_km": 5},
        {"centre": "Central Food Support", "food": "Beans", "demand_kg": 120, "distance_km": 5},
        {"centre": "Central Food Support", "food": "Vegetables", "demand_kg": 80, "distance_km": 5},
        {"centre": "Central Food Support", "food": "Tomatoes", "demand_kg": 70, "distance_km": 5},
    ])
    return donations, centres, demand

don0, cen0, dem0 = sample_data()

# ---------- Sidebar ----------
with st.sidebar:
    st.header("Control centre")
    page = st.radio("Navigate", [
        "Overview dashboard", "Data management", "AI allocation",
        "Performance analysis", "Expiry & waste risk",
        "Transport analytics", "What-if simulator", "Methodology"
    ])
    st.divider()
    st.download_button("Download sample donations", don0.to_csv(index=False), "sample_donations.csv", "text/csv", use_container_width=True)
    st.download_button("Download sample centres", cen0.to_csv(index=False), "sample_centres.csv", "text/csv", use_container_width=True)
    st.download_button("Download sample demand", dem0.to_csv(index=False), "sample_demand.csv", "text/csv", use_container_width=True)
    cost_weight = st.slider("Transport penalty", 0.0, 5.0, 0.8, 0.1)
    expiry_window = st.slider("Urgency window (days)", 1, 30, 7)

# ---------- Input data ----------
st.subheader("Input data")
a, b, c = st.columns(3)
with a:
    up_don = st.file_uploader("Donations CSV", type="csv", key="donations_upload")
with b:
    up_cen = st.file_uploader("Distribution centres CSV", type="csv", key="centres_upload")
with c:
    up_dem = st.file_uploader("Demand & distance CSV", type="csv", key="demand_upload")

try:
    donations = pd.read_csv(up_don) if up_don else don0.copy()
    centres = pd.read_csv(up_cen) if up_cen else cen0.copy()
    demand = pd.read_csv(up_dem) if up_dem else dem0.copy()
except Exception as exc:
    st.error(f"Could not read CSV: {exc}")
    st.stop()

required = {
    "Donations": (donations, {"food", "available_kg", "days_to_expiry"}),
    "Centres": (centres, {"centre", "capacity_kg", "priority"}),
    "Demand": (demand, {"centre", "food", "demand_kg", "distance_km"}),
}
for label, (df, columns) in required.items():
    missing = columns - set(df.columns)
    if missing:
        st.error(f"{label} CSV is missing columns: {', '.join(sorted(missing))}")
        st.stop()

for df, cols in [
    (donations, ["available_kg", "days_to_expiry"]),
    (centres, ["capacity_kg", "priority"]),
    (demand, ["demand_kg", "distance_km"])
]:
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if df[cols].isna().any().any():
        st.error(f"Invalid or blank numeric values in: {', '.join(cols)}")
        st.stop()

if (donations["available_kg"] < 0).any() or (centres["capacity_kg"] < 0).any() or (demand[["demand_kg", "distance_km"]] < 0).any().any():
    st.error("Supply, capacity, demand and distance cannot be negative.")
    st.stop()
if (centres["priority"] <= 0).any():
    st.error("Every centre priority must be greater than zero.")
    st.stop()

donations["food"] = donations["food"].astype(str).str.strip()
centres["centre"] = centres["centre"].astype(str).str.strip()
demand["food"] = demand["food"].astype(str).str.strip()
demand["centre"] = demand["centre"].astype(str).str.strip()

with st.expander("Review and edit input tables"):
    st.markdown("**Donations**")
    donations = st.data_editor(donations, use_container_width=True, num_rows="dynamic", key="don_editor")
    st.markdown("**Distribution centres**")
    centres = st.data_editor(centres, use_container_width=True, num_rows="dynamic", key="cen_editor")
    st.markdown("**Demand and distance**")
    demand = st.data_editor(demand, use_container_width=True, num_rows="dynamic", key="dem_editor")

if donations.empty or centres.empty or demand.empty:
    st.warning("Provide at least one donation, one centre and one demand row.")
    st.stop()

# Aggregate repeated entries safely.
donations = donations.groupby("food", as_index=False).agg(available_kg=("available_kg", "sum"), days_to_expiry=("days_to_expiry", "min"))
centres = centres.groupby("centre", as_index=False).agg(capacity_kg=("capacity_kg", "sum"), priority=("priority", "mean"))
demand = demand.groupby(["centre", "food"], as_index=False).agg(demand_kg=("demand_kg", "sum"), distance_km=("distance_km", "mean"))

food_set, centre_set = set(donations.food), set(centres.centre)
unmatched = demand[~demand.food.isin(food_set) | ~demand.centre.isin(centre_set)]
demand = demand[demand.food.isin(food_set) & demand.centre.isin(centre_set)].copy()
if demand.empty:
    st.error("No demand rows match the uploaded food and centre names.")
    st.stop()
if not unmatched.empty:
    st.warning(f"{len(unmatched)} demand row(s) were ignored because their food or centre name did not match the input tables.")

eligible = donations[donations.days_to_expiry > 0].copy()
expired = donations[donations.days_to_expiry <= 0].copy()

# ---------- Optimisation function ----------
def solve_allocation(supply_scale=1.0, demand_scale=1.0, capacity_scale=1.0):
    if eligible.empty:
        return None, "No unexpired food is available."
    supply = {r.food: float(r.available_kg) * supply_scale for r in eligible.itertuples()}
    expiry = {r.food: float(r.days_to_expiry) for r in eligible.itertuples()}
    caps = {r.centre: float(r.capacity_kg) * capacity_scale for r in centres.itertuples()}
    priorities = {r.centre: float(r.priority) for r in centres.itertuples()}
    dem = {(r.food, r.centre): float(r.demand_kg) * demand_scale for r in demand.itertuples()}
    dist = {(r.food, r.centre): float(r.distance_km) for r in demand.itertuples()}
    keys = [(f, c) for (f, c) in dem if f in supply]
    if not keys:
        return None, "No matching eligible food-demand combinations."
    model = pulp.LpProblem("FoodBridge_Allocation", pulp.LpMaximize)
    x = {key: pulp.LpVariable(f"kg_{i}", lowBound=0) for i, key in enumerate(keys)}
    for f in supply:
        model += pulp.lpSum(x[(ff, c)] for ff, c in keys if ff == f) <= supply[f]
    for centre in caps:
        model += pulp.lpSum(x[(f, cc)] for f, cc in keys if cc == centre) <= caps[centre]
    for f, centre in keys:
        model += x[(f, centre)] <= dem[(f, centre)]
    # Fairness is calculated using total centre demand, not a separate ratio per food.
    z = pulp.LpVariable("minimum_centre_fulfilment", lowBound=0, upBound=1)
    for centre in caps:
        centre_demand = sum(v for (f, cc), v in dem.items() if cc == centre)
        if centre_demand > 0:
            model += pulp.lpSum(x[(f, cc)] for f, cc in keys if cc == centre) >= z * centre_demand
    objective = [10000 * z]
    for f, centre in keys:
        days = expiry[f]
        urgency = 1 + max(0, expiry_window - days) / max(1, expiry_window) * 2
        benefit = 10 * urgency * priorities[centre] - cost_weight * dist[(f, centre)]
        objective.append(benefit * x[(f, centre)])
    model += pulp.lpSum(objective)
    status_code = model.solve(pulp.PULP_CBC_CMD(msg=False))
    status = pulp.LpStatus[status_code]
    if status not in ("Optimal", "Feasible"):
        return None, f"Solver status: {status}"
    rows = []
    for (food, centre), variable in x.items():
        qty = max(0.0, float(pulp.value(variable) or 0))
        if qty > 0.001:
            rows.append({
                "Food": food, "Distribution centre": centre,
                "Allocated (kg)": qty, "Distance (km)": dist[(food, centre)],
                "Days to expiry": int(expiry[food]), "Centre priority": priorities[centre]
            })
    return (pd.DataFrame(rows), float(pulp.value(z) or 0), status), None

solution, error = solve_allocation()
if error:
    st.error(error)
    st.stop()
result, min_fulfilment, solver_status = solution
total_supply = float(eligible.available_kg.sum())
total_demand = float(demand.demand_kg.sum())
allocated = float(result["Allocated (kg)"].sum()) if not result.empty else 0.0
fulfilment = allocated / total_demand * 100 if total_demand else 0.0
remaining = max(0.0, total_supply - allocated)
transport = float((result["Allocated (kg)"] * result["Distance (km)"]).sum()) if not result.empty else 0.0

# Traditional benchmark: deterministic first-come-first-served in input demand order.
base_supply = eligible.set_index("food").available_kg.to_dict()
base_capacity = centres.set_index("centre").capacity_kg.to_dict()
baseline_rows = []
for row in demand.itertuples():
    food, centre = row.food, row.centre
    if food not in base_supply or centre not in base_capacity:
        continue
    qty = min(float(row.demand_kg), base_supply[food], base_capacity[centre])
    if qty > 0:
        baseline_rows.append({"Food": food, "Distribution centre": centre, "Allocated (kg)": qty, "Distance (km)": float(row.distance_km)})
        base_supply[food] -= qty
        base_capacity[centre] -= qty
baseline = pd.DataFrame(baseline_rows)
base_total = float(baseline["Allocated (kg)"].sum()) if not baseline.empty else 0.0
base_transport = float((baseline["Allocated (kg)"] * baseline["Distance (km)"]).sum()) if not baseline.empty else 0.0
base_fulfilment = base_total / total_demand * 100 if total_demand else 0.0

# ---------- Pages ----------
if page == "Overview dashboard":
    st.header("Executive overview")
    st.caption("Live metrics calculated from the currently selected input datasets.")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Donated food available", f"{total_supply:,.0f} kg")
    m2.metric("Food allocated", f"{allocated:,.1f} kg")
    m3.metric("Demand fulfilled", f"{fulfilment:.1f}%")
    m4.metric("Unallocated usable food", f"{remaining:,.1f} kg")
    m5, m6, m7 = st.columns(3)
    m5.metric("Distribution centres", f"{len(centres):,}")
    m6.metric("Food types", f"{len(donations):,}")
    m7.metric("Transport load", f"{transport:,.0f} kgÂ·km")
    left, right = st.columns(2)
    with left:
        st.plotly_chart(px.pie(donations, names="food", values="available_kg", title="Donated food mix"), use_container_width=True)
    with right:
        centre_demand = demand.groupby("centre", as_index=False).demand_kg.sum()
        centre_alloc = result.groupby("Distribution centre", as_index=False)["Allocated (kg)"].sum()
        chart = centre_demand.merge(centre_alloc, left_on="centre", right_on="Distribution centre", how="left").fillna({"Allocated (kg)": 0})
        chart = chart.rename(columns={"centre": "Centre", "demand_kg": "Demand (kg)"})
        st.plotly_chart(px.bar(chart, x="Centre", y=["Demand (kg)", "Allocated (kg)"], barmode="group", title="Demand versus recommended allocation"), use_container_width=True)
    st.subheader("Operational alerts")
    if not expired.empty:
        st.error("Expired stock excluded: " + ", ".join(expired.food.astype(str)))
    urgent = eligible[eligible.days_to_expiry <= expiry_window]
    if not urgent.empty:
        st.warning("Urgent expiry window: " + ", ".join(urgent.food.astype(str)))
    if remaining > 0.01:
        st.info(f"{remaining:,.1f} kg of unexpired supply remains unallocated. Check demand, capacity and route constraints.")
    st.success(f"Optimisation solver status: {solver_status}. Minimum centre fulfilment ratio: {min_fulfilment*100:.1f}%.")

elif page == "Data management":
    st.header("Data management & quality")
    st.write("Review the active datasets below. Use the upload controls above to replace any sample dataset.")
    for label, df in [("Donations", donations), ("Distribution centres", centres), ("Demand and distance", demand)]:
        st.subheader(label)
        st.dataframe(df, use_container_width=True, hide_index=True)
    q1, q2, q3 = st.columns(3)
    q1.metric("Donation rows", len(donations))
    q2.metric("Centre rows", len(centres))
    q3.metric("Demand rows", len(demand))
    st.caption("Validation checks required columns, numeric values, non-negative quantities, positive centre priorities and matching food/centre names.")

elif page == "AI allocation":
    st.header("Recommended allocation plan")
    st.metric("Solver status", solver_status)
    st.metric("Minimum centre fulfilment", f"{min_fulfilment*100:.1f}%")
    st.dataframe(result.round(2), use_container_width=True, hide_index=True)
    st.download_button("Download allocation CSV", result.to_csv(index=False), "foodbridge_allocation_plan.csv", "text/csv")
    st.download_button("Download full input demand CSV", demand.to_csv(index=False), "foodbridge_demand_input.csv", "text/csv")

elif page == "Performance analysis":
    st.header("Traditional method vs FOODBRIDGE AI")
    comparison = pd.DataFrame({
        "Metric": ["Food allocated (kg)", "Demand fulfilled (%)", "Transport load (kgÂ·km)"],
        "Traditional": [base_total, base_fulfilment, base_transport],
        "FOODBRIDGE AI": [allocated, fulfilment, transport]
    })
    st.dataframe(comparison.round(1), use_container_width=True, hide_index=True)
    p1, p2, p3 = st.columns(3)
    p1.metric("Additional food allocated", f"{allocated-base_total:,.1f} kg")
    p2.metric("Fulfilment change", f"{fulfilment-base_fulfilment:+.1f} pp")
    p3.metric("Transport load change", f"{transport-base_transport:+,.1f} kgÂ·km")
    st.plotly_chart(px.bar(comparison, x="Metric", y=["Traditional", "FOODBRIDGE AI"], barmode="group", title="Benchmark comparison"), use_container_width=True)
    st.caption("The traditional benchmark is a deterministic first-come-first-served baseline using the same supply, demand and centre-capacity limits. It is not a measured real-world control group.")
    if transport > base_transport:
        st.warning("The AI allocation increases transport load relative to this baseline. Treat this as a trade-off to investigate, not an efficiency improvement.")
    else:
        st.success("The AI allocation has a lower transport load than this baseline in the current scenario.")

elif page == "Expiry & waste risk":
    st.header("Expiry and waste-risk monitoring")
    st.caption("Expiry urgency is a prioritisation signal only. It does not establish that food is safe to consume.")
    expiry_view = donations.copy()
    expiry_view["Status"] = expiry_view.days_to_expiry.apply(lambda d: "Expired â€” exclude" if d <= 0 else ("Urgent" if d <= expiry_window else "Within shelf life"))
    st.dataframe(expiry_view.sort_values("days_to_expiry"), use_container_width=True, hide_index=True)
    st.plotly_chart(px.bar(expiry_view, x="food", y="available_kg", color="Status", title="Available quantity by expiry status"), use_container_width=True)
    if not expired.empty:
        st.error("Expired food is excluded from optimisation: " + ", ".join(expired.food.astype(str)))
    if not eligible[eligible.days_to_expiry <= expiry_window].empty:
        st.warning("Prioritise operational review and timely dispatch for near-expiry items.")

elif page == "Transport analytics":
    st.header("Transport analytics")
    if result.empty:
        st.info("No allocation is currently recommended.")
    else:
        route = result.groupby("Distribution centre", as_index=False).apply(
            lambda g: pd.Series({
                "Allocated (kg)": g["Allocated (kg)"].sum(),
                "Transport load (kgÂ·km)": (g["Allocated (kg)"] * g["Distance (km)"]).sum(),
                "Average distance (km)": (g["Allocated (kg)"] * g["Distance (km)"]).sum() / g["Allocated (kg)"].sum()
            }), include_groups=False
        ).reset_index(drop=True)
        st.dataframe(route.round(2), use_container_width=True, hide_index=True)
        st.plotly_chart(px.bar(route, x="Distribution centre", y="Transport load (kgÂ·km)", title="Transport load by centre"), use_container_width=True)
        st.metric("Total transport load", f"{transport:,.1f} kgÂ·km")
        st.caption("Transport load is allocated kilograms multiplied by the supplied one-way distance. It is a proxy, not a vehicle routing or monetary-cost calculation.")

elif page == "What-if simulator":
    st.header("What-if scenario simulator")
    st.write("Change the scenario assumptions to see how the allocation responds. These are scenario calculations, not forecasts.")
    s1, s2, s3 = st.columns(3)
    with s1:
        supply_change = st.slider("Donation supply change", -50, 100, 0, 5)
    with s2:
        demand_change = st.slider("Demand change", -50, 100, 0, 5)
    with s3:
        capacity_change = st.slider("Centre capacity change", -50, 100, 0, 5)
    scenario, sim_error = solve_allocation(1+supply_change/100, 1+demand_change/100, 1+capacity_change/100)
    if sim_error:
        st.error(sim_error)
    else:
        sim_result, sim_z, sim_status = scenario
        sim_alloc = float(sim_result["Allocated (kg)"].sum()) if not sim_result.empty else 0
        sim_demand = total_demand * (1+demand_change/100)
        sim_rate = sim_alloc / sim_demand * 100 if sim_demand else 0
        x1, x2, x3 = st.columns(3)
        x1.metric("Scenario allocated", f"{sim_alloc:,.1f} kg", f"{sim_alloc-allocated:+,.1f} kg vs current")
        x2.metric("Scenario demand fulfilment", f"{sim_rate:.1f}%")
        x3.metric("Minimum centre fulfilment", f"{sim_z*100:.1f}%")
        st.dataframe(sim_result.round(2), use_container_width=True, hide_index=True)
        st.caption(f"Scenario solver status: {sim_status}")

elif page == "Methodology":
    st.header("Methodology, assumptions & limitations")
    st.markdown(""" **Optimisation approach** - Linear programming using PuLP. - Food supply, centre storage capacity and centre-food demand are hard constraints. - A max-min variable seeks to improve the lowest centre-level demand fulfilment ratio. - The objective then rewards expiry urgency and centre priority while penalising distance. **Benchmark** - The baseline allocates in the supplied demand-row order (first-come-first-served). - Both approaches use the same input supply, demand and capacity constraints. - Results depend on the order of baseline demand rows and the selected objective weights. **Important limitations** - This prototype uses supplied distances; it does not calculate road routes, vehicle capacity, traffic or monetary transport costs. - Expiry dates are represented as days-to-expiry and do not replace food-safety inspection. - Fairness is measured at centre level; population size, vulnerability and dietary requirements are not yet represented. - Sample data is illustrative and must not be presented as real-world impact. - The model requires field validation with food-bank operators before operational use. """)

st.divider()
st.caption("FOODBRIDGE AI â€¢ DataNova 2026 prototype â€¢ Transparent, human-supervised decision support")
