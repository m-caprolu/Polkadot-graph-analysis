import json
from collections import defaultdict

# Specify the target file for October 2024
file_name = "./exported_balances/balances_2024_10.json"

# Analyze the specified file
range_counts = defaultdict(int)
range_size = 10**7/2  # 1M ranges

try:
    # Read file content
    with open(file_name, 'r') as file:
        data = json.load(file)

    # Filter positive balances and calculate range counts
    for balance in data.values():
        if balance > 0:
            range_index = int(balance // range_size)
            range_counts[range_index] += 1

    print(f"Processed {file_name}")

except FileNotFoundError:
    print(f"File not found: {file_name}")
except json.JSONDecodeError:
    print(f"Invalid JSON format in {file_name}")

# Print the range counts
for range_index, count in sorted(range_counts.items()):
    range_start = range_index * range_size
    range_end = (range_index + 1) * range_size - 1
    print(f"{range_start} - {range_end}: {count} accounts")
