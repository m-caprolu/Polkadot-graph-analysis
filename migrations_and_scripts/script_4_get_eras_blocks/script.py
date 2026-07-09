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

def fetch_staking_events():
    """
    Fetch staking.erapayout (until era 461) and staking.erapaid (from era 462) events from the database.
    """
    query = """
        SELECT block_id, event_id, attributes 
        FROM polkadot_analysis.event
        WHERE module_id = 'Staking' 
        AND (event_id = 'erapaid' OR event_id = 'erapayout')
    """
    
    with connection.cursor() as cursor:
        cursor.execute(query)
        events = cursor.fetchall()
    return events

def process_events(events):
    """
    Process events and store era start and end blocks in a JSON file.
    """
    era_blocks = {}
    for event in events:
        block_id, _, attributes = event
        
        try:
            attributes = json.loads(attributes)
            era_index = None
            if isinstance(attributes, list):
                if isinstance(attributes[0], dict):
                    era_index = attributes[0].get('value')
                elif isinstance(attributes[0], int):
                    era_index = attributes[0]
            elif isinstance(attributes, dict):
                era_index = attributes['era_index']
            else:
                logging.error(f"Unknown attribute type: {attributes}")
                import pdb; pdb.set_trace()
            
            era_blocks[int(era_index)] = block_id

        except (json.JSONDecodeError, TypeError) as e:
            logging.error(f"Error processing event attributes: {attributes}, error: {e}")
            import pdb; pdb.set_trace()
    
    era_blocks = dict(sorted(era_blocks.items()))
    with open("era_blocks.json", "w") as file:
        json.dump(era_blocks, file, indent=4)
    
    logging.info("Saved era block data to era_blocks.json")

if __name__ == "__main__":
    events = fetch_staking_events()
    process_events(events)
