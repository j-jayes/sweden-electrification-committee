import subprocess
import pandas as pd

# Read the CSV file
df = pd.read_csv('data/temp/filenames_and_pages.csv', sep=';')

# Iterate over each row in the DataFrame
for index, row in df.iterrows():
    filename = row['filename']
    start_page = row['start_page']
    end_page = row['end_page']
    
    # Construct the command
    command = f"python src/01-create-table-pdfs.py committee-reports-pdf/{filename} {start_page} {end_page}"
    
    # Run the command
    subprocess.run(command, shell=True)