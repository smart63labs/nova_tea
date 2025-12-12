
import os
import sys
from google.genai import Client
from dotenv import load_dotenv

# Force stdout flush
sys.stdout.reconfigure(encoding='utf-8')

print("--- DIAGNOSTIC START ---")

# Load env
load_dotenv('tea/.env')
api_key = os.getenv('GOOGLE_API_KEY')

if not api_key:
    # Try config.json
    import json
    try:
        with open('dados/config.json', 'r') as f:
            cfg = json.load(f)
            api_key = cfg.get('api_key')
    except:
        pass

print(f"API Key present: {'Yes' if api_key else 'No'}")
if not api_key:
    print("CRITICAL: No API Key found.")
    sys.exit(1)

try:
    client = Client(api_key=api_key)
    print("Listing stores...")
    stores = list(client.file_search_stores.list())
    print(f"Total Stores Found: {len(stores)}")
    print("-" * 40)
    for s in stores:
        print(f"ID: {s.name}")
        print(f"Display Name: {s.display_name}")
        print("-" * 40)
    print("--- DIAGNOSTIC END ---")
except Exception as e:
    print(f"ERROR: {e}")
