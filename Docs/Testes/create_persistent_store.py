
import os
import sys
from google.genai import Client
from dotenv import load_dotenv

# Simulate App's loading
load_dotenv('tea/.env')
api_key = os.getenv('GOOGLE_API_KEY')
client = Client(api_key=api_key)

try:
    print(f"Creating persistent Store 'TEST_PERSISTENT_STORE_v2'...")
    store = client.file_search_stores.create(config={'display_name': 'TEST_PERSISTENT_STORE_v2'})
    print(f"✅ Created Store: {store.name}")
    print(f"Please run 'diagnose_stores_v2.py' after restarting the environment/process to verify if it still exists.")
except Exception as e:
    print(f"Error: {e}")
