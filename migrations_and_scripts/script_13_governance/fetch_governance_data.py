import yaml
import pymysql
import logging
import os
import json
from collections import defaultdict
from substrateinterface import SubstrateInterface
from scalecodec.base import ScaleBytes
import traceback


def load_config():
    config_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../config.yaml")
    )
    with open(config_path, "r") as file:
        return yaml.safe_load(file)


def connect_db(config):
    return pymysql.connect(
        host=config["database"]["host"],
        user=config["database"]["user"],
        password=config["database"]["password"],
        database=config["database"]["name"],
        port=config["database"]["port"],
        charset="utf8mb4",
    )


def connect_substrate(config):
    node_cfg = config.get("node", {})
    protocol = node_cfg.get("protocol", "wss")
    host = node_cfg.get("host", "rpc.polkadot.io")
    port = node_cfg.get("port", 443)
    url = f"{protocol}://{host}:{port}"

    return SubstrateInterface(url=url, type_registry_preset="polkadot")


def default_proposal_obj():
    return {
        "proposor_account_id": None,
        "voters": [],
        "state": None,
        "start_timestamp": None,
        "start_block": None,
        "decision_start_timestamps": [],
        "confirm_start_timestamps": [],
        "end_timestamp": None,
        "end_block": None,
        "aye_count": None,
        "nay_count": None,
        "support_count": None,
        "preimage_hash": None,
        "origin": None,
        "track": None,
        "call": None,
        "call_args": None,
    }


def fetch_governance_events(db_connection):
    query = """
        SELECT 
            block_id, module_id, event_id, attributes, timestamp
        FROM
            polkadot_analysis.event
                JOIN
            block ON event.block_id = block.id
        WHERE
            (
                (module_id = 'referenda' AND event_id = 'submitted')
                OR (module_id = 'referenda' AND event_id = 'confirmed')
                OR (module_id = 'referenda' AND event_id = 'rejected')
                OR (module_id = 'referenda' AND event_id = 'timedOut')
                OR (module_id = 'referenda' AND event_id = 'decisionStarted')
                OR (module_id = 'referenda' AND event_id = 'confirmStarted')
            )
            AND (attributes IS NOT NULL)
    """
    with db_connection.cursor() as cursor:
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return results


def feed_governance_events_into_governance_data(governance_events, governance_data):
    for event in governance_events:
        event_type = event["event_id"]
        attributes = json.loads(event["attributes"])
        index = attributes.get("index")

        if index is None:
            continue  # skip if index is not available

        data = governance_data[index]

        if event_type == "Submitted":
            data["track"] = attributes.get("track")
            data["start_timestamp"] = event["timestamp"]
            data["start_block"] = event["block_id"]
        elif event_type == "DecisionStarted":
            data["decision_start_timestamps"].append(event["timestamp"])
        elif event_type == "ConfirmStarted":
            data["confirm_start_timestamps"].append(event["timestamp"])
        elif event_type in ["Confirmed", "Rejected", "TimedOut", "Cancelled", "Killed"]:
            tally = attributes.get("tally", {})
            data["aye_count"] = tally.get("ayes")
            data["nay_count"] = tally.get("nays")
            data["support_count"] = tally.get("support")
            data["state"] = event_type.lower()
            data["end_timestamp"] = event["timestamp"]
            data["end_block"] = event["block_id"]


def fetch_governance_extrinsics(db_connection):
    query = """
        SELECT 
            block_id, extrinsic_idx, from_address, module_id, call_id, timestamp, call_args
        FROM
            polkadot_analysis.extrinsic
        WHERE
            (
                (module_id = 'ConvictionVoting' AND call_id = 'vote')
                OR (module_id = 'ConvictionVoting' AND call_id = 'remove_vote')
                OR (module_id = 'ConvictionVoting' AND call_id = 'delegate')
                OR (module_id = 'ConvictionVoting' AND call_id = 'undelegate')
                OR (module_id = 'Referenda' AND call_id = 'submit')
                OR (module_id = 'Preimage' AND call_id = 'note_preimage')
            )
            AND (success = 1)
            AND (call_args IS NOT NULL)
    """
    with db_connection.cursor() as cursor:
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return results


