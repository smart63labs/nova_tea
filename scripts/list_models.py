import os
import json
from google.genai import Client

# Load API Key
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'dados', 'config.json')
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        c = json.load(f)
        api_key = c.get('api_key')
else:
    api_key = 'AIzaSyAc2_lINTYRCDd09KByCzTAV4oalJ_DlLw'

print(f"Using API Key: {api_key[:20]}...")

# Create client with v1beta
client = Client(api_key=api_key, http_options={'api_version': 'v1beta'})

print("\n=== Listando modelos disponíveis na API v1beta ===\n")

try:
    models = client.models.list()
    print(f"Total de modelos encontrados: {len(list(models))}\n")
    
    for model in client.models.list():
        print(f"Nome: {model.name}")
        print(f"  Display Name: {model.display_name if hasattr(model, 'display_name') else 'N/A'}")
        print(f"  Suporta generateContent: {hasattr(model, 'supported_generation_methods') and 'generateContent' in getattr(model, 'supported_generation_methods', [])}")
        print()
        
except Exception as e:
    print(f"Erro ao listar modelos: {e}")
    import traceback
    traceback.print_exc()
