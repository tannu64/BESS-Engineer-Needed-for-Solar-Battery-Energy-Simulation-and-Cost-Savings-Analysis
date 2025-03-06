import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

###############################################################################
# 1. Data Generation for Site A and Site B
###############################################################################
def create_synthetic_site_data(site_label, days=3, load_base=500, load_variation=300, solar_capacity=8.0):
    """
    Creates a synthetic half-hourly dataset for a given 'site' with:
      - columns: ['Load_kW','Solar_kW','TariffRate']
      - index: 30-min DateTime for 'days' days
    'solar_capacity' adjusts the amplitude of midday solar.
    'load_base' and 'load_variation' control the site load magnitude.
    """
    freq = '30min'
    intervals_per_day = 48
    rng = pd.date_range("2025-01-01", periods=days*intervals_per_day, freq=freq)
    df = pd.DataFrame(index=rng, columns=['Load_kW','Solar_kW','TariffRate'], dtype=float)

    # Random load
    np.random.seed(hash(site_label) % 123456)  # pseudo-distinguish each site
    df['Load_kW'] = load_base + load_variation * np.random.rand(len(df))

    # Simplistic solar shape: 0 at night, bell around midday
    def solar_profile(hour):
        if 6 <= hour < 18:
            return solar_capacity * 1000.0 * np.exp(-0.5*((hour-12)/2)**2)
        return 0.0
    df['Solar_kW'] = [solar_profile(ts.hour) for ts in df.index]

    # Tariff: night=0.08, day=0.15, peak=0.25 (5..7 pm)
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
# 2. Helper Functions: Baseline, Solar-Only, Battery Dispatch (Scenario 1 & 2)
###############################################################################
def create_baseline_df(df):
    """
    Baseline: no solar, no battery => all load from grid.
    """
    base_df = df.copy()
    # Zero out solar
    base_df['Solar_kW'] = 0.0
    # Grid import = load (kW)*0.5
    base_df['Grid_Import_kWh'] = base_df['Load_kW'] * 0.5
    base_df['Cost'] = base_df['Grid_Import_kWh'] * base_df['TariffRate']
    return base_df

def create_solar_only_df(df):
    """
    Solar only: If solar>=load => no grid import that interval; else import shortfall.
    """
    s_df = df.copy()
    s_df['Grid_Import_kWh'] = 0.0
    s_df['Cost'] = 0.0

    for i in range(len(s_df)):
        load_kWh = s_df.iloc[i]['Load_kW'] * 0.5
        solar_kWh = s_df.iloc[i]['Solar_kW'] * 0.5
        tariff = s_df.iloc[i]['TariffRate']

        if solar_kWh >= load_kWh:
            # no import, cost=0
            pass
        else:
            shortfall = load_kWh - solar_kWh
            s_df.iloc[i, s_df.columns.get_loc('Grid_Import_kWh')] = shortfall
            s_df.iloc[i, s_df.columns.get_loc('Cost')] = shortfall * tariff

    return s_df

def simulate_scenario_1(df, battery_params, dt_hours=0.5):
    """
    Battery scenario #1: 
      - Solar charges battery first
      - Discharge ONLY 5..7 pm, then continue to empty by 11 pm if SoC>0
    """
    sim_df = df.copy()
    sim_df['SoC'] = 0.0
    sim_df['Grid_Import_kWh'] = 0.0
    sim_df['Grid_Export_kWh'] = 0.0
    sim_df['Cost'] = 0.0

    cap = battery_params['Capacity_kWh']
    max_c_kW = battery_params['Max_Charge_kW']
    max_d_kW = battery_params['Max_Discharge_kW']
    eff = battery_params['RoundTripEff']

    max_c_kWh = max_c_kW * dt_hours
    max_d_kWh = max_d_kW * dt_hours
    soc = 0.0

    for i in range(len(sim_df)):
        row = sim_df.iloc[i]
        hour = row.name.hour
        load_kWh = row['Load_kW'] * dt_hours
        solar_kWh = row['Solar_kW'] * dt_hours
        tariff = row['TariffRate']

        # 1) Charge from solar
        can_accept = cap - soc
        charge = min(solar_kWh, max_c_kWh, can_accept)
        soc += charge
        leftover_solar = solar_kWh - charge

        # 2) leftover solar meets load
        if leftover_solar >= load_kWh:
            # Surplus => export if you want
            sim_df.iloc[i, sim_df.columns.get_loc('Grid_Export_kWh')] = leftover_solar - load_kWh
        else:
            unmet = load_kWh - leftover_solar
            # Decide if we can discharge battery
            can_discharge_now = False
            if 17 <= hour < 19:
                can_discharge_now = True
            elif (19 <= hour < 23) and soc>0:
                can_discharge_now = True

            if can_discharge_now and soc>0:
                discharge_possible = min(soc, max_d_kWh)
                discharge_out = discharge_possible * eff
                if discharge_out >= unmet:
                    used = unmet
                    actual_discharge = used/eff
                    soc -= actual_discharge
                else:
                    used = discharge_out
                    actual_discharge = discharge_possible
                    soc -= actual_discharge
                    # remainder from grid
                    still_needed = unmet - used
                    sim_df.iloc[i, sim_df.columns.get_loc('Grid_Import_kWh')] = still_needed
                    sim_df.iloc[i, sim_df.columns.get_loc('Cost')] = still_needed * tariff
            else:
                # import all unmet
                sim_df.iloc[i, sim_df.columns.get_loc('Grid_Import_kWh')] = unmet
                sim_df.iloc[i, sim_df.columns.get_loc('Cost')] = unmet * tariff

        sim_df.iloc[i, sim_df.columns.get_loc('SoC')] = soc

    return sim_df

