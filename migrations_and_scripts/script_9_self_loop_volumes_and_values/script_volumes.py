import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Read the CSV
df = pd.read_csv('self_loop_volumes.csv')

# Convert day to datetime
df['day'] = pd.to_datetime(df['day'])

# Plotting
plt.figure(figsize=(14, 7))
plt.plot(df['day'], df['count'], color='skyblue')

# Format the x-axis to show month and year every 6 months
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=6))
plt.xticks(rotation=45, fontsize=16)

# Labels and title with updated font sizes
plt.xlabel('Date', fontsize=20)
plt.ylabel('Transactions Volume (log scale)', fontsize=20)
plt.title('Self-loop Transactions: Volume over Time', fontsize=20)

# Y-axis scale and grid
plt.gca().set_yscale('log')
plt.grid(True, linestyle='--', linewidth=0.5)
plt.tight_layout()

# Show plot
plt.show()
