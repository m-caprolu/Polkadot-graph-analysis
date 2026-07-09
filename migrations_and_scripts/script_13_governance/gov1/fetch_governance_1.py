import yaml
import pymysql
import logging
import os
import json
from collections import defaultdict
from substrateinterface import SubstrateInterface
from scalecodec.base import ScaleBytes


def load_config():
    config_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../config.yaml")
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


def parse_attributes(attributes_str):
    """Parse attributes from different formats."""
    if not attributes_str:
        return None

    try:
        attrs = json.loads(attributes_str)
    except:
        logging.error(f"Failed to parse attributes: {attributes_str}")
        return None

    return attrs


def extract_value_from_attributes(attrs, *keys):
    """
    Extract value from attributes in multiple formats.
    Handles formats:
    1. Direct value (int, str)
    2. List with type/value dicts: [{"type": "X", "value": Y}]
    3. Direct dict: {"key": value}
    """
    if attrs is None:
        return None

    # Format 1: Direct value (e.g., 35, "0x...")
    if isinstance(attrs, (int, str)):
        return attrs

    # Format 2: List of type/value dicts
    if isinstance(attrs, list):
        for key in keys:
            for item in attrs:
                if isinstance(item, dict):
                    if item.get("type") == key or item.get("name") == key:
                        return item.get("value")
        # If no match, return first value if exists
        if len(attrs) > 0 and isinstance(attrs[0], dict) and "value" in attrs[0]:
            return attrs[0]["value"]
        elif len(attrs) > 0:
            return attrs[0]

    # Format 3: Direct dict
    if isinstance(attrs, dict):
        for key in keys:
            if key in attrs:
                return attrs[key]

    return None


def extract_proposal_hash(attrs):
    """Extract proposal hash from attributes."""
    return extract_value_from_attributes(attrs, "proposal_hash", "Hash", "hash")


def extract_proposal_index(attrs):
    """Extract proposal index from attributes."""
    return extract_value_from_attributes(
        attrs, "proposal_index", "ProposalIndex", "index"
    )


def extract_ref_index(attrs):
    """Extract referendum index from attributes."""
    return extract_value_from_attributes(attrs, "ref_index", "ReferendumIndex", "index")


def extract_threshold(attrs):
    """Extract voting threshold from attributes."""
    return extract_value_from_attributes(attrs, "threshold", "VoteThreshold")


def extract_account(attrs):
    """Extract account from attributes."""
    return extract_value_from_attributes(attrs, "account", "AccountId", "who")


# Step 1: Fetch Public Proposals
def fetch_public_proposals(db_connection):
    """Fetch democracy.propose extrinsics with democracy.proposed events."""
    logging.info("Step 1: Fetching public proposals...")

    query = """
        SELECT 
            extrinsic.block_id,
            extrinsic.from_address AS from_address,
            extrinsic.module_id AS ex_mod,
            extrinsic.call_id AS ex_call,
            extrinsic.call_args AS ex_args,
            event.module_id AS ev_mod,
            event.event_id AS ev_call,
            event.attributes AS ev_args
        FROM
            polkadot_analysis.extrinsic
                JOIN
            polkadot_analysis.event ON extrinsic.block_id = event.block_id
                AND extrinsic.extrinsic_idx = event.extrinsic_idx
        WHERE
            extrinsic.module_id = 'democracy'
                AND extrinsic.call_id = 'propose'
                AND event.module_id = 'democracy'
                AND event.event_id = 'proposed'
                AND extrinsic.success = 1
    """

    with db_connection.cursor() as cursor:
        cursor.execute(query)
        results = cursor.fetchall()

    proposals_dict = {}

    for row in results:
        (
            block_id,
            from_address,
            ex_mod,
            ex_call,
            ex_args_str,
            ev_mod,
            ev_call,
            ev_args_str,
        ) = row

        ev_args = parse_attributes(ev_args_str)
        ex_args = parse_attributes(ex_args_str)

        if not ev_args or not ex_args:
            logging.error(f"Missing attributes in block {block_id}")
            continue

        proposal_index = extract_proposal_index(ev_args)

        if proposal_index is None:
            logging.error(f"Could not extract proposal index from {ev_args_str}")
            continue

        # Extract preimage hash from extrinsic args
        # Format 1: {"name": "proposal", "value": {"Lookup": {"hash": "0x..."}}}
        # Format 2: {"name": "proposal_hash", "value": "0x..."}
        preimage_hash = None
        if isinstance(ex_args, list):
            for arg in ex_args:
                if isinstance(arg, dict):
                    name = arg.get("name")
                    value = arg.get("value")

                    # Format 1: proposal with Lookup
                    if (
                        name == "proposal"
                        and isinstance(value, dict)
                        and "Lookup" in value
                    ):
                        preimage_hash = value["Lookup"].get("hash")
                    # Format 2: direct proposal_hash
                    elif name == "proposal_hash" and isinstance(value, str):
                        preimage_hash = value

                    if preimage_hash:
                        break

        key = ("public", proposal_index)
        proposals_dict[key] = {
            "proposal_index": proposal_index,
            "proposal_hash": None,
            "proposor_account_id": from_address,
            "source": "public",
            "status": "not_tabled",
            "preimage_hash": preimage_hash,
            "call": None,
            "call_args": None,
        }

    logging.info(f"Fetched {len(proposals_dict)} public proposals")
    return proposals_dict


