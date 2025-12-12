from google import genai
import os
import json

# Load config
CONFIG_PATH = os.path.join(os.getcwd(), 'dados', 'config.json')
api_key = None
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        c = json.load(f)
        api_key = c.get('api_key')

if not api_key:
    print("No API Key found")
    exit(1)

client = genai.Client(api_key=api_key)

print("Listing File Search Stores...")
try:
    for store in client.file_search_stores.list():
        print(f"Name: {store.name}")
        print(f"Display Name: {store.display_name}")
        print("-" * 20)
except Exception as e:
    print(f"Error listing stores: {e}")
