import yaml
import json
import pymysql
import logging
import os
from scalecodec.utils.ss58 import ss58_encode
from substrateinterface import SubstrateInterface

def load_config():
    with open("../../config.yaml", "r") as file:
        return yaml.safe_load(file)

def connect_db(config):
    return pymysql.connect(
        host=config["database"]["host"],
        user=config["database"]["user"],
        password=config["database"]["password"],
        database=config["database"]["name"],
        port=config["database"]["port"],
        charset='utf8mb4'
    )

def connect_substrate():
    return SubstrateInterface(url="wss://10.70.43.152:9933")

def load_eras():
    with open("../script_4_get_eras_blocks/era_blocks.json", "r") as file:
        return json.load(file)

def normalize_event(data):
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
        elif isinstance(data, list) and len(data) in [2, 3]:
            result["address"] = data[0]
            result["amount"] = data[2] if len(data) == 3 else data[1]
        if not result["address"]:
            raise ValueError("Address is missing or invalid in the input data.")
        return result
    except Exception as e:
        logging.error(f"Error processing event: {e}")
        return result

def process_era_data(eras, cursor, substrate):
    eras_staking_info = {}
    era_keys = sorted(map(int, eras.keys()))
    for i in range(len(era_keys) - 1):
        start_block, end_block = eras[str(era_keys[i])], eras[str(era_keys[i + 1])]
        cursor.execute("""
            SELECT block_id, extrinsic_idx FROM polkadot_analysis.extrinsics 
            WHERE call = 'staking.payout_stakers' AND block_id BETWEEN %s AND %s
        """, (start_block, end_block))
        payout_extrinsics = cursor.fetchall()
        import pdb; pdb.set_trace()
        for block_id, extrinsic_idx in payout_extrinsics:
            block_data = substrate.get_block(block_hash=substrate.get_block_hash(block_id))
            import pdb; pdb.set_trace()
            
            for extrinsic in block_data["extrinsics"]:
                if extrinsic["extrinsic_index"] == extrinsic_idx:
                    validator_stash = extrinsic["params"]["validator_stash"]
                    era = extrinsic["params"]["era"]
                    import pdb; pdb.set_trace()
                    
                    if era != era_keys[i]:
                        continue
                    cursor.execute("""
                        SELECT id FROM polkadot_analysis.block 
                        WHERE author = %s AND id BETWEEN %s AND %s
                    """, (validator_stash, start_block, end_block))
                    blocks_produced = [row[0] for row in cursor.fetchall()]
                    import pdb; pdb.set_trace()
                    
                    cursor.execute("""
                        SELECT attributes FROM polkadot_analysis.events 
                        WHERE block_id = %s AND extrinsic_idx = %s 
                          AND event IN ('staking.rewarded', 'staking.reward')
                    """, (block_id, extrinsic_idx))
                    nominators = [normalize_event(row[0]) for row in cursor.fetchall()]
                    import pdb; pdb.set_trace()
                    
                    if validator_stash not in eras_staking_info.get(str(era), {}):
                        eras_staking_info.setdefault(str(era), {})[validator_stash] = {
                            "reward": 0, "blocks_produced": blocks_produced, "nominators": []
                        }
                    for nom in nominators:
                        if nom["address"] == validator_stash:
                            eras_staking_info[str(era)][validator_stash]["reward"] += nom["amount"]
                        else:
                            eras_staking_info[str(era)][validator_stash]["nominators"].append({"address": nom["address"], "reward": nom["amount"]})
                    import pdb; pdb.set_trace()
    return eras_staking_info

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    config = load_config()
    db_connection = connect_db(config)
    cursor = db_connection.cursor()
    substrate = connect_substrate()
    eras = load_eras()
    staking_info = process_era_data(eras, cursor, substrate)
    with open("staking_info.json", "w") as f:
        json.dump(staking_info, f, indent=4)
    cursor.close()
    db_connection.close()

if __name__ == "__main__":
    main()
