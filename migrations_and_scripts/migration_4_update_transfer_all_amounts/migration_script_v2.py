import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
import json

# Database Connection
DB_CONNECTION = "mysql+mysqlconnector://crilab_db_admin:CRI%40admin24%21@10.70.43.249:3306/polkadot_analysis"
engine = create_engine(DB_CONNECTION, echo=False, isolation_level="READ_UNCOMMITTED", pool_pre_ping=True)
session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
db_session = scoped_session(session_factory)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler("migrations_and_scripts/migration_4_update_transfer_all_amounts/migration.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Get Correct Balance
def correct_balance(block_id, balance):
    if not isinstance(balance, int):
        raise ValueError(f"Balance is not an integer for block_id {block_id}")
    if block_id >= 1_248_328:
        token_decimals = 10
    else:
        token_decimals = 12
    return balance / 10 ** token_decimals

def parse_event(block_id, event):
    attributes = json.loads(event)
    parsed_event = {
        "from": None,
        "to": None,
        "amount": None
    }
    if isinstance(attributes, list) and len(attributes) == 3 and all(isinstance(attr, dict) for attr in attributes):
        parsed_event["from"] = attributes[0]['value']
        parsed_event["to"] = attributes[1]['value']
        parsed_event["amount"] = int(attributes[2]['value'])
    elif isinstance(attributes, list) and len(attributes) == 3 and isinstance(attributes[0], str) and isinstance(attributes[1], str) and isinstance(attributes[2], int):
        parsed_event["from"] = attributes[0]
        parsed_event["to"] = attributes[1]
        parsed_event["amount"] = int(attributes[2])
    elif isinstance(attributes, dict):
        parsed_event["from"] = attributes.get("from")
        parsed_event["to"] = attributes.get("to")
        parsed_event["amount"] = int(attributes.get("amount"))
    else:
        logger.error(f"Invalid event attributes: {attributes}")
        raise ValueError(f"Invalid event attributes: {attributes}")
    parsed_event["amount"] = correct_balance(block_id, parsed_event["amount"])
    return parsed_event

def get_block_ids_to_ignore(session):
    query = """
    SELECT DISTINCT(e2.block_id)
    FROM (
        SELECT DISTINCT block_id, extrinsic_idx
        FROM polkadot_analysis.extrinsic
        WHERE
            extrinsic.module_id = "Balances"
            AND extrinsic.call_id = "transfer_all"
            AND extrinsic.value = 0
    ) AS e1
    JOIN polkadot_analysis.extrinsic as e2
    ON e1.block_id = e2.block_id
    AND e1.extrinsic_idx = e2.extrinsic_idx
    WHERE e2.module_id = "Balances"
    AND e2.call_id IN ("transfer", "transfer_allow_death", "transfer_keep_alive")
    """
    result = session.execute(text(query))
    return {row[0] for row in result}

def process_batches(session, current_min, current_max, block_ids_to_ignore):
    query = """
    SELECT 
        event.block_id as event_block_id, 
        event.extrinsic_idx as event_extrinsic_idx,
        event.event_idx as event_idx,
        event.module_id as event_module_id,
        event.event_id as event_event_id,
        event.attributes as event_attributes
    FROM (
        SELECT DISTINCT block_id, extrinsic_idx
        FROM polkadot_analysis.extrinsic
        WHERE
            extrinsic.module_id = "Balances"
            AND extrinsic.call_id = "transfer_all"
            AND extrinsic.value = 0
    ) AS e
    JOIN polkadot_analysis.event
        ON e.block_id = event.block_id
        AND e.extrinsic_idx = event.extrinsic_idx
    WHERE event.module_id = "Balances" 
    AND event.event_id = "Transfer"
    AND event.block_id >= :current_min AND event.block_id < :current_max
    """
    result = session.execute(text(query), {'current_min': current_min, 'current_max': current_max})
    for row in result:
        if row['event_block_id'] in block_ids_to_ignore:
            logger.warning(f"Ignored block_id: {row['event_block_id']}")
        else:
            try:
                transaction = parse_event(row['event_block_id'], row['event_attributes'])
                logger.info(f"Block ID: {row['event_block_id']}, Extrinsic Index: {row['event_extrinsic_idx']}, Event Index: {row['event_idx']}, Transaction: {transaction}")
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Error parsing event attributes for block_id {row['event_block_id']}: {e}")
                continue

def main():
    session = db_session()
    try:
        block_ids_to_ignore = get_block_ids_to_ignore(session)
        logger.info(f"Block IDs to ignore: {block_ids_to_ignore}")

        # Define batch ranges
        batch_size = 1_000_000
        start_block_id = 0
        end_block_id = 23_098_211
        batch_ranges = [(i, min(i + batch_size, end_block_id)) for i in range(start_block_id, end_block_id, batch_size)]

        for current_min, current_max in batch_ranges:
            logger.info(f"Processing batch from block_id {current_min} to {current_max}")
            process_batches(session, current_min, current_max, block_ids_to_ignore)
    finally:
        session.close()

if __name__ == "__main__":
    main()