import yaml
import json
import pymysql
import logging
import os
from datetime import datetime
from scalecodec.utils.ss58 import ss58_encode, is_valid_ss58_address
from substrateinterface import SubstrateInterface

# Load database configuration
with open("../../config.yaml", "r") as file:
    config = yaml.safe_load(file)

DB_HOST = config["database"]["host"]
DB_PORT = config["database"]["port"]
DB_USER = config["database"]["user"]
DB_PASSWORD = config["database"]["password"]
DB_NAME = config["database"]["name"]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("script_5_get_validators_and_nominators.log"),
        logging.StreamHandler()
    ]
)

# Connect to the database
connection = pymysql.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME,
    port=DB_PORT,
    charset='utf8mb4'
)

def set_group_concat_max_len():
    """
    Set SESSION group_concat_max_len to handle large concatenations.
    """
    with connection.cursor() as cursor:
        cursor.execute("SET SESSION group_concat_max_len = 1000000;")
        connection.commit()

def fetch_payout_stakers():
    """
    Load all staking.payout_stakers extrinsics that have multiple call_args.
    """
    set_group_concat_max_len()
    query = """
        SELECT block_id, extrinsic_idx, COUNT(*) as counts, 
               GROUP_CONCAT(call_args SEPARATOR '-separator-') as concat_call_args
        FROM polkadot_analysis.extrinsic
        WHERE module_id = 'staking' AND 
            (call_id = 'payout_stakers' OR call_id = 'payout_stakers_by_page') AND success = 1
        GROUP BY block_id, extrinsic_idx
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
        return cursor.fetchall()

def parse_json_separated(json_string, separator="-separator-"):
    """
    Splits and parses JSON objects separated by a specific separator.
    """
    try:
        return [json.loads(obj) for obj in json_string.split(separator)]
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON: {e} | JSON: {json_string}")
        return []

def normalize_reward_event(data):
    """
    Extracts address and amount from staking event attributes.
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
            if "stash" in data:
                result["address"] = data["stash"]
            elif isinstance(data.get("dest"), dict) and "Account" in data["dest"]:
                result["address"] = data["dest"]["Account"]
            elif "who" in data:
                result["address"] = data["who"]
            if "amount" in data:
                result["amount"] = data["amount"]
        elif isinstance(data, list) and len(data) in [2, 3]:
            result["address"] = data[0]
            result["amount"] = data[2] if len(data) == 3 else data[1]
        if not result["address"]:
            raise ValueError("Address is missing or invalid in the input data.")
        return result
    except Exception as e:
        logging.error(f"Error processing event: {e}")
        import pdb; pdb.set_trace()
        return result

def normalize_payout_started_event(data, block_id):
    result = {"era_index": None, "validator_stash": None}
    if isinstance(data, list) and len(data) == 2 and isinstance(data[0], dict):
        # [{..., "value": <era_number>}, {..., "value": <validator_stash>}]
        result["era_index"] = int(data[0]["value"])
        result["validator_stash"] = data[1]["value"]
    elif isinstance(data, list) and len(data) == 2 and isinstance(data[0], int):
        # [<era_number>, <validator_stash>]
        result["era_index"] = int(data[0])
        result["validator_stash"] = data[1]
    elif isinstance(data, dict):
        # {"era_index": <era_index>, "validator_stash": <validator_stash>}
        assert "era_index" in data and "validator_stash" in data, "Invalid PayoutStarted event format"
        result["era_index"] = int(data["era_index"])
        result["validator_stash"] = data["validator_stash"]
    else:
        logging.error(f"Invalid PayoutStarted event format: {data}")
        raise ValueError("Invalid PayoutStarted event format")

    return result

def get_blocks_produced_by_validator(validator, era, era_blocks):
    start_block = era_blocks.get(str(era-1), 0) # In first iteration, start_block is set to 0
    end_block = era_blocks.get(str(era), start_block * 2) # In last iteration, end_block is set to 2 * start_block
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id FROM polkadot_analysis.block 
            WHERE author = %s AND id >= %s AND id < %s
        """, (validator, start_block, end_block))
        blocks_produced = [row[0] for row in cursor.fetchall()]
    
    return blocks_produced

def get_validator_rewards_count_in_extrinsic(validator_stash, block_id, extrinsic_idx):
    """
    Get the count of rewards for a specific validator in a given extrinsic.
    """
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) FROM polkadot_analysis.event 
            WHERE block_id = %s AND extrinsic_idx = %s 
              AND module_id = 'staking' AND (event_id = 'rewarded' OR event_id = 'reward')
              AND attributes LIKE %s
        """, (block_id, extrinsic_idx, f'%{validator_stash}%'))
        return cursor.fetchone()[0]

