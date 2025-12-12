
import os
import time
from google.genai import Client
from dotenv import load_dotenv

load_dotenv('tea/.env')
api_key = os.getenv('GOOGLE_API_KEY')
client = Client(api_key=api_key)

try:
    print("Creating test store...")
    store = client.file_search_stores.create(config={'display_name': 'TEST_PERSISTENCE_STORE'})
    print(f"Store created: {store.name}")
    
    print("Listing stores immediately...")
    stores = list(client.file_search_stores.list())
    found = any(s.name == store.name for s in stores)
    print(f"Store found in list? {found}")

    print("Waiting 5 seconds...")
    time.sleep(5)
    
    print("Listing stores again...")
    stores = list(client.file_search_stores.list())
    found = any(s.name == store.name for s in stores)
    print(f"Store persists? {found}")
    
    # Cleanup
    print("Cleaning up test store...")
    client.file_search_stores.delete(name=store.name)
    print("Cleanup done.")

except Exception as e:
    print(f"Error: {e}")
