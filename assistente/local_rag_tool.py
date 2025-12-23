import os
import re
from typing import Any, List, Optional
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.base_tool import ToolContext
from google.genai import types
from assistente.chroma_manager import chroma_manager

class LocalRagTool(BaseTool):
    """
    Ferramenta de RAG Local baseada em ChromaDB (Busca Vetorial).
    Suporta busca semântica multilingue em documentos locais.
    """

    def __init__(
        self,
        file_search_store_names: List[str] = None,
        top_k: int = 5
    ):
        super().__init__(
            name='local_rag',
            description='Busca semântica na base de conhecimento local e retorna trechos relevantes.'
        )
        self.file_search_store_names = file_search_store_names or []
        self.top_k = top_k

    def _get_declaration(self) -> Optional[types.FunctionDeclaration]:
        return types.FunctionDeclaration(
            name='local_rag',
            description='Busca informações detalhadas nos documentos locais do Governo do Tocantins usando inteligência semântica.',
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    'query': types.Schema(
                        type=types.Type.STRING,
                        description='O termo ou pergunta para pesquisar na base de conhecimento.',
                    ),
                    'limit': types.Schema(
                        type=types.Type.INTEGER,
                        description='Número máximo de resultados a retornar.',
                    ),
                },
                required=['query'],
            ),
        )

    async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
        query = args.get('query', '').strip()
        if not query:
            return {"results": []}
            
        limit = args.get('limit', self.top_k)
        results = []
        
        # Se não houver stores específicos, tenta a padrão
        stores = self.file_search_store_names if self.file_search_store_names else ['default_store']
        
        for store_name in stores:
            # Higieniza o nome da coleção para bater com o que foi indexado
            collection_name = store_name.replace('fileSearchStores/', '').replace('/', '_').replace('-', '_').replace('.', '_')
            
            try:
                # Realiza a busca vetorial via ChromaManager
                query_results = chroma_manager.query(
                    collection_name=collection_name,
                    query_text=query,
                    n_results=limit
                )
                
                if not query_results or not query_results['documents']:
                    continue
                
                # O Chroma retorna listas de listas (uma para cada query_text)
                documents = query_results['documents'][0]
                metadatas = query_results['metadatas'][0]
                distances = query_results['distances'][0] if 'distances' in query_results else [0] * len(documents)
                
                for i in range(len(documents)):
                    # Converte distância em score (aproximado)
                    # No cosseno, menor distância = maior similaridade
                    score = 1.0 - distances[i]
                    
                    results.append({
                        "score": round(float(score), 3),
                        "source": metadatas[i].get('source', 'desconhecido'),
                        "snippet": documents[i]
                    })
            except Exception as e:
                print(f"Erro ao buscar na coleção {collection_name}: {e}")
                continue
        
        # Ordena todos os resultados cruzados por score
        results.sort(key=lambda x: x['score'], reverse=True)
        return {"results": results[:limit]}
