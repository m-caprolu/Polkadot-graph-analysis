import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler

import matplotlib.pyplot as plt
import networkx as nx

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from scipy.optimize import curve_fit
import numpy as np

from timeit import default_timer as timer
import pytz

from random import sample
from datetime import datetime
from dateutil.rrule import rrule, MONTHLY

# create and configure logger
filename = "../../logs2/xnetworkx_analysis_aug24.log"
logging.basicConfig(level=logging.INFO,
                    handlers=[RotatingFileHandler(filename, maxBytes=1000000000, backupCount=100, mode='a'),
                              logging.StreamHandler(sys.stdout)],
                    format="[%(asctime)s] %(message)s",
                    datefmt='%Y-%m-%dT%H:%M:%S', )
logger = logging.getLogger()

DB_NAME = "polkadot_analysis"
DB_HOST = "localhost"
DB_PORT = 3306
DB_USERNAME = "root"
DB_PASSWORD = "root"
DEBUG = False

DB_CONNECTION = "mysql+mysqlconnector://{}:{}@{}:{}/{}".format(
    DB_USERNAME, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME)

engine = create_engine(DB_CONNECTION, echo=DEBUG, isolation_level="READ_UNCOMMITTED", pool_pre_ping=True)
session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
db_session = scoped_session(session_factory)


def create_graph(transactions):
    # Directed graphs with self loops and parallel edges
    # weighted edges
    di_graph = nx.MultiDiGraph()
    for row in transactions:
        try:
            date = datetime.fromtimestamp(row.timestamp / 1e3)
            date = date.strftime("%Y-%m-%d-%H")
            di_graph.add_edge(row.from_address, row.to_address, weight=float(row.value), date=date)
        except Exception as err:
            datetime = row.datetime
            dt_utc = datetime.astimezone(pytz.UTC).strftime("%Y-%m-%d-%H")
            di_graph.add_edge(row.from_address, row.to_address, weight=float(row.value), date=dt_utc)
            # logger.error("Error at transaction id {}-{}".format(row.block_id, row.extrinsic_idx))
    return di_graph


def print_node_degrees(graph, node):
    logger.info('\tDegrees data for node {}'.format(node))
    logger.info("\t\tMost important node In-Degree: {} || Weighted: {}".format(graph.in_degree(node),
                                                                               graph.in_degree(node, weight='weight')))
    logger.info("\t\tMost important node Out-Degree: {} || Weighted: {}".format(graph.out_degree(node),
                                                                                graph.out_degree(node,
                                                                                                 weight='weight')))
    logger.info("\t\tMost important node Total-Degree: {} || Weighted: {}".format(graph.degree(node),
                                                                                  graph.degree(node, weight='weight')))


# Centrality can be calculated by Degrees,Closeness or Betweenness.
def compute_centrality(g):
    nodes_degrees = nx.degree_centrality(g)
    max_centrality = max(nodes_degrees, key=nodes_degrees.get)
    logger.info(
        "\t\t\tNode with Max Degree Centrality: {}  || Degree: {} ".format(max_centrality,
                                                                           nodes_degrees[max_centrality]))
    return max_centrality

def func(x, a, b, c):
    return a * np.exp(-b * x) + c

def plot_scc(G):
    giant_comp = max(nx.strongly_connected_components(G), key=len)
    nx.write_gpickle(digraph, 'output2/giant_comp.gpickle')
    compute_centrality(giant_comp)
    logger.info('\tGiant component:')
    logger.info('\t\tNumber of nodes: {}'.format(giant_comp.number_of_nodes()))
    logger.info('\t\tNumber of edges: {}'.format(giant_comp.number_of_edges()))


