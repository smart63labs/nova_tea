import os
import sys
import re

# Adiciona o diretório raiz ao path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from assistente.chroma_manager import chroma_manager

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list:
    """Divide o texto em pedaços menores com sobreposição."""
    if not text:
        return []
        
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

def index_all():
    backup_dir = os.path.join(PROJECT_ROOT, 'dados', 'scraped_backup')
    if not os.path.exists(backup_dir):
        print(f"Diretório de backup não encontrado: {backup_dir}")
        return

    print("Iniciando indexação vetorial...")
    
    indexed_count = 0
    for root, _, files in os.walk(backup_dir):
        # Extrai o nome da store baseada na pasta
        rel_path = os.path.relpath(root, backup_dir)
        if rel_path == '.':
            collection_name = 'default_store'
        else:
            collection_name = rel_path.replace(os.sep, '_')

        for fn in files:
            if not fn.lower().endswith(('.md', '.txt')):
                continue
                
            file_path = os.path.join(root, fn)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception as e:
                print(f"Erro ao ler {file_path}: {e}")
                continue

            # Divide em chunks para melhor busca semântica
            chunks = chunk_text(content)
            if not chunks:
                continue

            documents = []
            metadatas = []
            ids = []
            
            for i, chunk in enumerate(chunks):
                doc_id = f"{collection_name}_{fn}_{i}"
                documents.append(chunk)
                metadatas.append({
                    "source": os.path.relpath(file_path, PROJECT_ROOT).replace(os.sep, '/'),
                    "filename": fn,
                    "store": collection_name
                })
                ids.append(doc_id)

            # Adiciona à coleção
            chroma_manager.add_documents(
                collection_name=collection_name,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            indexed_count += 1
            if indexed_count % 10 == 0:
                print(f"Documentos processados: {indexed_count}...")

    print(f"\nIndexação concluída! Total de documentos: {indexed_count}")

if __name__ == "__main__":
    index_all()
