import os
import sys
import json
import importlib
import asyncio

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = BASE_DIR # Assuming we run from root
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

CONFIG_PATH = os.path.join(PROJECT_ROOT, 'dados', 'config.json')
AGENTS_DIR = os.path.join(PROJECT_ROOT, 'dados', 'agentes')

# Load API Key
if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            c = json.load(f)
            if c.get('api_key'):
                os.environ['GOOGLE_API_KEY'] = c.get('api_key')
                print(f"API Key loaded from config.json: {c.get('api_key')[:20]}...")
    except Exception as e:
        print(f"Error loading config.json: {e}")

# Fallback: Set API key directly if not loaded
if not os.environ.get('GOOGLE_API_KEY'):
    # User's API key from the URL they tested
    os.environ['GOOGLE_API_KEY'] = 'AIzaSyAc2_lINTYRCDd09KByCzTAV4oalJ_DlLw'
    print("API Key set directly in script")
else:
    print(f"API Key found in environment: {os.environ.get('GOOGLE_API_KEY')[:20]}...")

from google.genai import types
from google.adk.runners import InMemoryRunner

# Use importlib to avoid shadowing issue if assistente.agent object exists in assistente package
assistente_agent_module = importlib.import_module('assistente.agent')

async def debug_chat():
    print(f"Agents Dir in module: {assistente_agent_module.AGENTS_DIR}")
    print(f"Available agents: {list(assistente_agent_module.sub_agents_map.keys())}")
    
    name = "Secretaria da Fazenda"
    norm_name = assistente_agent_module.normalize_name(name)
    print(f"Normalized '{name}' -> '{norm_name}'")

    agent_id = norm_name
    
    print(f"Loading agent: {agent_id}")
    used_agent = (getattr(assistente_agent_module, 'sub_agents_map', {}) or {}).get(agent_id)
    
    if used_agent:
        print(f"Agente carregado com sucesso: {used_agent.name}")
        print(f"Modelo: {used_agent.model}")
        print("Ferramentas configuradas:")
        for tool in used_agent.tools:
            print(f" - {type(tool).__name__}")
            if hasattr(tool, 'file_search_store_names'):
                print(f"   Stores: {tool.file_search_store_names}")
    else:
        print(f"Agente '{agent_id}' não encontrado em sub_agents_map.")
        return

    # Inicia o chat
    print("\nIniciando chat de teste...")
    import uuid
    from google.genai import types
    session_id = str(uuid.uuid4())
    user_msg = "quais os tipos de tributos ?"
    user_content = types.Content(role='user', parts=[types.Part(text=user_msg)])
    
    print(f"Usuário: {user_msg}")
    
    try:
        runner = InMemoryRunner(agent=used_agent, app_name='assistente')
        # Cria a sessão antes de usar
        await runner.session_service.create_session(app_name='assistente', session_id=session_id, user_id='user')
        
        async for event in runner.run_async(user_id='user', session_id=session_id, new_message=user_content):
            print(f"Evento: {event}")
    except Exception as e:
        print(f"\nErro durante a execução do chat: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_chat())
