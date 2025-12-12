import os
import json
from google.genai import Client

# Load config
try:
    with open('dados/config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
        api_key = config.get('api_key')
except Exception as e:
    print(f"Error loading config: {e}")
    exit(1)

if not api_key:
    print("API Key not found in config.json")
    exit(1)

try:
    client = Client(api_key=api_key)
    print("Listing stores...")
    stores = []
    for store in client.file_search_stores.list():
        print(f"Found store: {store.name} - {store.display_name}")
        stores.append(store)
    
    print(f"Total stores found: {len(stores)}")
except Exception as e:
    print(f"Error listing stores: {e}")