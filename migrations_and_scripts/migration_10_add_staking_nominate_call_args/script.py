import json
import pdb
import os
import logging
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from configs.db_configuration import connection
from modules.era_block_mapping import get_blocks_for_era
import csv

data = json.load(open("migrations_and_scripts/script_5_get_validators_and_nominators/empty_nominator_validators.json"))
all_eras = set()
for validator, eras in data.items():
    all_eras.update(eras)

all_blocks = set()
for era in all_eras:
    blocks = get_blocks_for_era(int(era))
    all_blocks.update(blocks)

with connection.cursor() as cursor:
    # query = """
    #     SELECT block_id
    #     FROM polkadot_analysis.extrinsic
    #     WHERE module_id = 'staking' AND call_id = 'nominate' AND success = 1
    # """
    query = """
        SELECT block_id
        FROM polkadot_analysis.extrinsic
        WHERE module_id = 'staking' AND call_id = 'set_controller' AND success = 1 
        AND call_args IS NULL
    """

    cursor.execute(query)
    db_block_ids = set(row[0] for row in cursor.fetchall())

intersection_blocks = all_blocks.intersection(db_block_ids)
print(f"Number of intersecting blocks: {len(intersection_blocks)}")
with open("migrations_and_scripts/migration_10_add_staking_nominate_call_args/intersecting_block_ids_2.csv", "w", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["block_id"])
    for block_id in intersection_blocks:
        writer.writerow([block_id])
print("Intersecting block IDs written to intersecting_block_ids.csv")