def simulate_scenario_2(df, battery_params, dt_hours=0.5):
    """
    Battery scenario #2: 
      - Solar charges battery first
      - Discharge if tariff>=0.15
      - Possibly charge from grid at night if allowGridCharge==True
    """
    sim_df = df.copy()
    sim_df['SoC'] = 0.0
    sim_df['Grid_Import_kWh'] = 0.0
    sim_df['Grid_Export_kWh'] = 0.0
    sim_df['Cost'] = 0.0

    cap = battery_params['Capacity_kWh']
    max_c_kW = battery_params['Max_Charge_kW']
    max_d_kW = battery_params['Max_Discharge_kW']
    eff = battery_params['RoundTripEff']
    allow_grid_charge = battery_params.get('AllowGridCharge', True)

    max_c_kWh = max_c_kW * dt_hours
    max_d_kWh = max_d_kW * dt_hours
    soc = 0.0

    for i in range(len(sim_df)):
        row = sim_df.iloc[i]
        hour = row.name.hour
        load_kWh = row['Load_kW'] * dt_hours
        solar_kWh = row['Solar_kW'] * dt_hours
        tariff = row['TariffRate']

        # 1) Charge from solar
        can_accept = cap - soc
        c_solar = min(solar_kWh, max_c_kWh, can_accept)
        soc += c_solar
        leftover_solar = solar_kWh - c_solar

        # 2) leftover solar meets load
        if leftover_solar >= load_kWh:
            sim_df.iloc[i, sim_df.columns.get_loc('Grid_Export_kWh')] = leftover_solar - load_kWh
        else:
            unmet = load_kWh - leftover_solar
            if tariff >= 0.15 and soc>0:
                discharge_possible = min(soc, max_d_kWh)
                discharge_out = discharge_possible * eff
                if discharge_out >= unmet:
                    used = unmet
                    actual_discharge = used / eff
                    soc -= actual_discharge
                else:
                    used = discharge_out
                    actual_discharge = discharge_possible
                    soc -= actual_discharge
                    still_needed = unmet - used
                    sim_df.iloc[i, sim_df.columns.get_loc('Grid_Import_kWh')] = still_needed
                    sim_df.iloc[i, sim_df.columns.get_loc('Cost')] = still_needed * tariff
            else:
                sim_df.iloc[i, sim_df.columns.get_loc('Grid_Import_kWh')] = unmet
                sim_df.iloc[i, sim_df.columns.get_loc('Cost')] = unmet * tariff

        # 3) Possibly charge from grid if nighttime
        if allow_grid_charge and tariff <= 0.08 and soc<cap:
            needed = cap - soc
            c_grid = min(needed, max_c_kWh)
            sim_df.iloc[i, sim_df.columns.get_loc('Grid_Import_kWh')] += c_grid
            sim_df.iloc[i, sim_df.columns.get_loc('Cost')] += c_grid * tariff
            soc += c_grid

        sim_df.iloc[i, sim_df.columns.get_loc('SoC')] = soc

    return sim_df

