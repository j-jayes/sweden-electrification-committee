from typing import ClassVar, Literal, Optional
from pydantic import BaseModel, Field
from openai import OpenAI, OpenAIError, BadRequestError, APIError
import openai
import base64
import requests
from dotenv import load_dotenv
import os
import json
import logging
import unicodedata
import json

# Load environment variables from .env file
load_dotenv()

# Retrieve the API key
api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI()

##########################################


prompt = f"""

You are an expert in extracting structured data from scanned historical tables. You are also an expert on Swedish geography and the country’s electrification. 

You are to help me extract data from a scan of a table about the power stations and transformers located in Sweden in the 1920s.

Your task:
1. Read the following table carefully from the scan
2. For each row:
   - Identify the index (row number).
   - Extract the company or owner name.
   - Extract the location. This will be put in a geocoding engine, so please try and provide a reasonable location in Sweden. If you see an abbreviation like `v.`, interpret it as “Väster” if context suggests that’s the correct expansion.
   - Determine if the row is a power station or a transformer. If it’s a transformer, the power source is “subscription” and the `power_station_name` should say `"subscription from X"`, where X is the station name or the text after “Ab. Fr.” 
   - If it’s a power station, read the abbreviation for the source:  
       - “v” or “vatten” => `water`  
       - “å” or “ånga” => `steam`  
       - “d” or “diesel” => `diesel`  
       - “o” or “olja” => `oil`  
   - Extract the capacity (in kVA), if provided, carefully.
- Note that the information in a row might depend on rows above it, indicated by >> or “ditto” where it should be filled in with the first non-empty row above. 
3. Return the data in valid JSON that conforms to the `PowerDataCollection` schema.  
4. Make sure all field names and data types match the Pydantic schema exactly.
5. Do not use python, just read the tables carefully and produce the output according to the schema. 
"""

def normalize_filename(filename):
    """Normalize filename to NFC form to avoid Unicode decomposition issues."""
    return unicodedata.normalize('NFC', filename)

def trim_filename(filename):
    # the purpose of this function is to remove the file extension from the filename as well as the suffix "_{i}" where i is the page number
    # e.g. "Älvsborg_1.png" -> "Älvsborg"
    return filename.split(".")[0].split("_")[0]

def read_in_table_headers(trimmed_filename):
    # read in the table headers from the json file in data/table_headers
    with open(f"data/table_headers/{trimmed_filename}_1.png.json", "r") as file:
        data = json.load(file)
    
    table_headers = ""
    for i, column in enumerate(data["columns"]):
        table_headers += f"{i+1}. {column['label']} - {column['description']}\n\n"
    
    return table_headers

class BasePowerData(BaseModel):
    """
    Base model capturing the row-level data from the 1924 Swedish electrification tables.
    """
    index: int = Field(..., description="Row index in the table")
    company_name: str = Field(..., description="Name of the company or owner")
    location: str = Field(..., description="Location (kommun/stad). Adjust as needed for geocoding (e.g., 'v' -> 'Väster')")
    power_station_name: Optional[str] = Field(
        None,
        description="Name of the power station, or 'subscription from X' if it's a transformer row"
    )
    power_source: Literal[
        "water",
        "steam",
        "diesel",
        "oil",
        "subscription"
    ] = Field(
        ...,
        description=(
            "The source of the power. "
            "Options are: "
            " - 'water' (from 'v' = vatten), "
            " - 'steam' (from 'å' = ånga), "
            " - 'diesel' (from 'd'), "
            " - 'oil' (from 'o'), "
            " - 'subscription' if the row is for a transformer (i.e., solid line or 'Ab. Fr')."
        )
    )
    installed_capacity_kva: Optional[int] = Field(
        None,
        description="Installed capacity in kVA. Can be 0 or None if not specified."
    )

class PowerDataCollection(BaseModel):
    """
    A container for multiple rows extracted from the table.
    """
    data: list[BasePowerData] = Field(
        ...,
        description="A list of power data entries extracted from the table."
    )


def get_table_data(filename):
    filename = normalize_filename(filename)  # Normalize filename before use
    logging.info(f"Processing file: {filename}")
    
    save_path = f"data/table_output/{filename}.json"

    table_headers = read_in_table_headers(trim_filename(normalize_filename(filename)))

    # Check if the file already exists
    if os.path.exists(save_path):
        logging.info(f"File {save_path} already exists. Skipping.")
        return
    
    try:
        response = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", 
                 "content": [
                     {"type": "text", "text": "Here is are the table headers:"},
                     {"type": "text", "text": table_headers},
                     {"type": "text", "text": f"Here is the scan of the table to extract data from, with filename {filename}"},
                     {
                        "type": "image_url",
                        "image_url": {
                            "url": f"https://github.com/j-jayes/sandbox/blob/main/images_electrification/{filename}?raw=true",
                        }
                    }
                 ]
                }
            ],
            response_format=PowerDataCollection,
            max_tokens=10000
        )

        json_object = json.loads(response.choices[0].message.content)
        json_object["filename"] = filename  # Use normalized filename

        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        # Save the JSON object
        with open(save_path, 'w', encoding="utf-8") as json_file:
            json.dump(json_object, json_file, indent=4, ensure_ascii=False)
        
        logging.info(f"Successfully processed and saved file: {filename}")

    except BadRequestError as e:
        logging.error(f"BadRequestError for document {filename}: {str(e)}")
    except APIError as e:
        logging.error(f"APIError for document {filename}: {str(e)}")
    except OpenAIError as e:
        logging.error(f"OpenAIError for document {filename}: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error for document {filename}: {str(e)}")


