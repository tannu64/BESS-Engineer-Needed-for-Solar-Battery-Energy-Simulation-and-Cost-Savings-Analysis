import pandas as pd
import numpy as np

def simulate_battery_dispatch(df, battery_params, dt_hours=0.5):
    """
    Simulates battery operation in a half-hourly time-stepped manner.
    Args:
      df (pd.DataFrame): Must include columns ['Load_kW', 'Solar_kW', 'TariffRate'].
                         Indexed by DateTime at 30-min intervals.
      battery_params (dict): e.g. {
          'Capacity_kWh': 16000,
          'Max_Charge_kW': 8000,
          'Max_Discharge_kW': 8000,
          'RoundTripEff': 0.9,
          'MinSoC_kWh': 0,
          'MaxSoC_kWh': 16000
       }
      dt_hours (float): Duration of each timestep in hours (0.5 for half-hour).
    Returns:
      pd.DataFrame: copy of df with added columns:
          'SoC', 'Grid_Import_kWh', 'Grid_Export_kWh', 'Cost'
    """

    # Make a copy so we don't modify the original
    sim_df = df.copy()

    # Check for required columns
    required_cols = ['Load_kW', 'Solar_kW', 'TariffRate']
    for col in required_cols:
        if col not in sim_df.columns:
            raise ValueError(f"DataFrame must have a '{col}' column.")

    # Initialize new columns
    sim_df['SoC'] = 0.0             # State of Charge (kWh)
    sim_df['Grid_Import_kWh'] = 0.0
    sim_df['Grid_Export_kWh'] = 0.0
    sim_df['Cost'] = 0.0

    # Optional: track battery charge/discharge to see flows
    sim_df['Battery_Charge_kWh'] = 0.0
    sim_df['Battery_Discharge_kWh'] = 0.0

    # Extract battery parameters
    capacity = battery_params.get('Capacity_kWh', 16000)
    max_charge_kW = battery_params.get('Max_Charge_kW', 8000)
    max_discharge_kW = battery_params.get('Max_Discharge_kW', 8000)
    eff = battery_params.get('RoundTripEff', 0.9)
    min_soc = battery_params.get('MinSoC_kWh', 0.0)
    max_soc = battery_params.get('MaxSoC_kWh', capacity)

    # Convert max charge/discharge (kW) to kWh per half-hour step
    max_charge_kWh = max_charge_kW * dt_hours
    max_discharge_kWh = max_discharge_kW * dt_hours

    # We'll iterate row by row, updating SoC based on the previous timestep
    soc = 0.0  # start at 0% or any initial SoC you want

    # Main loop
    for i in range(len(sim_df)):
        row = sim_df.iloc[i]
        load_kW = row['Load_kW']
        solar_kW = row['Solar_kW']
        tariff = row['TariffRate']

        # Energy needed for load, energy provided by solar, all in kWh for this step
        load_kWh = load_kW * dt_hours
        solar_kWh = solar_kW * dt_hours

        # 1) Use solar to serve the load first
        if solar_kWh >= load_kWh:
            # Surplus solar remains after meeting load
            surplus_solar = solar_kWh - load_kWh

            # 2) Attempt to charge battery with surplus
            #    Battery can only accept up to (max_charge_kWh) this interval
            #    and cannot exceed max_soc
            can_charge = max_soc - soc
            charge_needed = min(surplus_solar, max_charge_kWh, can_charge)
            
            # Battery charging is subject to charging efficiency
            # Typically, you might only lose efficiency on discharge,
            # or you might model it on both charge & discharge.
            # Let's apply half the round-trip penalty on charge, half on discharge:
            charge_in = charge_needed * 0.95  # or use sqrt of eff if you want symmetrical
            # We'll keep it simpler: 1) Some do eff on total discharge only
            # For demonstration: let's do half each way => sqrt(0.9) ~ 0.95

            new_soc = soc + charge_in
            # Surplus after battery
            surplus_after_batt = surplus_solar - charge_needed

            # Update SoC within bounds
            soc = min(new_soc, max_soc)

            # Record how much actually went into battery
            sim_df.iloc[i, sim_df.columns.get_loc('Battery_Charge_kWh')] = charge_needed

            # 3) If there's still surplus after battery is full, we can export
            sim_df.iloc[i, sim_df.columns.get_loc('Grid_Export_kWh')] = surplus_after_batt

            # No grid import, no cost for this step
            sim_df.iloc[i, sim_df.columns.get_loc('Grid_Import_kWh')] = 0.0
            sim_df.iloc[i, sim_df.columns.get_loc('Cost')] = 0.0

        else:
            # Not enough solar to cover the load
            # We'll see how much battery can discharge
            deficit_kWh = load_kWh - solar_kWh

            # 2) Discharge from battery
            # Battery can discharge up to max_discharge_kWh and up to current soc
            can_discharge = min(soc, max_discharge_kWh)
            
            # If we apply round-trip eff only on discharge:
            # discharge_out = can_discharge * eff
            # Or if you want to split charge/discharge losses, you'd do partial factor
            # We'll do total eff on discharge for demonstration:
            discharge_out = can_discharge * eff

            if discharge_out >= deficit_kWh:
                # Battery can fully cover the deficit
                used_from_battery = deficit_kWh
                # This means the battery actually discharges used_from_battery / eff from SoC
                actual_discharge = used_from_battery / eff
                soc -= actual_discharge
                sim_df.iloc[i, sim_df.columns.get_loc('Battery_Discharge_kWh')] = actual_discharge

                # No grid import
                sim_df.iloc[i, sim_df.columns.get_loc('Grid_Import_kWh')] = 0.0
                sim_df.iloc[i, sim_df.columns.get_loc('Cost')] = 0.0

            else:
                # Battery can't fully meet the deficit
                used_from_battery = discharge_out
                actual_discharge = can_discharge  # because discharge_out = can_discharge * eff
                soc -= actual_discharge
                sim_df.iloc[i, sim_df.columns.get_loc('Battery_Discharge_kWh')] = actual_discharge

                # Remaining load not met by battery
                still_needed = deficit_kWh - used_from_battery
                # Import from grid
                sim_df.iloc[i, sim_df.columns.get_loc('Grid_Import_kWh')] = still_needed
                sim_df.iloc[i, sim_df.columns.get_loc('Cost')] = still_needed * tariff

            # No surplus solar in this branch
            sim_df.iloc[i, sim_df.columns.get_loc('Grid_Export_kWh')] = 0.0

        # Update SoC in DataFrame
        sim_df.iloc[i, sim_df.columns.get_loc('SoC')] = soc

    return sim_df

