import networkx as nx
import json
graph = nx.read_gpickle("./validators_and_nominators_graph.gpickle")
graph_json = json.load(open('eras_staking_info.json'))
import pdb; pdb.set_trace()
num_nominators = sum(1 for node, data in graph.nodes(data=True) if data.get("role") == "nominator")
num_validators = sum(1 for node, data in graph.nodes(data=True) if data.get("role") == "validator")