# Step 2: Match referenda to proposals (Tabled)
def match_referenda_to_proposals(db_connection, proposals_dict):
    """Link democracy.started to democracy.tabled events."""
    logging.info("Step 2: Matching referenda to proposals...")

    query = """
        SELECT 
            block.timestamp,
            ev1.block_id,
            ev1.attributes AS started_attributes,
            ev2.attributes AS tabled_attributes
        FROM event AS ev1 
        JOIN event AS ev2 ON ev1.block_id = ev2.block_id
        JOIN block ON block.id = ev1.block_id
        WHERE ev1.module_id = 'democracy' AND ev1.event_id = 'started'
            AND ev2.module_id = 'democracy' AND ev2.event_id = 'tabled'
    """

    with db_connection.cursor() as cursor:
        cursor.execute(query)
        results = cursor.fetchall()

    referenda_dict = {}

    for row in results:
        timestamp, block_id, started_attrs_str, tabled_attrs_str = row

        if not started_attrs_str or not tabled_attrs_str:
            logging.error(f"NULL attributes in block {block_id}")
            continue

        started_attrs = parse_attributes(started_attrs_str)
        tabled_attrs = parse_attributes(tabled_attrs_str)

        ref_index = extract_ref_index(started_attrs)
        threshold = extract_threshold(started_attrs)
        proposal_index = extract_proposal_index(tabled_attrs)

        if ref_index is None or proposal_index is None:
            logging.error(f"Missing ref_index or proposal_index in block {block_id}")
            continue

        # Update proposal status
        proposal_key = ("public", proposal_index)
        if proposal_key in proposals_dict:
            proposals_dict[proposal_key]["status"] = "tabled"

        referenda_dict[ref_index] = {
            "proposal_key": proposal_key,
            "threshold": threshold,
            "voters": [],
            "state": None,
            "start_timestamp": timestamp,
            "start_block": block_id,
            "end_timestamp": None,
            "end_block": None,
            "source": "public",
        }

    logging.info(f"Matched {len(referenda_dict)} referenda to proposals")
    return referenda_dict


# Step 3: Process Preimages
def process_preimages(db_connection, proposals_dict, substrate):
    """Process democracy.note_imminent_preimage with democracy.PreimageNoted."""
    logging.info("Step 3: Processing preimages...")

    query = """
        SELECT 
            event.attributes AS ev_attributes,
            extrinsic.call_args AS ex_attributes
        FROM extrinsic 
        JOIN event ON extrinsic.block_id = event.block_id 
            AND extrinsic.extrinsic_idx = event.extrinsic_idx
        WHERE 
            extrinsic.module_id = 'democracy' AND extrinsic.call_id = 'note_imminent_preimage'
            AND event.module_id = 'democracy' AND event.event_id = 'PreimageNoted'
            AND extrinsic.success = 1
    """

    with db_connection.cursor() as cursor:
        cursor.execute(query)
        results = cursor.fetchall()

    preimage_count = 0

    for row in results:
        ev_attrs_str, ex_attrs_str = row

        if not ev_attrs_str or not ex_attrs_str:
            logging.warning("Empty attributes in preimage")
            continue

        ev_attrs = parse_attributes(ev_attrs_str)
        ex_attrs = parse_attributes(ex_attrs_str)

        # Extract hash from event attributes
        preimage_hash = extract_proposal_hash(ev_attrs)

        if not preimage_hash:
            logging.warning(f"Could not extract hash from {ev_attrs_str}")
            continue

        # Extract bytes from extrinsic attributes
        encoded_proposal = None
        if isinstance(ex_attrs, list):
            for arg in ex_attrs:
                if isinstance(arg, dict):
                    if (
                        arg.get("name") == "encoded_proposal"
                        or arg.get("type") == "Bytes"
                    ):
                        encoded_proposal = arg.get("value")
                        break

        if not encoded_proposal:
            logging.warning(
                f"Could not extract encoded_proposal for hash {preimage_hash}"
            )
            continue

        # Decode the proposal using substrate
        try:
            if encoded_proposal.startswith("0x"):
                encoded_proposal = encoded_proposal[2:]

            scale_data = ScaleBytes("0x" + encoded_proposal)
            call = substrate.create_scale_object("Call", data=scale_data)
            call.decode()
            decoded_call = call.value

            call_str = f"{decoded_call['call_module']}.{decoded_call['call_function']}"
            call_args = decoded_call.get("call_args", [])

            # Update all proposals with this preimage hash
            for key, proposal in proposals_dict.items():
                if proposal.get("preimage_hash") == preimage_hash:
                    proposal["call"] = call_str
                    proposal["call_args"] = call_args
                    preimage_count += 1

        except Exception as e:
            logging.warning(f"Failed to decode preimage {preimage_hash}: {e}")
            # Store as is
            for key, proposal in proposals_dict.items():
                if proposal.get("preimage_hash") == preimage_hash:
                    proposal["call"] = encoded_proposal
                    proposal["call_args"] = []

    logging.info(f"Processed {preimage_count} preimages")


