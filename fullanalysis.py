import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

###############################################################################
# Step 1: Synthetic Data Generation (Load, Tariff, Solar)
###############################################################################
def create_synthetic_data():
    """
    Creates a synthetic half-hourly dataset for a few days with columns:
      - Load_kW
      - Solar_kW
      - TariffRate
    Indexed by DateTime with 30-min frequency.
    """
    # Let's create 3 days of half-hour data: 48 intervals per day = 144 intervals
    rng = pd.date_range("2025-01-01", periods=48*3, freq='30min')
    df = pd.DataFrame(index=rng, columns=['Load_kW','Solar_kW','TariffRate'], dtype=float)

    # 1) Generate random Load
    np.random.seed(42)
    df['Load_kW'] = 500 + 300 * np.random.rand(len(df))  # random load in [500..800] kW

    # 2) Generate a simple solar profile: zero at night, a Gaussian peak midday
    def solar_profile(h):
        if 6 <= h < 18:
            # simple bell curve around noon
            return 1000.0 * np.exp(-0.5*((h-12)/2)**2)
        return 0.0
    df['Solar_kW'] = [solar_profile(ts.hour) for ts in df.index]

    # 3) Tariff: night=0.08, day=0.15, peak=0.25
    def tariff_func(dt):
        if 17 <= dt.hour < 19:
            return 0.25
        elif (8 <= dt.hour < 17) or (19 <= dt.hour < 23):
            return 0.15
        else:
            return 0.08
    df['TariffRate'] = df.index.map(tariff_func)

    return df

###############################################################################
# Step 2: Baseline Scenario (No Solar, No Battery)
###############################################################################
def create_baseline_df(df):
    """
    Baseline scenario: no solar, no battery.
    We assume the entire Load is met by grid, so:
      Grid_Import_kWh = Load_kW * 0.5 (each half-hour = 0.5 hr)
      Cost = Grid_Import_kWh * TariffRate
    """
    # Copy to avoid changing original
    df_base = df.copy()
    # Zero out solar for baseline
    df_base['Solar_kW'] = 0.0

    df_base['Grid_Import_kWh'] = df_base['Load_kW'] * 0.5
    df_base['Cost'] = df_base['Grid_Import_kWh'] * df_base['TariffRate']
    return df_base

###############################################################################
# Step 3: Solar-Only Scenario
###############################################################################
def create_solar_only_df(df):
    """
    Solar-Only scenario (no battery).
    If Solar >= Load, zero grid import; otherwise import the difference.
    """
    df_solar = df.copy()
    df_solar['Grid_Import_kWh'] = 0.0
    df_solar['Cost'] = 0.0

    for i in range(len(df_solar)):
        load_kWh = df_solar.iloc[i]['Load_kW'] * 0.5
        solar_kWh = df_solar.iloc[i]['Solar_kW'] * 0.5
        tariff = df_solar.iloc[i]['TariffRate']

        if solar_kWh >= load_kWh:
            # No grid import needed
            df_solar.iloc[i, df_solar.columns.get_loc('Grid_Import_kWh')] = 0.0
            df_solar.iloc[i, df_solar.columns.get_loc('Cost')] = 0.0
        else:
            # Shortfall
            shortfall = load_kWh - solar_kWh
            df_solar.iloc[i, df_solar.columns.get_loc('Grid_Import_kWh')] = shortfall
            df_solar.iloc[i, df_solar.columns.get_loc('Cost')] = shortfall * tariff

    return df_solar