def process_rewards(events, block_id):
    last_era_index = None
    last_validator_stash = None
    validator_nominator_rewards = {} # {(validator_stash, era_index): [{nominator_stash: reward}, ...]}
    
    for row in events:
        parsed_attributes = json.loads(row[1])
        if row[0] == "PayoutStarted":
            parsed_attributes = normalize_payout_started_event(parsed_attributes, block_id)
            last_era_index = parsed_attributes["era_index"]
            last_validator_stash = parsed_attributes["validator_stash"]
            validator_nominator_rewards[last_validator_stash, last_era_index] = []
        else: # Reward
            reward = normalize_reward_event(parsed_attributes)
            if not last_era_index or not last_validator_stash:
                logging.error("PayoutStarted event is missing before reward event.")
                continue

            validator_nominator_rewards[last_validator_stash, last_era_index].append(reward)
            if validator_nominator_rewards[last_validator_stash, last_era_index] == []:
                assert reward["address"] == last_validator_stash # First reward is for the validator
    
    return validator_nominator_rewards

def process_rewards_grouped_by_validator_no_era(events, validators_era_pairs, block_id): 
    # validator_era_pairs: {validator_stash: [era, ...]}

    validator_nominator_rewards = {} # {validator_stash: [[{nominator_stash: <stash>, reward: <value>}, ...], []]}
    # hash of validator_stash to list of eras to list of rewards
    validator_stash = ""
    local_wrong_count = 0
    for _, event in events:
        parsed_attributes = json.loads(event)
        reward = normalize_reward_event(parsed_attributes)
        if reward["address"] in validators_era_pairs.keys():
            validator_stash = reward["address"]
            if validator_stash not in validator_nominator_rewards:
                validator_nominator_rewards[validator_stash] = []
            validator_nominator_rewards[validator_stash].append([])

        if validator_stash == "":
            local_wrong_count += 1
            continue
        
        validator_idx = len(validator_nominator_rewards[validator_stash])-1
        if validator_idx + 1 > len(validators_era_pairs[validator_stash]): # out of range
            local_wrong_count += 1
            return {}, local_wrong_count
            # Corner Case: where the validator is a nominator for other validators. Example: 534380
        era_number = validators_era_pairs[validator_stash][validator_idx]

        validator_nominator_rewards[validator_stash][-1].append({
            "address": reward["address"],
            "amount": correct_balance(era_number, reward["amount"])
                        # validator_nominator_rewards[validator_stash] is array of all occurrences of the validator
                        # i'th occurrence means the i'th occurrence in validator_nominator_rewards[validator_stash]
                        # len(validator_nominator_rewards[validator_stash])-1 is the last occurrence of the validator
                        # validators_era_pairs[validator_stash] contains all era occurrences for that validator
        })
    return validator_nominator_rewards, local_wrong_count

