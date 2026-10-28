# Simulation and Capacity Optimization of a Renewable Microgrid

## Overview

This project presents a time-discrete Python simulation of a simplified renewable microgrid consisting of photovoltaic (PV) generation, wind generation, an electrical load, and a battery energy storage system.

The objective is to investigate the influence of battery capacity on supply reliability and renewable energy curtailment, and to determine an economically favorable storage capacity under simplified cost assumptions.

The model uses synthetic generation and demand profiles over a **30-day simulation period with hourly resolution**.

### Key Features

- **Renewable generation:** Synthetic PV and stochastic wind power profiles.
- **Electricity demand:** Time-dependent load profile with morning and evening demand peaks.
- **Battery storage:** Time-discrete energy balance incorporating charging and discharging efficiencies and storage capacity constraints.
- **Model verification:** Numerical verification of the energy balance at each simulation time step.
- **Parameter study:** Investigation of battery capacity effects on energy supply reliability and renewable energy curtailment.
- **Economic optimization:** Minimization of battery capacity costs and costs associated with unserved energy using `scipy.optimize.minimize_scalar`.
- **Sensitivity analysis:** Investigation of how the assumed cost of unserved energy influences the economically optimal battery capacity.

## Model Description

The microgrid consists of four main components:

| Component | Description |
|---|---|
| Photovoltaic generation | Simplified daily generation profile with randomized daily weather conditions; rated power of 100 kW |
| Wind generation | Stochastic mean-reverting power model with a rated power of 70 kW |
| Electrical load | Constant base load of 35 kW combined with Gaussian-shaped morning and evening demand peaks |
| Battery storage | Energy storage with a charging and discharging efficiency of 95%, subject to capacity constraints |

The system is simulated with a fixed time step of **1 hour**.

At each time step, the difference between renewable generation and electricity demand determines whether the battery is charged or discharged.

When renewable generation exceeds demand and the battery is fully charged, the remaining energy is curtailed. When demand exceeds generation and the battery is depleted, the remaining demand is classified as unserved energy.

The model assumes an islanded microgrid without an external electricity grid connection.
