import json
import os

# Paths
input_file = "era_blocks.json"
output_file = "era_blocks_v1.json"

# Read the original era_blocks.json
with open(input_file, "r") as f:
    era_blocks = json.load(f)

# Sort eras numerically (keys are likely strings)
eras_sorted = sorted(era_blocks.items(), key=lambda x: int(x[0]))

new_era_blocks = {}
prev_end_block = 0

for era, end_block in eras_sorted:
    start_block = prev_end_block
    new_era_blocks[era] = {
        "start_block": start_block,
        "end_block": end_block,
        "date": ""
    }
    prev_end_block = end_block

# Write to new file
with open(output_file, "w") as f:
    json.dump(new_era_blocks, f, indent=4)