# Step 4: Fetch Technical Committee Proposals
def fetch_tech_committee_proposals(db_connection, proposals_dict):
    """Fetch technical committee proposals."""
    logging.info("Step 4: Fetching technical committee proposals...")

    query = """
        SELECT attributes, block_id
        FROM event
        WHERE module_id = 'technicalcommittee' AND event_id = 'proposed'
    """

    with db_connection.cursor() as cursor:
        cursor.execute(query)
        results = cursor.fetchall()

    for row in results:
        attrs_str, block_id = row
        attrs = parse_attributes(attrs_str)

        if not attrs:
            continue

        account = extract_account(attrs)
        proposal_index = extract_proposal_index(attrs)
        proposal_hash = extract_proposal_hash(attrs)

        if proposal_index is None or proposal_hash is None:
            logging.warning(
                f"Missing data in tech committee proposal at block {block_id}"
            )
            continue

        key = ("tech", proposal_index)
        proposals_dict[key] = {
            "proposal_index": proposal_index,
            "proposal_hash": proposal_hash,
            "proposor_account_id": account,
            "source": "technical_committee",
            "status": "not_approved",
            "preimage_hash": None,
            "call": None,
            "call_args": None,
        }

    logging.info(
        f"Fetched {sum(1 for k in proposals_dict if k[0] == 'tech')} technical committee proposals"
    )


# Step 5: Link Technical Committee Approvals to Referenda
def link_tech_approvals_to_referenda(db_connection, proposals_dict, referenda_dict):
    """Link approved technical committee proposals to referenda."""
    logging.info("Step 5: Linking technical committee approvals to referenda...")

    query = """
        SELECT 
            block.timestamp,
            ev1.block_id,
            ev1.attributes AS proposal_hash_attrs,
            ev2.attributes AS referenda_details
        FROM event AS ev1 
        JOIN event AS ev2 ON ev1.block_id = ev2.block_id 
            AND ev1.extrinsic_idx = ev2.extrinsic_idx
        JOIN block ON block.id = ev1.block_id
        WHERE 
            ev1.module_id = 'technicalcommittee' AND
            ev1.event_id = 'approved' AND
            ev2.module_id = 'democracy' AND
            ev2.event_id = 'started'
    """

    with db_connection.cursor() as cursor:
        cursor.execute(query)
        results = cursor.fetchall()

    for row in results:
        timestamp, block_id, hash_attrs_str, ref_attrs_str = row

        hash_attrs = parse_attributes(hash_attrs_str)
        ref_attrs = parse_attributes(ref_attrs_str)

        proposal_hash = extract_proposal_hash(hash_attrs)
        ref_index = extract_ref_index(ref_attrs)
        threshold = extract_threshold(ref_attrs)

        if not proposal_hash or ref_index is None:
            logging.warning(f"Missing data in tech approval at block {block_id}")
            continue

        # Find the proposal with this hash
        proposal_key = None
        for key, proposal in proposals_dict.items():
            if key[0] == "tech" and proposal.get("proposal_hash") == proposal_hash:
                proposal["status"] = "approved"
                proposal_key = key
                break

        if proposal_key:
            referenda_dict[ref_index] = {
                "proposal_key": proposal_key,
                "threshold": threshold,
                "voters": [],
                "state": None,
                "start_timestamp": timestamp,
                "start_block": block_id,
                "end_timestamp": None,
                "end_block": None,
                "source": "technical_committee",
            }

    logging.info(
        f"Linked {sum(1 for r in referenda_dict.values() if r['source'] == 'technical_committee')} tech committee referenda"
    )


