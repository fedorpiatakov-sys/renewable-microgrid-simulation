import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize_scalar

rng = np.random.default_rng(42)

# Generation and Load Parameters
P_PV_rated = 100                # kW

P_wind_rated = 70               # kW

P_load_morning_peak = 70        # kW
P_load_evening_peak = 90        # kW
P_load_base = 35                # kW
t_load_morning = 1/24*8         # days
t_load_evening = 1/24*19        # days
sigma_morning = 0.05            # days
sigma_evening = 0.08            # days

eta_battery = 0.95              # -

# Economic parameters
c_investment = 250              # €/kWh
lifetime = 10                   # years
interest_rate = 0.05            # 1 / years  
c_unserved_0 = 2                # €/kWh

# Simulation parameters
E_battery_initial = 25         # kWh
battery_capacity = 200         # kWh
C_min = 25                     # kWh
C_max = 2000                   # kWh


# Annualization
annuity_factor = (
    interest_rate * (1 + interest_rate)**lifetime
    / ((1 + interest_rate)**lifetime - 1)
)
c_battery = c_investment * annuity_factor * 30 / 365

# Time
N = 30*24
t = np.arange(N) / 24

# PV Generation [kW]
P_PV_base = P_PV_rated * np.maximum(-np.cos(2*np.pi*t), 0)
weather_daily = rng.uniform(0.3, 1, 30)
weather_hourly = np.repeat(weather_daily, 24)
P_PV = P_PV_base*weather_hourly

# Wind Generation [kW]
wind_distribution = rng.normal(0, 8, N)
P_wind_mean = P_wind_rated/2
alpha = 0.01
P_wind = np.zeros(N)
P_wind[0] = P_wind_mean
for i in range(1, N):
    P_wind[i] = np.clip((P_wind[i-1] + 
                         alpha*(P_wind_mean - P_wind[i-1])
                         + wind_distribution[i]),
                         0, P_wind_rated)

# Load Profile [kW]
load_daily = rng.uniform(0.8, 1.2, 30)
load_hourly = np.repeat(load_daily, 24)
P_load_morning = (P_load_morning_peak - P_load_base)*np.exp(-(t % 1 - t_load_morning)**2/(2*sigma_morning)**2)
P_load_evening = (P_load_evening_peak - P_load_base)*np.exp(-(t % 1 - t_load_evening)**2/(2*sigma_evening)**2)
P_load = P_load_base + (P_load_morning + P_load_evening) * load_hourly

# Energy Balance [kWh]
P_generation = P_PV + P_wind
t_battery = np.arange(N + 1) / 24
delta_t = 1

def simulate_battery(capacity, P_gen, P_load, efficiency, delta_t, E_initial=None):
    if len(P_gen) != len(P_load):
        raise ValueError("Generation and load arrays must have equal lengths.")

    if capacity <= 0:
        raise ValueError("Battery capacity must be positive.")

    if not 0 < efficiency <= 1:
        raise ValueError("Battery efficiency must be between 0 and 1.")

    if E_initial is not None and not 0 <= E_initial <= capacity:
        raise ValueError("Initial energy must be between 0 and battery capacity.")
    
    N = len(P_gen)
    E_battery = np.zeros(N + 1)
    if E_initial is None:
        E_battery[0] = capacity * 0.5
    else:
        E_battery[0] = E_initial
    E_curtailed = np.zeros(N)
    E_unserved = np.zeros(N)
    for i in range(N):
        P_net = P_gen[i] - P_load[i]
        if P_net >= 0:
            E_battery[i+1] = E_battery[i] + P_net*delta_t*efficiency
            if E_battery[i+1] > capacity:
                E_curtailed[i] = (E_battery[i+1] - capacity)/efficiency
                E_battery[i+1] = capacity
        else:
            E_battery[i+1] = E_battery[i] + P_net*delta_t/efficiency
            if E_battery[i+1] < 0:
                E_unserved[i] = -(E_battery[i+1])*efficiency
                E_battery[i+1] = 0
    return E_battery, E_curtailed, E_unserved

