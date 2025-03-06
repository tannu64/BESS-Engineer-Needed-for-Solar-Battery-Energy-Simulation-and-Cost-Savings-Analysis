import pandas as pd
import numpy as np

def generate_synthetic_dataset(
    start_date='2025-01-01', 
    days=365,
    half_hours_per_day=48,
    weekend_factor=0.7, 
    annual_load_mwh=20000,  # total yearly consumption in MWh
    battery_size_kwh=16000,  # 16 MWh in kWh
    max_power_kw=8000,       # 8 MW max power (0.5C for 16 MWh battery)
    round_trip_eff=0.9
):
    """
    Generates a synthetic dataset with half-hourly load and tariff rates.
    Returns a pandas DataFrame.
    """

    # 1) Create a date range with half-hourly frequency
    total_intervals = days * half_hours_per_day
    date_range = pd.date_range(start=start_date, periods=total_intervals, freq='30min')
    
    # 2) Base Daily Profile: We'll define a rough shape for 24 hours 
    #    then interpolate to 48 half-hours
    base_profile_24 = np.array([
        0.6, 0.6, 0.7, 0.8, 0.9, 1.0,  # 00:00-05:00
        1.0, 1.1, 1.2, 1.2, 1.1, 1.0,  # 06:00-11:00
        1.0, 1.2, 1.2, 1.1, 1.1, 1.0,  # 12:00-17:00
        0.9, 0.8, 0.7, 0.7, 0.6, 0.6   # 18:00-23:00
    ])
    # Interpolate to get 48 half-hour points
    base_profile_48 = np.interp(np.linspace(0, 24, 48), np.arange(24), base_profile_24)
    
    # 3) Prepare an empty DataFrame
    df = pd.DataFrame(index=date_range, columns=['Load_kW', 'TariffRate'])
    
    # We'll build daily load with seasonality, weekend scaling, and random noise
    # First let's define a daily energy target that sums up to the chosen annual load
    # annual_load_mwh => daily load in MWh => daily_load_mwh
    daily_load_mwh = annual_load_mwh / days
    # convert MWh => kWh
    daily_load_kwh = daily_load_mwh * 1000
    
    # Seasonality (example: sine wave that peaks in winter or summer)
    day_of_year = np.arange(days)
    # Simple approach: peak in winter => shift sine wave
    # amplitude: 10% around a baseline of 1.0
    seasonal_factor = 1.0 + 0.1 * np.sin(2 * np.pi * (day_of_year / 365 - 0.2))
    
    # Fill the DataFrame
    idx = 0
    for d in range(days):
        current_day = date_range[d*half_hours_per_day]
        # Check if it's a weekend
        if current_day.weekday() < 5:
            w_factor = 1.0  # weekday
        else:
            w_factor = weekend_factor
        
        # base load shape for the day (48 half-hour intervals)
        day_profile = base_profile_48.copy()
        
        # apply seasonality
        day_profile = day_profile * seasonal_factor[d]
        
        # random noise around 5%
        noise = np.random.normal(1.0, 0.05, half_hours_per_day)
        day_profile = day_profile * noise
        
        # scale so total = daily_load_kwh
        day_sum = day_profile.sum()
        scale_factor = daily_load_kwh / day_sum
        day_profile_scaled = day_profile * scale_factor * w_factor
        
        # assign to DataFrame
        df.iloc[idx:idx+half_hours_per_day, df.columns.get_loc('Load_kW')] = day_profile_scaled
        idx += half_hours_per_day
    
    # 4) Define a Tariff Structure (time-based)
    # Example: peak (5 PM – 7 PM) = 0.25, day (8 AM – 5 PM, 7 PM – 11 PM) = 0.15, night (11 PM – 8 AM) = 0.08
    def get_tariff_rate(dt):
        hour = dt.hour
        if 17 <= hour < 19:
            return 0.25  # peak
        elif (8 <= hour < 17) or (19 <= hour < 23):
            return 0.15  # day
        else:
            return 0.08  # night

    df['TariffRate'] = df.index.to_series().apply(get_tariff_rate)
    
    # 5) Optionally, store Battery & round-trip efficiency as columns
    # Typically, battery parameters are used in a separate simulation model,
    # but we can store them for reference.
    df['BatterySize_kWh'] = battery_size_kwh
    df['MaxPower_kW'] = max_power_kw
    df['RoundTripEfficiency'] = round_trip_eff
    
    # Convert all numeric columns to float
    df = df.astype(float)
    
    return df

def main():
    # Generate the DataFrame
    df_synthetic = generate_synthetic_dataset()
    
    # Save to Excel
    df_synthetic.to_excel('synthetic_dataset_ireland.xlsx', sheet_name='SyntheticData')
    
    print("Synthetic dataset generated and saved to 'synthetic_dataset_ireland.xlsx'.")
    print(df_synthetic.head(10))  # show first 10 rows

if __name__ == "__main__":
    main()