def plot_centrality(G, month):
    # remove randomly selected nodes (to make example fast)
    G = G.to_undirected()
    num_to_remove = int(len(G) / 1.5)
    nodes = sample(list(G.nodes), num_to_remove)
    G.remove_nodes_from(nodes)

    # remove low-degree nodes
    low_degree = [n for n, d in G.degree() if d < 10]
    G.remove_nodes_from(low_degree)

    # largest connected component
    components = nx.connected_components(G)
    largest_component = max(components, key=len)
    H = G.subgraph(largest_component)

    # compute centrality
    centrality = nx.degree_centrality(H)  # , k=10, endpoints=True

    # compute community structure
    lpc = nx.community.label_propagation_communities(H)
    community_index = {n: i for i, com in enumerate(lpc) for n in com}

    #### draw graph ####
    fig, ax = plt.subplots(figsize=(20, 15))
    pos = nx.spring_layout(H, k=0.15, seed=4572321)
    node_color = [community_index[n] for n in H]
    node_size = [v * 20000 for v in centrality.values()]
    nx.draw_networkx(
        H,
        pos=pos,
        with_labels=False,
        node_color=node_color,
        node_size=node_size,
        edge_color="gainsboro",
        alpha=0.4,
    )

    # Title/legend
    font = {"color": "k", "fontweight": "bold", "fontsize": 20}
    ax.set_title("Transaction Graph (Largest Connected Component)", font)
    # Change font color for legend
    font["color"] = "r"

    # ax.text(
    #     0.80,
    #     0.10,
    #     "node color = community structure",
    #     horizontalalignment="center",
    #     transform=ax.transAxes,
    #     fontdict=font,
    # )
    # ax.text(
    #     0.80,
    #     0.06,
    #     "node size = betweeness centrality",
    #     horizontalalignment="center",
    #     transform=ax.transAxes,
    #     fontdict=font,
    # )

    # Resize figure for label readibility
    ax.margins(0.1, 0.05)
    fig.tight_layout()
    plt.axis("off")
    plt.savefig('output2/monthly/monthly-{}.png'.format(month), bbox_inches='tight')
    # plt.show()


def degree_histogram_directed(G, in_degree=False, out_degree=False):
    """Return a list of the frequency of each degree value.

    Parameters
    ----------
    G : Networkx graph
       A graph
    in_degree : bool
    out_degree : bool

    Returns
    -------
    hist : list
       A list of frequencies of degrees.
       The degree values are the index in the list.

    Notes
    -----
    Note: the bins are width one, hence len(list) can be large
    (Order(number_of_edges))
    """
    nodes = G.nodes()
    if in_degree:
        in_degree = dict(G.in_degree())
        degseq = [in_degree.get(k, 0) for k in nodes]
    elif out_degree:
        out_degree = dict(G.out_degree())
        degseq = [out_degree.get(k, 0) for k in nodes]
    else:
        degseq = [v for k, v in G.degree()]
    dmax = max(degseq) + 1
    freq = [0 for d in range(dmax)]
    for d in degseq:
        freq[d] += 1
    return freq


