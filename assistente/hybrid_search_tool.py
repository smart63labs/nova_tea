import os
from typing import Any, List, Optional
from google.adk.tools.base_tool import BaseTool, ToolContext
from google.genai import types
from assistente.chroma_manager import chroma_manager
from ddgs import DDGS

class HybridSearchTool(BaseTool):
    """
    Ferramenta Híbrida que combina RAG Local e Busca Web com Fallback.
    """

    def __init__(
        self,
        file_search_store_names: List[str] = None,
        enable_web: bool = True,
        rag_threshold: float = 0.4,
        top_k_rag: int = 5,
        top_k_web: int = 5,
        allowed_domains: List[str] = None
    ):
        super().__init__(
            name='hybrid_search',
            description='Pesquisa informações na base de conhecimento local e, se necessário, complementa com busca na internet restrita a sites oficiais.'
        )
        self.file_search_store_names = file_search_store_names or []
        self.enable_web = enable_web
        self.rag_threshold = rag_threshold
        self.top_k_rag = top_k_rag
        self.top_k_web = top_k_web
        self.allowed_domains = allowed_domains or ["to.gov.br", "al.to.leg.br"]

    def _get_declaration(self) -> Optional[types.FunctionDeclaration]:
        return types.FunctionDeclaration(
            name='hybrid_search',
            description='Busca informações detalhadas nos documentos locais do Governo do Tocantins. Se a informação não for encontrada localmente, realiza uma busca na internet.',
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    'query': types.Schema(
                        type=types.Type.STRING,
                        description='A pergunta ou termos para pesquisar.',
                    ),
                    'force_web': types.Schema(
                        type=types.Type.BOOLEAN,
                        description='Se verdadeiro, ignora a busca local e vai direto para a internet.',
                    ),
                },
                required=['query'],
            ),
        )

    async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
        query = args.get('query', '').strip()
        force_web = args.get('force_web', False)
        if not query:
            return {"results": []}

        rag_results = []
        is_rag_sufficient = False
        
        # 1. Tentar RAG (apenas se não for forçado web)
        if not force_web:
            stores = self.file_search_store_names if self.file_search_store_names else ['default_store']
            for store_name in stores:
                collection_name = store_name.replace('fileSearchStores/', '').replace('/', '_').replace('-', '_').replace('.', '_')
                try:
                    query_results = chroma_manager.query(
                        collection_name=collection_name,
                        query_text=query,
                        n_results=self.top_k_rag
                    )
                    if query_results and query_results['documents']:
                        docs = query_results['documents'][0]
                        metas = query_results['metadatas'][0]
                        dists = query_results['distances'][0] if 'distances' in query_results else [0] * len(docs)
                        
                        for i in range(len(docs)):
                            score = 1.0 - dists[i]
                            # Heurística: se o snippet for muito curto, o score efetivo é penalizado
                            if len(docs[i]) < 100:
                                score *= 0.5
                                
                            rag_results.append({
                                "type": "rag",
                                "score": round(float(score), 3),
                                "source": metas[i].get('source', 'local'),
                                "content": docs[i]
                            })
                except Exception as e:
                    print(f"Erro RAG: {e}")

        rag_results.sort(key=lambda x: x['score'], reverse=True)
        top_rag = [r for r in rag_results if r['score'] > 0.1][:self.top_k_rag]
        
        # Avalia se o RAG é suficiente: tem que ter pelo menos um resultado com score bom e conteúdo longo
        if top_rag:
            best_rag = top_rag[0]
            if best_rag['score'] >= self.rag_threshold and len(best_rag['content']) > 250:
                is_rag_sufficient = True
        
        # 2. Verificar se precisa de Web Fallback
        if force_web or (self.enable_web and not is_rag_sufficient):
            try:
                web_results = []
                with DDGS() as ddgs:
                    # Se for fallback, tenta ser mais específico
                    search_query = query
                    if top_rag and not force_web:
                         search_query = f"{query} passo a passo"
                    
                    # Adiciona restrição de domínio
                    if self.allowed_domains:
                        domain_filter = " OR ".join([f"site:{d}" for d in self.allowed_domains])
                        search_query = f"({search_query}) ({domain_filter})"
                        
                    ddgs_gen = ddgs.text(search_query, max_results=self.top_k_web)
                    for r in ddgs_gen:
                        web_results.append({
                            "type": "web",
                            "title": r.get('title'),
                            "link": r.get('href'),
                            "content": r.get('body')
                        })
                
                print(f"[DEBUG] Fonte de Dados: Web Search ({'Forçado' if force_web else 'Fallback - RAG Insuficiente'})")
                print(f"[DEBUG] Query Web: {search_query}")
                return {
                    "query": query,
                    "source_used": "web" if force_web else "web_fallback",
                    "reason": "RAG results insufficient or forceful web search" if not is_rag_sufficient else "Forceful web",
                    "web_results": web_results,
                    "partial_rag_results": top_rag if not force_web else []
                }
            except Exception as e:
                print(f"Erro Web Fallback: {e}")

        if is_rag_sufficient:
            print(f"[DEBUG] Fonte de Dados: RAG Local (Score: {top_rag[0]['score']:.2f})")
        else:
            print(f"[DEBUG] Fonte de Dados: RAG Local (Web desabilitada ou falha)")

        return {
            "query": query,
            "source_used": "rag",
            "results": top_rag
        }
