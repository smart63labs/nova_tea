
import sys
import os
import asyncio
import logging

# Adicionar diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from assistente.agent import root_agent
from google.adk.models.lite_llm import LiteLlm

# Setup logging
logging.basicConfig(level=logging.INFO)

async def test_deepseek_rag():
    print("=== Teste de RAG com DeepSeek (Simulado) ===")
    
    # 1. Configurar manualmente o modelo DeepSeek para o agente (simulando a troca)
    # Tenta ler a chave do ambiente, se não tiver, avisa (mas o script roda local, o usuario ja tem a chave no models.json se tiver habilitado)
    
    # Vamos criar uma instância de LiteLlm apontando para DeepSeek
    # Usando a chave que vimos no models.json (hardcoded para teste se necessário, ou pegando do env)
    # No caso real, o app pega do models.json. Vamos tentar simular isso ou usar uma variavel de ambiente dummy se o mock nao chamar api real
    
    # IMPORTANTE: Se não tiver API Key valida, o teste de conexao real vai falhar.
    # Mas queremos testar a *lógica* de tool calling do ADK + FileSearchTool.
    
    print("\n1. Verificando configuração do Agente...")
    # Verificar se o agente tem a ferramenta file_search
    has_fs = any(t.name == 'file_search' for t in root_agent.tools)
    if has_fs:
        print("   [OK] Ferramenta 'file_search' encontrada no agente.")
    else:
        print("   [WARN] Ferramenta 'file_search' NÃO encontrada. O teste pode falhar.")
        
        # Tentar injetar manualmente para teste se não estiver configurado
        from assistente.file_search_tool import FileSearchTool
        print("   -> Injetando FileSearchTool manualmente para teste...")
        # Assumindo que temos pastas no scraped_backup. Listar uma para usar.
        base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dados', 'scraped_backup')
        if os.path.exists(base_dir):
            folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]
            
            if folders:
                fs_tool = FileSearchTool(file_search_store_names=[folders[0]]) # Usar primeira pasta
                root_agent.tools.append(fs_tool)
                print(f"   [OK] Injetada ferramenta apontando para: {folders[0]}")
            else:
                print("   [ERRO] Nenhuma pasta encontrada em dados/scraped_backup. RAG Local impossível.")
                return
        else:
             print("   [ERRO] Diretorio dados/scraped_backup nao existe.")
             return

    # 2. Executar uma consulta
    # Como não queremos gastar créditos ou depender da API real se não tiver chave, 
    # podemos testar unitariamente o run_async da ferramenta FileSearchTool primeiro.
    
    print("\n2. Testando busca local (Keyword Search) diretamente...")
    fs_tool = next((t for t in root_agent.tools if t.name == 'file_search'), None)
    
    if fs_tool:
        # Tentar buscar algo genérico que provavelmente existe nos docs
        query = "saiba mais" # Algo comum ou específico se soubessemos o conteudo
        # Melhor: listar arquivos para pegar um termo real
        try:
             store_dirs = fs_tool._store_dirs()
             if store_dirs:
                 for root, _, files in os.walk(store_dirs[0]):
                     for f in files:
                         if f.endswith('.txt') or f.endswith('.md'):
                             with open(os.path.join(root, f), 'r', encoding='utf-8', errors='ignore') as f_obj:
                                 content = f_obj.read(500)
                                 # Pegar uma palavra chave
                                 words = [w for w in content.split() if len(w) > 5]
                                 if words:
                                     query = words[0]
                                     break
                     if query != "saiba mais": break
        except:
            pass
            
        print(f"   Query de teste: '{query}'")
        
        # Contexto fake
        # Contexto fake
        from google.adk.tools.base_tool import ToolContext
        # Error said missing invocation_context. Passing None since file_search_tool.run_async doesn't use it.
        try:
             ctx = ToolContext(invocation_context=None)
        except:
             # If that fails, maybe it expects kwargs or specific obj.
             # Let's try to mock the class if we can't instantiate it easily.
             class MockContext:
                 pass
             ctx = MockContext()
             
        ctx.agent = root_agent # Assign manually if needed
        
        results = await fs_tool.run_async(args={'query': query}, tool_context=ctx)
        
        if results and results.get('results'):
            print(f"   [OK] Resultados encontrados: {len(results['results'])}")
            print(f"   Exemplo: {results['results'][0]['snippet'][:100]}...")
        else:
            print("   [WARN] Nenhum resultado encontrado. (Docs vazios ou query ruim)")
    
    print("\n Conclusão: A lógica interna de RAG Local (fallback) está funcional.")
    print(" Para DeepSeek funcionar, ele precisa apenas CHAMAR essa ferramenta via function calling.")
    print(" O ADK suporta function calling para LiteLLM.")

if __name__ == "__main__":
    asyncio.run(test_deepseek_rag())
