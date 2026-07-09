import json
import matplotlib.pyplot as plt
from collections import defaultdict

# Specify the target file
file_name = "../../exported_balances/balances_2025_04.json"

# Initialize
range_counts = defaultdict(int)
range_size = 1000000  # 500 DOT ranges

try:
    # Load balances
    with open(file_name, 'r') as file:
        data = json.load(file)

    # Count how many fall in each balance range
    top_accounts = sorted(data.items(), key=lambda x: float(x[1]), reverse=True)[:10]

    # Print them
    for account, balance in top_accounts:
        print(f"Account: {account}, Balance: {balance}")

    for balance in data.values():
        balance = float(balance)
        if balance > 0:
            range_index = int(balance // range_size)
            range_counts[range_index] += 1

    print(f"Processed {file_name}")

except FileNotFoundError:
    print(f"File not found: {file_name}")
    exit()
except json.JSONDecodeError:
    print(f"Invalid JSON format in {file_name}")
    exit()

# Prepare data for plotting
x_vals = []
y_vals = []

for range_index in sorted(range_counts):
    range_start = range_index * range_size
    range_end = (range_index + 1) * range_size - 1
    count = range_counts[range_index]

    x_vals.append(range_start)
    y_vals.append(count)

    # print(f"{range_start:.0f} - {range_end:.0f}: {count} accounts")

# # --- Plotting ---
# plt.figure(figsize=(10, 5))
# plt.plot(x_vals, y_vals, marker='o')
# plt.xlabel("Balance Range Start (DOT)")
# plt.ylabel("Number of Accounts")
# plt.yscale('log') 
# plt.title("Account Count per Balance Range")
# plt.grid(True)
# plt.tight_layout()
# plt.show()

# --- Plotting as a bar chart ---
plt.figure(figsize=(10, 5))
plt.bar(x_vals, y_vals, width=range_size)  # width controls bar spacing
plt.xlabel("Balance Range Start (DOT)")
plt.ylabel("Number of Accounts (log)")
plt.title("Account Count per Balance Range")
plt.yscale('log')  # Log scale for y-axis
plt.grid(True)
plt.tight_layout()
plt.show()
