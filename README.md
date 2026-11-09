FOODBRIDGE AI

Intelligent Food Rescue, Fair Allocation and Waste Reduction

FOODBRIDGE AI is a data-driven decision-support prototype designed to help food banks and community distribution centres allocate donated food more effectively.

It uses optimisation techniques to recommend food distribution based on available supply, centre demand, storage capacity, expiry urgency, transport distance and allocation priorities.

Problem Statement

Food banks often face challenges distributing limited donated food across multiple communities. Poor allocation decisions can lead to:

- Food waste due to approaching expiry dates.
- Uneven distribution between community centres.
- Unmet food demand.
- Unnecessary transportation burdens.
- Difficulty making transparent allocation decisions.

FOODBRIDGE AI addresses these challenges through mathematical optimisation and interactive data analytics.

Proposed Solution

The platform analyses food donations, distribution-centre requirements and available operational information to generate recommended allocation plans.

Its optimisation engine uses linear programming through PuLP to identify allocations that respect supply, demand and storage constraints while considering fairness, urgency and distance.

Key Features

- Interactive dashboard: Overview of allocation performance and key indicators.
- Data management: Review and edit donation, centre and demand datasets.
- AI allocation engine: Generate optimised food distribution recommendations.
- Benchmark comparison: Compare recommendations against a deterministic first-come-first-served baseline.
- Expiry and waste monitoring: Identify food items approaching expiry.
- Transport analytics: Examine allocation-related transport loads and distances.
- What-if simulator: Explore how changes in operational inputs affect recommendations.
- Methodology and transparency: Explain assumptions, constraints and limitations.

Technology Stack

- Python
- Streamlit
- Pandas
- Plotly
- PuLP
- GitHub
- Streamlit Community Cloud

Optimisation Approach

FOODBRIDGE AI formulates food allocation as a linear programming problem.

The model considers:

1. Available food quantities.
2. Distribution-centre demand.
3. Centre storage capacity.
4. Transport distances.
5. Food expiry urgency.
6. Centre allocation priorities.
7. Minimum centre-level demand fulfilment.

The solver identifies an optimal solution for the mathematical formulation and supplied input data.

Benchmarking

The prototype compares its recommended allocation against a deterministic first-come-first-served benchmark.

Both approaches use the same supplied food availability, demand and centre-capacity limits.

The benchmark is illustrative. It is not a measured real-world control group.

Prototype Results

In the current sample scenario, the dashboard reports:

- Additional food allocated: 75.0 kg
- Fulfilment change: +6.0 percentage points

The recommended allocation also increases transport load relative to the benchmark. This trade-off is disclosed rather than presented as a transport efficiency improvement.

These figures are based on the prototype's sample scenario and must not be interpreted as verified real-world impact.

Live Demonstration

FOODBRIDGE AI:
https://foodbridge-ai-hesrm54jbeqnvzykjzvhze.streamlit.app/

Repository

https://github.com/preshydreams/foodbridge-ai

Limitations and Future Development

The current prototype has several limitations:

- It uses supplied distances rather than live road-route calculations.
- It does not currently model vehicle capacity, traffic or actual transport costs.
- Expiry information does not replace food-safety inspection.
- Fairness is measured at distribution-centre level.
- Sample data is illustrative and requires field validation.

Future development could include live route optimisation, vehicle scheduling, food-safety rules, population-based vulnerability measures, real food-bank datasets and integration with food donation networks.

Social Impact

FOODBRIDGE AI aims to support more transparent, responsible and data-informed food distribution decisions.

By helping food banks understand supply, demand, urgency and allocation trade-offs, the project seeks to contribute to reducing avoidable food waste and improving food access.

Author

Chukwunalu Ekule

Project: FOODBRIDGE AI
Competition: DataNova 2026 Global Data-thon
Problem: DN-SI-01 — Food Bank Resource Allocation Optimization
