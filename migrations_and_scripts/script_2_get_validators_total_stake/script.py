from substrateinterface import SubstrateInterface

def get_staking_exposure(era, validator):
    substrate = SubstrateInterface(url="wss://10.70.43.152:9933")

    # Fetch staking exposure from erasStakersClipped
    exposure = substrate.query(
        module="Staking",
        storage_function="ErasStakersClipped",
        params=[era, validator]
    )

    if exposure is None:
        print(f"No staking data for validator: {validator}")
        return

    # Extracting total stake, own stake, and nominators
    print("Exposure: ", exposure)
    total_stake = int(exposure['total'])
    own_stake = int(exposure['own'])
    nominators = [(n['who'], int(n['value'])) for n in exposure['others']]

    print(f"Era {era} - Validator {validator}:")
    print(f"  Total Stake: {total_stake}")
    print(f"  Own Stake: {own_stake}")
    print(f"  Nominators ({len(nominators)}):")
    for nominator, value in nominators:
        print(f"    {nominator}: {value}")

    substrate.close()

# Example usage
era = 1702  # Replace with your target era
validator = "13Ybj8CPEArUee78DxUAP9yX3ABmFNVQME1ZH4w8HVncHGzc"  # Replace with actual validator ID
get_staking_exposure(era, validator)
