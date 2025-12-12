import os
import json

AGENTS_DIR = r'c:\Users\88417646191\Documents\ADK\dados\agentes'
TARGET_STORE = "fileSearchStores/secretaria-da-fazenda-uthp30k9uf3n"
ALLOWED_AGENT = "secretaria_da_fazenda.json"

count = 0
for fname in os.listdir(AGENTS_DIR):
    if fname.endswith('.json') and fname != '_template.json' and fname != 'orquestrador.json':
        if fname == ALLOWED_AGENT:
            continue
            
        fpath = os.path.join(AGENTS_DIR, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            stores = data.get('file_search_stores', [])
            if TARGET_STORE in stores:
                print(f"Cleaning {fname}...")
                stores.remove(TARGET_STORE)
                data['file_search_stores'] = stores
                
                with open(fpath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                count += 1
        except Exception as e:
            print(f"Error processing {fname}: {e}")

print(f"Cleaned {count} agents.")
