
import os
import sys
import json

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

CONFIG_PATH = os.path.join(PROJECT_ROOT, 'dados', 'config.json')

# Load API Key
if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            c = json.load(f)
            if c.get('api_key'):
                os.environ['GOOGLE_API_KEY'] = c.get('api_key')
    except:
        pass

from google.genai import Client

def inspect_client():
    api_key = os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        print("No API Key found")
        return

    client = Client(api_key=api_key, http_options={'api_version': 'v1beta'})
    
    print("Inspecting client.file_search_stores...")
    if hasattr(client, 'file_search_stores'):
        fss = client.file_search_stores
        print(f"Attributes of file_search_stores: {dir(fss)}")
        
        if hasattr(fss, 'documents'):
            docs = fss.documents
            print(f"Attributes of file_search_stores.documents: {dir(docs)}")
        else:
            print("file_search_stores has no 'documents' attribute")
            
    else:
        print("client has no 'file_search_stores' attribute")

if __name__ == "__main__":
    inspect_client()
