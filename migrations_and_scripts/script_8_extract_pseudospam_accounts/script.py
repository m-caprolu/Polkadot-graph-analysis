import csv

# File paths
pseudospam_file = 'pseudospam_accounts.csv'
proper_file = 'proper_accounts.csv'

def load_unique_addresses(file_path):
    """Load unique addresses from a CSV file."""
    unique_addresses = set()
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        next(reader)  # Skip the header row
        for row in reader:
            from_address, to_address = row
            unique_addresses.add(from_address)
            unique_addresses.add(to_address)
    return unique_addresses

# Load unique addresses from both files
proper_addresses = load_unique_addresses(proper_file)
pseudospam_addresses = load_unique_addresses(pseudospam_file)

# Find addresses in pseudospam but not in proper
unique_pseudospam_only = pseudospam_addresses - proper_addresses

# Output the result
print("Addresses in pseudospam but not in proper:")
import pdb; pdb.set_trace()
for address in unique_pseudospam_only:
    print(address)