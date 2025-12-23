
import aiohttp
import json
import logging
from typing import AsyncGenerator, Optional
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from pydantic import Field

logger = logging.getLogger(__name__)

class LocalLLM(BaseLlm):
    endpoint: str = Field(..., description="The endpoint URL for the local model")
    model_hash: Optional[str] = Field(None, description="The actual model identifier for the local server (e.g., ai/gemma3:latest)")
    
    def _content_text(self, content) -> str:
        if not content:
            return ""
        if isinstance(content, str):
            return content
        parts = getattr(content, "parts", None)
        if parts:
            texts = []
            for p in parts:
                t = getattr(p, "text", None)
                if t:
                    texts.append(t)
            return "\n".join(texts).strip()
        t = getattr(content, "text", None)
        if t:
            return str(t).strip()
        return str(content).strip()

    def _schema_to_dict(self, schema):
        if not schema:
            return {}
        d = {}
        if hasattr(schema, 'type'):
             t = schema.type
             if hasattr(t, 'name'):
                 d['type'] = t.name.lower()
             elif isinstance(t, str):
                 d['type'] = t
             else:
                 d['type'] = str(t).lower()
                 
        if hasattr(schema, 'description') and schema.description:
            d['description'] = schema.description
        if hasattr(schema, 'format') and schema.format:
            d['format'] = schema.format
        if hasattr(schema, 'enum') and schema.enum:
            d['enum'] = schema.enum
        if hasattr(schema, 'properties') and schema.properties:
            d['properties'] = {k: self._schema_to_dict(v) for k, v in schema.properties.items()}
        if hasattr(schema, 'required') and schema.required:
            d['required'] = schema.required
        if hasattr(schema, 'items') and schema.items:
            d['items'] = self._schema_to_dict(schema.items)
        return d

    def _convert_tools(self, tools):
        openai_tools = []
        for t in tools:
            if hasattr(t, 'function_declarations') and t.function_declarations:
                for fd in t.function_declarations:
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": fd.name,
                            "description": fd.description,
                            "parameters": self._schema_to_dict(fd.parameters)
                        }
                    })
        return openai_tools

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        
        messages = []
        pending_tool_call_ids = {}
        call_seq = 0
        # Add system instruction if present in config
        if llm_request.config and llm_request.config.system_instruction:
             sys_inst = llm_request.config.system_instruction
             if isinstance(sys_inst, list):
                 for c in sys_inst:
                     txt = self._content_text(c)
                     if txt:
                         messages.append({"role": "system", "content": txt})
             elif hasattr(sys_inst, 'parts') and sys_inst.parts:
                 txt = self._content_text(sys_inst)
                 if txt:
                     messages.append({"role": "system", "content": txt})
             else:
                 txt = self._content_text(sys_inst)
                 if txt:
                     messages.append({"role": "system", "content": txt})

        # Add contents
        for content in llm_request.contents:
            role = content.role
            if role == 'model':
                role = 'assistant'
            
            if not content.parts:
                continue

            text_parts = []
            tool_calls = []
            tool_responses = []

            for part in content.parts:
                if part.text:
                    text_parts.append(part.text)
                elif part.function_call:
                    tool_calls.append(part.function_call)
                elif part.function_response:
                    tool_responses.append(part.function_response)

            # Handle Assistant/Model Messages
            if role == 'assistant':
                msg = {"role": "assistant"}
                if text_parts:
                    msg["content"] = "\n".join(text_parts)
                
                if tool_calls:
                    tcs = []
                    for fc in tool_calls:
                         call_id = f"call_{call_seq}"
                         call_seq += 1
                         pending_tool_call_ids.setdefault(fc.name, []).append(call_id)
                         tcs.append({
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": fc.name,
                                "arguments": json.dumps(fc.args)
                            }
                        })
                    msg["tool_calls"] = tcs
                
                if msg.get("content") or msg.get("tool_calls"):
                    messages.append(msg)

            # Handle User Messages (Text and/or Tool Responses)
            elif role == 'user':
                # User text
                if text_parts:
                    messages.append({"role": "user", "content": "\n".join(text_parts)})
                
                # Tool responses (must be separate 'tool' role messages)
                if tool_responses:
                    for fr in tool_responses:
                        name = fr.name
                        pending = pending_tool_call_ids.get(name) or []
                        tool_call_id = pending.pop(0) if pending else f"call_{name}"
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "name": name,
                            "content": json.dumps(fr.response)
                        })
        
        # Determine endpoint URL
        url = self.endpoint
        # Heuristic to construct chat completion URL if base is provided
        if not url.endswith('chat/completions'):
             if url.endswith('/v1'):
                 url = url.rstrip('/') + '/chat/completions'
             elif url.endswith('/'):
                 url += 'chat/completions' # Assume base root maps to OpenAI style
             elif 'engines/v1' in url:
                 url += '/chat/completions'
             else:
                 # If user gave "http://localhost:12434", assume it needs /v1/chat/completions or similar
                 # But sticking to what was likely provided as "base url"
                 url += '/chat/completions'

        # Use model_hash if available, otherwise fall back to model ID
        model_identifier = self.model_hash if self.model_hash else self.model
        
        payload = {
            "model": model_identifier,
            "messages": messages,
            "stream": stream
        }
        
        # Map some config parameters
        if llm_request.config:
            if llm_request.config.temperature is not None:
                payload['temperature'] = llm_request.config.temperature
            if llm_request.config.max_output_tokens is not None:
                payload['max_tokens'] = llm_request.config.max_output_tokens
            
            # Convert Tools
            if llm_request.config.tools:
                openai_tools = self._convert_tools(llm_request.config.tools)
                if openai_tools:
                    payload['tools'] = openai_tools
                    payload['tool_choice'] = "auto"

        logger.info(f"LocalLLM Request: URL={url}, Model={model_identifier}, Stream={stream}, Tools={len(payload.get('tools', []))}, SystemMessages={sum(1 for m in messages if m.get('role') == 'system')}, TotalMessages={len(messages)}")
        # logger.debug(f"Payload: {json.dumps(payload)}")

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        err_text = await resp.text()
                        logger.error(f"LocalLLM Error: HTTP {resp.status} - {err_text}")
                        yield LlmResponse(error_message=f"HTTP {resp.status}: {err_text}")
                        return

                    if stream:
                        current_tool_calls = {} # index -> {name, args}

                        async for line in resp.content:
                            line = line.strip()
                            if not line or line == b'data: [DONE]':
                                continue
                            if line.startswith(b'data: '):
                                line = line[6:]
                            
                            try:
                                chunk = json.loads(line)
                                if 'choices' in chunk and len(chunk['choices']) > 0:
                                    delta = chunk['choices'][0].get('delta', {})
                                    
                                    # Content
                                    content = delta.get('content', '')
                                    if content:
                                        yield LlmResponse(
                                            content=types.Content(
                                                role='model',
                                                parts=[types.Part(text=content)]
                                            ),
                                            partial=True
                                        )
                                    
                                    # Tool Calls
                                    tcs = delta.get('tool_calls')
                                    if tcs:
                                        for tc in tcs:
                                            idx = tc.get('index', 0)
                                            if idx not in current_tool_calls:
                                                current_tool_calls[idx] = {'name': '', 'arguments': ''}
                                            
                                            fn = tc.get('function', {})
                                            if fn.get('name'):
                                                current_tool_calls[idx]['name'] += fn['name']
                                            if fn.get('arguments'):
                                                current_tool_calls[idx]['arguments'] += fn['arguments']
                            except:
                                pass
                        
                        # Yield accumulated tool calls
                        if current_tool_calls:
                            parts = []
                            for idx in sorted(current_tool_calls.keys()):
                                tc = current_tool_calls[idx]
                                try:
                                    args = json.loads(tc['arguments'])
                                except:
                                    args = {} # Parsing failed, maybe empty
                                parts.append(types.Part(function_call=types.FunctionCall(name=tc['name'], args=args)))
                            
                            yield LlmResponse(content=types.Content(role='model', parts=parts), partial=False, turn_complete=True)
                        else:
                            # Final response to mark completion
                            yield LlmResponse(partial=False, turn_complete=True)
                        
                    else:
                        data = await resp.json()
                        if 'choices' in data and len(data['choices']) > 0:
                            message = data['choices'][0]['message']
                            content = message.get('content')
                            tool_calls = message.get('tool_calls')
                            
                            parts = []
                            if content:
                                parts.append(types.Part(text=content))
                            
                            if tool_calls:
                                for tc in tool_calls:
                                    fn = tc.get('function', {})
                                    name = fn.get('name')
                                    args_str = fn.get('arguments', '{}')
                                    try:
                                        args = json.loads(args_str)
                                    except:
                                        args = {}
                                    parts.append(types.Part(function_call=types.FunctionCall(name=name, args=args)))
                            
                            yield LlmResponse(
                                content=types.Content(
                                    role='model',
                                    parts=parts
                                ),
                                partial=False,
                                turn_complete=True
                            )
            except Exception as e:
                yield LlmResponse(error_message=str(e))