def loop_months(graph):
    try:
        start = datetime(2021, 1, 1)
        end = datetime(2022, 2, 28)
        months_list = [str(d.year) + "-" + str(d.month) for d in rrule(MONTHLY, dtstart=start, until=end)]

        for month in months_list:
            subgraph = nx.MultiDiGraph(((source, target, attr) for source, target, attr in graph.edges(data=True) if
                                        datetime.strptime(attr['date'], "%Y-%m-%d-%H").strftime("%Y-%#m").startswith(
                                            month)))
            nx.write_gpickle(subgraph, 'output2/graphs/multidigraph_{}.gpickle'.format(month))
            logger.info(month)

            logger.info("\tNumber of self-loops: {}".format(nx.number_of_selfloops(subgraph)))
            logger.info("\tNumber of Nodes: {}".format(nx.number_of_nodes(subgraph)))
            logger.info('\tNumber of edges: {}'.format(nx.number_of_edges(subgraph)))

            max_centrality = compute_centrality(subgraph)
            print_node_degrees(subgraph, max_centrality)
            logger.info("\tDensity: {}".format(nx.density(subgraph)))
            logger.info('\tAssortativity: {}'.format(nx.degree_assortativity_coefficient(subgraph)))
            logger.info('\tPearson: {}'.format(nx.degree_pearson_correlation_coefficient(subgraph)))

            logger.info('\tStrongly connected components:')
            logger.info("\t\tNumber of SCC components: {}".format(nx.number_strongly_connected_components(subgraph)))
            sccs = nx.strongly_connected_components(subgraph)

            logger.info('\t\tGiant SCC component:')
            giant_comp = max(sccs, key=len)
            giant_comp_graph = subgraph.subgraph(giant_comp)
            compute_centrality(giant_comp_graph)
            logger.info('\t\t\tNumber of nodes: {}'.format(giant_comp_graph.number_of_nodes()))
            logger.info('\t\t\tNumber of edges: {}'.format(giant_comp_graph.number_of_edges()))

            indegree = dict(giant_comp_graph.in_degree())
            outdegree = dict(giant_comp_graph.out_degree())
            degree = dict(giant_comp_graph.degree())

            logger.info("\t\t\tMost important node is: In-Degree {} || Out-Degree: {} || Total Degree:  {}".
                        format(max(indegree), max(outdegree), max(degree)))

            logger.info('\tWeakly connected components:')
            logger.info("\t\tNumber of WCC components: {}".format(nx.number_weakly_connected_components(subgraph)))
            wccs = nx.weakly_connected_components(subgraph)

            logger.info('\t\tGiant WCC component:')
            giant_comp = max(wccs, key=len)
            giant_comp_graph = subgraph.subgraph(giant_comp)
            compute_centrality(giant_comp_graph)
            logger.info('\t\t\tNumber of nodes: {}'.format(giant_comp_graph.number_of_nodes()))
            logger.info('\t\t\tNumber of edges: {}'.format(giant_comp_graph.number_of_edges()))

            indegree = dict(giant_comp_graph.in_degree())
            outdegree = dict(giant_comp_graph.out_degree())
            degree = dict(giant_comp_graph.degree())

            logger.info("\t\t\tMost important node is: In-Degree {} || Out-Degree: {} || Total Degree:  {}".
                        format(max(indegree), max(outdegree), max(degree)))

            # plot_centrality(subgraph, month)

            logger.info("=======================================END======================================")

    except Exception as error:
        logger.error(error)


def in_degree_histogram(G):
    G = G.to_directed()
    inde = list(G.in_degree().values())
    dmax = max(inde) + 1
    freq = [0 for d in range(dmax)]
    for d in inde:
        freq[d] += 1
    return freq


def out_degree_histogram(G):
    inde = list(G.out_degree().values())
    dmax = max(inde) + 1
    freq = [0 for d in range(dmax)]
    for d in inde:
        freq[d] += 1
    return


