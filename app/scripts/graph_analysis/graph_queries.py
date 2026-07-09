import networkx as nx
import pdb
import os

from collections import defaultdict
import networkx as nx
from datetime import datetime, timedelta
import calendar
import json

def calculate_balances(graph, start_date, end_date, balances):
    # balances = defaultdict(float)  # Dictionary to store balances for each node

    # Convert datetime to timestamp in milliseconds for easier comparison
    start_timestamp = int(start_date.timestamp() * 1000)
    end_timestamp = int(end_date.timestamp() * 1000)
    
    skipped = 0
    
    # Iterate over all nodes in the graph
    for node in graph.nodes():
        total_inward = 0
        total_outward = 0
        # Process outward transactions
        for neighbor in graph[node]:
            for i in range(len(graph[node][neighbor])):
                edge_data = graph[node][neighbor][i]
                date = edge_data.get('date', None)
                if date is None:
                    skipped += 1
                    continue
                if start_timestamp <= edge_data['date'] <= end_timestamp:
                    total_outward += edge_data['weight']

        for neighbor in graph.pred[node]:
            for i in range(len(graph.pred[node][neighbor])):
                edge_data = graph.pred[node][neighbor][i]
                date = edge_data.get('date', None)
                if date is None:
                    skipped += 1
                    continue
                if start_timestamp <= edge_data['date'] <= end_timestamp:
                    total_inward += edge_data['weight']

        # Calculate balance for the node
        balances[node] += total_inward - total_outward

    print("Skipped {} edges\n".format(skipped))
    return dict(balances)

# Get the directory of the current script
script_dir = os.path.dirname(__file__)
# Construct the relative path to the graph file
graph_file_path = os.path.join(script_dir, '../../../exported_graph/updated_graph_25_543_168.gpickle')
print("Reading graph from file:", graph_file_path)
# Read the graph from the file
try:
    graph = nx.read_gpickle(graph_file_path)
except FileNotFoundError:
    print(f"Error: The file {graph_file_path} was not found.")
    exit(1)
except nx.NetworkXError as e:
    print(f"Error reading the graph: {e}")
    exit(1)

# Process the graph (you can add your processing code here)
# For now, we will just print the number of nodes and edges
num_nodes = graph.number_of_nodes()
num_edges = graph.number_of_edges()

print(f"Number of nodes: {num_nodes}")
print(f"Number of edges: {num_edges}")
pdb.set_trace()
# Loop through all months from May 2020 to Jan 2025
start_year = 2020
end_year = 2025

monthly_balances = {}
balances = defaultdict(float)

for year in range(start_year, end_year + 1):
    for month in range(1, 13):  # Loop through all months
        # Skip months before May 2020
        if year == 2020 and month < 5:
            continue
        # Stop after April 2025
        if year == 2025 and month > 4:
            break

        # Get the first and last day of the month
        start_date = datetime(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        end_date = datetime(year, month, last_day, 23, 59, 59)

        # Calculate balances for the month
        balances = calculate_balances(graph, start_date, end_date, balances)
        # Define the output directory and file path
        output_dir = os.path.join(script_dir, '../../../exported_balances')
        os.makedirs(output_dir, exist_ok=True)
        output_file_path = os.path.join(output_dir, f'balances_{year}_{month:02d}.json')

        # Write the balances to a JSON file
        with open(output_file_path, 'w') as f:
            json.dump(balances, f, indent=4)
        monthly_balances[f"{year}-{month:02d}"] = balances

# Print monthly balances
for month, balances in monthly_balances.items():
    print(f"\nBalances for {month}:")
    for node, balance in balances.items():
        print(f"Node: {node}, Balance: {balance}")