E_battery, E_curtailed, E_unserved = simulate_battery(
    battery_capacity, P_generation, P_load, eta_battery, delta_t
    )

# Energy Balance Check [kWh]
E_unserved_tot = np.sum(E_unserved)
E_curtailed_tot = np.sum(E_curtailed)
E_wind_tot = np.sum(P_wind * delta_t)
E_PV_tot = np.sum(P_PV * delta_t)
E_load_tot = np.sum(P_load * delta_t)

def energy_balance_check(E_battery, E_curtailed, E_unserved, P_gen, P_load, efficiency, delta_t):
    E_net = (P_gen - P_load)*delta_t
    delta_E_battery = np.diff(E_battery)

    E_loss = np.where(
        delta_E_battery > 0,
        delta_E_battery * (1 / efficiency - 1),
        delta_E_battery * (efficiency - 1)
    )

    E_balance_residual = -E_net - E_unserved + delta_E_battery + E_curtailed + E_loss
    return np.allclose(E_balance_residual, 0, rtol=0, atol=1e-10)

# Ratios [%]
energy_served_ratio = (E_load_tot - E_unserved_tot) / E_load_tot * 100
shortage_hours_ratio = np.sum(E_unserved > 0) / N * 100
curtailment_ratio = E_curtailed_tot / (E_wind_tot + E_PV_tot) * 100

balance_valid = energy_balance_check(
    E_battery, E_curtailed, E_unserved,
    P_generation, P_load, eta_battery, delta_t
)

print(
    f'SYSTEM PERFORMANCE — {battery_capacity} kWh battery\n'
    f'Energy served: {energy_served_ratio.round(1)}%,\n'
    f'Shortage hours: {shortage_hours_ratio.round(1)}%,\n'
    f'Curtailment: {curtailment_ratio.round(1)}%,\n'
    f'Battery full: {(np.sum(E_battery[1:] == battery_capacity) / N * 100).round(1)}%,\n'
    f'Battery empty: {(np.sum(E_battery[1:] == 0) / N * 100).round(1)}%\n'
    f'Energy balance: {'PASSED' if balance_valid else 'FAILED'}'
    f'\n'
)

# Visualisation
fig1, axes1 = plt.subplots(2, 2, constrained_layout=True)
axes1[0, 0].plot(t, P_PV, label='PV')
axes1[0, 0].plot(t, P_wind, label='Wind')
axes1[0, 0].plot(t, P_load, label='Load')
axes1[0, 0].set_xlabel('Time [day]')
axes1[0, 0].set_ylabel('Power [kW]')
axes1[0, 0].set_xlim(0, 3)

axes1[1, 0].plot(t_battery, E_battery / battery_capacity * 100, color='r')
axes1[1, 0].set_xlim(0, 3)
axes1[1, 0].set_xlabel('Time [day]')
axes1[1, 0].set_ylabel('SOC [%]')

axes1[0, 1].bar(t, E_curtailed, width=1/24, label='Curtailed')
axes1[0, 1].bar(t, -E_unserved, width=1/24, label='Unserved')
axes1[0, 1].set_xlabel('Time [day]')
axes1[0, 1].set_ylabel('Energy [kWh]')
axes1[0, 1].set_xlim(0, 3)

axes1[0, 0].legend()
axes1[0, 1].legend()
axes1[1, 1].axis('off')

# Parameter Study
capacities_study = [50, 100, 200, 400, 800, 1600]
curtailed_ratios_list_50 = []
served_ratios_list_50 = []
energy_balance_check_50 = []
for capacity in capacities_study:
    E_battery_test, E_curtailed_test, E_unserved_test = simulate_battery(
        capacity, P_generation, P_load, eta_battery, delta_t
        )
    curtailed_ratios_list_50.append(np.sum(E_curtailed_test) / (E_PV_tot + E_wind_tot) * 100)
    served_ratios_list_50.append((E_load_tot - np.sum(E_unserved_test)) / E_load_tot * 100)
    energy_balance_check_50.append(energy_balance_check(
        E_battery_test, E_curtailed_test, E_unserved_test, P_generation, P_load, eta_battery, delta_t
        ))
