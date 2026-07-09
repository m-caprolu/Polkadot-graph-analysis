import json

def extract_schema(data):
    """Recursively extracts schema structure from JSON data."""
    if isinstance(data, dict):
        return {k: extract_schema(v) for k, v in data.items()}
    elif isinstance(data, list):
        if len(data) > 0:
            return [extract_schema(data[0])]
        else:
            return []
    else:
        return type(data).__name__

# Step 1: Read governance_data.json
with open("governance_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Step 2: Generate schema
schema = extract_schema(data)

# Step 3: Write the formatted schema to file
with open("governance_schema.json", "w", encoding="utf-8") as f:
    json.dump(schema, f, indent=3, ensure_ascii=False)

print("Schema written to governance_schema.json")