###############################################################################
# Step 4A: Battery Dispatch - Scenario 1 (Fixed Window)
###############################################################################
def simulate_scenario_1(df, battery_params, dt_hours=0.5):
    """
    - Solar charges battery first, leftover solar meets load.
    - Battery discharges ONLY during 5 PM–7 PM, 
      then continues discharging until 11 PM if still >0 SoC.
    """
    sim_df = df.copy()
    sim_df['SoC'] = 0.0
    sim_df['Grid_Import_kWh'] = 0.0
    sim_df['Grid_Export_kWh'] = 0.0
    sim_df['Cost'] = 0.0

    cap = battery_params['Capacity_kWh']
    max_charge_kW = battery_params['Max_Charge_kW']
    max_discharge_kW = battery_params['Max_Discharge_kW']
    eff = battery_params['RoundTripEff']

    # Convert to kWh per step
    max_charge_kWh = max_charge_kW * dt_hours
    max_discharge_kWh = max_discharge_kW * dt_hours

    soc = 0.0
    for i in range(len(sim_df)):
        row = sim_df.iloc[i]
        hour = row.name.hour
        load_kWh = row['Load_kW'] * dt_hours
        solar_kWh = row['Solar_kW'] * dt_hours
        tariff = row['TariffRate']

        # 1) Charge battery from solar first
        can_accept = cap - soc
        charge = min(solar_kWh, max_charge_kWh, can_accept)
        soc += charge

        leftover_solar = solar_kWh - charge

        # 2) Leftover solar meets load
        if leftover_solar >= load_kWh:
            # Surplus exported if we allow export
            sim_df.iloc[i, sim_df.columns.get_loc('Grid_Export_kWh')] = leftover_solar - load_kWh
        else:
            unmet_load = load_kWh - leftover_solar
            # Condition to discharge battery:
            # - 5..7 PM => definitely discharge
            # - 7..11 PM => if SoC>0, keep discharging
            can_discharge_now = False
            if 17 <= hour < 19:
                can_discharge_now = True
            elif (19 <= hour < 23) and soc > 0:
                can_discharge_now = True

            if can_discharge_now and soc>0:
                # Discharge up to max_discharge_kWh or what's needed
                discharge_possible = min(soc, max_discharge_kWh)
                discharge_out = discharge_possible * eff  # net energy to load
                if discharge_out >= unmet_load:
                    used = unmet_load
                    actual_discharge = used / eff
                    soc -= actual_discharge
                else:
                    used = discharge_out
                    actual_discharge = discharge_possible
                    soc -= actual_discharge
                    still_needed = unmet_load - used
                    sim_df.iloc[i, sim_df.columns.get_loc('Grid_Import_kWh')] = still_needed
                    sim_df.iloc[i, sim_df.columns.get_loc('Cost')] = still_needed * tariff
            else:
                # No battery discharge
                sim_df.iloc[i, sim_df.columns.get_loc('Grid_Import_kWh')] = unmet_load
                sim_df.iloc[i, sim_df.columns.get_loc('Cost')] = unmet_load * tariff

        sim_df.iloc[i, sim_df.columns.get_loc('SoC')] = soc

    return sim_df

###############################################################################
# Step 4B: Battery Dispatch - Scenario 2 (Flexible / Cost-Driven)
###############################################################################
def simulate_scenario_2(df, battery_params, dt_hours=0.5):
    """
    - Solar charges battery first.
    - Discharge if tariff >= 0.15 (day or peak).
    - Possibly charge from grid at night (tariff=0.08) if 'AllowGridCharge'=True.
    """
    sim_df = df.copy()
    sim_df['SoC'] = 0.0
    sim_df['Grid_Import_kWh'] = 0.0
    sim_df['Grid_Export_kWh'] = 0.0
    sim_df['Cost'] = 0.0

    cap = battery_params['Capacity_kWh']
    max_charge_kW = battery_params['Max_Charge_kW']
    max_discharge_kW = battery_params['Max_Discharge_kW']
    eff = battery_params['RoundTripEff']
    allow_grid_charge = battery_params.get('AllowGridCharge', True)

    max_charge_kWh = max_charge_kW * dt_hours
    max_discharge_kWh = max_discharge_kW * dt_hours

    soc = 0.0
    for i in range(len(sim_df)):
        row = sim_df.iloc[i]
        hour = row.name.hour
        load_kWh = row['Load_kW'] * dt_hours
        solar_kWh = row['Solar_kW'] * dt_hours
        tariff = row['TariffRate']

        # 1. Charge from solar
        can_accept = cap - soc
        charge_from_solar = min(solar_kWh, max_charge_kWh, can_accept)
        soc += charge_from_solar
        leftover_solar = solar_kWh - charge_from_solar

        # 2. Use leftover solar for load
        if leftover_solar >= load_kWh:
            sim_df.iloc[i, sim_df.columns.get_loc('Grid_Export_kWh')] = leftover_solar - load_kWh
        else:
            unmet_load = load_kWh - leftover_solar
            # If tariff >= 0.15, let's discharge battery
            if (tariff >= 0.15) and (soc > 0):
                discharge_possible = min(soc, max_discharge_kWh)
                discharge_out = discharge_possible * eff
                if discharge_out >= unmet_load:
                    used = unmet_load
                    actual_discharge = used / eff
                    soc -= actual_discharge
                else:
                    used = discharge_out
                    actual_discharge = discharge_possible
                    soc -= actual_discharge
                    still_needed = unmet_load - used
                    sim_df.iloc[i, sim_df.columns.get_loc('Grid_Import_kWh')] = still_needed
                    sim_df.iloc[i, sim_df.columns.get_loc('Cost')] = still_needed * tariff
            else:
                sim_df.iloc[i, sim_df.columns.get_loc('Grid_Import_kWh')] = unmet_load
                sim_df.iloc[i, sim_df.columns.get_loc('Cost')] = unmet_load * tariff

        # 3. Possibly charge from grid if night rate is 0.08
        if allow_grid_charge and (tariff <= 0.08) and soc < cap:
            needed = cap - soc
            charge_now = min(needed, max_charge_kWh)
            # we pay for this energy
            sim_df.iloc[i, sim_df.columns.get_loc('Grid_Import_kWh')] += charge_now
            sim_df.iloc[i, sim_df.columns.get_loc('Cost')] += charge_now * tariff
            soc += charge_now

        sim_df.iloc[i, sim_df.columns.get_loc('SoC')] = soc

    return sim_df

