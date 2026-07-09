import os
import json
import networkx as nx

if __name__ == "__main__":
    graph = nx.read_gpickle("./exported_graph/updated_graph_25_543_168.gpickle")
    N = 10
    nodes_count = len(graph.nodes)

    print(f"Top {N} accounts with highest balances:")
    degree_dict = dict(graph.degree())

    # Sort nodes by degree in descending order
    top_accounts = sorted(degree_dict.items(), key=lambda x: x[1], reverse=True)[:10]
    for account, degree in top_accounts:
        in_degree = graph.in_degree(account) / nodes_count 
        out_degree = graph.out_degree(account) / nodes_count
        degree_per = degree / nodes_count 
        print(f"{account} {degree_per} {in_degree} {out_degree}")
    