# Step 6: Fetch External Referenda
def fetch_external_referenda(db_connection, referenda_dict):
    """Fetch external referenda (ExternalTabled)."""
    logging.info("Step 6: Fetching external referenda...")

    query = """
        SELECT 
            block.timestamp,
            ev1.block_id,
            ev1.attributes AS started_attributes
        FROM event AS ev1 
        JOIN event AS ev2 ON ev1.block_id = ev2.block_id
        JOIN block ON block.id = ev1.block_id
        WHERE ev1.module_id = 'democracy' AND ev1.event_id = 'started'
            AND ev2.module_id = 'democracy' AND ev2.event_id = 'ExternalTabled'
    """

    with db_connection.cursor() as cursor:
        cursor.execute(query)
        results = cursor.fetchall()

    external_count = 0

    for row in results:
        timestamp, block_id, started_attrs_str = row

        started_attrs = parse_attributes(started_attrs_str)

        ref_index = extract_ref_index(started_attrs)
        threshold = extract_threshold(started_attrs)

        if ref_index is None:
            logging.warning(
                f"Missing ref_index in external referenda at block {block_id}"
            )
            continue

        # Only add if not already in referenda_dict
        if ref_index not in referenda_dict:
            referenda_dict[ref_index] = {
                "proposal_key": None,
                "threshold": threshold,
                "voters": [],
                "state": None,
                "start_timestamp": timestamp,
                "start_block": block_id,
                "end_timestamp": None,
                "end_block": None,
                "source": "external_referenda",
            }
            external_count += 1

    logging.info(f"Fetched {external_count} external referenda")


# Step 7: Process Voters
def process_voters(db_connection, referenda_dict):
    """Process democracy.voted events."""
    logging.info("Step 7: Processing voters...")

    # First, process votes from extrinsics (for early referenda <= 53)
    query_extrinsics = """
        SELECT
            block.timestamp,
            extrinsic.from_address,
            extrinsic.call_args
        FROM
            extrinsic
        JOIN block ON block.id = extrinsic.block_id
        WHERE
            module_id = 'democracy'
            AND call_id = 'vote'
            AND success = 1
    """

    with db_connection.cursor() as cursor:
        cursor.execute(query_extrinsics)
        results_ex = cursor.fetchall()

    vote_count_ex = 0

    for row in results_ex:
        timestamp, from_address, call_args_str = row

        if not call_args_str:
            continue

        call_args = parse_attributes(call_args_str)

        # Extract ref_index and vote details
        ref_index = None
        vote_data = None

        if isinstance(call_args, list):
            for arg in call_args:
                if isinstance(arg, dict):
                    if arg.get("name") == "ref_index":
                        ref_index = arg.get("value")
                    elif arg.get("name") == "vote":
                        vote_data = arg.get("value")

        if ref_index is None or vote_data is None or ref_index not in referenda_dict:
            continue

        # Parse vote
        vote_entry = {
            "account_id": from_address,
            "vote": None,
            "amount": None,
            "conviction": None,
            "timestamp": timestamp,
            "delegators": [],
        }

        if isinstance(vote_data, dict):
            if "Standard" in vote_data:
                standard = vote_data["Standard"]
                vote_entry["vote"] = "aye" if standard["vote"]["aye"] else "nay"
                vote_entry["amount"] = standard["balance"]
                vote_entry["conviction"] = standard["vote"].get("conviction")
            elif "Split" in vote_data:
                vote_entry["vote"] = "split"
                vote_entry["amount"] = vote_data["Split"]
            elif "SplitAbstain" in vote_data:
                vote_entry["vote"] = "abstain"
                vote_entry["amount"] = vote_data["SplitAbstain"]

        # Remove old vote from same account
        existing = referenda_dict[ref_index]["voters"]
        referenda_dict[ref_index]["voters"] = [
            v for v in existing if v["account_id"] != from_address
        ]
        referenda_dict[ref_index]["voters"].append(vote_entry)
        vote_count_ex += 1

    logging.info(f"Processed {vote_count_ex} votes from extrinsics")

    # Then, process votes from events
    query = """
        SELECT
            block.timestamp,
            event.attributes
        FROM
            event
        JOIN block ON block.id = event.block_id
        WHERE
            module_id = 'democracy' AND event_id = 'voted'
    """

    with db_connection.cursor() as cursor:
        cursor.execute(query)
        results = cursor.fetchall()

    vote_count = 0

    for row in results:
        timestamp, attrs_str = row

        if not attrs_str:
            continue

        attrs = parse_attributes(attrs_str)

        # Extract voter, ref_index, and vote details
        voter = extract_value_from_attributes(attrs, "voter", "AccountId")
        ref_index = extract_ref_index(attrs)
        vote_data = extract_value_from_attributes(attrs, "vote")

        if not voter or ref_index is None or not vote_data:
            logging.warning(f"Missing vote data: {attrs_str}")
            continue

        if ref_index not in referenda_dict:
            logging.warning(f"Vote for unknown referendum {ref_index}")
            continue

        # Parse vote
        vote_entry = {
            "account_id": voter,
            "vote": None,
            "amount": None,
            "conviction": None,
            "timestamp": timestamp,
            "delegators": [],
        }

        if isinstance(vote_data, dict):
            if "Standard" in vote_data:
                standard = vote_data["Standard"]
                vote_entry["vote"] = "aye" if standard["vote"]["aye"] else "nay"
                vote_entry["amount"] = standard["balance"]
                vote_entry["conviction"] = standard["vote"].get("conviction")
            elif "Split" in vote_data:
                vote_entry["vote"] = "split"
                vote_entry["amount"] = vote_data["Split"]
            elif "SplitAbstain" in vote_data:
                vote_entry["vote"] = "abstain"
                vote_entry["amount"] = vote_data["SplitAbstain"]

        referenda_dict[ref_index]["voters"].append(vote_entry)
        vote_count += 1

    logging.info(f"Processed {vote_count} votes")


