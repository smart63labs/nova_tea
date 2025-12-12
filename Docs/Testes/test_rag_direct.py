from google import genai
from google.genai import types
import os
import json
import time

# Load config
CONFIG_PATH = os.path.join(os.getcwd(), 'dados', 'config.json')
api_key = None
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        c = json.load(f)
        api_key = c.get('api_key')

client = genai.Client(api_key=api_key)

store_name = 'fileSearchStores/secretaria-da-fazenda-joyyaq4txyvy'
# model_name = 'gemini-2.0-flash' 
# model_name = 'gemini-2.0-flash' 
# model_name = 'gemini-2.0-flash-lite-preview-02-05' # Alternative
# model_name = 'gemini-2.5-flash' # From list_models.py
# model_name = 'gemini-1.5-flash' # Fallback for free tier
# model_name = 'gemini-2.5-flash-lite' # Attempting other flash model
model_name = 'gemini-flash-latest'

print(f"Querying model {model_name} with store {store_name}...")

import time

max_retries = 5
for attempt in range(max_retries):
    try:
        # Using types for better safety
        tool = types.Tool(
            file_search=types.FileSearch(file_search_store_names=[store_name])
        )
        response = client.models.generate_content(
            model=model_name,
            contents='o que é o O e-DOCS ?',
            config=types.GenerateContentConfig(tools=[tool])
        )
        
        print("Response received:")
        print(response.text)
        break
    except Exception as e:
        print(f"Error (Attempt {attempt+1}/{max_retries}): {e}")
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "503" in str(e):
            wait_time = 60
            print(f"Rate limited or Overloaded. Waiting {wait_time}s...")
            time.sleep(wait_time)
        else:
            break
