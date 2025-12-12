
import os
import json
from google.genai import Client
from dotenv import load_dotenv

load_dotenv('tea/.env')
api_key = os.getenv('GOOGLE_API_KEY')
client = Client(api_key=api_key)

store_name = 'fileSearchStores/secretaria-da-fazenda-uthp30k9uf3n'

print(f"Inspecting files in {store_name}...")

try:
    for doc in client.file_search_stores.documents.list(parent=store_name):
        print(f"\n--- Document: {doc.name} ---")
        print("Attributes:")
        for attr in dir(doc):
            if not attr.startswith('_'):
                try:
                    val = getattr(doc, attr)
                    if not callable(val):
                        print(f"  {attr}: {val}")
                except Exception as e:
                    print(f"  {attr}: <error reading: {e}>")
        
        # Tentar pegar detalhes adicionais usando a API de files se possível
        # O doc.name geralmente é algo como 'corpora/ID/documents/ID' ou similar na nova API?
        # Na verdade, o SDK v2 (google-genai) é um pouco diferente.
        # Vamos ver o que tem no 'doc'.
        
except Exception as e:
    print(f"Error: {e}")
