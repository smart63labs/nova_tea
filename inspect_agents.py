
import os
from google.genai import types
from google import genai
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)

# --- Configuration ---
# Assuming same config as app.py
PROJECT_ID = "ia-sandbox-443714"
LOCATION = "us-central1"

def get_genai_client():
    import json
    
    # Try to load from config.json
    try:
        with open('dados/config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            api_key = config.get('api_key')
            if api_key:
                os.environ['GOOGLE_API_KEY'] = api_key
    except Exception as e:
        print(f"Could not load config.json: {e}")

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not set")
        return None
    return genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})

def inspect_agents():
    client = get_genai_client()
    if not client:
        return

    print("Listing caches...")
    try:
        if hasattr(client, 'caches'):
            for cache in client.caches.list(config={'page_size': 10}):
                 print(f"Cache: {cache.name}")
                 # Check contents
                 print(f"  Contents: {cache}")
        else:
            print("No 'caches' attribute.")
            
    except Exception as e:
        print(f"Error listing caches: {e}")

if __name__ == "__main__":
    inspect_agents()
