import asyncio
from tea.ddg_search_tool import DdgSearchTool

async def test_search():
    tool = DdgSearchTool(max_results=3)
    print("Testando busca: 'Previsão do tempo Palmas Tocantins'")
    
    # Simula a estrutura de argumentos que o ADK passa
    args = {'query': 'Previsão do tempo Palmas Tocantins'}
    
    # O ToolContext não é estritamente necessário para esse teste simples
    result = await tool.run_async(args=args, tool_context=None)
    
    print("\nResultados:")
    if "results" in result:
        for r in result["results"]:
            print(f"- {r['title']}: {r['link']}")
            print(f"  Snippet: {r['snippet'][:100]}...")
    else:
        print(f"Erro: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(test_search())