def get_proposal_index(db_connection, block_id, extrinsic_idx):
    query = """
        SELECT 
            attributes
        FROM
            polkadot_analysis.event
                JOIN
            block ON event.block_id = block.id
        WHERE
            module_id = 'Referenda' AND event_id = 'Submitted'
            AND event.block_id = %s
            AND event.extrinsic_idx = %s
    """
    with db_connection.cursor() as cursor:
        cursor.execute(query, (block_id, extrinsic_idx))
        result = cursor.fetchone()
        if result:
            attributes = json.loads(result[0])
            return attributes.get("index")
    return None


def feed_governance_extrinsics_into_governance_data(
    db_connection,
    governance_extrinsics,
    governance_data,
    substrate,
    preimages,  # , hash_index_map
):
    for idx, ext in enumerate(
        sorted(governance_extrinsics, key=lambda x: x["timestamp"])
    ):
        # if idx % 100 == 0 and len(governance_extrinsics) > 0:
        #     percent = (idx + 1) / len(governance_extrinsics) * 100
        #     logging.info(f"Processed {idx + 1} / {len(governance_extrinsics)} extrinsics ({percent:.2f}%)")
        module = ext["module_id"]
        call = ext["call_id"]
        args = json.loads(ext["call_args"])
        timestamp = ext["timestamp"]
        from_address = ext["from_address"]
        block_id = ext["block_id"]
        extrinsic_idx = ext["extrinsic_idx"]

        if module == "Referenda" and call == "submit":
            # Get proposal hash and map to index

            # {'name': 'proposal', 'type': 'BoundedCallOf<T, I>', 'value': {'Inline': '0x13030700d0ed902e001674eb12e6f33dd2de536ee9b4a220095d68d2d4c38d3470abeea6306cb6fe38'}}
            # {"name": "proposal", "type": "BoundedCallOf<T, I>", "value": {"Lookup": {"len": 42, "hash": "0x449d2e72eca2b3b958966f75b5b3d03c2a51d290268277df7b655240a5ef5e51"}}

            index = get_proposal_index(db_connection, block_id, extrinsic_idx)

            proposal_value = args[1]["value"]
            if isinstance(proposal_value, dict):
                if "Lookup" in proposal_value and "hash" in proposal_value["Lookup"]:
                    preimage_hash = proposal_value["Lookup"]["hash"]
                elif "Inline" in proposal_value:
                    preimage_hash = proposal_value["Inline"]
                else:
                    logging.warning(
                        f"Unknown proposal format in extrinsic: {proposal_value}"
                    )
                    continue
            else:
                logging.warning(f"Proposal value is not a dict: {proposal_value}")
                continue
            # index = hash_index_map.get(preimage_hash)
            if index is None:
                continue

            data = governance_data[index]
            data["preimage_hash"] = preimage_hash
            data["proposor_account_id"] = from_address
            data["origin"] = args[0]["value"]

        elif module == "Preimage" and call == "note_preimage":
            # Example: 0x1a041001039a6e9257349bba17f88788016821455b1e3fffbd0947dcbad6e8a938b5063bac010321fc0d6cfaa46fd7ac946c6152fb989bc2ab9cbee53f389e2be0d8b68dac776501020e5751c026e543b2e8ab2eb06099daa1d1e5df47778f7787faab45cdf12fe3a80001fe000100a3020007000000004800e2a50100380102159683585683496ac571319927d253dbcba0c602f4dcc7574430180736441f01007610010100a3020007000000004800e2a501003c
            # Decoded example: {'call_index': '0x1305', 'call_function': 'spend', 'call_module': 'Treasury', 'call_args': [{'name': 'asset_kind', 'type': 'AssetKind', 'value': {'V3': {'location': {'parents': 0, 'interior': {'X1': {'Parachain': 1000}}}, 'asset_id': {'Concrete': {'parents': 0, 'interior': {'X2': ({'PalletInstance': 50}, {'GeneralIndex': 1337})}}}}}}, {'name': 'amount', 'type': 'AssetBalanceOf<T, I>', 'value': 288000000000}, {'name': 'beneficiary', 'type': 'BeneficiaryLookupOf<T, I>', 'value': {'V3': {'parents': 0, 'interior': {'X1': {'AccountId32': {'network': None, 'id': '0xb346948ec9e4cf84b965ec17a752b3e8eff098934aaad42ec50a347dd7936583'}}}}}}, {'name': 'valid_from', 'type': 'Option<BlockNumberFor<T, I>>', 'value': None}], 'call_hash': '0x6b046f76ce4b4fb75180e760f6b62c388719552b9315a95e56e5537358128e85'}

            hex_bytes = args[0]["value"]

            # Strip "0x" if present
            if isinstance(hex_bytes, str) and hex_bytes.startswith("0x"):
                hex_bytes = hex_bytes[2:]

            # Validate hex string
            try:
                scale_data = ScaleBytes("0x" + hex_bytes)
            except ValueError:
                logging.warning(f"Invalid hex string: {hex_bytes}")
                continue

            call = substrate.create_scale_object("Call", data=scale_data)
            try:
                call.decode()
            except Exception:
                logging.warning(
                    f"Failed to decode call from preimage hex: in block {block_id}"
                )
                continue
            decoded_call = call.value
            call = f"{decoded_call['call_function']}.{decoded_call['call_module']}"
            call_args = decoded_call["call_args"]
            preimage_hash = decoded_call["call_hash"]

            preimages[preimage_hash] = {
                "call": call,
                "call_args": call_args,
            }

            # index = hash_index_map.get(call_hash)
            # if index is None:
            #     logging.warning(
            #         f"Call hash not found in hash_index_map in note_preimage {call_hash} for block {block_id}"
            #     )
            #     continue
            # data = governance_data[index]
            # data["call"] = call
            # data["call_args"] = call_args

        elif module == "ConvictionVoting" and call == "vote":
            # {'Split': {'aye': 150000000000, 'nay': 150000000000}}
            # {'SplitAbstain': {'aye': 0, 'nay': 0, 'abstain': 10000000000}}
            # {'Standard': {'vote': {'aye': False, 'conviction': 'None'}, 'balance': 10000000000}}}

            index = next(arg["value"] for arg in args if arg["name"] == "poll_index")
            vote_arg = next(arg["value"] for arg in args if arg["name"] == "vote")

            # Initialize defaults
            vote_entry = {
                "account_id": from_address,
                "vote": None,
                "amount": None,
                "conviction": None,
                "timestamp": timestamp,
                "delegators": [],
            }

            if "Standard" in vote_arg:
                v = vote_arg["Standard"]
                vote_entry["vote"] = "aye" if v["vote"]["aye"] else "nay"
                vote_entry["amount"] = v["balance"]
                vote_entry["conviction"] = v["vote"]["conviction"]

            elif "Split" in vote_arg:
                v = vote_arg["Split"]
                vote_entry["vote"] = "split"
                vote_entry["amount"] = {"aye": v["aye"], "nay": v["nay"]}
                vote_entry["conviction"] = None

            elif "SplitAbstain" in vote_arg:
                v = vote_arg["SplitAbstain"]
                vote_entry["vote"] = "abstain"
                vote_entry["amount"] = {
                    "aye": v["aye"],
                    "nay": v["nay"],
                    "abstain": v["abstain"],
                }
                vote_entry["conviction"] = None

            else:
                raise ValueError(f"Unknown vote type: {vote_arg}")

            # Remove old vote from same account
            existing = governance_data[index]["voters"]
            governance_data[index]["voters"] = [
                v for v in existing if v["account_id"] != from_address
            ]
            governance_data[index]["voters"].append(vote_entry)

        elif module == "ConvictionVoting" and call == "remove_vote":
            index = next(arg["value"] for arg in args if arg["name"] == "index")
            existing = governance_data[index]["voters"]
            governance_data[index]["voters"] = [
                v for v in existing if v["account_id"] != from_address
            ]

        elif module == "ConvictionVoting" and call == "delegate":
            class_id = next(arg["value"] for arg in args if arg["name"] == "class")
            to = next(arg["value"] for arg in args if arg["name"] == "to")
            conviction = next(
                arg["value"] for arg in args if arg["name"] == "conviction"
            )
            amount = next(arg["value"] for arg in args if arg["name"] == "balance")

            # Append delegator to the delegatee's record
            for idx, pdata in governance_data.items():
                for v in pdata["voters"]:
                    if v["account_id"] == to:
                        # Remove older delegation from same delegator
                        v["delegators"] = [
                            d
                            for d in v["delegators"]
                            if d["account_id"] != from_address
                        ]
                        v["delegators"].append(
                            {
                                "account_id": from_address,
                                "timestamp": timestamp,
                                "amount": amount,
                                "conviction": conviction,
                                "class": class_id,
                            }
                        )

        elif module == "ConvictionVoting" and call == "undelegate":
            class_id = next(arg["value"] for arg in args if arg["name"] == "class")

            # Remove all delegations from this account
            for idx, pdata in governance_data.items():
                for v in pdata["voters"]:
                    v["delegators"] = [
                        d for d in v["delegators"] if d["account_id"] != from_address
                    ]


