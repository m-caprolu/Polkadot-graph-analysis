import logging
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.sql import text
import json

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("migrations/migration_4_update_trasnfer_all_amounts/migration.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database Connection
DB_CONNECTION = "mysql+mysqlconnector://crilab_db_admin:CRI%40admin24%21@10.70.43.249:3306/polkadot_analysis"
engine = create_engine(DB_CONNECTION, echo=False, isolation_level="READ_UNCOMMITTED", pool_pre_ping=True)
session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
db_session = scoped_session(session_factory)

# Constants for batch size
BATCH_SIZE = 1000

# Get Correct Balance
def correct_balance(block_id, balance):
    if not isinstance(balance, int):
        raise ValueError(f"Balance is not an integer for block_id {block_id}")
    if block_id >= 1_248_328:
        token_decimals = 10
    else:
        token_decimals = 12
    return balance / 10 ** token_decimals

def parse_event(event):
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
    return parsed_event
# Migration Process
def migrate_data_with_block_id_batching(batch_size=1_000_000):
    """
    Migrate data by processing batches of block_id ranges.
    """
    # Step 1: Determine the minimum and maximum block_id
    min_block_id = 0
    max_block_id = 23_098_211

    current_min = min_block_id
    batch_count = 0

    while current_min < max_block_id:
        current_max = current_min + batch_size
        batch_count += 1
        logger.info(f"Processing batch {batch_count}: block_id >= {current_min} and < {current_max}")

        # Step 2: Fetch `balances.transfer_all` extrinsics and matching `balances.transfer` events
        query = text("""
            SELECT 
                e.block_id AS extrinsic_block_id,
                e.extrinsic_idx AS extrinsic_idx,
                e.nesting_idx AS extrinsic_nesting_idx,
                e.batch_idx AS extrinsic_batch_idx,
                e.unique_sequence AS extrinsic_unique_sequence,
                e.from_address AS extrinsic_from_address,
                e.to_address AS extrinsic_to_address,
                ev.event_idx AS event_idx,
                ev.attributes AS event_attributes
            FROM extrinsic e
            LEFT JOIN event ev
                ON e.block_id = ev.block_id
                AND e.extrinsic_idx = ev.extrinsic_idx
                AND ev.module_id = 'Balances'
                AND ev.event_id = 'Transfer'
            WHERE e.module_id = 'Balances' AND e.call_id = 'transfer_all' AND e.value = 0
              AND e.block_id >= :current_min AND e.block_id < :current_max
        """)
        rows = db_session.execute(query, {"current_min": current_min, "current_max": current_max}).fetchall()

        if not rows:
            logger.info("No rows found in this batch.")
            current_min = current_max
            current_max = current_min + batch_size
            continue

        # Step 3: Group results by extrinsic
        extrinsic_events = {}
        for row in rows:
            extrinsic_key = (row["extrinsic_block_id"], row["extrinsic_idx"], row["extrinsic_nesting_idx"], row["extrinsic_batch_idx"], row["extrinsic_unique_sequence"])
            # This is not correct, because the key contains other fields as well
            # If we ignore the other fields, we will consider 1 extrinsic only in the batch.
            # However, this will allows us to iterated over events only once. So, if we decide to add all events without checking extrinsic, this will be correct.
            # If we need to match event data with extrinsic data, we need to consider all fields in the key.
            # Problem: If we iterate over events without comparing with extrinsic data, we may consider balances.transfer event that is not initiated from balances.transfer_all extrinsic.
            
            if extrinsic_key not in extrinsic_events:
                extrinsic_events[extrinsic_key] = {
                    "from_address": row["extrinsic_from_address"],
                    "to_address": row["extrinsic_to_address"],
                    "events": []
                }
            if row["event_idx"] is not None:
                extrinsic_events[extrinsic_key]["events"].append(row["event_attributes"])

        # Step 4: Process each extrinsic
        for extrinsic_key, extrinsic_data in extrinsic_events.items():
            block_id, extrinsic_idx, nesting_idx, batch_idx, unique_sequence = extrinsic_key
            from_address = extrinsic_data["from_address"]
            to_address = extrinsic_data["to_address"]
            events = extrinsic_data["events"]

            # Sample Event: ['[{"type": "AccountId", "value": "15W6rEHTso3PZzSFi4sqwr3TuTrKaxv17p2bakL6Sjj4Dynn"}, {"type": "AccountId", "value": "16kvim4sqin7Ph3A5c38SmRbo5c9H1HhJ4mUdgKL7WW72Rnp"}, {"type": "Balance", "value": 10848999985}]']
            if len(events) == 1:
                # Single event: Parse attributes and update the extrinsic with the amount
                parsed_event = parse_event(events[0])
                if parsed_event["from"] == from_address and parsed_event["to"] == to_address:
                    amount = correct_balance(block_id, parsed_event["amount"])
                    logger.info(f"Updating extrinsic case 1: block_id={block_id}, extrinsic_idx={extrinsic_idx}, nesting_idx={nesting_idx}, batch_idx={batch_idx}, unique_sequence={unique_sequence}, amount={amount}, from_address={from_address}, to_address={to_address}")
                    update_extrinsic(block_id, extrinsic_idx, nesting_idx, batch_idx, unique_sequence, amount)
                else:
                    logger.warning("Failure Case 1: From and To address do not match {} {} in block {} extrinsic {}".format(parsed_event["from"], parsed_event["to"], block_id, extrinsic_idx))
                    # import pdb; pdb.set_trace()

            elif len(events) > 1:
                # Multiple events: Match `from_address` and `to_address`
                matched_events = []
                for event in events:
                    parsed_event = parse_event(event)
                    # import pdb; pdb.set_trace()
                    if parsed_event["from"] == from_address and parsed_event["to"] == to_address:
                        matched_events.append(parsed_event)

                if len(matched_events) == 0:
                    logger.warning(f"Failure Case 2-1: No matching events found: block_id={block_id}, extrinsic_idx={extrinsic_idx}, nesting_idx={nesting_idx}, batch_idx={batch_idx}, unique_sequence={unique_sequence}, from_address={from_address}, to_address={to_address}")
                elif len(matched_events) == 1:
                    # import pdb; pdb.set_trace()
                    amount = matched_events[0]['amount']
                    amount = correct_balance(block_id, amount)
                    logger.info(f"Updating extrinsic case 2: block_id={block_id}, extrinsic_idx={extrinsic_idx}, nesting_idx={nesting_idx}, batch_idx={batch_idx}, unique_sequence={unique_sequence}, amount={amount}, from_address={from_address}, to_address={to_address}")
                    # import pdb; pdb.set_trace()
                    update_extrinsic(block_id, extrinsic_idx, nesting_idx, batch_idx, unique_sequence, amount)
                elif len(matched_events) > 1:
                    logger.warning(f"Failure Case 2-2: Unresolved case: block_id={block_id}, extrinsic_idx={extrinsic_idx}, nesting_idx={nesting_idx}, batch_idx={batch_idx}, unique_sequence={unique_sequence}, from_address={from_address}, to_address={to_address}")
                    # import pdb; pdb.set_trace()

        # Increment the block_id range for the next batch
        current_min = current_max


def update_extrinsic(block_id, extrinsic_idx, nesting_idx, batch_idx, unique_sequence, amount):
    """
    Update the extrinsic table with the amount.
    """
    # logger.debug(f"Executing update for block_id={block_id}, extrinsic_idx={extrinsic_idx}, nesting_idx={nesting_idx}, batch_idx={batch_idx}, unique_sequence={unique_sequence}, amount={amount}")
    # db_session.execute(
    #     text("""
    #         UPDATE extrinsic
    #         SET value = :amount
    #         WHERE block_id = :block_id AND extrinsic_idx = :extrinsic_idx AND nesting_idx = :nesting_idx AND batch_idx = :batch_idx AND unique_sequence = :unique_sequence
    #     """), {"amount": amount, "block_id": block_id, "extrinsic_idx": extrinsic_idx, "nesting_idx": nesting_idx, "batch_idx": batch_idx, "unique_sequence": unique_sequence}
    # )
    # db_session.commit()

# Run the migration
if __name__ == "__main__":
    migrate_data_with_block_id_batching(batch_size=1_000_000)
