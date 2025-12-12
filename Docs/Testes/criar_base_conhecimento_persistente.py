import os
import glob
import time
from google import genai
from dotenv import load_dotenv

# Configuração
PASTA_DOCUMENTOS = 'base_conhecimento_arquivos'
NOME_STORE_PADRAO = 'Base de Conhecimento Oficial'

def criar_base_persistente():
    # 1. Carrega Credenciais
    load_dotenv('tea/.env')
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("❌ ERRO: GOOGLE_API_KEY não encontrada no arquivo tea/.env")
        return

    client = genai.Client(api_key=api_key)
    print("✅ Cliente Gemini inicializado.")

    # 2. Verifica Arquivos
    arquivos_validos = []
    extensoes = ['*.pdf', '*.txt', '*.docx', '*.md', '*.html']
    
    if not os.path.exists(PASTA_DOCUMENTOS):
        os.makedirs(PASTA_DOCUMENTOS)
        print(f"⚠️ Pasta '{PASTA_DOCUMENTOS}' criada. Coloque seus arquivos nela e rode o script novamente.")
        return

    for ext in extensoes:
        arquivos_validos.extend(glob.glob(os.path.join(PASTA_DOCUMENTOS, ext)))
    
    if not arquivos_validos:
        print(f"⚠️ Nenhum arquivo encontrado na pasta '{PASTA_DOCUMENTOS}'.")
        print("   Por favor, coloque arquivos PDF, TXT, DOCX ou MD lá e tente novamente.")
        return

    print(f"📄 Encontrados {len(arquivos_validos)} arquivos para processar.")

    # 3. Cria a Vector Store (Persistente)
    nome_store = input(f"Digite um nome para a nova base (Enter para '{NOME_STORE_PADRAO}'): ").strip()
    if not nome_store:
        nome_store = NOME_STORE_PADRAO

    print(f"\n🚀 Criando Vector Store: '{nome_store}'...")
    try:
        store = client.file_search_stores.create(name=nome_store)
        print(f"✅ Vector Store criada com sucesso!")
        print(f"   ID: {store.name}")
    except Exception as e:
        print(f"❌ Erro ao criar Store: {e}")
        return

    # 4. Upload e Associação de Arquivos
    print("\n📤 Iniciando upload dos arquivos...")
    arquivos_enviados = []
    
    for path in arquivos_validos:
        try:
            print(f"   ➡ Enviando: {os.path.basename(path)}...", end="\r")
            # Upload do arquivo
            file = client.files.upload(path=path)
            arquivos_enviados.append(file)
            print(f"   ✅ Enviado: {os.path.basename(path)} (ID: {file.name})")
        except Exception as e:
            print(f"   ❌ Falha em {os.path.basename(path)}: {e}")

    if not arquivos_enviados:
        print("❌ Nenhum arquivo foi enviado com sucesso.")
        return

    # 5. Adiciona arquivos à Store
    print(f"\n🔗 Adicionando {len(arquivos_enviados)} arquivos à Vector Store...")
    
    sucessos = 0
    for file in arquivos_enviados:
        try:
            # Associa o arquivo à store
            client.file_search_stores.files.create(
                file_search_store_id=store.name.split('/')[-1],
                file_search_file={'resource_name': file.name}
            )
            sucessos += 1
            print(f"   ✅ Indexado: {file.display_name}")
        except Exception as e:
            print(f"   ❌ Erro ao indexar {file.display_name}: {e}")

    # 6. Relatório Final
    print("\n" + "="*50)
    print("🎉 PROCESSO CONCLUÍDO COM SUCESSO!")
    print("="*50)
    print(f"Nome da Base: {nome_store}")
    print(f"ID DA STORE:  {store.name}")
    print(f"Arquivos:     {sucessos}/{len(arquivos_validos)} indexados")
    print("="*50)
    print("\n⚠️ IMPORTANTE: COPIE O ID ACIMA E ATUALIZE SEU ARQUIVO JSON DO AGENTE.")
    print(f'Exemplo em dados/agentes/seu_agente.json:')
    print(f'"file_search_stores": ["{store.name}"]')
    print("="*50)

if __name__ == "__main__":
    criar_base_persistente()