def map_hash_to_index(hash_index_map, governance_events):
    # {'block_id': 15978430, 'module_id': 'Referenda', 'event_id': 'Submitted', 'attributes': '{"index": 0, "track": 30, "proposal": {"Lookup": {"len": 8, "hash": "0x4663134d9382e57f574fa9d584723bd6b5265f567268dd8a70e878cf2df1a7cb"}}}', 'timestamp': 1686831900001}

    # Hash inside Referenda.Submitted is the preimage hash, which can be submitted multiple times for different referenda.
    for event in governance_events:
        if event["module_id"] == "Referenda" and event["event_id"] == "Submitted":
            attributes = json.loads(event["attributes"])
            index = attributes.get("index")
            hash = (
                attributes.get("proposal", {}).get("Lookup", {}).get("hash")
                or attributes.get("proposal", {}).get("Inline")
                or attributes.get("proposal", {}).get("Legacy", {}).get("hash")
            )

            if index is not None and hash is not None:
                hash_index_map[hash] = index
            elif index is None:
                logging.warning(f"Missing index in event: {event}")
            elif hash is None:
                logging.warning(f"Missing hash in event: {event}")


# Helper Functions
from typing import Any


def get_schema_signature(obj: Any):
    """
    Recursively generate a schema signature (type structure) for comparison.
    Returns a hashable representation (tuples of keys/types) for dicts/lists.
    """
    if isinstance(obj, dict):
        return tuple(sorted((k, get_schema_signature(v)) for k, v in obj.items()))
    elif isinstance(obj, list):
        if not obj:
            return ("list", None)
        return ("list", get_schema_signature(obj[0]))
    else:
        return type(obj).__name__  # use string names to ensure hashability


