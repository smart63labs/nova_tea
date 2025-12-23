from typing import Any, List, Optional
try:
    from typing import override
except ImportError:
    from typing_extensions import override

import os
import re

from google.adk.models.llm_request import LlmRequest
from google.adk.utils.model_name_utils import is_gemini_model
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.base_tool import ToolContext
from google.genai import types

class FileSearchTool(BaseTool):
    """
    Tool that enables Gemini API File Search (RAG) capabilities.
    Wraps the types.FileSearch configuration.
    """

    def __init__(
        self,
        file_search_store_names: List[str],
        *,
        top_k: Optional[int] = None,
        metadata_filter: Optional[str] = None,
        bypass_multi_tools_limit: bool = False
    ):
        """
        Args:
            file_search_store_names: List of resource names of the file search stores (e.g. ["projects/.../locations/.../ragCorpora/..."]).
            top_k: The number of file search retrieval chunks to retrieve.
            metadata_filter: Metadata filter to apply to the file search retrieval documents.
            bypass_multi_tools_limit: If True, allows this tool to be used with other tools even if the model has a limit.
        """
        super().__init__(name='file_search', description='Gemini API File Search Tool')
        self.file_search_store_names = file_search_store_names
        self.top_k = top_k
        self.metadata_filter = metadata_filter
        self.bypass_multi_tools_limit = bypass_multi_tools_limit
        self._project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._scraped_backup_dir = os.path.join(self._project_root, 'dados', 'scraped_backup')

    def _get_declaration(self) -> Optional[types.FunctionDeclaration]:
        return types.FunctionDeclaration(
            name='file_search',
            description='Busca na base de conhecimento local e retorna trechos relevantes com a fonte.',
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    'query': types.Schema(
                        type=types.Type.STRING,
                        description='Pergunta ou termos para buscar nos documentos.',
                    ),
                    'top_k': types.Schema(
                        type=types.Type.INTEGER,
                        description='Quantidade máxima de trechos para retornar.',
                    ),
                },
                required=['query'],
            ),
        )

    def _store_dirs(self) -> list[str]:
        dirs: list[str] = []
        for store_name in self.file_search_store_names or []:
            if not store_name:
                continue
            folder = str(store_name)
            if folder.startswith('fileSearchStores/'):
                folder = folder[len('fileSearchStores/') :]
            candidate = os.path.join(self._scraped_backup_dir, folder)
            if os.path.isdir(candidate):
                dirs.append(candidate)
        if dirs:
            return dirs
        if os.path.isdir(self._scraped_backup_dir):
            return [self._scraped_backup_dir]
        return []

    def _score_text(self, text: str, tokens: list[str]) -> int:
        if not text or not tokens:
            return 0
        t = text.lower()
        return sum(t.count(tok) for tok in tokens if tok)

    def _extract_snippet(self, text: str, tokens: list[str], max_chars: int = 900) -> str:
        if not text:
            return ""
        lower = text.lower()
        idx = -1
        for tok in tokens:
            if not tok:
                continue
            pos = lower.find(tok)
            if pos != -1 and (idx == -1 or pos < idx):
                idx = pos
        if idx == -1:
            return text[:max_chars].strip()
        start = max(0, idx - 250)
        end = min(len(text), idx + max_chars)
        return text[start:end].strip()

    async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
        query = (args.get('query') or '').strip()
        if not query:
            return {"results": []}
        top_k = args.get('top_k')
        try:
            top_k_int = int(top_k) if top_k is not None else None
        except Exception:
            top_k_int = None
        k = top_k_int if top_k_int and top_k_int > 0 else (self.top_k or 4)

        tokens = [t for t in re.split(r'\W+', query.lower()) if len(t) >= 3]
        results: list[dict[str, Any]] = []
        for base_dir in self._store_dirs():
            for root, _, files in os.walk(base_dir):
                for fn in files:
                    if not fn.lower().endswith(('.md', '.txt')):
                        continue
                    path = os.path.join(root, fn)
                    try:
                        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                            text = f.read()
                    except Exception:
                        continue
                    score = self._score_text(text, tokens)
                    if score <= 0:
                        continue
                    snippet = self._extract_snippet(text, tokens)
                    rel_path = os.path.relpath(path, self._project_root)
                    results.append(
                        {
                            "score": score,
                            "source": rel_path.replace('\\', '/'),
                            "snippet": snippet,
                        }
                    )

        results.sort(key=lambda r: r.get('score', 0), reverse=True)
        return {"results": results[:k]}

    @override
    async def process_llm_request(
        self,
        *,
        tool_context: ToolContext,
        llm_request: LlmRequest,
    ) -> None:
        llm_request.config = llm_request.config or types.GenerateContentConfig()
        llm_request.config.tools = llm_request.config.tools or []
        
        if is_gemini_model(llm_request.model):
            # Create the FileSearch configuration
            file_search_config = types.FileSearch(
                file_search_store_names=self.file_search_store_names,
                top_k=self.top_k,
                metadata_filter=self.metadata_filter
            )
            
            llm_request.config.tools.append(
                types.Tool(file_search=file_search_config)
            )
        else:
            await super().process_llm_request(tool_context=tool_context, llm_request=llm_request)
