from typing import List, Optional
try:
    from typing import override
except ImportError:
    from typing_extensions import override

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
