import json
import networkx as nx
import matplotlib.pyplot as plt

def build_graph(data):
    G = nx.MultiDiGraph()
    
    counter = 0
    for era, validators in data.items():
        counter = counter + 1
        for validator, details in validators.items():
            # Add validator node if not already present
            if validator not in G:
                G.add_node(validator) # , role='validator'
            
            # Ensure the era key exists
            if era not in G.nodes[validator]:
                G.nodes[validator][era] = {}

            # Add era-specific data
            G.nodes[validator][era]['blocks_produced'] = details['blocks_produced']
            G.nodes[validator][era]['reward'] = details['reward']
            
            for nominator in details['nominators']:
                nominator_address = nominator['address']
                reward = nominator['reward']
                
                # Add nominator node if not already present
                if nominator_address not in G:
                    G.add_node(nominator_address) # , role='nominator'
                
                # Add edge with reward as attribute
                G.add_edge(nominator_address, validator, reward=reward, era=era)
        print("Processed", counter, "eras")
    return G

if __name__ == "__main__":
    with open('eras_staking_info.json', 'r') as f:
        data = json.load(f)
    
    G = build_graph(data)
    nx.write_gpickle(G, 'validators_and_nominators_graph.gpickle')