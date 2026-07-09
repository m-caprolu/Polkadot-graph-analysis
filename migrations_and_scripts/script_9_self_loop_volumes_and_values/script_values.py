import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.dates as mdates
import numpy as np

# Set global font size BEFORE plotting
plt.rcParams.update({'font.size': 20})

# Load the data
df = pd.read_csv('self_loop_values.csv')

# Convert timestamp from milliseconds to datetime
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

# Define specific top addresses
top_addresses = [
    '13sJXsUBHpiPyaKDYk6EfYz7VEBknGubTx5SBafvDDBdnga9',
    '14gE9dZTMJouPRZhotTvM1vNbaaGJgDmWJHsUhtcQ4jXs4ov'
]

# Plot setup
plt.figure(figsize=(14, 7))
plt.yscale('log')

# Plot all data
plt.scatter(df['timestamp'], df['value'], s=1, c='black', label='All addresses')

# Color map for top addresses
cmap = plt.get_cmap('tab10')

# Highlight top addresses
for i, addr in enumerate(top_addresses):
    subset = df[df['from_address'] == addr]
    label = addr[:10] + '...' + addr[-6:]  # Optional: shorten label
    plt.scatter(subset['timestamp'], subset['value'], s=10, color=cmap(i), label=label)

# Format x-axis
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=6))
plt.xticks(rotation=45)

# Labels and title
plt.xlabel('Time', fontsize=20)
plt.ylabel('TXs value (log scale)', fontsize=20)
plt.title('Self-loop Transaction: Values over Time', fontsize=20)

# Legend and grid
plt.legend(fontsize=16)
plt.grid(True, which="both", linestyle='--', linewidth=0.5)
plt.tight_layout()

# Show plot
plt.show()