print(f'Energy Balance Check 50%: {np.all(energy_balance_check_50)}')

curtailed_ratios_list_const = []
served_ratios_list_const = []
energy_balance_check_const = []
for capacity in capacities_study:
    E_battery_test, E_curtailed_test, E_unserved_test = simulate_battery(
        capacity, P_generation, P_load, eta_battery, delta_t, E_battery_initial
        )
    curtailed_ratios_list_const.append(np.sum(E_curtailed_test) / (E_PV_tot + E_wind_tot) * 100)
    served_ratios_list_const.append((E_load_tot - np.sum(E_unserved_test)) / E_load_tot * 100)
    energy_balance_check_const.append(energy_balance_check(
        E_battery_test, E_curtailed_test, E_unserved_test, P_generation, P_load, eta_battery, delta_t
        ))
print(f'Energy Balance Check const: {np.all(energy_balance_check_const)}\n')

fig2, axes2 = plt.subplots(1, 2, constrained_layout=True)
axes2[0].plot(capacities_study, curtailed_ratios_list_50, label='Curtailed Ratios 50%')
axes2[0].plot(capacities_study, served_ratios_list_50, label='Served Ratios 50%')
axes2[1].plot(capacities_study, curtailed_ratios_list_const, label='Curtailed Ratios 25 kWh')
axes2[1].plot(capacities_study, served_ratios_list_const, label='Served Ratios 25 kWh')
axes2[0].set_xlabel('Battery Capacity [kWh]')
axes2[0].set_ylabel('Ratio [%]')
axes2[1].set_xlabel('Battery Capacity [kWh]')
axes2[1].set_ylabel('Ratio [%]')
axes2[0].legend()
axes2[1].legend()

# Cost Optimization
def total_cost(capacity, c_unserved):
    E_battery, E_curtailed, E_unserved = simulate_battery(
        capacity, P_generation, P_load, eta_battery, delta_t, E_battery_initial
        )
    E_unserved_tot = np.sum(E_unserved)
    return c_battery * capacity + c_unserved * E_unserved_tot

capacities_optimization = np.linspace(C_min, C_max, 200)
c_unserved_values = [0.5, 1, 2, 5, 10]
optimal_capacities = []
for c in c_unserved_values:
    res = minimize_scalar(
        lambda C: total_cost(C, c),
        bounds=(E_battery_initial, C_max),
        method='bounded'
    )
    optimal_capacities.append(res.x)
    costs = [total_cost(capacity, c) for capacity in capacities_optimization]
    idx = np.argmin(costs)
    print(
        f'Grid minimum for unserved cost = {c}€:',
          capacities_optimization[idx].round(3),
          costs[idx].round(3)
        )
    print(
        f'Optimizer minimum for unserved cost = {c}€:',
          res.x.round(3),
          res.fun.round(3)
        )

res_0 = minimize_scalar(
    lambda C: total_cost(C, c_unserved_0),
    bounds=(C_min, C_max),
    method='bounded'
)
costs_optimization = [total_cost(capacity, c_unserved_0) for capacity in capacities_optimization]

fig3, axes3 = plt.subplots(1, 2, constrained_layout=True)
axes3[0].axvline(res_0.x, linestyle='--', label='Optimized capacity')
axes3[0].plot(capacities_optimization, costs_optimization, label='Cost Curve')
axes3[0].set_xlabel('Battery Capacity [kWh]')
axes3[0].set_ylabel('Total Cost [€ / 30 days]')
axes3[0].legend()

axes3[1].plot(c_unserved_values, optimal_capacities)
axes3[1].set_xlabel('Unserved cost [€ / kWh]')
axes3[1].set_ylabel('Optimal battery capacity [kWh]')
