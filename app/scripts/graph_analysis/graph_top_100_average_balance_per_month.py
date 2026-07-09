import json
import glob

# Initialize start and end dates
start_year, start_month = 2020, 5
end_year, end_month = 2025, 5

# Helper function to generate file names in the specified range
def generate_file_names(start_year, start_month, end_year, end_month):
    current_year, current_month = start_year, start_month
    file_names = []

    while (current_year < end_year) or (current_year == end_year and current_month <= end_month):
        file_names.append(f"balances_{current_year}_{current_month:02}.json")
        
        # Move to the next month
        current_month += 1
        if current_month > 12:
            current_month = 1
            current_year += 1

    return file_names

# Generate the file names
file_names = generate_file_names(start_year, start_month, end_year, end_month)

# Analyze each file
results = []

for file_name in file_names:
    try:
        # Read file content
        file_name = f"./exported_balances/{file_name}"
        with open(file_name, 'r') as file:
            data = json.load(file)

        # Filter positive balances
        positive_balances = [balance for balance in data.values() if balance > 0]
        # positive_balances = [balance if balance > 0 else 0 for balance in data.values()]

        if not positive_balances:
            print(f"No positive balances in {file_name}")
            results.append(0)
            continue
        positive_balances = [balance for balance in data.values() if balance > 0]

        # Sort balances descending
        sorted_balances = sorted(positive_balances, reverse=True)

        # Calculate averages
        top_100_balances = sorted_balances[:100]
        rest_balances = sorted_balances[100:]

        top_100_average = sum(top_100_balances) / len(top_100_balances) if top_100_balances else 0
        rest_average = sum(rest_balances) / len(rest_balances) if rest_balances else 0

        if rest_average > 0:
            ratio = top_100_average / rest_average
            results.append(ratio)
            print(f"{file_name}: {ratio:.4f}")
        else:
            print(f"No accounts outside the top 100 or their average is zero in {file_name}.")
            results.append(0)

    except FileNotFoundError:
        print(f"File not found: {file_name}")
        results.append(0)
    except json.JSONDecodeError:
        print(f"Invalid JSON format in {file_name}")
        results.append(0)

# Print all results separated by spaces
print(" ".join(map(lambda x: f"{x:.4f}", results)))
