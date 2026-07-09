import json

# Load times.json
with open('times.json', 'r') as f:
    times = json.load(f)  # {block_number(str): timestamp(str)}

# Load era_blocks_v1.json
with open('era_blocks_v1.json', 'r') as f:
    eras = json.load(f)  # {era(str): {start_block, end_block, date}}

# Map start time to each era's start_block
for era, data in eras.items():
    start_block = str(data['start_block'])
    start_time = times.get(start_block, "")
    data['date'] = start_time

# Save the updated eras with mapped dates
with open('era_blocks_with_dates.json', 'w') as f:
    json.dump(eras, f, indent=4)