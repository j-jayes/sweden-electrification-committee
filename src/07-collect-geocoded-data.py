import pandas as pd
import json
import os

input_folder = "data/table_output_geocoded"
dfs = []

for filename in os.listdir(input_folder):
    if filename.endswith(".json"):
        filepath = os.path.join(input_folder, filename)
        with open(filepath, "r") as f:
            data = json.load(f)
        # Flatten the JSON and add a column for the source file if needed
        df = pd.json_normalize(data["data"], sep="_")
        df["source_file"] = filename  # optional, to track which file a row came from
        dfs.append(df)

# Concatenate all the DataFrames
all_data = pd.concat(dfs, ignore_index=True)

# Save combined data to a single Parquet file
output_parquet = "data/table_output_geocoded_combined/all_geocoded_data.parquet"
all_data.to_parquet(output_parquet, index=False)
print(f"Saved combined data to {output_parquet}")
