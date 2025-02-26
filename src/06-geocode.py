import os
import json
import requests
import dotenv

# Load environment variables from .env file
dotenv.load_dotenv()

API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# File to store the cache of geocoding results so we don't call the API repeatedly
CACHE_FILE = "data/geocode_cache.json"

def load_cache():
    """Load geocoding cache if available."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    """Save geocoding cache to disk."""
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

def extract_county(file_name):
    """
    Extract the county name from the file name.
    For example, for 'Älvsborg_1.png' it returns 'Älvsborg'.
    """
    base = os.path.basename(file_name)
    # Split at underscore and take the first part
    county = base.split('_')[0]
    return county

def geocode_location(query, cache):
    """
    Geocode a location query using Google Geocoding API.
    Checks the cache first to avoid duplicate calls.
    """
    if query in cache:
        print(f"Cache hit for: {query}")
        return cache[query]
    
    print(f"Geocoding: {query}")
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": query, "key": API_KEY}
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        print(f"Error: Received status code {response.status_code} for query: {query}")
        return None
    
    data = response.json()
    if data.get("status") != "OK" or not data.get("results"):
        print(f"Geocoding failed for {query}: {data.get('status')}")
        return None
    
    result = data["results"][0]
    geocode_result = {
        "formatted_address": result.get("formatted_address"),
        "location": result["geometry"]["location"]
    }
    # Save the result to cache
    cache[query] = geocode_result
    return geocode_result

def process_file(filepath, cache):
    """Process a single JSON file: print its content, geocode locations, and add geocoding data."""
    print(f"\nProcessing file: {filepath}")
    with open(filepath, "r") as f:
        file_data = json.load(f)
    
    # Print the file content to the console for inspection
    print(json.dumps(file_data, indent=2, ensure_ascii=False))
    
    # Extract county name from the 'filename' key in the JSON file
    filename_in_json = file_data.get("filename", "")
    county = extract_county(filename_in_json)
    county_suffix = f"{county} county, Sweden"
    
    # Process each record in the 'data' list
    for record in file_data.get("data", []):
        original_location = record.get("location", "")
        # Append the county to the location string
        full_location = f"{original_location}, {county_suffix}"
        record["full_location"] = full_location
        
        # Geocode the full location, using the cache to avoid duplicate calls
        geocode_result = geocode_location(full_location, cache)
        record["geocoding"] = geocode_result
    
    return file_data

def main():
    input_folder = "data/table_output"
    output_folder = "data/table_output_geocoded"
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Load or initialize the cache
    cache = load_cache()
    
    # Process every JSON file in the input folder
    for file_name in os.listdir(input_folder):
        if file_name.endswith(".json"):
            filepath = os.path.join(input_folder, file_name)
            processed_data = process_file(filepath, cache)
            
            # Save the updated file to the output folder
            output_filepath = os.path.join(output_folder, file_name)
            with open(output_filepath, "w") as out_f:
                json.dump(processed_data, out_f, indent=2, ensure_ascii=False)
    
    # Save the cache for future runs
    save_cache(cache)
    print("\nProcessing complete.")

if __name__ == "__main__":
    main()
