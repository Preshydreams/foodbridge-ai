import streamlit as st
import pandas as pd
import plotly.express as px
import pulp
from io import StringIO

st.set_page_config(page_title="FoodBridge AI", page_icon="🥫", layout="wide")

st.title("🥫 FoodBridge AI")
st.caption("Data-driven food rescue and allocation | Prototype for DataNova 2026")

st.info(
    "Decision-support prototype: recommends how to allocate donated food across "
    "community distribution centres while considering demand, expiry urgency, "
    "centre capacity and transport distance. It does not replace food-safety checks "
    "or human decisions."
)

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

with st.sidebar:
    st.header("Scenario controls")
    st.write("Start with the sample scenario or upload your own CSV files.")
    st.download_button("Download donations CSV", don0.to_csv(index=False), "sample_donations.csv", "text/csv")
    st.download_button("Download centres CSV", cen0.to_csv(index=False), "sample_centres.csv", "text/csv")
    st.download_button("Download demand CSV", dem0.to_csv(index=False), "sample_demand.csv", "text/csv")
    st.divider()
    cost_weight = st.slider("Transport cost importance", 0.0, 5.0, 0.8, 0.1)
    expiry_window = st.slider("Urgent expiry window (days)", 1, 30, 7)

st.subheader("1. Input data")
c1, c2, c3 = st.columns(3)
with c1:
    up_don = st.file_uploader("Donations CSV", type=["csv"], key="don")
with c2:
    up_cen = st.file_uploader("Distribution centres CSV", type=["csv"], key="cen")
with c3:
    up_dem = st.file_uploader("Demand and distance CSV", type=["csv"], key="dem")

try:
    donations = pd.read_csv(up_don) if up_don else don0.copy()
    centres = pd.read_csv(up_cen) if up_cen else cen0.copy()
    demand = pd.read_csv(up_dem) if up_dem else dem0.copy()
except Exception as e:
    st.error(f"Could not read uploaded CSV: {e}")
    st.stop()

required = {
    "donations": (donations, {"food", "available_kg", "days_to_expiry"}),
    "centres": (centres, {"centre", "capacity_kg", "priority"}),
    "demand": (demand, {"centre", "food", "demand_kg", "distance_km"}),
}
errors = []
for name, (df, cols) in required.items():
    missing = cols - set(df.columns)
    if missing:
        errors.append(f"{name}: missing columns {', '.join(sorted(missing))}")
if errors:
    for e in errors:
        st.error(e)
    st.stop()

for df, cols in [(donations, ["available_kg", "days_to_expiry"]),
                 (centres, ["capacity_kg", "priority"]),
                 (demand, ["demand_kg", "distance_km"])]:
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if df[cols].isna().any().any():
        st.error(f"Numeric input contains blank or invalid values in: {', '.join(cols)}")
        st.stop()

if (donations["available_kg"] < 0).any() or (centres["capacity_kg"] < 0).any() or (demand[["demand_kg", "distance_km"]] < 0).any().any():
    st.error("Quantities, capacities, demand and distances must be zero or greater.")
    st.stop()
if (centres["priority"] <= 0).any():
    st.error("Centre priority values must be greater than zero.")
    st.stop()

food_set = set(donations["food"].astype(str))
centre_set = set(centres["centre"].astype(str))
demand = demand[demand["food"].astype(str).isin(food_set) & demand["centre"].astype(str).isin(centre_set)].copy()
donations["food"] = donations["food"].astype(str)
centres["centre"] = centres["centre"].astype(str)
demand["food"] = demand["food"].astype(str)
demand["centre"] = demand["centre"].astype(str)

with st.expander("Review or edit your input tables", expanded=False):
    st.markdown("**Donations**")
    donations = st.data_editor(donations, use_container_width=True, num_rows="dynamic", key="edit_don")
    st.markdown("**Distribution centres**")
    centres = st.data_editor(centres, use_container_width=True, num_rows="dynamic", key="edit_cen")
    st.markdown("**Demand and distance**")
    demand = st.data_editor(demand, use_container_width=True, num_rows="dynamic", key="edit_dem")