def produced_blocks(validator_stash, era, era_blocks):
    start_block = era_blocks.get(str(era-1), 0) # In first iteration, start_block is set to 0
    end_block = era_blocks.get(str(era), start_block * 2) # In last iteration, end_block is set to 2 * start_block

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id FROM polkadot_analysis.block 
            WHERE author = %s AND id >= %s AND id < %s LIMIT 1
        """, (validator_stash, start_block, end_block))
        return cursor.fetchone() != None        


def correct_balance(era, balance):
    if not isinstance(balance, int):
        raise ValueError(f"Balance is not an integer for era {era}")
    if era >= 80: #80: 1_247_607, should be 1_248_328 (small inaccuracy)
        token_decimals = 10
    else:
        token_decimals = 12
    return balance / 10 ** token_decimals

def load_eras():
    with open("../script_4_get_eras_blocks/era_blocks.json", "r") as file:
        return json.load(file)

def process_payout_stakers():
    """
    Process the payout stakers extrinsics and extract staking rewards.
    """
    eras_staking_info = {}
    rows = fetch_payout_stakers()
    era_blocks = load_eras()
    print("Loaded payout_stakers")
    counter = 0
    wrong_count = 0
    skipped_blocks = []
    total = len(rows)
    for row in rows:
        counter = counter + 1
        if counter % 1000 == 0:
            print("Processed {} out of {} with percentage: {}%, correct_count: {}, wrong_count: {}".format(counter, total, counter/total*100, counter, wrong_count))

        block_id, extrinsic_idx, _, concat_call_args = row
        parsed_data = parse_json_separated(concat_call_args)
        validator_era_pairs = {}
        
        for obj in parsed_data:
            validator_stash = obj[0]['value']
            era = int(obj[1]['value'])
            if not is_valid_ss58_address(validator_stash):
                validator_stash = ss58_encode(validator_stash.replace('0x', ''), 0)
            if validator_stash not in validator_era_pairs:
                validator_era_pairs[validator_stash] = []
            validator_era_pairs[validator_stash].append(era)
        
        # Get countof payoutStarted
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM polkadot_analysis.event 
                WHERE block_id = %s AND extrinsic_idx = %s 
                  AND module_id = 'staking' AND event_id = 'PayoutStarted'
            """, (block_id, extrinsic_idx))
            payout_started_count = cursor.fetchone()[0]

        if payout_started_count == 0:
            # PayoutStarted event not found, proceed to process rewards
            filtered_validator_era_pairs = {}

            for validator in validator_era_pairs.keys():
                reward_count = get_validator_rewards_count_in_extrinsic(validator, block_id, extrinsic_idx)
                if reward_count == len(validator_era_pairs[validator]):
                    filtered_validator_era_pairs[validator] = validator_era_pairs[validator]
                else:
                    logging.warning(f"Skipping validator {validator} at block {block_id} with extrinsic {extrinsic_idx} due to mismatch in reward count. Expected: {len(validator_era_pairs[validator])}, Found: {reward_count}")

            for validator_stash, eras in filtered_validator_era_pairs.items():
                for era in eras:
                    if not produced_blocks(validator_stash, era, era_blocks):
                        import pdb; pdb.set_trace() # Important: do not remove, want to find if there are exceptions
                        logging.error(f"Validator {validator_stash} at era {era} block {block_id} produced 0 blocks but had rewards")
                        filtered_validator_era_pairs.pop(validator_stash, None)
                        wrong_count += 1
            
            rewards = {}
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT event_id, attributes FROM polkadot_analysis.event
                    WHERE block_id = %s AND extrinsic_idx = %s 
                    AND module_id = 'staking' AND (event_id = 'rewarded' OR event_id = 'reward')
                """, (block_id, extrinsic_idx))
                rewards, local_wrong_count = process_rewards_grouped_by_validator_no_era(cursor.fetchall(), validator_era_pairs, block_id)

            if local_wrong_count:
                logging.error(f"Unhandled rewards (around): {local_wrong_count} for block {block_id} extrinsic {extrinsic_idx} with unknown validator")
                wrong_count += 1

            if rewards == {}:
                logging.warning(f"Rewards are empty for block {block_id} extrinsic {extrinsic_idx}, Skipping")
                skipped_blocks.append((block_id, extrinsic_idx))
                continue
            for validator_stash, eras in filtered_validator_era_pairs.items():
                # TODO: continue here, divide the rewards between validator and nominators
                assert len(rewards[validator_stash]) == len(eras), "Mismatch in number of rewards and eras for validator {} at block {}".format(validator_stash, block_id)
                for index_0, era in enumerate(eras):
                    for index_1, reward_details in enumerate(rewards[validator_stash][index_0]):
                        if index_1 == 0:
                            # First is the validator, get produced_blocks count
                            blocks_produced = get_blocks_produced_by_validator(validator_stash, era, era_blocks)

                            assert len(blocks_produced) > 0, "Validator {} at era {} block {} produced 0 blocks but had rewards".format(validator_stash, era, block_id)
                            if str(era) not in eras_staking_info:
                                eras_staking_info[str(era)] = {}
                            
                            eras_staking_info[str(era)][validator_stash] = {
                                "reward": reward_details["amount"],
                                "blocks_produced": blocks_produced,
                                "nominators": []
                            }
                        else:
                            eras_staking_info[str(era)][validator_stash]["nominators"].append({
                                    "address": reward_details["address"],
                                    "reward": reward_details["amount"]
                                })
        else:
            # PayoutStarted event found, proceed to process rewards
            
            rewards = []
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT event_id, attributes FROM polkadot_analysis.event
                    WHERE block_id = %s AND extrinsic_idx = %s 
                    AND module_id = 'staking' AND (event_id = 'rewarded' OR event_id = 'reward' OR event_id = 'PayoutStarted')
                """, (block_id, extrinsic_idx))
                rewards = process_rewards(cursor.fetchall(), block_id)

            for validator_stash, era in rewards.keys():
                for reward_details in rewards[(validator_stash, era)]:
                    if reward_details["address"] == validator_stash:
                        blocks_produced = get_blocks_produced_by_validator(validator_stash, era, era_blocks)
                        if len(blocks_produced) == 0:
                            print("Validator {} at era {} block {} produced 0 blocks but had rewards".format(validator_stash, era, block_id))

                        if str(era) not in eras_staking_info:
                            eras_staking_info[str(era)] = {}
                        eras_staking_info[str(era)][validator_stash] = {
                            "reward": correct_balance(era, reward_details["amount"]),
                            "blocks_produced": blocks_produced,
                            "nominators": []
                        }
                    else:
                        eras_staking_info[str(era)][validator_stash]["nominators"].append({
                                "address": reward_details["address"],
                                "reward": correct_balance(era, reward_details["amount"])
                            })
        
    with open("eras_staking_info.json", "w") as file:
        json.dump(eras_staking_info, file, indent=4)
    
    logging.info(f"Processed {counter} rows with {wrong_count} blocks with errors and skipped {len(skipped_blocks)} blocks")
    logging.info(f"Skipped blocks: {skipped_blocks}")
    logging.info("Saved staking rewards data to eras_staking_info.json")

if __name__ == "__main__":
    process_payout_stakers()
