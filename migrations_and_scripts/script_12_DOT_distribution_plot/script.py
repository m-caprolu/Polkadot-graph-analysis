import matplotlib.pyplot as plt
import numpy as np

# Provided data
x_values = [0.5, 1, 1.5, 2, 2.5, 3]  # Total Balance (DOT / 1e7)
y_values = [3468059, 27, 4, 1, 1, 2]  # Number of Accounts

# Plot settings
plt.figure(figsize=(6, 6))  # Square plot
plt.bar(x_values, y_values, width=0.45)

plt.yscale('log')  # Logarithmic scale for y-axis

# LaTeX-style label with scientific scale
plt.xlabel("Total Balance (DOT × $10^7$)")
plt.ylabel("Number of Accounts (log)")
plt.title("(a) Distribution of DOT", fontsize=16)

plt.xticks(x_values)
plt.grid(False)
plt.tight_layout()
plt.show()