# Step 8: Process Referenda States
def process_referenda_states(db_connection, referenda_dict):
    """Process democracy.Passed, NotPassed, Cancelled events."""
    logging.info("Step 8: Processing referenda states...")

    query = """
        SELECT
            block.timestamp,
            event.block_id,
            event.event_id,
            event.attributes
        FROM
            event
        JOIN block ON block.id = event.block_id
        WHERE
            module_id = 'democracy' AND event_id IN ('Passed', 'NotPassed', 'Cancelled')
    """

    with db_connection.cursor() as cursor:
        cursor.execute(query)
        results = cursor.fetchall()

    for row in results:
        timestamp, block_id, event_id, attrs_str = row

        attrs = parse_attributes(attrs_str)
        ref_index = extract_ref_index(attrs)

        if ref_index is None:
            logging.warning(f"Missing ref_index in {event_id} at block {block_id}")
            continue

        if ref_index in referenda_dict:
            referenda_dict[ref_index]["state"] = event_id.lower()
            referenda_dict[ref_index]["end_timestamp"] = timestamp
            referenda_dict[ref_index]["end_block"] = block_id

    logging.info(
        f"Updated states for {len([r for r in referenda_dict.values() if r['state']])} referenda"
    )


# Step 9: Process Delegations
def process_delegations(db_connection, referenda_dict):
    """Process democracy.delegated and undelegated events."""
    logging.info("Step 9: Processing delegations...")

    query = """
        SELECT block_id, attributes, event_id
        FROM event
        WHERE module_id = 'democracy' AND event_id IN ('delegated', 'undelegated')
        ORDER BY block_id
    """

    with db_connection.cursor() as cursor:
        cursor.execute(query)
        results = cursor.fetchall()

    current = {}  # delegator -> (target, start_block)
    history = []  # list of (delegator, target, start_block, end_block)

    for row in results:
        block_id, attrs_str, event_id = row

        attrs = parse_attributes(attrs_str)
        if not attrs:
            continue

        if event_id.lower() == "delegated":
            # Extract who and target
            if isinstance(attrs, list) and len(attrs) >= 2:
                who = (
                    attrs[0] if isinstance(attrs[0], str) else extract_account(attrs[0])
                )
                target = (
                    attrs[1]
                    if isinstance(attrs[1], str)
                    else extract_value_from_attributes(attrs[1], "AccountId", "target")
                )
            else:
                who = extract_value_from_attributes(attrs, "who", "AccountId")
                target = extract_value_from_attributes(attrs, "target")

            if not who or not target:
                continue

            # Close previous delegation if exists
            if who in current:
                old_target, start_block = current[who]
                history.append(
                    {
                        "delegator": who,
                        "target": old_target,
                        "start_block": start_block,
                        "end_block": block_id,
                    }
                )

            # Open new delegation
            current[who] = (target, block_id)

        elif event_id.lower() == "undelegated":
            account = extract_account(attrs)

            if not account:
                continue

            if account in current:
                target, start_block = current[account]
                history.append(
                    {
                        "delegator": account,
                        "target": target,
                        "start_block": start_block,
                        "end_block": block_id,
                    }
                )
                del current[account]

    # Close still-active delegations
    for delegator, (target, start_block) in current.items():
        history.append(
            {
                "delegator": delegator,
                "target": target,
                "start_block": start_block,
                "end_block": None,
            }
        )

    # Add delegators to voters
    for ref_index, ref_data in referenda_dict.items():
        start_block = ref_data["start_block"]
        end_block = ref_data["end_block"]

        for voter in ref_data["voters"]:
            voter_account = voter["account_id"]

            # Find delegations to this voter during referendum period
            for delegation in history:
                if delegation["target"] != voter_account:
                    continue

                # Check if delegation overlaps with referendum period
                del_start = delegation["start_block"]
                del_end = delegation["end_block"]

                if del_start is None or start_block is None:
                    continue

                # Delegation started before referendum ended
                if end_block is None or del_end is None:
                    # One or both are still active
                    if del_start <= (end_block or float("inf")):
                        voter["delegators"].append(
                            {
                                "account_id": delegation["delegator"],
                                "timestamp": None,  # TODO: could fetch from block
                                "amount": None,
                                "conviction": None,
                                "class": None,
                            }
                        )
                else:
                    # Both have end blocks
                    if del_start < end_block and (
                        del_end is None or del_end > start_block
                    ):
                        voter["delegators"].append(
                            {
                                "account_id": delegation["delegator"],
                                "timestamp": None,
                                "amount": None,
                                "conviction": None,
                                "class": None,
                            }
                        )

    total_delegators = sum(
        len(v["delegators"]) for r in referenda_dict.values() for v in r["voters"]
    )
    logging.info(
        f"Processed {len(history)} delegation records, added {total_delegators} delegators to voters"
    )