###############################################################################
# 3. Summaries & Cost-Benefit
###############################################################################
def cost_benefit_analysis(df_baseline, df_solar, df_s1, df_s2, label="(No label)"):
    """
    Print summary of grid import & cost for each scenario vs baseline.
    """
    base_imp = df_baseline['Grid_Import_kWh'].sum()
    base_cost = df_baseline['Cost'].sum()

    sol_imp = df_solar['Grid_Import_kWh'].sum()
    sol_cost = df_solar['Cost'].sum()

    s1_imp = df_s1['Grid_Import_kWh'].sum()
    s1_cost = df_s1['Cost'].sum()

    s2_imp = df_s2['Grid_Import_kWh'].sum()
    s2_cost = df_s2['Cost'].sum()

    print(f"\n=== Cost-Benefit Analysis: Phase {label} ===")
    print(f"Baseline:  import={base_imp:.2f} kWh, cost={base_cost:.2f}")
    print(f"SolarOnly: import={sol_imp:.2f} kWh, cost={sol_cost:.2f}"
          f" | Savings vs baseline= {(base_cost - sol_cost):.2f}")

    print(f"Scenario1: import={s1_imp:.2f} kWh, cost={s1_cost:.2f}"
          f" | Savings vs baseline= {(base_cost - s1_cost):.2f}")

    print(f"Scenario2: import={s2_imp:.2f} kWh, cost={s2_cost:.2f}"
          f" | Savings vs baseline= {(base_cost - s2_cost):.2f}")

    diff_1_2 = s1_cost - s2_cost
    if diff_1_2>0:
        print(f"=> Scenario 2 is cheaper than Scenario 1 by {diff_1_2:.2f}")
    else:
        print(f"=> Scenario 1 is cheaper than Scenario 2 by {abs(diff_1_2):.2f}")

###############################################################################
# 4. PHASE I: Site A only
###############################################################################
def phase_I_simulation(days=3):
    """
    Phase I: Site A alone (8 MWp, 16 MWh, 8 MW inverter)
    """
    # 1) Generate synthetic data for Site A
    dfA = create_synthetic_site_data("A", days=days, load_base=500, load_variation=300, solar_capacity=8.0)

    # 2) Baseline, solar-only
    dfA_baseline = create_baseline_df(dfA)
    dfA_solar = create_solar_only_df(dfA)

    # 3) Battery scenarios
    batteryA = {
        'Capacity_kWh': 16000,
        'Max_Charge_kW': 8000,
        'Max_Discharge_kW': 8000,
        'RoundTripEff': 0.90,
        'AllowGridCharge': True
    }
    dfA_s1 = simulate_scenario_1(dfA, batteryA)
    dfA_s2 = simulate_scenario_2(dfA, batteryA)

    # Summaries
    cost_benefit_analysis(dfA_baseline, dfA_solar, dfA_s1, dfA_s2, label="I (Site A)")

    return (dfA_baseline, dfA_solar, dfA_s1, dfA_s2)

###############################################################################
# 5. PHASE II: Site A + Site B aggregated
###############################################################################
def phase_II_simulation(days=3):
    """
    Phase II: Aggregated site = Site A + Site B
      - 8 + 4.5 = 12.5 MWp solar
      - 16 + 9 = 25 MWh battery
      - 8 + 4.5 = 12.5 MW max inverter (0.5 C)
    We'll just sum load & sum solar from each site to make an aggregated profile.
    """
    # Generate data for Site A & B
    dfA = create_synthetic_site_data("A2", days=days, load_base=500, load_variation=300, solar_capacity=8.0)
    dfB = create_synthetic_site_data("B2", days=days, load_base=200, load_variation=150, solar_capacity=4.5)

    # Combine them: sum load, sum solar, keep the same TariffRate (assuming same tariff schedule)
    # If the sites have different tariffs, you'd need a different approach.
    dfAgg = dfA.copy()
    dfAgg['Load_kW'] = dfA['Load_kW'] + dfB['Load_kW']
    dfAgg['Solar_kW'] = dfA['Solar_kW'] + dfB['Solar_kW']
    # TariffRate = same for both sites (just assume same structure)
    # If you want separate tariff for each site, you'd have to handle that differently.

    # Baseline, solar-only for aggregated
    dfAgg_base = create_baseline_df(dfAgg)
    dfAgg_solar = create_solar_only_df(dfAgg)

    # Battery now 25 MWh, 12.5 MW
    battery_agg = {
        'Capacity_kWh': 25000,
        'Max_Charge_kW': 12500,
        'Max_Discharge_kW': 12500,
        'RoundTripEff': 0.90,
        'AllowGridCharge': True
    }
    dfAgg_s1 = simulate_scenario_1(dfAgg, battery_agg)
    dfAgg_s2 = simulate_scenario_2(dfAgg, battery_agg)

    cost_benefit_analysis(dfAgg_base, dfAgg_solar, dfAgg_s1, dfAgg_s2, label="II (A+B)")

    return (dfAgg_base, dfAgg_solar, dfAgg_s1, dfAgg_s2)

###############################################################################
# 6. Putting It All Together
###############################################################################
if __name__ == "__main__":
    # Phase I: Site A only
    phase_I_simulation(days=3)

    # Phase II: Combined A + B
    phase_II_simulation(days=3)

    # If desired, you can store the final DataFrames or plot them 
    # to produce the time-series results and summary tables.
    print("\nDone. See above for cost-benefit analysis of Phase I & II.")