# set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
list_of_files_to_process = [
    "Älvsborg_1.png", "Älvsborg_2.png", "Älvsborg_3.png", "Älvsborg_4.png", "Älvsborg_5.png", "Älvsborg_6.png", "Älvsborg_7.png", "Älvsborg_8.png", 
    "Blekinge_1.png", "Blekinge_2.png", "Blekinge_3.png", 
    "Gävleborg_1.png", "Gävleborg_2.png", "Gävleborg_3.png", "Gävleborg_4.png", "Gävleborg_5.png", "Gävleborg_6.png", "Gävleborg_7.png", 
    "Goteborgs-och-Bohus_1.png", "Goteborgs-och-Bohus_2.png", "Goteborgs-och-Bohus_3.png", 
    "Gotland_1.png", 
    "Halland_1.png", "Halland_2.png", "Halland_3.png", "Halland_4.png", "Halland_5.png", "Halland_6.png", "Halland_7.png", "Halland_8.png", "Halland_9.png", "Halland_10.png", 
    "Jämtland_1.png", "Jämtland_2.png", "Jämtland_3.png", "Jämtland_4.png", 
    "Jönköping_1.png", "Jönköping_2.png", "Jönköping_3.png", "Jönköping_4.png", "Jönköping_5.png", "Jönköping_6.png", "Jönköping_7.png", "Jönköping_8.png", "Jönköping_9.png", "Jönköping_10.png", "Jönköping_11.png", "Jönköping_12.png", "Jönköping_13.png", "Jönköping_14.png", "Jönköping_15.png", 
    "Kalmar_1.png", "Kalmar_2.png", "Kalmar_3.png", "Kalmar_4.png", "Kalmar_5.png", 
    "Kopparberg_1.png", "Kopparberg_2.png", "Kopparberg_3.png", "Kopparberg_4.png", "Kopparberg_5.png", "Kopparberg_6.png", "Kopparberg_7.png", "Kopparberg_8.png", "Kopparberg_9.png", 
    "Kristianstad_1.png", "Kristianstad_2.png", "Kristianstad_3.png", "Kristianstad_4.png", "Kristianstad_5.png", "Kristianstad_6.png", "Kristianstad_7.png", "Kristianstad_8.png", "Kristianstad_9.png", 
    "Kronobergs_1.png", "Kronobergs_2.png", "Kronobergs_3.png", "Kronobergs_4.png", 
    "Örebro_1.png", "Örebro_2.png", "Örebro_3.png", "Örebro_4.png", "Örebro_5.png", "Örebro_6.png", 
    "Östergötland_1.png", "Östergötland_2.png", "Östergötland_3.png", "Östergötland_4.png", 
    "Södermanland_1.png", "Södermanland_2.png", "Södermanland_3.png", "Södermanland_4.png", 
    "Stockholm_1.png", "Stockholm_2.png", "Stockholm_3.png", "Stockholm_4.png", "Stockholm_5.png", "Stockholm_6.png", 
    "Uppsala_1.png", "Uppsala_2.png", "Uppsala_3.png", 
    "urn-nbn-se-kb-digark-1892077_1.png",
    "Värmland_1.png", "Värmland_2.png", "Värmland_3.png", "Värmland_4.png", "Värmland_5.png", "Värmland_6.png", "Värmland_7.png", "Värmland_8.png", "Värmland_9.png", "Värmland_10.png", "Värmland_11.png", 
    "Västerbotten_1.png", "Västerbotten_2.png", "Västerbotten_3.png", "Västerbotten_4.png", 
    "Västernorrland_1.png", "Västernorrland_2.png", "Västernorrland_3.png", "Västernorrland_4.png", "Västernorrland_5.png", "Västernorrland_6.png", "Västernorrland_7.png", "Västernorrland_8.png", "Västernorrland_9.png", "Västernorrland_10.png", 
    "Västmanland_1.png", "Västmanland_2.png", "Västmanland_3.png", "Västmanland_4.png"
]



def main():   
    for filename in list_of_files_to_process:
        # log filename
        get_table_data(filename)

if __name__ == "__main__":
    main()