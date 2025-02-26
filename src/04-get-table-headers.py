from typing import ClassVar, Literal, Optional, List
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

# Load environment variables from .env file
load_dotenv()

# Retrieve the API key
api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI()

##########################################

prompt = """
You are an expert in extracting structured data from scanned historical tables. You are also an expert on Swedish geography and the country’s electrification. You are to help me extract data from a scan of a table about the power stations and transformers located in Sweden in the 1920s.

I want you to create a json table that links the column number to the column label to the column description. Be concise and clear, and continue to use the Swedish descriptions. In the case that column labels are shared in part between columns, write the full description in the table.

context: on several other pages of the table, the column numbers are present but the headings missing. We need the column labels in order to extract the data. Return only the json table.  Do not use python, just read the table and return the output. 
"""
class ColumnHeader(BaseModel):
    id: int = Field(..., description="Numeric identifier for the column")
    label: str = Field(..., description="Short label for the column header")
    description: Optional[str] = Field(None, description="Longer notes about this column")

class TableSchema(BaseModel):
    columns: List[ColumnHeader]

def normalize_filename(filename):
    """Normalize filename to NFC form to avoid Unicode decomposition issues."""
    return unicodedata.normalize('NFC', filename)

def get_table_headers(filename):
    filename = normalize_filename(filename)  # Normalize filename before use
    logging.info(f"Processing file: {filename}")
    
    save_path = f"data/table_headers/{filename}.json"
    
    # Check if the file already exists
    if os.path.exists(save_path):
        logging.info(f"File {save_path} already exists. Skipping.")
        return
    
    try:
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", 
                 "content": [
                     {"type": "text", "text": f"Here is the table to extract, with filename {filename}"},
                     {
                        "type": "image_url",
                        "image_url": {
                            "url": f"https://github.com/j-jayes/sandbox/blob/main/images_electrification/{filename}?raw=true",
                        }
                    }
                 ]
                }
            ],
            response_format=TableSchema,
            max_tokens=3000
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

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Normalize all filenames in the list
list_of_files_to_process = [
    normalize_filename("Älvsborg_1.png"),
    normalize_filename("Blekinge_1.png"),
    normalize_filename("Gävleborg_1.png"),
    normalize_filename("Goteborgs-och-Bohus_1.png"),
    normalize_filename("Gotland_1.png"),
    normalize_filename("Halland_1.png"),
    normalize_filename("Jämtland_1.png"),
    normalize_filename("Jönköping_1.png"),
    normalize_filename("Kalmar_1.png"),
    normalize_filename("Kopparberg_1.png"),
    normalize_filename("Kronobergs_1.png"),
    normalize_filename("Kristianstad_1.png"),
    normalize_filename("Örebro_1.png"),
    normalize_filename("Östergötland_1.png"),
    normalize_filename("Södermanland_1.png"),
    normalize_filename("Stockholm_1.png"),
    normalize_filename("Uppsala_1.png"),
    normalize_filename("urn-nbn-se-kb-digark-1892077_1.png"),
    normalize_filename("Värmland_1.png"),
    normalize_filename("Västerbotten_1.png"),
    normalize_filename("Västernorrland_1.png"),
    normalize_filename("Västmanland_1.png")
]

def main():
    for filename in list_of_files_to_process:
        get_table_headers(filename)

if __name__ == "__main__":
    main()