# ---------------------------------------------------------------------

if __name__ == "__main__":
    # EXAMPLE USE:
    import matplotlib.pyplot as plt

    # Suppose you have a DataFrame `df` with half-hour index, columns: Load_kW, Solar_kW, TariffRate
    # Here we just create a synthetic example for demonstration:
    date_range = pd.date_range("2025-01-01", periods=48*7, freq='30min')  # one week
    df_example = pd.DataFrame(index=date_range, columns=['Load_kW','Solar_kW','TariffRate'], dtype=float)

    # Fill with random or synthetic values:
    np.random.seed(42)
    df_example['Load_kW'] = 500 + 300*np.sin(np.linspace(0,10,len(df_example))) + 100*np.random.rand(len(df_example))
    df_example['Solar_kW'] = 0.0
    # Let's make a "daytime" solar shape, zero at night
    for i, ts in enumerate(df_example.index):
        hour = ts.hour
        if 6 <= hour < 18:
            # peak midday around 1000 kW
            df_example.iloc[i, df_example.columns.get_loc('Solar_kW')] = 1000*np.exp(-0.5*((hour-12)/2)**2)

    # Tariff rate in three blocks: night=0.08, day=0.15, peak=0.25
    def mock_tariff(dt):
        if 17 <= dt.hour < 19:
            return 0.25
        elif (8 <= dt.hour < 17) or (19 <= dt.hour < 23):
            return 0.15
        else:
            return 0.08
    df_example['TariffRate'] = df_example.index.map(mock_tariff)

    # Define battery parameters
    battery_params = {
        'Capacity_kWh': 16000,
        'Max_Charge_kW': 8000,
        'Max_Discharge_kW': 8000,
        'RoundTripEff': 0.90,
        'MinSoC_kWh': 0,
        'MaxSoC_kWh': 16000
    }

    # Run simulation
    result_df = simulate_battery_dispatch(df_example, battery_params, dt_hours=0.5)

    # Plot results
    plt.figure(figsize=(10,5))
    plt.plot(result_df.index, result_df['Load_kW'], label='Load (kW)', color='black')
    plt.plot(result_df.index, result_df['Solar_kW'], label='Solar (kW)', color='orange')
    plt.ylabel('Power (kW)')
    plt.title('Load & Solar Over Time (One Week Example)')
    plt.legend()
    plt.show()

    plt.figure(figsize=(10,5))
    plt.plot(result_df.index, result_df['SoC'], label='SoC (kWh)', color='blue')
    plt.ylabel('Battery SoC (kWh)')
    plt.title('Battery State of Charge')
    plt.legend()
    plt.show()

    # Summaries
    total_grid_import = result_df['Grid_Import_kWh'].sum()
    total_export = result_df['Grid_Export_kWh'].sum()
    total_cost = result_df['Cost'].sum()

    print(f"Total Grid Import (kWh): {total_grid_import:.2f}")
    print(f"Total Grid Export (kWh): {total_export:.2f}")
    print(f"Total Cost: {total_cost:.2f}")

