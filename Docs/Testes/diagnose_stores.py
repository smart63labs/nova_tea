from google import genai
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv('tea/.env')
api_key = os.getenv('GOOGLE_API_KEY')

if not api_key:
    print("Erro: GOOGLE_API_KEY não encontrada no arquivo .env")
    exit(1)

client = genai.Client(api_key=api_key)

print("--- Stores de Busca Persistentes (Vector Stores) ---")
try:
    stores = list(client.file_search_stores.list())
    if stores:
        for store in stores:
            print(f"Nome da Store: {store.name} | Criada em: {store.create_time}")
            # Lista arquivos dentro da store
            try:
                files = list(client.file_search_stores.files.list(file_search_store_id=store.name.split('/')[-1]))
                print(f"  - Arquivos na store ({len(files)}):")
                for f in files:
                    print(f"    - {f.name}")
            except Exception as e:
                print(f"  - Erro ao listar arquivos da store: {e}")
    else:
        print("Nenhuma Vector Store encontrada. Você deve ter usado apenas arquivos temporários.")
except Exception as e:
    print(f"Erro ao listar stores: {e}")

print("\n--- Arquivos Temporários Ativos (expiram em 48h) ---")
try:
    temp_files = list(client.files.list())
    if temp_files:
        for file in temp_files:
            print(f"Nome do Arquivo: {file.name} | Nome Original: {file.display_name} | Criado em: {file.create_time}")
    else:
        print("Nenhum arquivo temporário encontrado. Todos expiraram ou foram deletados.")
except Exception as e:
    print(f"Erro ao listar arquivos: {e}")
