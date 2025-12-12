import requests
import json
import os
import time

BASE_URL = "http://127.0.0.1:3001"

def test_integration():
    print("Starting Full Integration Test...")

    # 1. Get Agents List
    print("1. Listing agents...")
    try:
        res = requests.get(f"{BASE_URL}/api/agents")
        agents = res.json()
        fazenda_agent = next((a for a in agents if "fazenda" in a['name'].lower()), None)
        
        if not fazenda_agent:
            print("Agente Secretaria da Fazenda not found. Creating/Updating config...")
            # We can't create via API easily if it's not in the list, but it should be there.
            # Assuming 'secretaria_da_fazenda' exists as ID.
            agent_id = 'secretaria_da_fazenda'
        else:
            agent_id = fazenda_agent['id']
            print(f"Found agent: {agent_id}")

    except Exception as e:
        print(f"Failed to list agents: {e}")
        return

    # 2. Create Store
    print(f"2. Creating Store for {agent_id}...")
    store_name_display = "Secretaria da Fazenda - Teste TIA"
    store_resource_name = ""
    
    try:
        res = requests.post(f"{BASE_URL}/api/knowledge/stores", json={"display_name": store_name_display})
        if res.status_code != 200:
            print(f"Failed to create store: {res.text}")
            return
        store_data = res.json()
        store_resource_name = store_data['name']
        print(f"Store created: {store_resource_name}")
    except Exception as e:
        print(f"Error creating store: {e}")
        return

    # 3. Associate Store with Agent
    print("3. Associating Store with Agent...")
    try:
        # First get current config to not overwrite other fields
        # Note: The API /api/agent/<id> is a POST that updates fields.
        
        payload = {
            "file_search_stores": [store_resource_name]
        }
        
        res = requests.post(f"{BASE_URL}/api/agent/{agent_id}", json=payload)
        if res.status_code == 200:
            print("Association successful.")
        else:
            print(f"Failed to associate: {res.text}")
            return
    except Exception as e:
        print(f"Error associating: {e}")
        return

    # 4. Upload File
    print("4. Uploading Test File...")
    file_content = """
    O-eDOCS (Ambiente de Teste TIA)
    
    O O-eDOCS é o Sistema de Gestão de Documentos Digitais do Governo do Tocantins.
    Ele permite a criação, tramitação, assinatura e arquivamento de documentos oficiais de forma totalmente digital.
    Principais funcionalidades:
    - Assinatura digital com validade jurídica.
    - Tramitação entre secretarias.
    - Classificação arquivística automática.
    - Redução do uso de papel (Zero Paper).
    
    Este é um arquivo de teste gerado automaticamente para validar o sistema TIA.
    """
    
    filename = "oedocs_teste_tia.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(file_content)
        
    try:
        with open(filename, "rb") as f:
            files = {'file': (filename, f, 'text/plain')}
            data = {'store_name': store_resource_name}
            res = requests.post(f"{BASE_URL}/api/knowledge/upload", files=files, data=data)
            
        if res.status_code == 200:
            print("Upload successful.")
        else:
            print(f"Upload failed: {res.text}")
            return
    except Exception as e:
        print(f"Error uploading: {e}")
        return
    finally:
        if os.path.exists(filename):
            os.remove(filename)

    # Wait a bit for indexing
    print("Waiting 10s for indexing...")
    time.sleep(10)

    # 5. Query Chat
    print("5. Querying Chat...")
    try:
        # We target the specific agent to ensure it uses the store
        prompt = "O que é o O-eDOCS segundo o arquivo de teste?"
        payload = {
            "message": prompt,
            "target": agent_id
        }
        
        res = requests.post(f"{BASE_URL}/api/chat", data=payload)
        print(f"Status Code: {res.status_code}")
        try:
            response = res.json()
            print("\nResponse from TIA:")
            print(json.dumps(response, indent=2, ensure_ascii=False))
            
            reply = response.get('reply', '')
            if "Teste TIA" in reply:
                print("\nSUCCESS: RAG is working and retrieving from the correct store!")
            else:
                print("\nWARNING: Response might not be from the uploaded file. Check content.")
        except Exception as e:
            print(f"Failed to parse JSON: {res.text}")
            
    except Exception as e:
        print(f"Error querying chat: {e}")

if __name__ == "__main__":
    test_integration()
