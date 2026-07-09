import os
import json

def load_balances(folder_path, file_name):
    file_path = os.path.join(folder_path, file_name)
    
    with open(file_path, mode='r') as file:
        balances = json.load(file)
    
    return balances

def get_top_accounts(balances, top_n=100):
    sorted_accounts = sorted(balances.items(), key=lambda item: item[1], reverse=True)
    return sorted_accounts[:top_n]

def count_negative_balances(balances):
    return sum(1 for balance in balances.values() if balance < 0)

if __name__ == "__main__":
    folder_path = 'exported_balances'
    file_name = 'balances_2025_04.json'
    
    balances = load_balances(folder_path, file_name)
    
    top_accounts = get_top_accounts(balances)
    negative_balance_count = count_negative_balances(balances)
    
    print("Top 10 accounts with highest balances:")
    for account, balance in top_accounts:
        print(f"Account: {account}, Balance: {balance}")
    
    print(f"Number of accounts with negative balances: {negative_balance_count}")
