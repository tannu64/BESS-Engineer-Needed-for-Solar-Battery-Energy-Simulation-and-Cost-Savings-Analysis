import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

def plot_tmy_data(csv_file):
    """
    This function replicates your Code 1 logic:
      - Reads the TMY CSV (724460TYA.CSV)
      - Extracts station info & location from the first line
      - Reads columns for ETR, GHI, DNI, DHI, T_amb from the main data
      - Plots DNI, DHI, and GHI vs. hour of the year
    """
    # ---------------------------------------------------------------------
    # 1. Read initial lines for station info
    # ---------------------------------------------------------------------
    # station, GMT_offset, latitude, longitude, altitude from the first line
    station, GMT_offset, latitude, longitude, altitude = np.genfromtxt(
        csv_file,
        max_rows=1,
        delimiter=",",
        usecols=(0, 3, 4, 5, 6)  # columns for station, GMT, lat, lon, alt
    )
    
    # location_name, location_state from first line as well (usecols=1,2)
    location_name, location_state = np.genfromtxt(
        csv_file,
        max_rows=1,
        delimiter=",",
        usecols=(1, 2),
        dtype=str
    )
    
    # ---------------------------------------------------------------------
    # 2. Read the main hourly data (starting from line 3)
    # ---------------------------------------------------------------------
    ETR, GHI, DNI, DHI, T_amb = np.genfromtxt(
        csv_file,
        skip_header=2,
        delimiter=",",
        usecols=(2, 4, 7, 10, 31),
        unpack=True
    )
    
    # ---------------------------------------------------------------------
    # 3. Print station/location info
    # ---------------------------------------------------------------------
    print("Location information:")
    print("  station number:          ", station)
    print("  station name and state:  ", location_name, location_state)
    print("  GMT offset:              ", GMT_offset)
    print("  Latitude (degrees):      ", latitude)
    print("  Longitude (degrees):     ", longitude)
    print("  Altitude (m):            ", altitude)
    print()
    
    # ---------------------------------------------------------------------
    # 4. Plot DNI
    # ---------------------------------------------------------------------
    plt.figure()
    plt.plot(DNI, label='Direct Normal Irradiance (DNI)', color='black')
    plt.title(f'Direct Normal Irradiance at "{location_name} {location_state}"')
    plt.xlabel('Hour of the Year')
    plt.ylabel('DNI [W/m²]')
    plt.legend()
    plt.grid(True)
    plt.show()
    
    # ---------------------------------------------------------------------
    # 5. Plot DHI
    # ---------------------------------------------------------------------
    plt.figure()
    plt.plot(DHI, label='Diffuse Horizontal Irradiance (DHI)', color='blue')
    plt.title(f'Diffuse Horizontal Irradiance at "{location_name} {location_state}"')
    plt.xlabel('Hour of the Year')
    plt.ylabel('DHI [W/m²]')
    plt.legend()
    plt.grid(True)
    plt.show()
    
    # ---------------------------------------------------------------------
    # 6. Plot GHI
    # ---------------------------------------------------------------------
    plt.figure()
    plt.plot(GHI, label='Global Horizontal Irradiance (GHI)', color='red')
    plt.title(f'Global Horizontal Irradiance at "{location_name} {location_state}"')
    plt.xlabel('Hour of the Year')
    plt.ylabel('GHI [W/m²]')
    plt.legend()
    plt.grid(True)
    plt.show()

def plot_synthetic_data(excel_file):
    """
    This function replicates your Code 2 logic:
      - Reads the Excel file with the first column as the DateTime index
      - Plots half-hourly Load_kW time-series, daily average load,
        and a histogram of TariffRate.
    """
    df = pd.read_excel(excel_file, index_col=0, parse_dates=True)
    
    # 2. Quick overview
    print("DataFrame Head:")
    print(df.head())
    print("\nDataFrame Info:")
    print(df.info())
    print("\nBasic Statistics:")
    print(df.describe())
    
    # 3. Plot the half-hourly Load_kW
    if 'Load_kW' not in df.columns:
        print("ERROR: 'Load_kW' column not found in Excel data.")
        return
    
    plt.figure(figsize=(12, 5))
    plt.plot(df.index, df['Load_kW'], label='Load (kW)', color='blue')
    plt.title('Half-Hourly Load Over the Year')
    plt.xlabel('Date')
    plt.ylabel('Load (kW)')
    plt.legend()
    plt.tight_layout()
    plt.show()
    
    # 4. Plot daily average load
    daily_avg_load = df['Load_kW'].resample('D').mean()
    
    plt.figure(figsize=(12, 5))
    plt.plot(daily_avg_load.index, daily_avg_load, label='Daily Average Load (kW)', color='green')
    plt.title('Daily Average Load Over the Year')
    plt.xlabel('Date')
    plt.ylabel('Load (kW)')
    plt.legend()
    plt.tight_layout()
    plt.show()
    
    # 5. Histogram of TariffRate
    if 'TariffRate' not in df.columns:
        print("WARNING: 'TariffRate' column not found. Skipping histogram.")
        return
    
    plt.figure(figsize=(6,4))
    df['TariffRate'].hist(bins=20, color='orange', edgecolor='black')
    plt.title('Histogram of Tariff Rate')
    plt.xlabel('Tariff Rate (currency/kWh)')
    plt.ylabel('Frequency')
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # 1) Plot TMY data (Code 1)
    tmy_csv_path = '724460TYA.CSV'  # Adjust if needed
    plot_tmy_data(tmy_csv_path)
    
    # 2) Plot synthetic dataset (Code 2)
    synthetic_excel_path = 'synthetic_dataset_ireland.xlsx'  # Adjust if needed
    plot_synthetic_data(synthetic_excel_path)

