
from substrateinterface import SubstrateInterface

# Connect to the local Polkadot node (HTTP or WS endpoint)
substrate = SubstrateInterface(
    url="http://127.0.0.1:9933", 
    type_registry_preset='polkadot'
)

# --- Quick balance lookup at specific blocks ---
TARGET_ADDRESS = "16ZL8yLyXv3V3L3z9ofR1ovFLziyXaN1DPq4yffMAZ9czzBD"
BLOCKS = [27643048, 2115964]  # (newer, older)

for bn in BLOCKS:
    bh = substrate.get_block_hash(bn)
    if not bh:
        print(f"Block {bn}: could not resolve block hash")
        continue

    # Polkadot changed denomination early; your script uses 12 pre-1248328.
    token_decimals = substrate.token_decimals if bn >= 1248328 else 12

    acc = substrate.query(
        module='System',
        storage_function='Account',
        params=[TARGET_ADDRESS],
        block_hash=bh
    )

    free = acc['data']['free'].value / (10 ** token_decimals)
    reserved = acc['data']['reserved'].value / (10 ** token_decimals)
    total = (acc['data']['free'].value + acc['data']['reserved'].value) / (10 ** token_decimals)
    nonce = acc['nonce'].value

    print(f"[Block {bn}] free={free:.10f}, reserved={reserved:.10f}, total={total:.10f}, nonce={nonce}")
# --- end quick lookup ---
