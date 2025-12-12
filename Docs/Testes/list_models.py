import os
import json
from google.genai import Client

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

client = Client(api_key=api_key)
print("Listing models...")
try:
    # Try v1beta
    for m in client.models.list():
        print(f"Model: {m.name}")
        # if 'generateContent' in m.supported_generation_methods:
        #    print(f"- {m.name}")
except Exception as e:
    print(f"Error listing models: {e}")
