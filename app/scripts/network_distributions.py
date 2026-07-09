"""
network_distributions.py

Graph Analysis of the Polkadot transactions graph.

<Author>: Hanaa Abbas
<Email>: hanaaloutfy94@gmail.com
<Date>: 31 May, 2023

GNU General Public License Version 3
"""

import collections
import logging
import sys
import traceback
from datetime import datetime
from logging.handlers import RotatingFileHandler
from timeit import default_timer as timer
import os

import matplotlib.pyplot as plt
import networkx as nx
import powerlaw  # Power laws are probability distributions with the form:p(x)∝x−α
from dateutil.rrule import rrule, MONTHLY

# create and configure logger
filename = "./logs/network_distributions.log"
logging.basicConfig(level=logging.INFO,
                    handlers=[RotatingFileHandler(filename, maxBytes=1000000000, backupCount=100, mode='a'),
                              logging.StreamHandler(sys.stdout)],
                    format="[%(asctime)s] %(message)s",
                    datefmt='%Y-%m-%dT%H:%M:%S', )
logger = logging.getLogger()


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
        start = datetime(2020, 8, 1)
        end = datetime(2022, 5, 1)
        months_list = [str(d.year) + "-" + str(d.month) for d in rrule(MONTHLY, dtstart=start, until=end)]

        for month in months_list:
            subgraph = nx.MultiDiGraph(((source, target, attr) for source, target, attr in graph.edges(data=True) if
                                        datetime.strptime(attr['date'], "%Y-%m-%d-%H").strftime("%Y-%#m").startswith(
                                            month)))
            logger.info(month)
            # in_degree_freq = degree_histogram_directed(subgraph, in_degree=True)
            # out_degree_freq = degree_histogram_directed(subgraph, out_degree=True)
            # plt.figure(figsize=(12, 8))
            # plt.loglog(range(len(in_degree_freq)), in_degree_freq, 'g-', label='in-degree')
            # plt.loglog(range(len(out_degree_freq)), out_degree_freq, 'b-', label='out-degree')
            # plt.xlabel('Degree (log)')
            # plt.ylabel('Fraction of Nodes (log)')
            # plt.legend(loc="upper right")
            # plt.title('In-Degree and Out-Degree Distribution of {}'.format(month))
            # plt.savefig('output2/degree/monthly-{}-InOut.png'.format(month), bbox_inches='tight')
            #
            # degree = degree_histogram_directed(subgraph)
            # plt.figure(figsize=(12, 8))
            # plt.loglog(range(len(degree)), degree, 'b-', label='degree')
            # plt.xlabel('Degree (log)')
            # plt.ylabel('Fraction of Nodes (log)')
            # plt.legend(loc="upper right")
            # plt.title('Degree Distribution of {}'.format(month))
            # plt.savefig('output2/degree/monthly-{}-Degree.png'.format(month), bbox_inches='tight')

            degree_sequence = sorted([d for n, d in digraph.degree()], reverse=True)
            plt.figure(figsize=(12, 8))
            fit = powerlaw.Fit(degree_sequence, discrete=True)
            fig2 = fit.plot_pdf(color='b', linewidth=2)
            fig2 = fit.plot_pdf(color='g', linewidth=2, label='original data')
            fit.power_law.plot_pdf(color='r', linestyle='--', label='power-law')
            logger.info('degree month {}:== alpha= {} sigma= {}'.format(month, fit.power_law.alpha, fit.power_law.sigma))
            plt.text(60, .025, r'$\alpha=-{:.2f},\ \sigma={:.5f},\ \ xmin={:.2f}$'.format(fit.power_law.alpha,
                                                                                          fit.power_law.sigma,
                                                                                          fit.power_law.xmin))
            plt.legend(loc="upper right")
            plt.title('In-Degree Distribution (with power-law fitting)')
            plt.xlabel('Vertex Degree')
            plt.ylabel('PDF of Vertices')
            plt.savefig('output/degree/monthly-{}-FitCurve.png'.format(month), bbox_inches='tight')

            logger.info("=======================================NEXT======================================")

    except Exception as error:
        logger.error(error)


