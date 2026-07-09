# This script gets all the validators a certain nominator nominated using `staking.nominate` extrinsic for all eras

# - validator: era: nominators: []
# - nominate.staking => process validators
# - era = get_block_era(block) + 1 # because nominating for next era not current
# - Load isolated validators, get nominators for isolated validators. If a validator had zero nominators, report.

import json
import os
import sys
import logging
import csv
import pdb

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from configs.db_configuration import connection
from modules.era_block_mapping import get_era_for_block

def process_args(args):
    try:
        args_json = json.loads(args)

        for arg in args_json:
            if (arg.get("name") == "targets" or arg.get("type") == "Vec<AccountIdLookupOf>") and "value" in arg:
                # Example: [{"name": "targets", "type": "Vec<AccountIdLookupOf>", "value": ["11VR4pF6c7kfBhfmuwwjWY3FodeYBKWx7ix2rsRCU2q6hqJ", "1jqkeJhuoRudNTVL5dV1qZf8RQtyzcf6ZT4yyvUQbKFktr8"]}]
                return arg["value"]
            else:
                pdb.set_trace() # TODO: handle other formats
    except Exception:
        pass
    return []

# Load isolated validators
with open("migrations_and_scripts/script_5_get_validators_and_nominators/empty_nominator_validators.json") as f:
    isolated_validators = json.load(f)

validator_era_nominators = {}

with connection.cursor() as cursor:
    query = """
        SELECT block_id, call_args, from_address
        FROM polkadot_analysis.extrinsic
        WHERE module_id = 'staking' AND call_id = 'nominate' AND success = 1 
        AND call_args IS NOT NULL
    """
    # TODO: remove last line after fetching is complete
    cursor.execute(query)
    rows = cursor.fetchall()

    for block_id, args, nominator in rows:

        args = process_args(args) 
        era = get_era_for_block(block_id) + 1  # nominating for next era
        try:
            nominated_validators = json.loads(args)[0]  # assuming args is a JSON array: [validators]
        except Exception:
            continue

        for validator in nominated_validators:
            if validator in isolated_validators:
                if validator_era_nominators[validator] is None:
                    validator_era_nominators[validator] = {}
                if validator_era_nominators[validator].get(era) is None:
                    validator_era_nominators[validator][era] = []
                validator_era_nominators[validator][era].append(nominator)

# Report validators with zero nominators
report = []
for validator in isolated_validators:
    for era in set(era for (v, era) in validator_era_nominators if v == validator):
        nominators = validator_era_nominators[validator][era]
        if not nominators:
            report.append({'validator': validator, 'era': era, 'nominators': []})

# Save report to CSV
with open("isolated_validators_zero_nominators.csv", "w", newline='') as csvfile:
    fieldnames = ['validator', 'era', 'nominators']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for entry in report:
        writer.writerow(entry)