def get_unique_formats(governance_extrinsics, call_ids):
    for call_id in call_ids:
        print(f"\n=== Unique formats for call_id: {call_id} ===")
        seen_signatures = {}

        for ext in governance_extrinsics:
            if ext["call_id"] != call_id:
                continue

            try:
                parsed_args = json.loads(ext["call_args"])
            except Exception:
                continue  # skip invalid entries

            signature = get_schema_signature(parsed_args)

            if signature not in seen_signatures:
                seen_signatures[signature] = parsed_args

        # Print one example per unique schema
        for i, (sig, example) in enumerate(seen_signatures.items(), 1):
            print(f"\nFormat #{i}:\n{json.dumps(example, indent=2)}")


def get_token_decimals_at_block(substrate, block_number):
    if block_number >= 1248328:
        return substrate.token_decimals
    else:
        return 12


def get_total_balance_at_block_hash(substrate, account_address, block_id, block_hash):
    token_decimals = get_token_decimals_at_block(substrate, block_id)
    acc = substrate.query(
        module="System",
        storage_function="Account",
        params=[account_address],
        block_hash=block_hash,
    )
    total = (acc["data"]["free"].value + acc["data"]["reserved"].value) / (
        10**token_decimals
    )
    return total


def add_voter_balances(governance_data, substrate):
    total_count = len(governance_data)
    current_count = 0
    logging.info(f"Adding voter balances for {total_count} proposals.")
    for idx, pdata in governance_data.items():
        start_block = pdata["start_block"]
        end_block = pdata["end_block"]
        if start_block is None or end_block is None:
            # import pdb

            # pdb.set_trace()
            print(f"Skipping proposal {idx} due to missing start or end block.")
            continue
        start_block_hash = substrate.get_block_hash(start_block)
        end_block_hash = substrate.get_block_hash(end_block)

        logging.info(
            f"Processing proposal {idx}: start_block={start_block}, end_block={end_block}"
        )

        for v in pdata["voters"]:
            account_address = v["account_id"]
            total_balance_at_start = get_total_balance_at_block_hash(
                substrate, account_address, start_block, start_block_hash
            )
            total_balance_at_end = get_total_balance_at_block_hash(
                substrate, account_address, end_block, end_block_hash
            )
            v["start_balance"] = total_balance_at_start
            v["end_balance"] = total_balance_at_end

        current_count += 1
        if current_count % 10 == 0:
            logging.info(f"Processed {current_count} / {total_count} proposals.")


