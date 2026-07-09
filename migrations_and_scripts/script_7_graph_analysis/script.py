import networkx as nx
from collections import Counter

graph = nx.read_gpickle("./updated_graph_25_543_168.gpickle")

nodes_count = len(graph.nodes)
edges_count = len(graph.edges)

in_degree_counts = Counter(dict(graph.in_degree()).values())
out_degree_counts = Counter(dict(graph.out_degree()).values())

sorted_in_degree_counts = dict(sorted(in_degree_counts.items()))
sorted_out_degree_counts = dict(sorted(out_degree_counts.items()))

import pdb; pdb.set_trace()

