
import os
import json
from google.genai import Client
from dotenv import load_dotenv
import datetime

load_dotenv('tea/.env')
api_key = os.getenv('GOOGLE_API_KEY')
client = Client(api_key=api_key)

# Pegar a primeira store para teste
stores = list(client.file_search_stores.list())
if not stores:
    print("Nenhuma store encontrada.")
    exit()

store_name = stores[0].name
print(f"Testando store: {store_name}")

files = []
for f in client.file_search_stores.documents.list(parent=store_name):
    # Simula a logica do app.py
    file_data = {
        "name": f.name,
        "display_name": getattr(f, 'display_name', None),
        "file_uri": f.name,
        "mime_type": getattr(f, 'mime_type', None),
        "size_bytes": getattr(f, 'size_bytes', None),
        "create_time": getattr(f, 'create_time', None).isoformat() if getattr(f, 'create_time', None) else None,
        "update_time": getattr(f, 'update_time', None).isoformat() if getattr(f, 'update_time', None) else None,
        "state": str(getattr(f, 'state', None))
    }
    files.append(file_data)

print(json.dumps(files, indent=2))
