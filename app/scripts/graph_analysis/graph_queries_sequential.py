# %%
import networkx as nx

# %%
# import matplotlib.pyplot as plt

# %%
digraph = nx.read_gpickle('./exported_graph/updated_graph_25_543_168.gpickle')
print("Graph Reading COMPLETED...")
n_nodes = nx.number_of_nodes(digraph)
print("\tNumber of Nodes: {}".format(n_nodes))
n_edges = nx.number_of_edges(digraph)
print('\tNumber of edges: {}'.format(n_edges))
n_assortativity = nx.degree_assortativity_coefficient(digraph)
print('\tAssortativity: {}'.format(n_assortativity))
n_recpricity = nx.overall_reciprocity(digraph)
print('\tReciprocity: {}'.format(n_recpricity))
n_density = nx.density(digraph)
print("\tDensity: {}".format(n_density))
n_clustering = nx.average_clustering(digraph)
print("\tAverage Clustering: {}".format(n_clustering))
n_transitivity = nx.transitivity(digraph)

print("\t\tTransitivity: {}".format(n_transitivity))

scc_count = nx.number_strongly_connected_components(digraph)
print('\t#SCC: {}'.format(scc_count))
wcc_count = nx.number_weakly_connected_components(digraph)
print('\t#WCC: {}'.format(wcc_count))

giant_scc_comp = digraph.subgraph(max(nx.strongly_connected_components(digraph), key=len))
giant_wcc_comp = digraph.subgraph(max(nx.weakly_connected_components(digraph), key=len))

print('\tGiant SCC component:')
print('\t\tNumber of nodes: {}'.format(giant_scc_comp.number_of_nodes()))
print('\t\tNumber of edges: {}'.format(giant_scc_comp.number_of_edges()))

print('\tGiant WCC component:')
print('\t\tNumber of nodes: {}'.format(giant_wcc_comp.number_of_nodes()))
print('\t\tNumber of edges: {}'.format(giant_wcc_comp.number_of_edges()))

import pdb; pdb.set_trace();

# # %%
# # print("Number of self-loops: {}".format(nx.number_of_selfloops(digraph)))
# # print("Number of Nodes: {}".format(nx.number_of_nodes(digraph)))
# print('Number of edges: {}'.format(nx.number_of_edges(digraph)))

# # %% [markdown]
# # Connectivity: connectivity is one of the basic concepts of graph theory: it asks for the minimum number of elements (nodes or edges) that need to be removed to separate the remaining nodes into two or more isolated subgraphs

# # %%
# # print("Is Strongly Connected? {}".format(nx.is_strongly_connected(digraph)))

# # %%
# # print("Is Weakly Connected? {}".format(nx.is_weakly_connected(digraph)))

# # %%
# print('\tAssortativity: {}'.format(nx.degree_assortativity_coefficient(digraph)))
# print('\tPearson: {}'.format(nx.degree_pearson_correlation_coefficient(digraph)))
# print('\t#SCC: {}'.format(nx.number_strongly_connected_components(digraph)))
# print('\t#WCC: {}'.format(nx.number_weakly_connected_components(digraph)))

# # %%
# print("Average Degree Connectivity: {}".format(nx.average_degree_connectivity(digraph)))

# # %%
# # print("Graph Clique Number: {}".format(nx.graph_clique_number(digraph.to_undirected())))

# # %%
# number_of_nodes = [len(n) for n in sorted(nx.strongly_connected_components(digraph))]
# print("Number of SCC: {}".format(len(number_of_nodes)))