# Step 10: Process Treasury Proposals
def process_treasury_proposals(db_connection):
    """Process treasury proposals."""
    logging.info("Step 10: Processing treasury proposals...")

    query = """
        SELECT ev.block_id, ex.from_address AS account,  
        ev.attributes AS ev_attributes, ex.call_args AS ex_attributes
        FROM event AS ev 
        JOIN extrinsic AS ex ON ev.block_id = ex.block_id AND ev.extrinsic_idx = ex.extrinsic_idx
        WHERE ev.module_id = 'treasury' AND ev.event_id = 'proposed'
        AND ex.module_id = 'treasury' AND ex.call_id = 'propose_spend'
        AND ex.success = 1
    """

    treasury_dict = {}

    with db_connection.cursor() as cursor:
        cursor.execute(query)
        results = cursor.fetchall()

    for row in results:
        block_id, account, ev_attrs_str, ex_attrs_str = row

        ev_attrs = parse_attributes(ev_attrs_str)
        proposal_index = extract_proposal_index(ev_attrs)

        if proposal_index is None:
            continue

        key = (proposal_index, "treasury")
        treasury_dict[key] = {
            "proposor_account": account,
            "block_id": block_id,
            "type": "treasury",
            "amount": None,
            "source": "public",
            "status": "proposed",
        }

    logging.info(f"Processed {len(treasury_dict)} treasury proposals")
    return treasury_dict


def process_treasury_status(db_connection, treasury_dict):
    """Process treasury awarded/rejected/slashed events to set status."""
    logging.info("Processing treasury status events...")

    query = """
        SELECT 
            event_id,
            attributes
        FROM
            event
        WHERE
            module_id = 'treasury' AND event_id IN ('awarded', 'rejected', 'slashed')
    """

    with db_connection.cursor() as cursor:
        cursor.execute(query)
        results = cursor.fetchall()

    status_counts = {"awarded": 0, "rejected": 0, "slashed": 0}

    for row in results:
        event_id, attrs_str = row
        attrs = parse_attributes(attrs_str)

        if not attrs:
            continue

        proposal_index = extract_proposal_index(attrs)
        amount = extract_value_from_attributes(attrs, "award", "Balance", "slashed")

        if proposal_index is None:
            continue

        key = (proposal_index, "treasury")
        if key in treasury_dict:
            treasury_dict[key]["status"] = event_id
            if amount is not None:
                treasury_dict[key]["amount"] = amount
            if event_id in status_counts:
                status_counts[event_id] += 1

    logging.info(
        "Marked treasury proposals as awarded=%s, rejected=%s, slashed=%s",
        status_counts["awarded"],
        status_counts["rejected"],
        status_counts["slashed"],
    )


