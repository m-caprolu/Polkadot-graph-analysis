from substrateinterface import SubstrateInterface
import csv

# Configuration
URL = "wss://rpc.polkadot.io"
INPUT_CSV = "as_multi_block_ids.csv"
OUTPUT_CSV = "multisig_data.csv"
BATCH_SIZE = 10  # Configurable batch size

def fetch_multisig_addresses():
    # Connect to Polkadot RPC
    with SubstrateInterface(url=URL, ss58_format=0, type_registry_preset='polkadot') as substrate:
        try:
            # Read block numbers from input file
            with open(INPUT_CSV, 'r') as file:
                block_numbers = file.readlines()
                block_numbers = [int(x.strip()) for x in block_numbers]
            print("Block numbers fetched:", block_numbers)

            batch = []  # To store rows for batch writing

            # Iterate through each block
            for block_id in block_numbers:
                block = substrate.get_block(block_number=block_id)
                print(f"Processing block: {block_id}")

                # Iterate through each extrinsic in the block
                for extrinsic in block['extrinsics']:
                    if (extrinsic.value['call']['call_function'] == "as_multi" and
                            extrinsic.value['call']['call_module'] == "Multisig"):
                        
                        # Extract threshold and other signatories
                        threshold = extrinsic.value['call']['call_args'][0]['value']
                        other_signatories = extrinsic.value['call']['call_args'][1]['value']

                        # Add the initiating signatory to the list
                        initiating_signatory = extrinsic.value['address'].replace('0x', '')
                        other_signatories.append(initiating_signatory)

                        # Generate multisig address
                        multi_address = substrate.generate_multisig_account(
                            signatories=other_signatories,
                            threshold=threshold
                        )

                        # Prepare row for batch
                        row = [multi_address, threshold] + other_signatories
                        batch.append(row)

                        # Write batch if it reaches the configured size
                        if len(batch) >= BATCH_SIZE:
                            write_batch_to_csv(batch)
                            batch.clear()  # Clear the batch after writing

            # Write any remaining rows
            if batch:
                write_batch_to_csv(batch)

        except Exception as e:
            print(f"Error occurred: {e}")

def write_batch_to_csv(batch):
    """
    Writes a batch of rows to the output CSV file.
    Avoids duplicates by checking for existing records in the file.
    """
    try:
        with open(OUTPUT_CSV, mode='a+', newline='', encoding='utf-8') as file:
            # Read existing rows to prevent duplicates
            file.seek(0)
            existing_rows = file.readlines()
            existing_multisig_addresses = [row.strip().split(',')[0] for row in existing_rows]

            writer = csv.writer(file)

            # Write only non-duplicate rows
            for row in batch:
                if row[0] not in existing_multisig_addresses:
                    writer.writerow(row)
                    print(f"Row written: {row}")
                else:
                    print(f"Duplicate found, skipping: {row[0]}")

    except Exception as e:
        print(f"Error writing batch to CSV: {e}")

if __name__ == "__main__":
    fetch_multisig_addresses()