###############################################################################
# Step 5: Cost-Benefit Analysis
###############################################################################
def cost_benefit_analysis(df_baseline, df_solar, df_s1, df_s2):
    """
    Prints out key metrics: total grid import, total cost,
    cost savings vs. baseline, etc.
    """
    # Baseline
    base_import = df_baseline['Grid_Import_kWh'].sum()
    base_cost   = df_baseline['Cost'].sum()

    # Solar only
    solar_import = df_solar['Grid_Import_kWh'].sum()
    solar_cost   = df_solar['Cost'].sum()

    # Scenario 1
    s1_import = df_s1['Grid_Import_kWh'].sum()
    s1_cost   = df_s1['Cost'].sum()

    # Scenario 2
    s2_import = df_s2['Grid_Import_kWh'].sum()
    s2_cost   = df_s2['Cost'].sum()

    print("\n=== Cost-Benefit Analysis ===\n")
    print(f"Baseline:  import={base_import:.2f} kWh, cost={base_cost:.2f}")

    print(f"SolarOnly: import={solar_import:.2f} kWh, cost={solar_cost:.2f}")
    print(f"  => Savings vs baseline: {base_cost - solar_cost:.2f}  ({base_import - solar_import:.2f} kWh reduction)")

    print(f"Scenario1: import={s1_import:.2f} kWh, cost={s1_cost:.2f}")
    print(f"  => Savings vs baseline: {base_cost - s1_cost:.2f}  ({base_import - s1_import:.2f} kWh reduction)")

    print(f"Scenario2: import={s2_import:.2f} kWh, cost={s2_cost:.2f}")
    print(f"  => Savings vs baseline: {base_cost - s2_cost:.2f}  ({base_import - s2_import:.2f} kWh reduction)")

    # Direct comparison between S1 and S2
    diff = s1_cost - s2_cost
    if diff > 0:
        print(f"Scenario2 is cheaper than Scenario1 by {diff:.2f}")
    else:
        print(f"Scenario2 is more expensive than Scenario1 by {abs(diff):.2f}")

###############################################################################
# MAIN: Put It All Together
###############################################################################
if __name__ == "__main__":

    # 1) Create or load your data
    df_original = create_synthetic_data()

    # 2) Baseline scenario
    df_baseline = create_baseline_df(df_original)

    # 3) Solar-Only scenario
    df_solar = create_solar_only_df(df_original)

    # 4) Battery Scenarios
    battery_params = {
        'Capacity_kWh': 16000,
        'Max_Charge_kW': 8000,
        'Max_Discharge_kW': 8000,
        'RoundTripEff': 0.90,
        'AllowGridCharge': True  # relevant for scenario 2
    }

    df_s1 = simulate_scenario_1(df_original, battery_params)
    df_s2 = simulate_scenario_2(df_original, battery_params)

    # 5) Compare results
    cost_benefit_analysis(df_baseline, df_solar, df_s1, df_s2)

    # Optional: plot comparisons
    plt.figure(figsize=(10,5))
    plt.plot(df_s1.index, df_s1['SoC'], label='Scenario 1 SoC', color='red')
    plt.plot(df_s2.index, df_s2['SoC'], label='Scenario 2 SoC', color='green')
    plt.ylabel('Battery SoC (kWh)')
    plt.title('Comparison of Battery State of Charge')
    plt.legend()
    plt.tight_layout()
    plt.show()
