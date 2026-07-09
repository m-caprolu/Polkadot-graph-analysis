# Polkadot Analysis
This project is intended to be the first of its type to generate and analyze Polkadot's network through the analysis of its full transaction graph.
Polkadot uses a phased roll-out deployment approach, therefore, the transfer function was not actually enabled from the start of the network, i.e., genesis block. 
Hence, we base our analysis starting from when the transfer function was enabled on August 18, 2020. You are free to start your analysis earlier on in the chain.
To do so, modify the global parameter, `BLOCK_TRANSFER_FUNCTION` in the `main.py` file. 

## Polkadot:
Polkadot is a sharded multi-chain framework, built using the Substrate framework. Substrate provides a set of pallets that you can enable in your chain's runtime.  
In this project, we only handle the querying of block data, including events, extrinsics and accounts for the purpose of generating the network's transaction graph.

### Structure of the Graph:
In Polkadot's transaction graph, a node corresponds to a user address and an edge corresponds to a transaction. The attributes of the edge are the timestamp and the value of the transaction. 
In Polkadot, transactions are referred to as signed extrinsics.
For our purposes, we are only interested in extrinsics having ``module_id`` as ``Balances`` and `call_id` being either `transfer` or `transfer_keep_alive`.

For a more comprehensive implementation of a true Money Flow Graph, one should include other signed extrinsics related to `staking` rewards, `tips` and other form of `deposits` into the treasury or other accounts, for example, 
transaction fee deposits. Note that on Polkadot, before a transaction is accepted, the transaction fee is deducted from the sender's account first. 

There are several types of accounts or keys, namely the ``Controller`` and `Stash` accounts. Each account corresponds to a unique public key. Public keys are represented using `SS58 Format` on Polkadot and most substrate-based blockchains. The format encoding allows the identification of the network from the prefix value of the address. 
For instance, from the address value alone, one can distinguish whether this account belongs to Polkadot or Kusama, the canary network of Polkadot. 

### Graph Metrics:
The appropriate graph metrics are to be decided. 

## How to Use and Install:
The python script is split into two module: (1) data collector, and (2) graph builder and analyzer.
The first script connects to the substrate instance and queries all blocks in the specified range. The data is stored in a pre-created MySQL database. 
For the structure of the database, please refer to the ``schema.sql`` file. Run the SQL commands in order: schema creation, table creation, then finally triggers. 
We have added two triggers to document historical changes to user accounts on Polkadot. 

Install the project requirements using the ``requirements.txt`` file, and also install networkx dependencies:
> pip install -r requirements.txt
> pip install networkx[default,extra]

On Windows, you will need to install Visual Studio Build Tools for the installation to complete successfully.
Make sure to install the latest MVSC Build Tools, Windows SDK corresponding your OS version, and ``C++/CLI tools``.

If you run from commandline, ensure that you run this command for the program to run:
> set "PYTHONPATH=%cd%" 

#### Database setup
1. Install mysql locally
2. Connect to mysql using: `sudo mysql -u root`
3. Run commands in `schema.sql`

#### Command to Run:
```python3 -m app.scripts.main --url=wss://rpc.polkadot.io```
- Write `y` to accept option. E.g. Clear DB.