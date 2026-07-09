from substrateinterface import SubstrateInterface

substrate = SubstrateInterface(
    url="wss://rpc.polkadot.io",
    type_registry_preset="polkadot"
)

era_index = 1890
validator_stash = "16KDeHRyHTXhTSkv3BDNKzBVrxsqdqvNacLy4TH5DfD64yEG"

result = substrate.query(
    module='Staking',
    storage_function='ErasStakers',
    params=[era_index, validator_stash]
)

exposure = result.value
print("Total stake:", exposure['total'])
print("Own stake:", exposure['own'])
print("Nominators:")
for nom in exposure['others']:
    print(f" - {nom['who']} staked {nom['value']}")
