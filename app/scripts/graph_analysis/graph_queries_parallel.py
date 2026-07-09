import networkx as nx
import concurrent.futures
from multiprocessing import freeze_support

# Define functions for parallel computation
def count_self_loops(g):
    return nx.number_of_selfloops(g)

def count_nodes(g):
    return nx.number_of_nodes(g)

def count_edges(g):
    return nx.number_of_edges(g)

def is_strongly_connected(g):
    return nx.is_strongly_connected(g)

def is_weakly_connected(g):
    return nx.is_weakly_connected(g)

def degree_assortativity(g):
    return nx.degree_assortativity_coefficient(g)

def degree_pearson(g):
    return nx.degree_pearson_correlation_coefficient(g)

def count_scc(g):
    return nx.number_strongly_connected_components(g)

def count_wcc(g):
    return nx.number_weakly_connected_components(g)

def avg_degree_connectivity(g):
    return nx.average_degree_connectivity(g)

def clique_number(g):
    return nx.graph_clique_number(g.to_undirected())

def scc_sizes(g):
    return [len(n) for n in sorted(nx.strongly_connected_components(g))]

def main():
    # Read the graph
    print("Graph Reading START...")
    digraph = nx.read_gpickle('../../../exported_graph/updated_graph_26.gpickle')
    print("Graph Reading COMPLETED...")

    # Run computations in parallel
    with concurrent.futures.ProcessPoolExecutor() as executor:
        future_to_function = {
            executor.submit(count_self_loops, digraph): "Number of self-loops",
            executor.submit(count_nodes, digraph): "Number of Nodes",
            executor.submit(count_edges, digraph): "Number of Edges",
            executor.submit(is_strongly_connected, digraph): "Is Strongly Connected?",
            # executor.submit(is_weakly_connected, digraph): "Is Weakly Connected?",
            executor.submit(degree_assortativity, digraph): "Assortativity",
            executor.submit(degree_pearson, digraph): "Pearson",
            executor.submit(count_scc, digraph): "#SCC",
            # executor.submit(count_wcc, digraph): "#WCC",
            executor.submit(avg_degree_connectivity, digraph): "Average Degree Connectivity",
            # executor.submit(clique_number, digraph): "Graph Clique Number",
            executor.submit(scc_sizes, digraph): "Number of SCC"
        }

        for future in concurrent.futures.as_completed(future_to_function):
            function_name = future_to_function[future]
            try:
                result = future.result()
                print(f"{function_name}: {result}")
            except Exception as exc:
                print(f"{function_name} generated an exception: {exc}")

if __name__ == '__main__':
    freeze_support()  # Required for Windows
    main()