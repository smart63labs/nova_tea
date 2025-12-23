import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional
import re

class ChromaManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChromaManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self._project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._db_path = os.path.join(self._project_root, 'dados', 'chroma_db')
        
        # Garante que a pasta existe
        os.makedirs(self._db_path, exist_ok=True)
        
        # Inicializa cliente persistente
        self.client = chromadb.PersistentClient(path=self._db_path)
        
        # Modelo de embedding multilingue para melhor suporte ao Português
        # Nota: O Chroma baixará este modelo no primeiro uso (aprox. 400MB)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
        
        self._initialized = True

    def get_collection(self, name: str):
        """Obtém ou cria uma coleção higienizada."""
        clean_name = name.replace('/', '_').replace('.', '_').replace('-', '_')
        return self.client.get_or_create_collection(
            name=clean_name,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"} # Similaridade de cosseno
        )

    def add_documents(self, collection_name: str, documents: List[str], metadatas: List[Dict], ids: List[str]):
        """Adiciona documentos à coleção em batches."""
        collection = self.get_collection(collection_name)
        # Chroma recomenda batches para grandes volumes
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            collection.add(
                documents=documents[i:i+batch_size],
                metadatas=metadatas[i:i+batch_size],
                ids=ids[i:i+batch_size]
            )

    def query(self, collection_name: str, query_text: str, n_results: int = 5):
        """Realiza busca semântica."""
        collection = self.get_collection(collection_name)
        return collection.query(
            query_texts=[query_text],
            n_results=n_results
        )

    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> list:
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

    def index_document(self, content: str, store_name: str, filename: str):
        """
        Divide um conteúdo em chunks e indexa no ChromaDB.
        
        Args:
            content: Conteúdo em texto/markdown
            store_name: Nome da coleção (fileSearchStores/...)
            filename: Nome original do arquivo
        """
        import logging
        
        collection_name = store_name.replace('fileSearchStores/', '').replace('/', '_').replace('-', '_').replace('.', '_')
        if not collection_name:
            collection_name = 'default_store'

        logging.info(f"Indexing to ChromaDB collection '{collection_name}': {filename}")

        # Divide em chunks
        chunks = self.chunk_text(content)
        if not chunks:
            logging.warning(f"No content to index for {filename}")
            return False

        documents = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            # ID único para o chunk
            doc_id = f"{collection_name}_{filename}_{i}"
            documents.append(chunk)
            metadatas.append({
                "source": filename,
                "store": store_name,
                "chunk_index": i
            })
            ids.append(doc_id)

        try:
            # Adiciona/Atualiza na coleção
            self.add_documents(
                collection_name=collection_name,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logging.info(f"✅ Document {filename} indexed in ChromaDB ({len(chunks)} chunks).")
            return True
        except Exception as e:
            logging.error(f"❌ Error indexing to ChromaDB: {e}")
            return False

# Instância global para reuso
chroma_manager = ChromaManager()
