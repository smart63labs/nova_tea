from typing import Any, Optional, List
from google.adk.tools.base_tool import BaseTool, ToolContext
from google.genai import types
from ddgs import DDGS

class DdgSearchTool(BaseTool):
    """
    Ferramenta de busca web via DuckDuckGo.
    Utilizada como alternativa ao GoogleSearchTool para modelos que não são Gemini.
    """

    def __init__(self, max_results: int = 5):
        super().__init__(
            name='ddg_search',
            description='Pesquisa na internet usando DuckDuckGo para encontrar informações atualizadas e externas.'
        )
        self.max_results = max_results

    def _get_declaration(self) -> Optional[types.FunctionDeclaration]:
        return types.FunctionDeclaration(
            name='ddg_search',
            description='Pesquisa na internet para obter informações em tempo real ou que não constam na base local.',
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    'query': types.Schema(
                        type=types.Type.STRING,
                        description='A pergunta ou termos de busca para pesquisar no DuckDuckGo.',
                    ),
                },
                required=['query'],
            ),
        )

    async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
        query = args.get('query', '').strip()
        if not query:
            return {"results": []}

        try:
            results = []
            with DDGS() as ddgs:
                ddgs_gen = ddgs.text(query, max_results=self.max_results)
                for r in ddgs_gen:
                    results.append({
                        "title": r.get('title'),
                        "link": r.get('href'),
                        "snippet": r.get('body')
                    })
            
            return {"query": query, "results": results}
        except Exception as e:
            return {"error": f"Erro ao realizar busca web: {str(e)}", "results": []}
