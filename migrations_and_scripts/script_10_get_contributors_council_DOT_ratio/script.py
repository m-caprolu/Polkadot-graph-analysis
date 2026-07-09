import json

# Load JSON files
with open('./contributers.json') as f:
    contributers = json.load(f)

with open('./technical_fellowship.json') as f:
    technical_fellowship = json.load(f)

with open('../../exported_balances/balances_2025_04.json') as f:
    balances_raw = json.load(f)

# Convert all to float
balances = {k: float(v) for k, v in balances_raw.items()}

# Filter positive balances only for balance computations
positive_balances = {k: v for k, v in balances.items() if v > 0}

# --- Balance calculations ---
total_balance = sum(positive_balances.values())

# Account sets
all_accounts = set(balances.keys())  # includes negatives and zero
positive_accounts = set(positive_balances.keys())

contributor_accounts = set(contributers) & positive_accounts
fellowship_accounts = set(technical_fellowship) & positive_accounts
rest_accounts = positive_accounts - contributor_accounts - fellowship_accounts

# Balance sums
contributers_total_balance = sum(positive_balances[acc] for acc in contributor_accounts)
technical_fellowship_total_balance = sum(positive_balances[acc] for acc in fellowship_accounts)
rest_balance = sum(positive_balances[acc] for acc in rest_accounts)

# Percentages
pct_contributers = (contributers_total_balance / total_balance) * 100 if total_balance else 0
pct_technical_fellowship = (technical_fellowship_total_balance / total_balance) * 100 if total_balance else 0
pct_rest = (rest_balance / total_balance) * 100 if total_balance else 0

# --- Account counts ---
total_accounts = len(all_accounts)  # includes all, even negative or zero
contributor_count = len(contributor_accounts)
fellowship_count = len(fellowship_accounts)
rest_count = len(rest_accounts)

# --- Output ---
print(f"Total Balance (positive only): {total_balance}")
print(f"Contributors Balance: {contributers_total_balance}")
print(f"Technical Fellowship Balance: {technical_fellowship_total_balance}")
print(f"Rest Balance: {rest_balance}")
print(f"Contributors %: {pct_contributers:.2f}%")
print(f"Technical Fellowship %: {pct_technical_fellowship:.2f}%")
print(f"Rest %: {pct_rest:.2f}%")

print(f"Total Accounts (all balances): {len(all_accounts)}")
print(f"Contributor Accounts (positive balance): {len(contributers)}")
print(f"Technical Fellowship Accounts (positive balance): {len(technical_fellowship)}")
print(f"Rest Accounts (positive balance): {len(all_accounts) - len(contributers) - len(technical_fellowship) }")