if donations.empty or centres.empty or demand.empty:
    st.warning("Add at least one donation, one centre and one demand row.")
    st.stop()

# Aggregate duplicate records to keep the optimization model well-defined.
donations = donations.groupby("food", as_index=False).agg(
    available_kg=("available_kg", "sum"),
    days_to_expiry=("days_to_expiry", "min")
)
centres = centres.groupby("centre", as_index=False).agg(
    capacity_kg=("capacity_kg", "sum"),
    priority=("priority", "mean")
)
demand = demand.groupby(["centre", "food"], as_index=False).agg(
    demand_kg=("demand_kg", "sum"),
    distance_km=("distance_km", "mean")
)

# Only food with a positive shelf-life is eligible. Expired lots are excluded.
eligible = donations[donations["days_to_expiry"] > 0].copy()
expired = donations[donations["days_to_expiry"] <= 0].copy()

st.subheader("2. Optimise the distribution plan")
if st.button("⚡ Generate optimal allocation", type="primary", use_container_width=True):
    if eligible.empty:
        st.error("No unexpired food is available to allocate.")
        st.stop()

    model = pulp.LpProblem("FoodBridge_Allocation", pulp.LpMaximize)
    keys = []
    x = {}
    for _, row in demand.iterrows():
        f, c = row["food"], row["centre"]
        if f in set(eligible["food"]):
            key = (f, c)
            keys.append(key)
            x[key] = pulp.LpVariable(f"kg_{len(keys)}", lowBound=0, cat="Continuous")

    if not x:
        st.error("No matching food-demand combinations found. Check the CSV names.")
        st.stop()

    supply_map = eligible.set_index("food")["available_kg"].to_dict()
    expiry_map = eligible.set_index("food")["days_to_expiry"].to_dict()
    cap_map = centres.set_index("centre")["capacity_kg"].to_dict()
    priority_map = centres.set_index("centre")["priority"].to_dict()
    dem_map = {(r["food"], r["centre"]): r["demand_kg"] for _, r in demand.iterrows()}
    dist_map = {(r["food"], r["centre"]): r["distance_km"] for _, r in demand.iterrows()}

    # Each food type cannot exceed donated supply.
    for f in eligible["food"]:
        model += pulp.lpSum(x[(ff, c)] for ff, c in keys if ff == f) <= float(supply_map[f])

    # Each centre cannot receive more than its storage/handling capacity.
    for c in centres["centre"]:
        model += pulp.lpSum(x[(f, cc)] for f, cc in keys if cc == c) <= float(cap_map[c])

    # Never allocate more than a centre's stated demand for a food type.
    for (f, c) in keys:
        model += x[(f, c)] <= float(dem_map[(f, c)])

    # Max-min fairness: raise the minimum demand-fulfilment ratio across centres.
    z = pulp.LpVariable("minimum_fulfilment_ratio", lowBound=0, upBound=1, cat="Continuous")
    for c in centres["centre"]:
        total_demand_c = float(demand.loc[demand["centre"] == c, "demand_kg"].sum())
        if total_demand_c > 0:
            model += pulp.lpSum(x[(f, cc)] for f, cc in keys if cc == c) >= z * total_demand_c

    # Objective: fairness first, then urgent food and priority-weighted fulfilment,
    # while penalising long-distance transport. All quantities are in kilograms.
    terms = [10000 * z]
    for (f, c) in keys:
        days = float(expiry_map[f])
        urgency = 1.0 + max(0, expiry_window - days) / max(1, expiry_window) * 2.0
        priority = float(priority_map[c])
        distance = float(dist_map[(f, c)])
        benefit = (10.0 * urgency * priority) - (cost_weight * distance)
        terms.append(benefit * x[(f, c)])
    model += pulp.lpSum(terms)

    solver = pulp.PULP_CBC_CMD(msg=False)
    status = model.solve(solver)
    if pulp.LpStatus[status] not in ("Optimal", "Feasible"):
        st.error(f"Optimisation did not produce a usable solution: {pulp.LpStatus[status]}")
        st.stop()

    rows = []
    for (f, c), var in x.items():
        qty = max(0.0, float(pulp.value(var) or 0))
        if qty > 0.01:
            rows.append({
                "Food": f, "Distribution centre": c,
                "Allocated (kg)": round(qty, 1),
                "Distance (km)": float(dist_map[(f, c)]),
                "Days to expiry": int(expiry_map[f]),
                "Centre priority": float(priority_map[c])
            })
    result = pd.DataFrame(rows)
    if result.empty:
        st.warning("The model found no allocation. Check that demand matches the available food types.")
        st.stop()

    total_supply = float(eligible["available_kg"].sum())
    total_allocated = float(result["Allocated (kg)"].sum())
    total_demand = float(demand["demand_kg"].sum())
    total_transport = float((result["Allocated (kg)"] * result["Distance (km)"]).sum())
    fulfilment = min(100.0, total_allocated / total_demand * 100) if total_demand else 0
    remaining = max(0.0, total_supply - total_allocated)

    a, b, c, d = st.columns(4)
    a.metric("Food allocated", f"{total_allocated:,.1f} kg")
    b.metric("Demand fulfilled", f"{fulfilment:.1f}%")
    c.metric("Unallocated usable food", f"{remaining:,.1f} kg")
    d.metric("Transport load", f"{total_transport:,.0f} kg·km")

    st.success(f"Optimisation status: {pulp.LpStatus[status]}. Minimum centre fulfilment: {float(pulp.value(z) or 0)*100:.1f}%")

    st.subheader("Recommended allocation")
    st.dataframe(result, use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Download allocation plan",
        result.to_csv(index=False),
        "foodbridge_allocation_plan.csv",
        "text/csv",
        use_container_width=True
    )

    by_centre = result.groupby("Distribution centre", as_index=False)["Allocated (kg)"].sum()
    fig1 = px.bar(by_centre, x="Distribution centre", y="Allocated (kg)",
                  title="Recommended food allocation by centre")
    st.plotly_chart(fig1, use_container_width=True)

    demand_by_centre = demand.groupby("centre", as_index=False)["demand_kg"].sum().rename(columns={"centre":"Distribution centre"})
    served_by_centre = result.groupby("Distribution centre", as_index=False)["Allocated (kg)"].sum()
    compare = demand_by_centre.merge(served_by_centre, on="Distribution centre", how="left").fillna(0)
    compare["Fulfilment (%)"] = (compare["Allocated (kg)"] / compare["demand_kg"].replace(0, pd.NA) * 100).fillna(0).round(1)
    fig2 = px.bar(compare, x="Distribution centre", y=["demand_kg", "Allocated (kg)"],
                  barmode="group", title="Demand versus allocated food")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Decision notes")
    urgent_names = eligible.loc[eligible["days_to_expiry"] <= expiry_window, "food"].tolist()
    if urgent_names:
        st.write("Near-expiry foods considered urgent:", ", ".join(urgent_names))
    else:
        st.write("No eligible food is inside the selected urgent-expiry window.")
    if not expired.empty:
        st.warning("Expired food was excluded from the allocation model: " +
                   ", ".join(expired["food"].astype(str).tolist()) +
                   ". A human food-safety officer must decide its safe disposal.")
    st.caption(
        "Method: linear programming with supply, demand and centre-capacity constraints; "
        "a max-min service fairness variable; urgency/priority rewards; and a distance penalty. "
        "This is a prototype using the supplied scenario data, not a field-validated deployment."
    )
else:
    st.markdown(
        "**How to use:** review the sample data, optionally upload your own CSVs, "
        "then click **Generate optimal allocation**. The sample figures are illustrative, "
        "not real-world measurements."
    )

st.divider()
st.caption("FoodBridge AI • DataNova 2026 prototype • Built for transparent, human-supervised decisions")
