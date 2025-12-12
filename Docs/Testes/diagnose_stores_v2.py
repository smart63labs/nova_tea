
import os
from google.genai import Client
from dotenv import load_dotenv

# Load env from tea/.env which seems to be the source of truth
load_dotenv('tea/.env')
api_key = os.getenv('GOOGLE_API_KEY')

print(f"API Key found: {'Yes' if api_key else 'No'}")
if api_key:
    print(f"API Key prefix: {api_key[:5]}...")

try:
    client = Client(api_key=api_key)
    print("Listing stores via google.genai.Client...")
    stores = list(client.file_search_stores.list())
    print(f"Found {len(stores)} stores.")
    for s in stores:
        print(f" - Name: {s.name} | Display: {s.display_name}")
except Exception as e:
    print(f"Error listing stores: {e}")