# Step 11: Process Tips
def process_tips(db_connection, treasury_dict):
    """Process tips (NewTip and TipClosed events)."""
    logging.info("Step 11: Processing tips...")

    # Fetch NewTip events
    query_new = """
        SELECT 
            ex.block_id, ex.from_address AS account, ev.attributes AS ev_attributes
        FROM
            polkadot_analysis.event AS ev 
        JOIN polkadot_analysis.extrinsic AS ex
            ON ev.block_id = ex.block_id AND ev.extrinsic_idx = ex.extrinsic_idx
        WHERE
            ev.module_id = 'tips' AND ev.event_id = 'newTip' AND ex.module_id = 'tips'
            AND ex.call_id = 'report_awesome'
            AND ex.success = 1
    """

    with db_connection.cursor() as cursor:
        cursor.execute(query_new)
        results = cursor.fetchall()

    for row in results:
        block_id, account, ev_attrs_str = row

        ev_attrs = parse_attributes(ev_attrs_str)
        tip_hash = extract_value_from_attributes(ev_attrs, "tip_hash", "Hash")

        if not tip_hash:
            continue

        key = (tip_hash, "tip")
        treasury_dict[key] = {
            "proposor_account": account,
            "block_id": block_id,
            "type": "tip",
            "amount": None,
            "source": "public",
            "status": "proposed",
        }

    # Fetch TipClosed/TipRetracted/TipRejected events
    query_closed = """
        SELECT event_id, attributes
        FROM event
        WHERE module_id = 'tips' AND event_id IN ('TipClosed', 'TipRetracted')
    """

    with db_connection.cursor() as cursor:
        cursor.execute(query_closed)
        results = cursor.fetchall()

    for row in results:
        event_id, attrs_str = row
        attrs = parse_attributes(attrs_str)

        tip_hash = extract_value_from_attributes(attrs, "tip_hash", "Hash")
        payout = extract_value_from_attributes(attrs, "payout", "Balance")

        if not tip_hash:
            continue

        key = (tip_hash, "tip")
        if key in treasury_dict:
            if event_id == "TipClosed":
                treasury_dict[key]["amount"] = payout
                treasury_dict[key]["status"] = "awarded"
            elif event_id == "TipRetracted":
                treasury_dict[key]["amount"] = 0
                treasury_dict[key]["status"] = "retracted"

    logging.info(f"Processed {sum(1 for k in treasury_dict if k[1] == 'tip')} tips")


# Step 12: Process Bounties
def process_bounties(db_connection, treasury_dict):
    """Process bounties."""
    logging.info("Step 12: Processing bounties...")

    # Fetch BountyProposed events
    query_proposed = """
        SELECT block_id, attributes
        FROM event
        WHERE module_id = 'bounties' AND event_id = 'bountyProposed'
    """

    with db_connection.cursor() as cursor:
        cursor.execute(query_proposed)
        results = cursor.fetchall()

    for row in results:
        block_id, attrs_str = row

        attrs = parse_attributes(attrs_str)
        index = extract_value_from_attributes(attrs, "index", "BountyIndex")

        if index is None:
            continue

        key = (index, "bounty")
        treasury_dict[key] = {
            "proposor_account": None,
            "block_id": block_id,
            "type": "bounty",
            "amount": 0,
            "source": "public",
            "status": "proposed",
        }

    # Fetch BountyClaimed events
    query_claimed = """
        SELECT attributes
        FROM event
        WHERE module_id = 'bounties' AND event_id = 'bountyClaimed'
    """

    with db_connection.cursor() as cursor:
        cursor.execute(query_claimed)
        results = cursor.fetchall()

    for row in results:
        attrs_str = row[0]
        attrs = parse_attributes(attrs_str)

        index = extract_value_from_attributes(attrs, "index", "BountyIndex")
        payout = extract_value_from_attributes(attrs, "payout", "Balance")

        if index is None:
            continue

        key = (index, "bounty")
        if key in treasury_dict:
            treasury_dict[key]["amount"] = payout
            treasury_dict[key]["status"] = "awarded"

    # Fetch BountyRejected events
    query_rejected = """
        SELECT attributes
        FROM event
        WHERE module_id = 'bounties' AND event_id = 'bountyRejected'
    """

    with db_connection.cursor() as cursor:
        cursor.execute(query_rejected)
        results = cursor.fetchall()

    for row in results:
        attrs_str = row[0]
        attrs = parse_attributes(attrs_str)

        index = extract_value_from_attributes(attrs, "index", "BountyIndex")

        if index is None:
            continue

        key = (index, "bounty")
        if key in treasury_dict:
            treasury_dict[key]["status"] = "rejected"

    logging.info(
        f"Processed {sum(1 for k in treasury_dict if k[1] == 'bounty')} bounties"
    )


