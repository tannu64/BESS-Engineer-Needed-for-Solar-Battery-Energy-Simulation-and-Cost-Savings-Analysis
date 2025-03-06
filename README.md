# Battery Energy Storage System (BESS) Simulation and Cost Savings Analysis  
This project simulates and analyzes a **Battery Energy Storage System (BESS) with Solar PV** using **Python** to optimize **grid consumption reduction and cost savings**.  
The analysis is conducted in **two phases**:  
- **Phase I:** Site A (8 MWp solar, 16 MWh battery, 8 MVA inverter)  
- **Phase II:** Site A + Site B (12.5 MWp total solar, 25 MWh total battery, 12.5 MVA inverter)  

## 📌 Project Scope  
- **Simulations to determine:**  
  ✅ Grid consumption reduction using solar & battery  
  ✅ Cost savings from battery discharge during peak hours  
  ✅ Energy yield from solar generation alone  
- **Simulation Scenarios:**  
  - **Scenario 1:** Battery discharges **only from 5 PM – 7 PM** and must be **fully discharged by 11 PM**  
  - **Scenario 2:** Battery discharges during peak hours **and** when it **maximizes cost savings**  

## 🛠️ Tools & Technologies  
- **Python**  
- **pandas, numpy, matplotlib** for data handling & visualization  
- **Jupyter Notebook/PyCharm/VS Code** for running simulations  
- **CSV/Excel files** for storing results  


## 📊 Simulation Framework  

The simulation is **time-stepped (half-hourly)** and tracks:  
✅ **Solar Generation**  
✅ **Battery State of Charge (SoC)**  
✅ **Site Load**  
✅ **Grid Import/Export**  
✅ **Running Cost Over Each Timestep**  

### **Phase I – Site A (8 MWp Solar, 16 MWh Battery)**
| **Scenario**  | **Grid Import (kWh)** | **Total Cost (€)** | **Savings (€)** |
|--------------|----------------|----------------|----------------|
| **Baseline** | 46,529.90 | 6,138.16 | --- |
| **Solar Only** | 26,718.87 | 3,153.53 | **2,984.63** |
| **Scenario 1** | 22,333.36 | 2,119.24 | **4,018.92** |
| **Scenario 2** | 43,932.49 | 3,514.60 | **2,623.56** |

### **Phase II – Site A + Site B (12.5 MWp Solar, 25 MWh Battery)**
| **Scenario**  | **Grid Import (kWh)** | **Total Cost (€)** | **Savings (€)** |
|--------------|----------------|----------------|----------------|
| **Baseline** | 66,283.52 | 8,732.28 | --- |
| **Solar Only** | 38,216.56 | 4,501.97 | **4,230.31** |
| **Scenario 1** | 31,565.59 | 2,974.87 | **5,757.42** |
| **Scenario 2** | 64,963.75 | 5,197.10 | **3,535.18** |

### **Cost Savings Summary**  
- **Scenario 1 consistently saved more money** by strictly discharging during peak hours (5–7 PM).  
- **Scenario 2 was more flexible but resulted in higher overall grid import costs.**  
- **Total cost savings from battery operation in Phase II:** **€5,757.42**  

## 📌 Key Takeaways  
✔️ **Scenario 1 is the best strategy**—it saves more money by discharging only during peak hours.  
✔️ **Scenario 2 is more flexible** but incurs **higher costs due to frequent discharges & grid charging inefficiencies.**  
✔️ **Phase II saves more money** due to **higher solar PV capacity** and **larger total battery storage.**  

## 🚀 Final Deliverables  
✅ **Simulation Results (Hourly/Half-Hourly)** – Load, solar, battery SoC, grid import/export, cost per interval.  
✅ **Summary Tables** – Daily, monthly, annual totals of grid consumption, solar contribution, and battery usage.  
✅ **Energy Yield Analysis** – kWh offset from solar alone.  
✅ **Battery Utilization Metrics** – Number of full cycles, SoC trends.  
✅ **Raw Files** – CSV and Python scripts containing time-series data & cost analysis.  
✅ **Recommendations** – Insights on optimal battery operation and potential inverter adjustments.  

## 📌 Next Steps  
🔹 **Optimize Scenario 2** by implementing a more advanced dispatch logic using **Pyomo** or **PuLP** for optimal cost scheduling.  
🔹 **Include Grid Export Pricing** to analyze potential revenue from solar overgeneration.  
🔹 **Validate the results** with real energy consumption & solar production data from Ireland.  

## 📩 Contact  
For any questions or further analysis, please reach out via **Upwork:https://www.upwork.com/freelancers/~01a14d825a9bd8689d**
 or **LinkedIn:https://www.linkedin.com/in/tanveer-hussain-277119196/**.  

## Upwork Job Description
We, REIN are seeking an experienced Battery Energy Storage System (BESS) Engineer to analyze and simulate the performance of a solar + Battery storage system (DC Coupled) for a project. The goal is to optimize energy savings by reducing grid consumption and discharging the battery during peak hours based on the provided tariff structure.
The project is located in Ireland.
Project Scope:
We require simulations to determine:
• Reduction in grid consumption using solar and battery storage.
• Estimated cost savings from optimized battery discharging during peak hours.
• Energy yield from solar generation (without batteries).
You will be provided with half-hourly client energy consumption data and the site details along with electricity rates breakdown.
Site Details: provisional
Site A (Phase 1)
• Solar Capacity: 8 MWp
• Battery: 16 MWh (0.5C)
• Inverter: 8 MVA (DC:AC = 1)
Site B (Phase 2)
• Solar Capacity: 4.5 MWp
• Battery: 9 MWh (0.5C)
• Inverter: 4.5 MVA (DC:AC = 1)
Simulation Requirements:
Simulation 1:
• Solar generation first charges the battery.
• Once battery is charged, excess solar generation supplies the site.
• Battery discharges only during peak hours (5 PM – 7 PM).
• Battery fully discharges before 11 PM.
Simulation 2:
• Solar generation first charges the battery.
• Once battery is charged, excess solar generation supplies the site.
• Battery discharges during peak hours (5 PM – 7 PM) and during higher day rates if beneficial.
• Battery can charge from lower night rates and discharge during higher day rates.
• Ensure enough battery energy is available for peak hour discharge.

Deliverables:
• Simulation results showing grid consumption hourly reduction and cost savings.
• Energy yield calculations from solar generation alone.
• Cost-benefit analysis of battery discharge strategies.
• Recommendations for optimal battery operation.
• Raw files of the analysis.

Project Phases:
o Phase I: Only site A with Solar and Batteries. (clients wants to split projects into two phases)
o Phase II: Both site A & B with Solar and Batteries

Ideal Candidate:
• Experience in BESS modelling, solar PV simulation, and energy cost analysis.
• Familiarity with grid-connected battery storage optimization.
• Expertise in tools like HOMER, PVSyst, MATLAB, Python, or any relevant simulation software.
• Ability to analyze half-hourly energy data and provide detailed reports.
If you have relevant experience and can deliver accurate simulations for battery storage and solar energy savings, please apply with:
1. Details of similar projects you’ve worked on.
2. Your approach to solving this problem.
3. Expected timeline for the simulations.
Looking forward to working with you!
