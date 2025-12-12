
import os
import sys
import json
import logging

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

CONFIG_PATH = os.path.join(BASE_DIR, 'dados', 'config.json')

# Load Key
if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            c = json.load(f)
            if c.get('api_key'):
                os.environ['GOOGLE_API_KEY'] = c.get('api_key')
    except:
        pass

from google.genai import Client

def get_genai_client():
    api_key = os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        print("API Key not found in env or config")
        return None
    return Client(api_key=api_key)

def test_delete(name):
    print(f"Attempting to delete store: {name}")
    client = get_genai_client()
    try:
        # Try force=True first
        try:
            print("Trying delete with force=True...")
            client.file_search_stores.delete(name=name, force=True)
            print("✅ Success with force=True")
            return
        except TypeError:
            print("force=True not supported.")
        except Exception as e:
            print(f"force=True failed: {e}")

        client.file_search_stores.delete(name=name)
        print("✅ Success")
    except Exception as e:
        print(f"❌ Error caught: {type(e).__name__}: {e}")
        if "non-empty" in str(e):
             print("Store is non-empty. Listing files:")
             try:
                for doc in client.file_search_stores.documents.list(parent=name):
                    print(f" - Document Name: {doc.name}")
                    print(f" - Document Display Name: {doc.display_name}")
                    # print(f" - Document Fields: {dir(doc)}")
                    print(f" - Document Dict: {doc.to_json_dict()}")
                    
                    # Check for file_id in dict
                    # It might be in custom_metadata or just implicit
                    
                    doc_id_part = doc.name.split('/')[-1]
                    potential_file_id = f"files/{doc_id_part}"
                    print(f" - Potential File ID: {potential_file_id}")
                    
                    try:
                        print(f"   -> Attempting client.files.delete({potential_file_id})...")
                        client.files.delete(name=potential_file_id)
                        print("   ✅ File deleted.")
                    except Exception as fe:
                        print(f"   ❌ Failed to delete file: {fe}")
                        
                    # Try deleting document again just in case
                    try:
                         print(f"   -> Attempting client.file_search_stores.documents.delete({doc.name})...")
                         client.file_search_stores.documents.delete(name=doc.name)
                         print("   ✅ Document deleted.")
                    except Exception as de:
                         print(f"   ❌ Failed to delete document via SDK: {de}")
                         # Try raw REST API delete with force=true
                         try:
                             print(f"   -> Attempting raw REST DELETE for document with force=true...")
                             doc_url = f"https://generativelanguage.googleapis.com/v1beta/{doc.name}?force=true&key={os.environ.get('GOOGLE_API_KEY')}"
                             res = requests.delete(doc_url)
                             print(f"   RAW DELETE Status: {res.status_code}")
                             print(f"   RAW DELETE Response: {res.text}")
                         except Exception as re:
                             print(f"   ❌ Failed raw delete: {re}")

                    # Check Agents - SKIPPING as client has no agents attribute
                
                print("Listing ALL files to find match...")
                try:
                    for f in client.files.list():
                        print(f" - File: {f.name} ({f.display_name})")
                        if "oedocstestetiatxt-lpsgj2wg5eih" in f.name:
                            print(f"   MATCH FOUND: {f.name}")
                            try:
                                client.files.delete(name=f.name)
                                print("   ✅ Deleted found file.")
                            except Exception as e:
                                print(f"   ❌ Failed to delete found file: {e}")
                except Exception as e:
                    print(f"Error listing files: {e}")

                print("Retrying store delete...")
                client.file_search_stores.delete(name=name)
                print("✅ Store deleted successfully after cleanup")
             except Exception as le:
                 print(f"Error during cleanup: {le}")

import requests

def list_agents_raw():
    api_key = os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        print("No API Key")
        return

    base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    # Try listing agents
     # url = f"{base_url}/agents?key={api_key}"
     # print(f"GET {url.replace(api_key, 'KEY')}")
     # res = requests.get(url)
     # print(f"Status: {res.status_code}")
     
    # Try forcing document delete via REST
    pass

if __name__ == "__main__":
    # list_agents_raw()
    # Use the ID from the user's error
    # fileSearchStores/secretaria-da-fazenda-teste-ui6jmj2of2ji
    test_delete("fileSearchStores/secretaria-da-fazenda-teste-ui6jmj2of2ji")