# Main
if __name__ == '__main__':
    try:
        # Graph Analysis
        start = timer()

        script_dir = os.path.dirname(__file__)
        graph_file_path = os.path.join(script_dir, '../../exported_graph/updated_graph_71.gpickle')
        digraph = nx.read_gpickle(graph_file_path)

        # digraph = nx.read_gpickle('../../output2/multidigraph_without_loops_july.gpickle')
        
        logger.info("Graph Reading COMPLETED...")
        # loop_months(digraph)

        # Degree Distribution
        out_degree_freq = degree_histogram_directed(digraph, out_degree=True)
        in_degree_freq = degree_histogram_directed(digraph, in_degree=True)
        fig = plt.figure(figsize=(12, 8))
        plt.subplot(2, 1, 1)
        plt.loglog(range(len(in_degree_freq)), in_degree_freq, 'g-', label='in-degree')
        plt.ylabel('Number of Nodes (log)')
        plt.legend(loc="upper right")
        plt.subplot(2, 1, 2)
        plt.loglog(range(len(out_degree_freq)), out_degree_freq, 'b-', label='out-degree')
        plt.ylabel('Number of Nodes (log)')
        plt.legend(loc="upper right")
        plt.xlabel('Degree (log)')
        fig.suptitle('In-Degree and Out-Degree Distribution')
        plt.tight_layout()
        plt.savefig('output/degree/InOutDegreeDistribution.png', bbox_inches='tight')

        total_degree = degree_histogram_directed(digraph)
        plt.figure(figsize=(12, 8))
        plt.loglog(range(len(total_degree)), total_degree, 'b-', label='total_degree')
        plt.xlabel('Total Degree (log)')
        plt.ylabel('Number of Nodes (log)')
        plt.title('Degree Distribution')
        plt.savefig('output/degree/TotalDegreeDistribution.png', bbox_inches='tight')

        # https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6399239/
        indegree_sequence = sorted([d for n, d in digraph.in_degree()], reverse=True)
        fig = plt.figure(figsize=(12, 8))
        fit = powerlaw.Fit(indegree_sequence, discrete=True)
        fig2 = fit.plot_pdf(color='g', linewidth=2, label='original data')
        fit.power_law.plot_pdf(color='r', linestyle='--', label='power-law')
        logger.info('In Degree:== alpha= {} sigma= {}'.format(fit.power_law.alpha, fit.power_law.sigma))
        plt.text(60, .025, r'$\alpha=-{:.2f},\ \sigma={:.5f},\ \ xmin={:.2f}$'.format(fit.power_law.alpha, fit.power_law.sigma, fit.power_law.xmin))
        plt.legend(loc="upper right")
        plt.title('In-Degree Distribution (with power-law fitting)')
        plt.xlabel('Vertex In-Degree')
        plt.ylabel('PDF of Vertices')
        plt.savefig('output/degree/power-law-indegree.png', bbox_inches='tight')

        outdegree_sequence = sorted([d for n, d in digraph.out_degree()], reverse=True)
        fig = plt.figure(figsize=(12, 8))
        fit = powerlaw.Fit(outdegree_sequence, discrete=True)
        fig2 = fit.plot_pdf(color='g', linewidth=2, label='original data')
        fit.power_law.plot_pdf(color='r', linestyle='--', label='power-law')
        logger.info('Out Degree:== alpha= {} sigma= {}'.format(fit.power_law.alpha, fit.power_law.sigma))
        plt.text(60, .025, r'$\alpha=-{:.2f},\ \sigma={:.5f},\ \ xmin={:.2f}$'.format(fit.power_law.alpha, fit.power_law.sigma, fit.power_law.xmin))
        plt.legend(loc="upper right")
        plt.title('Out-Degree Distribution (with power-law fitting)')
        plt.xlabel('Vertex Out-Degree')
        plt.ylabel('PDF of Vertices')
        plt.savefig('output/degree/power-law-outdegree.png', bbox_inches='tight')

        degree_sequence = sorted([d for n, d in digraph.degree()], reverse=True)
        fig = plt.figure(figsize=(12, 8))
        fit = powerlaw.Fit(degree_sequence, discrete=True)
        fig2 = fit.plot_pdf(color='g', linewidth=2, label='original data')
        fit.power_law.plot_pdf(color='r', linestyle='--', label='power-law')
        logger.info('Degree:== alpha= {} sigma= {}'.format(fit.power_law.alpha, fit.power_law.sigma))
        plt.text(60, .025, r'$\alpha=-{:.2f},\ \sigma={:.5f},\ \ xmin={:.2f}$'.format(fit.power_law.alpha, fit.power_law.sigma, fit.power_law.xmin))
        plt.legend(loc="upper right")
        plt.title('Degree Distribution (with power-law fitting)')
        plt.xlabel('Vertex Degree')
        plt.ylabel('PDF of Vertices')
        plt.savefig('output/degree/power-law-degree.png', bbox_inches='tight')

        # component size distribution (line graph)
        plt.figure(figsize=(12, 8))
        wcc_component_size = sorted(nx.weakly_connected_components(digraph), key=len, reverse=True)
        sizes = [len(comp) for comp in wcc_component_size]
        values_count = collections.Counter(sizes)
        val, cnt = zip(*values_count.items())
        plt.loglog(val, cnt, 'g-', label='wcc')
        plt.ylabel('Fraction of Nodes (log)')
        wcc_component_size = sorted(nx.strongly_connected_components(digraph), key=len, reverse=True)
        sizes = [len(comp) for comp in wcc_component_size]
        values_count = collections.Counter(sizes)
        val, cnt = zip(*values_count.items())
        plt.loglog(val, cnt, 'b-', label='scc')
        plt.xlabel('Component Size (log)')
        plt.ylabel('Fraction of Nodes (log)')
        plt.legend(loc="upper right")
        plt.title('Components Size Distribution')
        plt.savefig('output/component/full-dist.png', bbox_inches='tight')

        # component size histogram
        plt.figure(figsize=(12, 8))
        fig, ax = plt.subplots(2)
        fig.tight_layout()
        fig.suptitle('Components Size Distribution of Polkadot Transactions Graph')

        scc_component_size = sorted(nx.strongly_connected_components(digraph), key=len, reverse=True)
        scc_sizes = [len(comp) for comp in scc_component_size]
        val2, cnt2 = zip(*collections.Counter(scc_sizes).items())
        # pl = plt.bar(val2, cnt2, width=0.30, color='b', label='SCC')
        pl = ax[0].bar(val2, cnt2, width=0.70, color='b', label='SCC')
        ax[0].legend(loc="upper right")
        for bar in pl:
            ax[0].annotate(bar.get_height(),
                           xy=(bar.get_x() + 0.07, bar.get_height() + 8),
                           fontsize=6)

        wcc_component_size = sorted(nx.weakly_connected_components(digraph), key=len, reverse=True)
        wcc_sizes = [len(comp) for comp in wcc_component_size]
        val1, cnt1 = zip(*collections.Counter(wcc_sizes).items())
        pl = ax[1].bar(val1, cnt1, width=0.70, color='g', label='WCC')
        for bar in pl:
            ax[1].annotate(bar.get_height(),
                           xy=(bar.get_x() + 0.07, bar.get_height() + 8),
                           fontsize=6)

        ax[0].set_xticks([v + 0.4 for v in val1])
        ax[0].set_xticklabels(val1)
        ax[1].set_xticks([v + 0.4 for v in val1])
        ax[1].set_xticklabels(val1)

        ax[0].set_xscale('log')
        ax[0].set_yscale('log')
        ax[1].set_xscale('log')
        ax[1].set_yscale('log')

        plt.xlabel('Component Size (log)')
        plt.ylabel('# Nodes (log)')
        plt.legend(loc="upper right")
        fig.tight_layout()
        plt.savefig('output/component/hist-component-dist.png', bbox_inches='tight')

        logger.info("=======================================END======================================")
        logger.info("Graph Analysis Total Execution Time (seconds): {}".format(timer() - start))

    except Exception as err:
        logger.error(traceback.format_exc())
