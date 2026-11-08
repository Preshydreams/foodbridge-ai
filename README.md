# FoodBridge AI

A prototype for the DataNova 2026 Food Bank Resource Allocation Optimization problem.

## What it does
- Allocates donated food across distribution centres.
- Respects available supply, centre capacity and food-specific demand.
- Gives extra weight to food nearing its expiry date (but excludes already-expired food).
- Uses a max-min fairness constraint to improve the minimum demand-fulfilment ratio across centres.
- Penalises longer transport distances.
- Shows a recommended allocation table and charts.
- Supports CSV uploads and downloadable allocation plans.

## Run locally
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy free with Streamlit Community Cloud
1. Create a public GitHub repository.
2. Upload `app.py` and `requirements.txt`.
3. Go to https://share.streamlit.io/ and connect GitHub.
4. Choose the repository and `app.py` as the main file.
5. Deploy and test the public link in a private/incognito browser.

## CSV formats

### donations.csv
Required columns: `food, available_kg, days_to_expiry`

### centres.csv
Required columns: `centre, capacity_kg, priority`

### demand.csv
Required columns: `centre, food, demand_kg, distance_km`

Names in the `food` and `centre` columns must match across files.

## Important limitations
- Sample data is synthetic and illustrative.
- Distance is currently a supplied road-distance estimate, not live routing.
- The prototype uses a linear-programming objective; weights are tunable and should be calibrated with food-bank operators.
- The model does not determine whether food is safe to distribute. Expired food is excluded; food-safety decisions remain with qualified staff.
- This tool supports human decision-making and does not autonomously dispatch food.

## Validation plan for the competition
1. Run a baseline allocation (e.g. allocate in input order) on the same test scenarios.
2. Compare total demand fulfilled, minimum centre fulfilment ratio, transport load (kg·km), and unallocated unexpired supply.
3. Test scarcity, surplus, capacity bottlenecks, and near-expiry scenarios.
4. Report only measured results from reproducible runs.
