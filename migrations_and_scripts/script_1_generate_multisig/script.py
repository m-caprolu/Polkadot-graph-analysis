from substrateinterface import SubstrateInterface, Keypair

def generate_multisig(addresses, threshold):
    # Connect to a Polkadot node
    substrate = SubstrateInterface(
        url="wss://rpc.polkadot.io",
        type_registry_preset='polkadot'
    )

    # Generate multisig address
    multisig_address = substrate.generate_multisig_account(
        signatories=addresses,
        threshold=threshold
    )

    return multisig_address

if __name__ == "__main__":
    # Example addresses and threshold
    addresses = ['121avdvM8H6BUgxFrg8fVT5mH346XNYW5YEwdo3xvLnhL9rn',
                #  '12rEKaqDn6r5UDGnjXRt3SQyjixsVedWm5KzmfQoXD4EHTyV', 
                 '12gtHEvUQzHV2n4CnYsHZfs9iKRaVwssaLsP3xHbqwpapfH1', 
                 '13b1ppco1mQLBLGX71zBabh7aUaEvqQVoSWhQmHGjWwGTjxM', 
                 '143faiSeYd3agjdp5PBbg4iuFioeRJyC12ZuGsXJRGetaBNU', 
                 '16fn8ZaWKUJ8XVnRsJjsHZqJy1ZUHUfkzDwiUPRRKUV4o2BN',
                 '12eG9pcfYthDyqV12koahZDj3rd7J3zrWhFwwv3zXbjQRV9s'
                 ]


    threshold = 4

    multisig_address = generate_multisig(addresses, threshold)
    print(f"Generated multisig address: {multisig_address}")