# Main
if __name__ == '__main__':
    try:
        # Graph Analysis
        start = timer()
        # Conditions for a proper balance transfer
        # signed_transactions = db_session.query(Transaction).filter(Transaction.signed == 1,
        #                                                            Transaction.to_address.is_not(None),
        #                                                            Transaction.from_address.is_not(None),
        #                                                            Transaction.from_address != Transaction.to_address,
        #                                                            Transaction.success == 1,
        #                                                            Transaction.value > 0,
        #                                                            Transaction.module_id == 'Balances',
        #                                                            Transaction.call_id.in_(
        #                                                                ['transfer', 'transfer_keep_alive',
        #                                                                 'transfer_all'])
        #                                                            )
        # count = signed_transactions.count()
        # logger.info("SUCCESSFUL Balances Transfer (only) Count={}".format(
        #     count))  # 6288538,6261388(w/o self loops) digraph = create_graph(signed_transactions)

        # digraph = create_graph(signed_transactions)
        # logger.info("GRAPH CREATED!!!!!!")
        # nx.write_gpickle(digraph, 'output2/multidigraph_without_loops_july.gpickle')

        digraph = nx.read_gpickle('../../output2/multidigraph_without_loops_july.gpickle')
        logger.info("Graph Reading COMPLETED...")

        # loop_months(digraph)

        fig, ax = plt.subplots()
        degree = nx.degree_histogram(digraph)
        x = range(len(degree))
        y = [z / float(sum(degree)) for z in degree]
        # plt.loglog(x, y, color="blue", linewidth=2)
        x = np.log(x)
        y = np.log(y + 1)  # Need to add something to make log work
        popt, pcov = curve_fit(func, x, y)
        ax.plot(x, func(x, *popt), 'g--', label='power-law fit')
        ax.plot(x, y, 'bo', label='data')

        plt.title("Degree Distribution")
        plt.legend(loc="upper right")
        plt.xlabel('Degree Size')
        plt.ylabel('Fraction of Nodes (log)')
        plt.savefig("degree_distribution.png")
        plt.show()
        # plt.clf()

        #
        logger.info("\tNumber of self-loops: {}".format(nx.number_of_selfloops(digraph)))
        logger.info("\tNumber of Nodes: {}".format(nx.number_of_nodes(digraph)))
        logger.info('\tNumber of edges: {}'.format(nx.number_of_edges(digraph)))
        logger.info('\tAssortativity: {}'.format(nx.degree_assortativity_coefficient(digraph)))
        logger.info('\tReciprocity: {}'.format(nx.overall_reciprocity(digraph)))
        logger.info('\tPearson: {}'.format(nx.degree_pearson_correlation_coefficient(digraph)))
        logger.info("\tDensity: {}".format(nx.density(digraph)))
        logger.info('\t#SCC: {}'.format(nx.number_strongly_connected_components(digraph)))
        logger.info('\t#WCC: {}'.format(nx.number_weakly_connected_components(digraph)))

        # Found infinite path length because the graph is not connected
        # logger.info("\tUndirected Graph Diameter: {}".format(nx.diameter(graph)))

        # logger.info("\tAverage Degree Connectivity: {}".format(nx.average_degree_connectivity(digraph)))

        # The degree centrality for a node v is the fraction of nodes it is connected to.
        # logger.info('\tDegree Centrality:')
        # nodes_degrees = nx.degree_centrality(digraph)
        # max_centrality = sorted(nodes_degrees, key=nodes_degrees.get, reverse=True)[:20]
        # for a in max_centrality:
        #     logger.info("{} -----> {}".format(a, nodes_degrees[a]))
        #
        # logger.info('\tIn-Degree Centrality:')
        # nodes_degrees = nx.in_degree_centrality(digraph)
        # max_centrality = sorted(nodes_degrees, key=nodes_degrees.get, reverse=True)[:20]
        # for a in max_centrality:
        #     logger.info("{} -----> {}".format(a, nodes_degrees[a]))
        #
        # logger.info('\tOut-Degree Centrality:')
        # nodes_degrees = nx.out_degree_centrality(digraph)
        # max_centrality = sorted(nodes_degrees, key=nodes_degrees.get, reverse=True)[:20]
        # for a in max_centrality:
        #     logger.info("{} -----> {}".format(a, nodes_degrees[a]))


        # undirected graph
        # graph = nx.Graph(digraph)
        # logger.info("\t\tTransitivity: {}".format(nx.transitivity(graph)))
        # logger.info("\t\tTriangles: {}".format(nx.triangles(graph)))
        # logger.info("\tAverage Clustering: {}".format(nx.average_clustering(graph)))

        # giant_scc_comp = digraph.subgraph(max(nx.strongly_connected_components(digraph), key=len))
        # giant_wcc_comp = digraph.subgraph(max(nx.weakly_connected_components(digraph), key=len))
        #
        # logger.info('\tGiant SCC component:')
        # logger.info('\t\tNumber of nodes: {}'.format(giant_scc_comp.number_of_nodes()))
        # logger.info('\t\tNumber of edges: {}'.format(giant_scc_comp.number_of_edges()))
        #
        # logger.info('\tGiant WCC component:')
        # logger.info('\t\tNumber of nodes: {}'.format(giant_wcc_comp.number_of_nodes()))
        # logger.info('\t\tNumber of edges: {}'.format(giant_wcc_comp.number_of_edges()))
        #

        logger.info("Graph Analysis Total Execution Time (seconds): {}".format(timer() - start))

    except Exception as err:
        db_session.remove()  # close db connection
        logger.error(traceback.format_exc())
