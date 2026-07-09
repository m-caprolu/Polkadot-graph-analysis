import networkx as nx
import json
# graph = nx.read_gpickle("./updated_graph_25_543_168.gpickle")
# graph = nx.read_gpickle("./updated_graph_25_543_168.gpickle")

import pdb; pdb.set_trace()
import networkx as nx
import datetime

# Load the original graph once (we'll reload it in each iteration)
original_graph_path = "./updated_graph_25_543_168.gpickle"

# Helper: convert a year to epoch milliseconds
def year_to_epoch_ms(year: int) -> int:
    dt = datetime.datetime(year, 1, 1, tzinfo=datetime.timezone.utc)
    return int(dt.timestamp() * 1000)

# Define year ranges
year_ranges = [(2020, 2021), (2021, 2022), (2022, 2023), (2023, 2024), (2024, 2025)]

for start_year, end_year in year_ranges:
    # Reload the original graph each iteration
    G = nx.read_gpickle(original_graph_path)

    start_epoch = year_to_epoch_ms(start_year)
    end_epoch   = year_to_epoch_ms(end_year)

    # Keep only edges within the time range
    edges_to_keep = [
        (u, v, k, data)
        for u, v, k, data in G.edges(keys=True, data=True)
        if "date" in data and start_epoch <= data["date"] < end_epoch
    ]

    # Build a subgraph with only those edges
    H = G.edge_subgraph([(u, v, k) for u, v, k, _ in edges_to_keep]).copy()

    # Remove isolated nodes (nodes without edges)
    isolated_nodes = [n for n in H.nodes if H.degree(n) == 0]
    H.remove_nodes_from(isolated_nodes)

    # Save the filtered graph
    out_path = f"graph_{start_year}.gpickle"
    nx.write_gpickle(H, out_path)
    print(f"Saved {out_path} with {H.number_of_nodes()} nodes and {H.number_of_edges()} edges")