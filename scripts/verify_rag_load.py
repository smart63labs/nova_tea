import os
import sys

# Adiciona o diretório raiz ao path (um nível acima de scripts/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)


# Simula o ambiente para carregar o agent.py
os.environ['GOOGLE_API_KEY'] = 'fake_key'

try:
    from assistente.local_rag_tool import LocalRagTool
    
    # Busca o agente original apenas para pegar os nomes dos stores
    from assistente.agent import sub_agents_map
    agent_info = sub_agents_map.get('secretaria_da_fazenda')
    stores = []
    if agent_info:
        # Extrai os nomes das ferramentas de busca (caso existam)
        stores = getattr(agent_info, 'file_search_store_names', [])
        # Caso o agente no mapa não tenha a info, pegamos fixo para teste
        if not stores:
            stores = ["fileSearchStores/secretaria-da-fazenda-406ahm359ier"]
    
    print(f"\n--- Iniciando Teste Direto do LocalRagTool (ChromaDB) ---")
    rag_tool = LocalRagTool(file_search_store_names=stores)
    print(f"Bases configuradas: {stores}")
    
    # Questão de teste semântico
    test_query = "qual o calendário de vencimento do imposto de veículos?"
    print(f"Pergunta semântica: '{test_query}'")
    
    import asyncio
    async def run_test():
        return await rag_tool.run_async(
            args={'query': test_query, 'limit': 3},
            tool_context=None
        )
    
    results = asyncio.run(run_test())
    
    if results.get('results'):
        print(f"\n✅ SUCESSO! Encontrados {len(results['results'])} resultados relevantes.")
        for i, r in enumerate(results['results']):
            print(f"\nResultado {i+1} [Score: {r['score']}]:")
            print(f"Fonte: {r['source']}")
            print(f"Trecho: {r['snippet'][:200]}...")
    else:
        print("\n❌ FALHA: Nenhum resultado encontrado. Verifique se a indexação foi bem sucedida.")

except Exception as e:
    print(f"Erro no teste: {e}")
    import traceback
    traceback.print_exc()