# Step 13: Export to JSON
def export_to_json(proposals_dict, referenda_dict, treasury_dict, output_dir):
    """Export dictionaries to JSON files."""
    logging.info("Step 13: Exporting to JSON...")

    os.makedirs(output_dir, exist_ok=True)

    # Convert tuple keys to strings for JSON serialization
    proposals_json = {f"{k[0]}_{k[1]}": v for k, v in proposals_dict.items()}
    referenda_json = {str(k): v for k, v in referenda_dict.items()}
    treasury_json = {f"{k[0]}_{k[1]}": v for k, v in treasury_dict.items()}

    proposals_path = os.path.join(output_dir, "gov1_proposals.json")
    referenda_path = os.path.join(output_dir, "gov1_referenda.json")
    treasury_path = os.path.join(output_dir, "gov1_treasury.json")

    with open(proposals_path, "w") as f:
        json.dump(proposals_json, f, indent=2)

    with open(referenda_path, "w") as f:
        json.dump(referenda_json, f, indent=2)

    with open(treasury_path, "w") as f:
        json.dump(treasury_json, f, indent=2)

    logging.info(f"Exported proposals to {proposals_path}")
    logging.info(f"Exported referenda to {referenda_path}")
    logging.info(f"Exported treasury to {treasury_path}")


def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    config = load_config()
    db_connection = connect_db(config)
    logging.info("Database connection established.")

    substrate = connect_substrate(config)
    logging.info("Substrate connection established.")

    # Step 1: Fetch public proposals
    proposals_dict = fetch_public_proposals(db_connection)

    # Step 2: Match referenda to proposals
    referenda_dict = match_referenda_to_proposals(db_connection, proposals_dict)

    # Step 3: Process preimages
    # process_preimages(db_connection, proposals_dict, substrate)

    # Step 4: Fetch technical committee proposals
    fetch_tech_committee_proposals(db_connection, proposals_dict)

    # Step 5: Link tech approvals to referenda
    link_tech_approvals_to_referenda(db_connection, proposals_dict, referenda_dict)

    # Step 6: Fetch external referenda
    fetch_external_referenda(db_connection, referenda_dict)

    # Step 7: Process voters
    process_voters(db_connection, referenda_dict)

    # Step 8: Process referenda states
    process_referenda_states(db_connection, referenda_dict)

    # Step 9: Process delegations
    process_delegations(db_connection, referenda_dict)

    # Step 10-12: Process treasury data
    treasury_dict = process_treasury_proposals(db_connection)
    process_treasury_status(db_connection, treasury_dict)
    process_tips(db_connection, treasury_dict)
    process_bounties(db_connection, treasury_dict)

    # Step 13: Export to JSON
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    export_to_json(proposals_dict, referenda_dict, treasury_dict, output_dir)

    logging.info("=== Summary ===")
    logging.info(f"Total proposals: {len(proposals_dict)}")
    logging.info(f"  - Public: {sum(1 for k in proposals_dict if k[0] == 'public')}")
    logging.info(
        f"  - Tech Committee: {sum(1 for k in proposals_dict if k[0] == 'tech')}"
    )
    logging.info(f"Total referenda: {len(referenda_dict)}")
    logging.info(
        f"  - Public: {sum(1 for r in referenda_dict.values() if r['source'] == 'public')}"
    )
    logging.info(
        f"  - Tech Committee: {sum(1 for r in referenda_dict.values() if r['source'] == 'technical_committee')}"
    )
    logging.info(
        f"  - External: {sum(1 for r in referenda_dict.values() if r['source'] == 'external_referenda')}"
    )
    logging.info(f"Total treasury items: {len(treasury_dict)}")
    logging.info(
        f"  - Treasury proposals: {sum(1 for k in treasury_dict if k[1] == 'treasury')}"
    )
    logging.info(f"  - Tips: {sum(1 for k in treasury_dict if k[1] == 'tip')}")
    logging.info(f"  - Bounties: {sum(1 for k in treasury_dict if k[1] == 'bounty')}")

    db_connection.close()
    logging.info("Database connection closed.")


if __name__ == "__main__":
    main()