def fill_preimage_in_governance_data(governance_data, preimages):
    for idx, pdata in governance_data.items():
        preimage_hash = pdata.get("preimage_hash")
        if preimage_hash and preimage_hash in preimages:
            pdata["call"] = preimages[preimage_hash]["call"]
            pdata["call_args"] = preimages[preimage_hash]["call_args"]
        elif preimage_hash:
            logging.warning(
                f"Preimage hash {preimage_hash} for proposal {idx} not found in preimages."
            )


def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    config = load_config()
    db_connection = connect_db(config)
    logging.info("Database connection established.")

    substrate = None
    substrate = connect_substrate(config)
    logging.info("Substrate connection established.")

    governance_events = fetch_governance_events(db_connection)
    logging.info(f"Fetched {len(governance_events)} governance events.")

    governance_extrinsics = fetch_governance_extrinsics(db_connection)
    logging.info(f"Fetched {len(governance_extrinsics)} governance extrinsics.")

    # get_unique_formats(governance_extrinsics, ['vote', 'remove_vote', 'delegate', 'undelegate', 'submit', 'note_preimage'])
    # import pdb; pdb.set_trace()

    hash_index_map = {}
    map_hash_to_index(hash_index_map, governance_events)
    governance_data = defaultdict(lambda: default_proposal_obj())

    feed_governance_events_into_governance_data(governance_events, governance_data)
    logging.info("Fed governance events into governance data.")

    preimages = {}
    feed_governance_extrinsics_into_governance_data(
        db_connection, governance_extrinsics, governance_data, substrate, preimages
    )
    logging.info("Fed governance extrinsics into governance data.")

    fill_preimage_in_governance_data(governance_data, preimages)
    logging.info("Filled preimages into governance data.")

    add_voter_balances(governance_data, substrate)
    logging.info("Added voter balances to governance data.")
    import pdb

    pdb.set_trace()

    json.dump(governance_data, open("governance_data.json", "w"), indent=4)
    tail_indexes = [1541, 1542, 1543, 1544, 1545, 1546, 1547, 1548, 1549, 1553, 1555, 1557, 1558, 1559, 1560, 1562, 1563, 1564, 1567, 1568, 1570, 1572, 1573, 1574, 1575, 1576, 1577, 1578, 1579, 1580]
    for i in tail_indexes: governance_data.pop(i, None)
    db_connection.close()
    logging.info("Database connection closed.")


if __name__ == "__main__":
    main()
