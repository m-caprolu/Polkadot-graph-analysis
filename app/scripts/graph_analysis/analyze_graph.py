# %%
import networkx as nx

# %%
# import matplotlib.pyplot as plt

# %%
digraph = nx.read_gpickle('./exported_graph/updated_graph_25_543_168.gpickle')
print("Graph Reading COMPLETED...")

# import pdb; pdb.set_trace();

digraph.remove_node('ClaimAttestsSystem')
digraph.remove_node('StakingRewardSystem')

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