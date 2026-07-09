import yaml
import json
import pymysql
import logging
import os
from scalecodec.utils.ss58 import ss58_encode

# Load database configuration
with open("../../config.yaml", "r") as file:
    config = yaml.safe_load(file)

DB_HOST = config["database"]["host"]
DB_PORT = config["database"]["port"]
DB_USER = config["database"]["user"]
DB_PASSWORD = config["database"]["password"]
DB_NAME = config["database"]["name"]

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Connect to the database
connection = pymysql.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME,
    port=DB_PORT,
    charset='utf8mb4'
)

def normalize_event(data):
    """
    Normalize different reward event formats into {"address": ..., "amount": ...}
    Handles various input structures and prioritizes the 'Account' field over 'stash' if both exist.
    """
    result = {"address": None, "amount": None}

    try:
        if isinstance(data, list) and isinstance(data[0], dict):
            for item in data:
                if item.get("type") == "AccountId":
                    result["address"] = item.get("value")
                elif item.get("type") == "Balance" or item.get("type_name") == "BalanceOf":
                    result["amount"] = int(item.get("value"))
                elif item.get("type_name") == "AccountId":
                    result["address"] = ss58_encode(item.get("value").replace('0x', ''), 0)

        elif isinstance(data, dict):
            if isinstance(data.get("dest"), dict) and "Account" in data["dest"]:
                result["address"] = data["dest"]["Account"]
            elif "stash" in data:
                result["address"] = data["stash"]
            elif "who" in data:
                result["address"] = data["who"]
            if "amount" in data:
                result["amount"] = data["amount"]

        elif isinstance(data, list) and len(data) == 2:
            result["address"] = data[0]
            result["amount"] = data[1]

        elif isinstance(data, list) and len(data) == 3:
            result["address"] = data[0]
            result["amount"] = data[2]

        if not result["address"]:
            raise ValueError("Address is missing or invalid in the input data.")

        return result

    except Exception as e:
        logging.warning(f"Error processing event: {e}")
        return result


def process_batches(batch_size=1_000_000):
    """
    Fetch staking rewards in batches, extract unique addresses, and store in batch files.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT MAX(id) FROM polkadot_analysis.block")
        max_block_id = cursor.fetchone()[0]

        if not max_block_id:
            logging.error("No blocks found in database.")
            return

        start_block = 1

        while start_block <= max_block_id:
            end_block = min(start_block + batch_size - 1, max_block_id)
            logging.info(f"Processing batch: {start_block} to {end_block}")

            # Fetch events for this batch
            query = f"""
                SELECT attributes FROM polkadot_analysis.event
                WHERE module_id = "Staking" 
                AND (event_id = "Reward" OR event_id = "Rewarded")
                AND block_id BETWEEN {start_block} AND {end_block}
            """
            cursor.execute(query)
            rows = cursor.fetchall()

            unique_addresses = set()
            
            for row in rows:
                attributes = json.loads(row[0])
                event_data = normalize_event(attributes)
                if event_data["address"]:
                    unique_addresses.add(event_data["address"])

            # Write unique addresses to file
            filename = f"addresses_{start_block}_{end_block}.txt"
            with open(filename, "w") as f:
                for address in unique_addresses:
                    f.write(f"{address}\n")

            logging.info(f"Batch {start_block}-{end_block} written to {filename}")

            # Move to next batch
            start_block += batch_size


def merge_batches():
    """
    Merge all batch files into a single file with unique addresses.
    """
    logging.info("Merging all batch files...")

    unique_addresses = set()
    batch_files = [f for f in os.listdir() if f.startswith("addresses_") and f.endswith(".txt")]

    for batch_file in batch_files:
        logging.info(f"Reading {batch_file}")
        with open(batch_file, "r") as f:
            for line in f:
                unique_addresses.add(line.strip())

    # Write final unique addresses file
    final_filename = "unique_addresses.txt"
    with open(final_filename, "w") as f:
        for address in unique_addresses:
            f.write(f"{address}\n")

    logging.info(f"Merged {len(batch_files)} batch files into {final_filename}, containing {len(unique_addresses)} unique addresses.")


if __name__ == "__main__":
    try:
        process_batches()
        merge_batches()
        logging.info("Process completed successfully.")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
    finally:
        connection.close()
