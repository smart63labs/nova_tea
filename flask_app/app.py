import os
import sys
import logging

# FIX: Disable Symlinks for HuggingFace on Windows (prevents WinError 1314 without Dev Mode)
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"

import json
import importlib
import asyncio
import time
import aiohttp
import litellm

# Fix para LiteLLM: Evita "RuntimeError: <Queue ...> is bound to a different event loop"
# Ocorre quando misturamos Flask (threads) com LiteLLM (que tenta usar o loop principal/ASGI)
litellm.success_callback = []
litellm.failure_callback = []
litellm.callbacks = []
litellm.telemetry = False
litellm.suppress_instrumentation = True

# Setup paths and load config/env BEFORE other imports
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

CONFIG_PATH = os.path.join(PROJECT_ROOT, 'dados', 'config.json')
MODELS_PATH = os.path.join(PROJECT_ROOT, 'dados', 'models.json')
AGENTS_DIR = os.path.join(PROJECT_ROOT, 'dados', 'agentes')
ENV_PATH = os.path.join(PROJECT_ROOT, 'assistente', '.env')

# Load Key from JSON first to ensure it's in env before any google/agent import
if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            c = json.load(f)
            if c.get('api_key'):
                os.environ['GOOGLE_API_KEY'] = c.get('api_key')
    except:
        pass

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response, stream_with_context
from flask_cors import CORS
from dotenv import load_dotenv
from google.genai import types, Client
from google.adk.runners import InMemoryRunner

assistente_agent = importlib.import_module('assistente.agent')
from assistente.chroma_manager import chroma_manager

# Import scraping service
try:
    from services.scraping import ScraperFactory
    SCRAPING_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Scraping service not available: {e}")
    SCRAPING_AVAILABLE = False

def get_genai_client():
    api_key = os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        cfg = load_settings()
        api_key = cfg.get('api_key')
    if not api_key:
        return None
    return Client(api_key=api_key, http_options={'api_version': 'v1beta'})

def load_settings():
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
    
    # Load agents individually
    agents = {}
    if os.path.exists(AGENTS_DIR):
        for fname in os.listdir(AGENTS_DIR):
            if fname.endswith('.json'):
                # Special handling for orchestrator
                if fname == 'orquestrador.json':
                    try:
                        with open(os.path.join(AGENTS_DIR, fname), 'r', encoding='utf-8') as f:
                            root_data = json.load(f)
                            cfg['root'] = {
                                'system_prompt': root_data.get('system_prompt', ''),
                                'user_prompt': root_data.get('user_prompt', '')
                            }
                    except:
                        pass
                    continue

                aid = fname[:-5]
                try:
                    with open(os.path.join(AGENTS_DIR, fname), 'r', encoding='utf-8') as f:
                        agents[aid] = json.load(f)
                except:
                    pass
    
    cfg.setdefault("model", "gemini-2.5-flash")
    cfg.setdefault("api_key", "")
    cfg.setdefault("root", {"system_prompt": "", "user_prompt": ""})
    cfg["agents"] = agents # Override agents with loaded files
    
    return cfg

def save_settings(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    os.makedirs(AGENTS_DIR, exist_ok=True)
    
    # Separate agents and root from main config
    agents = cfg.pop('agents', {})
    root_cfg = cfg.pop('root', {})
    
    # Save main config
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        
    # Save root config to orquestrador.json
    root_data = {
        "name": "ASSISTENTE_Orquestrador",
        "system_prompt": root_cfg.get('system_prompt', ''),
        "user_prompt": root_cfg.get('user_prompt', '')
    }
    with open(os.path.join(AGENTS_DIR, 'orquestrador.json'), 'w', encoding='utf-8') as f:
        json.dump(root_data, f, ensure_ascii=False, indent=2)

    # Save agents individually
    for aid, acfg in agents.items():
        with open(os.path.join(AGENTS_DIR, f'{aid}.json'), 'w', encoding='utf-8') as f:
            json.dump(acfg, f, ensure_ascii=False, indent=2)
            
    # Restore objects to cfg for return/logic
    cfg['agents'] = agents
    cfg['root'] = root_cfg

    # Update env if key changed
    if cfg.get('api_key'):
        os.environ['GOOGLE_API_KEY'] = cfg.get('api_key')
        set_env_key(cfg.get('api_key'))

def load_models_config():
    if os.path.exists(MODELS_PATH):
        try:
            with open(MODELS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    # Default structure if file missing
    return {
        "active_model_id": "gemini-2.0-flash-exp",
        "models": []
    }

def save_models_config(data):
    os.makedirs(os.path.dirname(MODELS_PATH), exist_ok=True)
    with open(MODELS_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def set_env_key(key):
    lines = []
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
    wrote = False
    new_lines = []
    for line in lines:
        if line.startswith('GOOGLE_API_KEY='):
            new_lines.append('GOOGLE_API_KEY=' + key)
            wrote = True
        else:
            new_lines.append(line)
    if not wrote:
        new_lines.append('GOOGLE_API_KEY=' + key)
    with open(ENV_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))

def reload_agents():
    global assistente_agent, runner
    assistente_agent = importlib.reload(assistente_agent)

def build_runner():
    return InMemoryRunner(agent=assistente_agent.root_agent if hasattr(assistente_agent, 'root_agent') else assistente_agent.agent, app_name='assistente')

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev')

settings = load_settings()
runner = build_runner()
session_id = runner.session_service.create_session_sync(app_name='assistente', user_id='user').id

def list_agents():
    ents = getattr(assistente_agent, 'entidades', [])
    return [(assistente_agent.normalize_name(e), e) for e in ents]

def get_agent_name_by_id(agent_id):
    raw = (agent_id or '').strip()
    if raw:
        m = (getattr(assistente_agent, 'sub_agents_map', {}) or {})
        if raw in m:
            return raw, None
        norm = assistente_agent.normalize_name(raw)
        if norm in m:
            return norm, None
    for aid, title in list_agents():
        if aid == raw:
            return aid, title
        if raw and assistente_agent.normalize_name(title) == norm:
            return aid, title
    return None, None

@app.route('/')
def index():
    return redirect(url_for('chat'))

@app.route('/api/agents', methods=['GET'])
def api_agents_list():
    agents = list_agents()
    return jsonify([{'id': a[0], 'name': a[1]} for a in agents])


@app.route('/api/models', methods=['GET', 'POST'])
def api_models_config():
    if request.method == 'POST':
        data = request.json
        
        # Load current config to update
        current_config = load_models_config()
        
        # Update active model
        if 'active_model_id' in data:
            current_config['active_model_id'] = data['active_model_id']
        
        # Update models list if provided, or update individual fields
        if 'models' in data:
            # Create a map for easier update
            incoming_models_map = {m['id']: m for m in data['models']}
            
            for model in current_config['models']:
                mid = model['id']
                if mid in incoming_models_map:
                    inc = incoming_models_map[mid]
                    if 'enabled' in inc:
                        model['enabled'] = inc['enabled']
                    if 'endpoint' in inc:
                        if model['type'].startswith('local_'):
                            model['endpoint'] = inc['endpoint']
                        elif model['type'] == 'litellm_local':
                            model['api_base'] = inc['endpoint']
                    if 'api_key' in inc:
                        model['api_key'] = inc['api_key']
        
        save_models_config(current_config)
        
        # Also update main config to reflect active model
        main_cfg = load_settings()
        main_cfg['model'] = current_config['active_model_id']
        save_settings(main_cfg)
        
        # Set API Key for active model if present
        active_model = next((m for m in current_config['models'] if m['id'] == current_config['active_model_id']), None)
        if active_model and active_model.get('api_key'):
            key = active_model['api_key']
            m_type = active_model.get('type', '')
            m_name = active_model.get('model_name', '')
            
            # Map correct env var
            if m_type == 'google_genai':
                os.environ['GOOGLE_API_KEY'] = key
            elif m_type == 'litellm':
                env_var = active_model.get('api_key_env')
                if not env_var:
                    if 'groq' in m_name: env_var = 'GROQ_API_KEY'
                    elif 'deepseek' in m_name: env_var = 'DEEPSEEK_API_KEY'
                    elif 'openrouter' in m_name: env_var = 'OPENROUTER_API_KEY'
                    else: env_var = 'DEEPSEEK_API_KEY' # Default fallback
                os.environ[env_var] = key
        elif main_cfg.get('api_key'):
             # Fallback to main config key (Google)
             os.environ['GOOGLE_API_KEY'] = main_cfg['api_key']

        # Reload agents to apply changes
        try:
            reload_agents()
            global runner, session_id
            runner = build_runner()
            session_id = runner.session_service.create_session_sync(app_name='tia', user_id='user').id
        except Exception as e:
            print(f"Error reloading agents: {e}")
            
        return jsonify({"status": "success", "config": current_config})
    
    # GET
    return jsonify(load_models_config())

@app.route('/settings/models', methods=['GET', 'POST'])
def settings_models():
    if request.method == 'POST':
        data = request.form.to_dict()
        
        # Load current config to update
        current_config = load_models_config()
        
        # Update active model
        if 'active_model_id' in data:
            current_config['active_model_id'] = data['active_model_id']
        
        # Update models enabled status and endpoints
        for model in current_config['models']:
            mid = model['id']
            # Enabled checkbox (present if checked)
            model['enabled'] = f'enabled_{mid}' in data
            
            # Update endpoint if local
            if model['type'].startswith('local_') or model['type'].startswith('litellm_local'):
                ep_key = f'endpoint_{mid}'
                if ep_key in data and data[ep_key].strip():
                    if model['type'].startswith('litellm_local'):
                         model['api_base'] = data[ep_key].strip()
                    else:
                         model['endpoint'] = data[ep_key].strip()

            # Update API Key for litellm models
            if model['type'] == 'litellm':
                key_name = f'api_key_{mid}'
                if key_name in data and data[key_name].strip():
                    model['api_key'] = data[key_name].strip()
        
        save_models_config(current_config)
        
        # Also update main config to reflect active model and global API key
        main_cfg = load_settings()
        main_cfg['model'] = current_config['active_model_id']
        
        if 'api_key' in data and data['api_key'].strip():
            main_cfg['api_key'] = data['api_key'].strip()
            
        save_settings(main_cfg)
        
        # Reload agents to apply changes
        reload_agents()
        global runner, session_id
        runner = build_runner()
        session_id = runner.session_service.create_session_sync(app_name='tia', user_id='user').id
        
        return redirect(url_for('settings_models'))
    
    models_config = load_models_config()
    main_cfg = load_settings()
    return render_template('settings_model.html', models_config=models_config, api_key=main_cfg.get('api_key', ''))

@app.route('/api/models/test', methods=['POST'])
async def api_test_model_connection():
    data = request.json
    model_id = data.get('model_id')
    model_type = data.get('model_type')
    endpoint = data.get('endpoint')
    api_key = data.get('api_key')
    
    if not model_id:
        return jsonify({"success": False, "message": "Model ID missing"})

    try:
        if model_type.startswith('local_') or model_type.startswith('litellm'):
            if not endpoint:
                # Try to use api_base if endpoint is missing (common for litellm)
                models_cfg = load_models_config()
                for m in models_cfg.get('models', []):
                    if m.get('id') == model_id:
                         endpoint = m.get('api_base')
                         break
            
            if not endpoint and model_type == 'litellm':
                 # System-defined endpoint for Cloud Providers
                 if 'deepseek' in model_id:
                     endpoint = "https://api.deepseek.com/chat/completions"
                 elif 'groq' in model_id:
                     endpoint = "https://api.groq.com/openai/v1/chat/completions"

            if not endpoint:
                return jsonify({"success": False, "message": "Endpoint missing"})
            
            # Get model_hash from models config
            models_cfg = load_models_config()
            model_hash = None
            for m in models_cfg.get('models', []):
                if m.get('id') == model_id:
                    model_hash = m.get('model_hash')
                    # Also try to grab model_name if hash is missing
                    if not model_hash:
                         model_hash = m.get('model_name')
                    break
            
            # Use model_hash if available, otherwise fall back to model_id
            model_identifier = model_hash if model_hash else model_id
            
            # Sanitization for Litellm models (remove provider prefix for raw HTTP test)
            # e.g. "deepseek/deepseek-chat" -> "deepseek-chat"
            if model_type.startswith('litellm') and '/' in model_identifier:
                model_identifier = model_identifier.split('/', 1)[1]
            
            # Simple connection test for local model
            url = endpoint
            # Construct chat completion URL for testing
            chat_url = endpoint
            
            # If it's already a full URL including chat/completions, leave it
            if not chat_url.endswith('chat/completions'):
                # Heuristics for Ollama/LocalAI
                if chat_url.endswith('/v1'):
                     chat_url = chat_url.rstrip('/') + '/chat/completions'
                elif chat_url.endswith('/'):
                     chat_url += 'v1/chat/completions'
                elif 'engines/v1' in chat_url:
                     chat_url += '/chat/completions'
                else:
                     if 'localhost' in chat_url and '/v1' not in chat_url:
                          chat_url += '/v1/chat/completions'
                     else:
                          chat_url += '/chat/completions'
            
            # Minimal payload to test connectivity
            payload = {
                "model": model_identifier,  # Use model_hash instead of model_id
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1
            }
            
            logging.info(f"Testing Local LLM Connection: URL={chat_url}, Model={model_identifier}")
            
            # Use ONLY provided API key
            headers = {'Content-Type': 'application/json'}
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'
            else:
                # If no key provided for a model that requires it (like DeepSeek cloud), it should fail or warn.
                # However, local models might not need it.
                # DeepSeek Cloud (litellm) definitely needs it.
                if model_type == 'litellm': 
                    return jsonify({"success": False, "message": "API Key faltando. Por favor inicie a chave na tela de configurações."})
            
            async with aiohttp.ClientSession() as session:
                try:
                    # Increased timeout to 120s for local models that might need to load
                    async with session.post(chat_url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                        if resp.status == 200:
                             logging.info("Local LLM Connection Successful")
                             return jsonify({"success": True, "message": "Conectado com sucesso! O modelo respondeu."})
                        else:
                             text = await resp.text()
                             logging.error(f"Local LLM Connection Failed: HTTP {resp.status} - {text}")
                             return jsonify({"success": False, "message": f"Erro HTTP {resp.status}: {text[:200]}"})
                except asyncio.TimeoutError:
                     logging.error("Local LLM Connection Timeout")
                     return jsonify({"success": False, "message": "Timeout: O modelo demorou muito para responder (>120s). Verifique se o Docker está rodando e se o modelo foi baixado (ollama pull ...)."})
                except aiohttp.ClientConnectorError as ex:
                     logging.error(f"Local LLM Connection Error: {ex}")
                     return jsonify({"success": False, "message": f"Erro de conexão: Não foi possível conectar ao endpoint {chat_url}. Verifique se o Docker está rodando na porta correta."})
                except Exception as ex:
                     logging.error(f"Local LLM Connection Exception: {type(ex).__name__}: {str(ex)}")
                     return jsonify({"success": False, "message": f"Falha na conexão: {type(ex).__name__}: {str(ex)}"})

        elif model_type.startswith('google_genai'):
            # Test Google GenAI
            client_key = api_key
            if not client_key:
                client_key = os.environ.get('GOOGLE_API_KEY')
                if not client_key:
                     cfg = load_settings()
                     client_key = cfg.get('api_key')
            
            if not client_key:
                 return jsonify({"success": False, "message": "API Key not configured"})
            
            client = Client(api_key=client_key, http_options={'api_version': 'v1beta'})
            
            try:
                # Use aio client for async generation
                resp = await client.aio.models.generate_content(
                    model=model_id,
                    contents="Hi"
                )
                return jsonify({"success": True, "message": "Connected successfully"})
            except Exception as e:
                 return jsonify({"success": False, "message": str(e)})
                 
        return jsonify({"success": False, "message": "Unknown model type"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/chat', methods=['GET'])
def chat():
    agents = list_agents()
    return render_template('chat.html', agents=agents)

async def self_process_events(runner, user_id, session_id, message, events_list):
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=message):
        events_list.append(event)

@app.route('/api/chat', methods=['POST'])
def api_chat():
    import uuid
    import json
    session_id = request.form.get('session_id') or str(uuid.uuid4())
    user_id = 'user'
    target = request.form.get('target', 'auto')
    message = request.form.get('message', '').strip()
    cfg = load_settings()
    if target == 'auto':
        # Hot-reload system prompt for orchestrator
        root_sys = (cfg.get('root') or {}).get('system_prompt', '')
        if root_sys and hasattr(assistente_agent, 'root_agent'):
             assistente_agent.root_agent.instruction = root_sys

        up = (cfg.get('root') or {}).get('user_prompt', '')
        final_message = (up + '\n\n' + message).strip() if up else message
        used_runner = runner
    else:
        aid, title = get_agent_name_by_id(target)
        if not aid:
            return jsonify({"error": "agent_not_found"}), 404
        up = ((cfg.get('agents') or {}).get(aid) or {}).get('user_prompt', '')
        final_message = (up + '\n\n' + message).strip() if up else message
        used_agent = (getattr(assistente_agent, 'sub_agents_map', {}) or {}).get(aid)
        if not used_agent:
            return jsonify({"error": "agent_unavailable"}), 404
        
        # Hot-reload instruction for specialist agent
        spec_sys = ((cfg.get('agents') or {}).get(aid) or {}).get('system_prompt', '')
        if spec_sys:
             used_agent.instruction = spec_sys

        used_runner = InMemoryRunner(agent=used_agent, app_name='assistente')
    
    # Garantir que a sessão existe no runner utilizado
    try:
        used_runner.session_service.create_session_sync(app_name='assistente', user_id=user_id, session_id=session_id)
    except Exception:
        # Sessão pode já existir, ignoramos
        pass

    user_content = types.Content(role='user', parts=[types.Part(text=final_message)])
    
    def generate():
        try:
            yield f"data: {json.dumps({'status': 'processing'})}\n\n"
            
            print(f"[DEBUG] Iniciando processamento do runner para: {session_id}")
            if message:
                print(f"[DEBUG] Input do usuário: {message[:100]}...")
                
            # Executar o fluxo com streaming SÍNCRONO
            # O runner.run() retorna um gerador síncrono
            event_count = 0
            has_started_text = False
            
            for event in used_runner.run(user_id='user', session_id=session_id, new_message=user_content):
                event_count += 1
                # print(f"[DEBUG] Evento {event_count}: {type(event)}") # Descomente para debug intenso
                
                if event.is_final_response():
                    print(f"[DEBUG] Resposta final recebida.")
                    if event.content and event.content.parts:
                        parts = [p.text for p in event.content.parts if getattr(p, 'text', None) and not getattr(p, 'thought', False)]
                        text = ''.join(parts)
                        if text:
                            yield f"data: {json.dumps({'reply': text})}\n\n"
                elif hasattr(event, 'content') and event.content.parts:
                    # Capturando chunks de texto durante a geração
                    for part in event.content.parts:
                        if getattr(part, 'text', None):
                            if not has_started_text:
                                print(f"[DEBUG] Iniciando geração de texto...")
                                has_started_text = True
                            yield f"data: {json.dumps({'chunk': part.text})}\n\n"
                        elif getattr(part, 'function_call', None):
                            fn_name = part.function_call.name
                            fn_args = part.function_call.args
                            print(f"[DEBUG] Chamada de função detectada: {fn_name}")
                            print(f"        Argumentos: {json.dumps(fn_args)}")
                            yield f"data: {json.dumps({'status': 'delegating', 'tool': fn_name})}\n\n"
            
            print(f"[DEBUG] Processamento concluído. Total eventos: {event_count}")
            yield "data: [DONE]\n\n"

        except Exception as e:
            # ... (tratamento de erro existente)
            print(f"[ERROR] Erro crítico no loop do runner: {e}")
            import traceback
            traceback.print_exc()
            error_msg = str(e)
            
            # ... (mapeamento de erros 429/etc)
            friendly_msg = "Ocorreu um erro inesperado ao processar sua solicitação. Por favor, tente novamente."
            error_code = 500

            # 1. Cota Excedida / Rate Limit (429)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "quota" in error_msg.lower() or "rate_limit" in error_msg.lower():
                import re
                wait_time = "alguns instantes"
                
                # Tenta extrair o tempo específico (ex: "Please try again in 11.85s")
                match = re.search(r"try again in (\d+(\.\d+)?)s", error_msg)
                if match:
                    seconds = float(match.group(1))
                    wait_time = f"{seconds:.1f} segundos"
                
                if "Free Tier" in error_msg or "Gemini" in error_msg:
                    friendly_msg = "A cota diária deste modelo (Gemini Free) foi atingida. Tente novamente amanhã ou mude para um modelo Groq/DeepSeek."
                else:
                    friendly_msg = f"Limite de requisições atingido. O sistema pede que você aguarde {wait_time} antes de tentar novamente."
                
                error_code = 429
            
            # 2. Autenticação (401)
            elif "401" in error_msg or "authentication" in error_msg.lower() or "unauthorized" in error_msg.lower():
                friendly_msg = "Chave de API inválida, expirada ou não configurada corretamente. Por favor, verifique as chaves nas configurações do sistema."
                error_code = 401
                
            # 3. Modelo não encontrado (404)
            elif "404" in error_msg or "model_not_found" in error_msg.lower() or "not found" in error_msg.lower():
                friendly_msg = "O modelo selecionado não foi encontrado ou não está disponível no provedor. Tente selecionar outro modelo."
                error_code = 404
                
            # 4. Instabilidade do Provedor (500/503)
            elif "500" in error_msg or "503" in error_msg or "service_unavailable" in error_msg.lower() or "internal server error" in error_msg.lower():
                friendly_msg = "O provedor de IA (Google/Groq/DeepSeek) está enfrentando instabilidade momentânea. Por favor, aguarde alguns segundos e tente novamente."
                error_code = 503
                
            # 5. Timeout ou Erro de Conexão
            elif "timeout" in error_msg.lower() or "connection" in error_msg.lower() or "deadline" in error_msg.lower():
                friendly_msg = "Não foi possível conectar ao servidor de IA. Verifique sua conexão com a internet ou tente novamente em instantes."
                error_code = 408
            
            # Se for um erro específico que já contém detalhes úteis, mas não foi mapeado
            else:
                friendly_msg = f"Erro no processamento: {error_msg[:100]}..."

            yield f"data: {json.dumps({'error': friendly_msg, 'code': error_code, 'raw_error': error_msg[:200]})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    if request.method == 'POST':
        data = request.json
        cfg = load_settings()
        # Merge updates
        if 'model' in data:
            cfg['model'] = data['model']
        if 'api_key' in data:
            cfg['api_key'] = data['api_key']
        if 'root' in data:
            cfg['root'] = data['root']
        if 'agents' in data:
            logging.info(f"Merging {len(data['agents'])} agents into config")
            # Merge agent data instead of overwriting to preserve fields
            if 'agents' not in cfg:
                cfg['agents'] = {}
            for aid, adata in data['agents'].items():
                if aid not in cfg['agents']:
                    cfg['agents'][aid] = adata
                else:
                    cfg['agents'][aid].update(adata)
                logging.debug(f"Agent {aid} updated with {list(adata.keys())}")
            
        save_settings(cfg)
        reload_agents()
        global runner, session_id
        runner = build_runner()
        session_id = runner.session_service.create_session_sync(app_name='tia', user_id='user').id
        return jsonify({"status": "success"})
    
    return jsonify(load_settings())

@app.route('/api/agent/<agent_id>', methods=['POST'])
def api_save_agent(agent_id):
    data = request.json
    file_path = os.path.join(AGENTS_DIR, f'{agent_id}.json')
    
    current_data = {}
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                current_data = json.load(f)
        except:
            pass
            
    # Update fields
    if 'system_prompt' in data:
        current_data['system_prompt'] = data['system_prompt']
    if 'user_prompt' in data:
        current_data['user_prompt'] = data['user_prompt']
    if 'enabled' in data:
        current_data['enabled'] = data['enabled']
    if 'name' in data:
        current_data['name'] = data['name']
    if 'enable_web_search' in data:
        current_data['enable_web_search'] = data['enable_web_search']
    if 'file_search_stores' in data:
        current_data['file_search_stores'] = data['file_search_stores']
    
    # New multi-LLM configuration fields
    if 'gemini_enable_web' in data:
        current_data['gemini_enable_web'] = data['gemini_enable_web']
    if 'others_enable_web' in data:
        current_data['others_enable_web'] = data['others_enable_web']
    if 'gemini_file_search_stores' in data:
        current_data['gemini_file_search_stores'] = data['gemini_file_search_stores']
    if 'others_file_search_stores' in data:
        current_data['others_file_search_stores'] = data['others_file_search_stores']
        
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(current_data, f, ensure_ascii=False, indent=2)
        
    reload_agents()
    global runner, session_id
    runner = build_runner()
    session_id = runner.session_service.create_session_sync(app_name='tia', user_id='user').id
    
    return jsonify({"status": "success"})

@app.route('/settings/model', methods=['GET', 'POST'])
def settings_model():
    return redirect(url_for('settings_models'))

@app.route('/agents', methods=['GET'])
def agents_list():
    agents = list_agents()
    return render_template('agents.html', agents=agents)

@app.route('/agents/<agent_id>', methods=['GET', 'POST'])
def agent_detail(agent_id):
    aid, title = get_agent_name_by_id(agent_id)
    if not aid:
        return 'Agent not found', 404
    cfg = load_settings()
    rec = (cfg.get('agents') or {}).get(aid) or {}
    if request.method == 'POST':
        sp = request.form.get('system_prompt', '')
        up = request.form.get('user_prompt', '')
        cfg.setdefault('agents', {})[aid] = {"system_prompt": sp, "user_prompt": up}
        save_settings(cfg)
        reload_agents()
        global runner, session_id
        runner = build_runner()
        session_id = runner.session_service.create_session_sync(app_name='tia', user_id='user').id
        return redirect(url_for('agent_detail', agent_id=agent_id))
    return render_template('agent_detail.html', agent_id=aid, title=title, system_prompt=rec.get('system_prompt', ''), user_prompt=rec.get('user_prompt', ''))

@app.route('/api/knowledge/stores', methods=['GET', 'POST'])
def api_knowledge_stores():
    import logging
    logging.basicConfig(filename='debug.log', level=logging.DEBUG)
    
    client = get_genai_client()
    if not client:
        logging.error("API Key not configured")
        return jsonify({"error": "API Key not configured"}), 400
        
    if request.method == 'POST':
        data = request.json
        display_name = data.get('display_name')
        logging.info(f"Creating store with display_name: {display_name}")
        try:
            store = client.file_search_stores.create(config={'display_name': display_name})
            logging.info(f"Store created: {store.name} - {store.display_name}")
            return jsonify({"name": store.name, "display_name": store.display_name})
        except Exception as e:
            logging.error(f"Error creating store: {e}", exc_info=True)
            print(f"Error creating store: {e}")
            return jsonify({"error": str(e)}), 500
            
    # GET: List stores
    try:
        logging.info("Listing stores...")
        stores = []
        # list() usually returns an iterator or pager
        for store in client.file_search_stores.list():
            stores.append({
                "name": store.name,
                "display_name": store.display_name
            })
        logging.info(f"Found {len(stores)} stores")
        
        # --- AUTO-SYNC: Clean orphaned stores from agents ---
        # User requested: "sistema deve ter a capacidade de alterar ela conforme se altera a base"
        try:
            # DISABLED TEMPORARILY due to user request (preserving broken refs)
            # valid_names = set(s['name'] for s in stores)
            # clean_orphaned_stores(valid_names)
            # enforce_store_ownership(stores)
            
            # Feature: Show "Ghost" Stores (Local references not found in Cloud)
            # This helps users see that their config is preserved even if API Key changed/lost access
            cloud_store_names = set(s['name'] for s in stores)
            if os.path.exists(AGENTS_DIR):
                for fname in os.listdir(AGENTS_DIR):
                    if fname.endswith('.json') and fname != 'orquestrador.json':
                        try:
                            with open(os.path.join(AGENTS_DIR, fname), 'r', encoding='utf-8') as f:
                                ag_data = json.load(f)
                            for ref_store in ag_data.get('file_search_stores', []):
                                if ref_store not in cloud_store_names:
                                    # Add placeholder for missing store
                                    stores.append({
                                        "name": ref_store,
                                        "display_name": f"⚠️ [Sem Acesso] {ref_store.split('/')[-1]}",
                                        "status": "missing_permission"
                                    })
                                    cloud_store_names.add(ref_store) # Avoid duplicates
                        except:
                            pass
        except Exception as sync_e:
            logging.error(f"Error during auto-sync of stores: {sync_e}")
            # Do not fail the request just because sync failed
        # ----------------------------------------------------

        return jsonify(stores)
    except Exception as e:
        logging.error(f"Error listing stores: {e}", exc_info=True)
        print(f"Error listing stores: {e}")
        return jsonify({"error": str(e)}), 500

def update_agents_store_binding(store_name, action='unbind', target_agents=None):
    """
    Modifies all agents to remove (unbind) or add (bind) a store reference.
    Returns list of affected agent IDs.
    """
    import logging
    affected_agents = []
    
    if not os.path.exists(AGENTS_DIR):
        return affected_agents

    logging.info(f"Agent-Store Binding: {action.upper()} store {store_name}...")
    
    # Normalize store_name to ensure matching (handle potential resource prefix diffs)
    # Target: fileSearchStores/xyz
    target_suffix = store_name.split('/')[-1] # xyz
    
    for fname in os.listdir(AGENTS_DIR):
        if fname.endswith('.json') and fname != 'orquestrador.json':
            if target_agents and fname not in target_agents:
                continue
            fpath = os.path.join(AGENTS_DIR, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    agent_data = json.load(f)
                
                stores = agent_data.get('file_search_stores', [])
                original_len = len(stores)
                new_stores = []
                
                changed = False
                if action == 'unbind':
                    # Remove if matches full name OR suffix
                    for s in stores:
                        if s == store_name or s.endswith(f"/{target_suffix}") or ms_compare(s, store_name):
                            changed = True
                            # Skip (remove)
                        else:
                            new_stores.append(s)
                            
                elif action == 'bind':
                    new_stores = list(stores)
                    # Check if already exists (fuzzy check)
                    exists = any(s == store_name or s.endswith(f"/{target_suffix}") for s in stores)
                    if not exists:
                        new_stores.append(store_name)
                        changed = True
                
                if changed:
                    agent_data['file_search_stores'] = new_stores
                    with open(fpath, 'w', encoding='utf-8') as f:
                        json.dump(agent_data, f, ensure_ascii=False, indent=2)
                    affected_agents.append(fname)
                    logging.info(f"Agent {fname}: {action} {store_name} (Updated list: {new_stores})")
                    
            except Exception as e:
                logging.error(f"Error updating agent binding {fname}: {e}")
                
    if affected_agents:
        logging.info(f"Binding updated for agents: {affected_agents}. Reloading...")
        try:
            reload_agents()
            global runner, session_id
            runner = build_runner()
            time.sleep(2)
            session_id = runner.session_service.create_session_sync(app_name='tia', user_id='user').id
        except Exception as e:
            logging.error(f"Error reloading agents after {action}: {e}")
            try:
                target_suffix = store_name.split('/')[-1]
                import types as _types_mod
                mod = tea_agent
                sub_map = getattr(mod, 'sub_agents_map', {}) or {}
                for aid, sub_agent in sub_map.items():
                    tools = getattr(sub_agent, 'tools', []) or []
                    if action == 'unbind':
                        new_tools = []
                        for t in tools:
                            stores_attr = getattr(t, 'file_search_store_names', None)
                            if stores_attr:
                                if any(s == store_name or str(s).endswith(f"/{target_suffix}") for s in stores_attr):
                                    continue
                            new_tools.append(t)
                        sub_agent.tools = new_tools
                runner = build_runner()
                time.sleep(1)
            except Exception as ie:
                logging.error(f"Fallback runtime unbind failed: {ie}")
        
    return affected_agents

def ms_compare(s1, s2):
    # Weak comparison helper
    return s1.strip('/') == s2.strip('/') or s1 in s2 or s2 in s1

def clean_orphaned_stores(valid_store_names):
    """
    Iterates through all agent configs and removes file_search_stores 
    references that are not present in valid_store_names.
    """
    import logging
    changed_any = False
    
    if not os.path.exists(AGENTS_DIR):
        return

    for fname in os.listdir(AGENTS_DIR):
        if fname.endswith('.json') and fname != 'orquestrador.json':
            fpath = os.path.join(AGENTS_DIR, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    agent_data = json.load(f)
                
                current_stores = agent_data.get('file_search_stores', [])
                if not current_stores:
                    continue
                    
                # Keep only stores that exist in the valid list
                new_stores = [s for s in current_stores if s in valid_store_names]
                
                if len(new_stores) != len(current_stores):
                    logging.info(f"Auto-Sync: Removing orphaned stores from {fname}. Old: {current_stores}, New: {new_stores}")
                    agent_data['file_search_stores'] = new_stores
                    
                    with open(fpath, 'w', encoding='utf-8') as f:
                        json.dump(agent_data, f, ensure_ascii=False, indent=2)
                    changed_any = True
            except Exception as e:
                logging.error(f"Error syncing agent {fname}: {e}")
    
    if changed_any:
        logging.info("Auto-Sync: Changes detected, reloading agents...")
        reload_agents()
        global runner, session_id
        runner = build_runner()
        # Recreate session to ensure consistency (optional but checks out)
        session_id = runner.session_service.create_session_sync(app_name='tia', user_id='user').id

def enforce_store_ownership(store_list):
    import logging
    if not os.path.exists(AGENTS_DIR):
        return
    # Build map store_name -> display_name
    store_map = {}
    for s in store_list:
        try:
            store_map[s['name']] = s.get('display_name') or s['name']
        except Exception:
            pass
    def normalize(txt):
        return (txt or '').lower().strip().encode('ascii', 'ignore').decode('ascii')
    changed_any = False
    for fname in os.listdir(AGENTS_DIR):
        if fname.endswith('.json') and fname != 'orquestrador.json':
            fpath = os.path.join(AGENTS_DIR, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    agent_data = json.load(f)
                agent_name = agent_data.get('name') or fname[:-5]
                nAgent = normalize(agent_name)
                current = agent_data.get('file_search_stores', []) or []
                new_list = []
                removed = []
                for sn in current:
                    disp = store_map.get(sn, sn)
                    nDisp = normalize(disp)
                    if nDisp == nAgent:
                        new_list.append(sn)
                    else:
                        removed.append(sn)
                if removed:
                    agent_data['file_search_stores'] = new_list
                    with open(fpath, 'w', encoding='utf-8') as f:
                        json.dump(agent_data, f, ensure_ascii=False, indent=2)
                    logging.info(f"Ownership sync: Removed stores not belonging to {agent_name}: {removed}")
                    changed_any = True
            except Exception as e:
                logging.error(f"Error enforcing ownership for {fname}: {e}")
    if changed_any:
        logging.info("Ownership sync: Changes detected, reloading agents...")
        reload_agents()
        global runner, session_id
        runner = build_runner()
        session_id = runner.session_service.create_session_sync(app_name='tia', user_id='user').id

@app.route('/api/knowledge/stores/<path:name>', methods=['DELETE'])
def api_knowledge_store_delete(name):
    import logging
    logging.info(f"Deleting store: {name}")
    
    # 1. Disassociate from Agents (User's Instruction)
    try:
        if os.path.exists(AGENTS_DIR):
            for fname in os.listdir(AGENTS_DIR):
                if fname.endswith('.json') and fname != 'orquestrador.json':
                    fpath = os.path.join(AGENTS_DIR, fname)
                    try:
                        with open(fpath, 'r', encoding='utf-8') as f:
                            agent_data = json.load(f)
                        
                        stores = agent_data.get('file_search_stores', [])
                        if name in stores:
                            logging.info(f"Removing store {name} from agent {fname}")
                            stores.remove(name)
                            agent_data['file_search_stores'] = stores
                            with open(fpath, 'w', encoding='utf-8') as f:
                                json.dump(agent_data, f, ensure_ascii=False, indent=2)
                    except Exception as ae:
                        logging.error(f"Error checking agent {fname}: {ae}")
    except Exception as e:
        logging.error(f"Error cleaning agent references: {e}")

    client = get_genai_client()
    if not client:
        return jsonify({"error": "API Key not configured"}), 400
    try:
        # Use client.file_search_stores.delete for stores
        # Note: The user example used client.files.delete which is for individual files.
        # But this route is for STORES (api/knowledge/stores/...), so we must use file_search_stores.delete.
        # If the ID passed is actually a file ID (unlikely given the route), it would fail.
        # Assuming 'name' is a store resource name.
        
        client.file_search_stores.delete(name=name)
        logging.info(f"✅ Store {name} deleted successfully.")
        return jsonify({"status": "success"})
    except Exception as e:
        error_msg = str(e)
        logging.error(f"❌ Error deleting store {name}: {error_msg}")
        
        # Check if it's a 400 Non-Empty error
        if "400" in error_msg and "non-empty" in error_msg:
             logging.info(f"Store {name} is not empty. Cleaning up files...")
             try:
                 # List and delete all documents in the store
                 for doc in client.file_search_stores.documents.list(parent=name):
                     # Try to delete the underlying file first using client.files.delete
                     try:
                         # Extract file ID from document name (heuristic: suffix)
                         # Document name format: stores/STORE_ID/documents/FILE_ID
                         # File ID format: files/FILE_ID
                         file_suffix = doc.name.split('/')[-1]
                         file_id = f"files/{file_suffix}"
                         logging.info(f"Attempting to delete underlying file: {file_id}")
                         client.files.delete(name=file_id)
                         logging.info(f"✅ Underlying file {file_id} deleted.")
                     except Exception as fe:
                         # Log warning but continue to try deleting document
                         logging.warning(f"⚠️ Could not delete underlying file {file_id} (might be already deleted): {fe}")

                     logging.info(f"Deleting document {doc.name} from store")
                     try:
                        client.file_search_stores.documents.delete(name=doc.name)
                     except Exception as de:
                        logging.warning(f"Failed to delete document via SDK: {de}. Trying REST API with force=true...")
                        try:
                            import requests
                            api_key = os.environ.get('GOOGLE_API_KEY')
                            if not api_key:
                                # Try to reload key if env var not set (e.g. if loaded via config.json only)
                                # But get_genai_client usually sets it or uses it.
                                # Let's assume we can get it from the client object if possible, or reload from config.
                                # client.api_key might be available?
                                api_key = getattr(client, 'api_key', None)
                                if not api_key:
                                     # Last resort: read config
                                     with open(CONFIG_PATH, 'r') as f:
                                         api_key = json.load(f).get('api_key')
                            
                            doc_url = f"https://generativelanguage.googleapis.com/v1beta/{doc.name}?force=true&key={api_key}"
                            res = requests.delete(doc_url)
                            if res.status_code != 200:
                                raise Exception(f"REST API failed with {res.status_code}: {res.text}")
                            logging.info(f"✅ Document {doc.name} deleted via REST API (force=true).")
                        except Exception as re:
                            logging.error(f"❌ Failed raw delete: {re}")
                            raise re # Re-raise to trigger outer loop failure if needed

                 # Retry deleting store
                 client.file_search_stores.delete(name=name)
                 logging.info(f"✅ Store {name} deleted after cleanup.")
                 return jsonify({"status": "success", "message": "Base limpa e excluída com sucesso"})
             except Exception as inner_e:
                 logging.error(f"Error cleaning up store {name}: {inner_e}")
                 return jsonify({"error": f"Falha ao esvaziar a base: {str(inner_e)}"}), 500

        # Check if it's a Not Found error (404 from Google API)
        if "404" in error_msg or "Not Found" in error_msg:
            logging.info(f"Store {name} not found, considering deleted.")
            return jsonify({"status": "success", "message": "Base não encontrada, considerada excluída"}), 200
        
        # Check for 403 Permission Denied
        if "403" in error_msg and "or it may not exist" in error_msg:
             logging.info(f"Store {name} permission denied/not found, considering deleted.")
             return jsonify({"status": "success", "message": "Base não encontrada ou sem permissão, considerada excluída"}), 200
            
        return jsonify({"error": error_msg}), 500

# Global tasks dictionary for background processing
processing_tasks = {}

# Global tasks dictionary for scraping
scraping_tasks = {}

@app.route('/api/knowledge/process', methods=['POST'])
def api_knowledge_process():
    import logging
    import uuid
    import threading
    
    # Force UTF-8 logging
    for handler in logging.getLogger().handlers:
        if hasattr(handler, 'stream') and hasattr(handler.stream, 'reconfigure'):
             try:
                handler.stream.reconfigure(encoding='utf-8')
             except:
                pass

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    temp_path = os.path.join(PROJECT_ROOT, 'temp_uploads')
    os.makedirs(temp_path, exist_ok=True)
    
    # Simple sanitization
    # safe_name = "".join([c for c in file.filename if c.isalnum() or c in "._- "]).strip()
    # local_filename = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    
    original_filename = file.filename
    safe_local_name = re.sub(r'\s+', '_', sanitize_filename(original_filename) or 'arquivo')
    local_filename = f"{uuid.uuid4().hex[:8]}_{safe_local_name}"
    
    local_path = os.path.join(temp_path, local_filename)
    
    try:
        file.save(local_path)
        logging.info(f"File saved to temp path for processing: {local_path}")
        
        # Create task
        task_id = str(uuid.uuid4())
        processing_tasks[task_id] = {
            "status": "initializing",
            "progress": 0,
            "message": "Iniciando...",
            "original_name": file.filename,
            "result": None,
            "error": None
        }
        
        # Start background thread
        thread = threading.Thread(target=process_document_task, args=(task_id, local_path, file.filename))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "status": "queued",
            "task_id": task_id
        })
        
    except Exception as e:
        logging.error(f"Error starting processing task: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/knowledge/status/<task_id>', methods=['GET'])
def api_knowledge_status(task_id):
    task = processing_tasks.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)

def process_document_task(task_id, local_path, original_filename):
    import logging
    import time
    import gc
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
    from docling.datamodel.base_models import InputFormat
    import pypdf

    task = processing_tasks[task_id]
    
    try:
        task["status"] = "processing"
        task["message"] = "Analisando estrutura do PDF..."
        
        # Configure Pipeline to use EasyOCR
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        # Force full page OCR to ensure text extraction from scans
        # Added Portuguese ('pt') to language list to improve recognition
        pipeline_options.ocr_options = EasyOcrOptions(force_full_page_ocr=True, lang=['pt', 'en'])

        # Create converter (OCR enabled)
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

        # Create fallback converter (No OCR) for problematic pages
        pipeline_options_no_ocr = PdfPipelineOptions()
        pipeline_options_no_ocr.do_ocr = False
        pipeline_options_no_ocr.do_table_structure = True
        converter_no_ocr = DocumentConverter(
             format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options_no_ocr)
            }
        )

        # Check if it is a PDF to allow splitting
        is_pdf = local_path.lower().endswith('.pdf')
        full_markdown = ""

        if is_pdf:
            try:
                reader = pypdf.PdfReader(local_path)
                total_pages = len(reader.pages)
                task["total_pages"] = total_pages
                logging.info(f"PDF has {total_pages} pages. Starting split processing...")
                
                # Process page by page
                for i in range(total_pages):
                    task["message"] = f"Processando página {i+1} de {total_pages}..."
                    task["progress"] = int((i / total_pages) * 100)
                    
                    # Create temporary single-page PDF
                    writer = pypdf.PdfWriter()
                    writer.add_page(reader.pages[i])
                    
                    page_path = f"{local_path}_page_{i}.pdf"
                    with open(page_path, "wb") as f_out:
                        writer.write(f_out)
                    
                    try:
                        # Try Convert single page with OCR
                        logging.info(f"Converting page {i+1} with OCR...")
                        result = converter.convert(page_path)
                        page_md = result.document.export_to_markdown()
                        full_markdown += f"\n\n<!-- Page {i+1} -->\n{page_md}"
                    except Exception as page_e:
                        logging.warning(f"OCR failed for page {i+1} ({page_e}). Retrying without OCR...")
                        # Fallback: Try without OCR
                        try:
                            result_no_ocr = converter_no_ocr.convert(page_path)
                            page_md = result_no_ocr.document.export_to_markdown()
                            full_markdown += f"\n\n<!-- Page {i+1} -->\n> **Nota:** OCR falhou nesta página. Conteúdo extraído apenas do texto digital.\n\n{page_md}"
                        except Exception as fallback_e:
                            logging.error(f"Error processing page {i+1} (Fallback also failed): {fallback_e}")
                            full_markdown += f"\n\n<!-- Error on Page {i+1}: Conversion failed completely. -->\n"
                    finally:
                        if os.path.exists(page_path):
                            try:
                                os.remove(page_path)
                            except:
                                pass
                        # Aggressive GC to prevent bad_alloc
                        gc.collect()
                    
                    # Update progress
                    processing_tasks[task_id]["progress"] = int(((i + 1) / total_pages) * 100)

            except Exception as split_e:
                logging.warning(f"Failed to split PDF, falling back to full processing: {split_e}")
                task["message"] = "Processamento em lote (arquivo único)..."
                result = converter.convert(local_path)
                full_markdown = result.document.export_to_markdown()
        else:
            # Non-PDF or fallback
            task["message"] = "Processando arquivo..."
            result = converter.convert(local_path)
            full_markdown = result.document.export_to_markdown()

        task["status"] = "completed"
        task["progress"] = 100
        task["message"] = "Concluído!"
        task["result"] = full_markdown
        
        # === NEW: Indexing result to local RAG (ChromaDB) ===
        try:
            # We use the task original name or a generated one
            store_name = request.json.get('store_name') if request.is_json else None
            # If we don't have store_name here, we might need it passed down
            # For now, if no store_name, we use 'default_store' or try to infer
            # In knowledge_process, we might not have store_name yet
            if not store_name:
                store_name = 'default_store'
                
            chroma_manager.index_document(
                content=full_markdown,
                store_name=store_name,
                filename=original_filename
            )
        except Exception as chroma_e:
            logging.error(f"Failed to index task result to ChromaDB: {chroma_e}")
        
    except Exception as e:
        logging.error(f"Task failed: {e}", exc_info=True)
        task["status"] = "failed"
        task["error"] = str(e)
    finally:
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
            except:
                pass

@app.route('/api/knowledge/upload', methods=['POST'])
def api_knowledge_upload():
    import logging
    import uuid
    import unicodedata
    import re
    import time
    
    # Force UTF-8 logging
    for handler in logging.getLogger().handlers:
        if hasattr(handler, 'stream') and hasattr(handler.stream, 'reconfigure'):
             try:
                handler.stream.reconfigure(encoding='utf-8')
             except:
                pass

    client = get_genai_client()
    if not client:
        return jsonify({"error": "API Key not configured"}), 400
        
    store_name = request.form.get('store_name')
    if not store_name:
        return jsonify({"error": "store_name is required"}), 400
        
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    temp_path = os.path.join(PROJECT_ROOT, 'temp_uploads')
    os.makedirs(temp_path, exist_ok=True)
    
    # Helper to clean filename
    def sanitize_filename(name):
        # Normalize unicode characters (decomposes accents, e.g. á -> a + ´)
        # NFKD compatibility decomposition helps with chars like º -> o
        normalized = unicodedata.normalize('NFKD', name)
        # Encode to ASCII, ignoring non-ascii characters that couldn't be decomposed
        ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
        # Replace non-alphanumeric (allowing . - _ and space) with _
        # We allow spaces for the display name version, but usually good to trim
        clean = re.sub(r'[^a-zA-Z0-9._ -]', '', ascii_text)
        return clean.strip()

    original_filename = file.filename
    # For display_name in GenAI, preserve original (unicode, including º, nº, etc.)
    display_name = (original_filename or '').strip() or "sem_nome"

    # For local system path, strict safety (ASCII only, spaces to underscore) + UUID prefix
    safe_local_name = re.sub(r'\s+', '_', sanitize_filename(original_filename) or 'arquivo')
    local_filename = f"{uuid.uuid4().hex[:8]}_{safe_local_name}"
        
    local_path = os.path.join(temp_path, local_filename)
    
    try:
        file.save(local_path)
        logging.info(f"File saved to temp path: {local_path}")
        
        # === BACKUP: Salva cópia permanente antes de enviar para RAG ===
        try:
            from datetime import datetime
            import shutil
            
            backup_base_dir = os.path.join(PROJECT_ROOT, 'dados', 'scraped_backup')
            os.makedirs(backup_base_dir, exist_ok=True)
            
            # Organiza por store
            store_folder_name = store_name.replace('fileSearchStores/', '') if store_name else 'sem_store'
            store_backup_dir = os.path.join(backup_base_dir, store_folder_name)
            os.makedirs(store_backup_dir, exist_ok=True)
            
            # Adiciona timestamp ao nome do arquivo
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_name, ext = os.path.splitext(original_filename)
            backup_filename = f"{base_name}_{timestamp}{ext}"
            backup_file_path = os.path.join(store_backup_dir, backup_filename)
            
            # Copia do temp para backup
            shutil.copy2(local_path, backup_file_path)
            
            logging.info(f"✅ Backup de arquivo enviado salvo em: {backup_file_path}")
        except Exception as backup_e:
            logging.error(f"Erro ao salvar backup físico do upload: {backup_e}")
        # === FIM DO BACKUP ===

        # Determine mime_type explicitly to avoid "Unknown mime type" errors
        import mimetypes
        mime_type, _ = mimetypes.guess_type(local_path)
        
        # Fallback for types often missing in Windows registry
        if not mime_type:
            ext = os.path.splitext(local_path)[1].lower()
            if ext == '.md':
                mime_type = 'text/markdown'
            elif ext == '.txt':
                mime_type = 'text/plain'
            elif ext == '.csv':
                mime_type = 'text/csv'
            elif ext == '.pdf':
                mime_type = 'application/pdf'
        
        # Prepare upload config
        upload_config = {'display_name': display_name}
        if mime_type:
            logging.info(f"Using explicit mime_type: {mime_type}")
            upload_config['mime_type'] = mime_type
        
        # Upload directly to File Search Store to preserve display_name
        logging.info(f"Uploading file '{display_name}' directly to File Search Store {store_name}...")
        op = client.file_search_stores.upload_to_file_search_store(
            file=local_path,
            file_search_store_name=store_name,
            config=upload_config
        )
        # Wait for completion
        try:
            max_wait = 300
            waited = 0
            while not getattr(op, 'done', False) and waited < max_wait:
                time.sleep(2)
                waited += 2
                op = client.operations.get(operation=op)
        except Exception as oe:
            logging.warning(f"Operation polling failed or not supported: {oe}")
        logging.info(f"✅ File uploaded/indexed to store.")
        
        # === NEW: Sync to Local RAG (ChromaDB) ===
        try:
            # Read content for indexing
            # If it's binary like PDF, we might want to convert it first?
            # For now, let's handle text files. For PDFs, they usually go through knowledge/process first
            ext = os.path.splitext(local_path)[1].lower()
            if ext in ['.txt', '.md', '.csv']:
                with open(local_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                chroma_manager.index_document(
                    content=content,
                    store_name=store_name,
                    filename=original_filename
                )
            elif ext == '.pdf':
                # Optional: trigger a docling conversion for the local RAG as well?
                # For now, let's assume the user wants full sync.
                logging.info(f"Triggering local indexing for PDF: {original_filename}")
                from docling.document_converter import DocumentConverter
                converter = DocumentConverter()
                result = converter.convert(local_path)
                content = result.document.export_to_markdown()
                chroma_manager.index_document(
                    content=content,
                    store_name=store_name,
                    filename=original_filename
                )
        except Exception as chroma_e:
            logging.error(f"Failed to sync upload to ChromaDB: {chroma_e}")

        return jsonify({"status": "uploaded", "message": "Arquivo enviado, indexado e salvo em backup físico com sucesso."})
        
    except Exception as e:
        logging.error(f"Error uploading/attaching file: {e}", exc_info=True)
        print(f"Error uploading file: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
            except:
                pass

@app.route('/api/knowledge/stores/<path:name>/files', methods=['GET'])
def api_knowledge_store_files(name):
    client = get_genai_client()
    if not client:
        return jsonify({"error": "API Key not configured"}), 400
        
    try:
        files = []
        # List files in the store
        # In SDK, these are accessed via 'documents'
        for f in client.file_search_stores.documents.list(parent=name):
            # Get attributes directly from the document object first
            display_name = getattr(f, 'display_name', None)
            mime_type = getattr(f, 'mime_type', None)
            size_bytes = getattr(f, 'size_bytes', None)
            create_time = getattr(f, 'create_time', None)
            update_time = getattr(f, 'update_time', None)
            state = str(getattr(f, 'state', None))

            file_id = f.name.split('/')[-1] if f and getattr(f, 'name', None) else None
            
            # Only try to fetch external file details if metadata is missing
            if file_id and (not display_name or not mime_type):
                try:
                    # Try to get from files API (might fail with 403 if it's a store-managed doc)
                    file_res = client.files.get(name=f"files/{file_id}")
                    display_name = getattr(file_res, 'display_name', None) or display_name
                    mime_type = getattr(file_res, 'mime_type', None) or mime_type
                    size_bytes = getattr(file_res, 'size_bytes', None) or size_bytes
                except Exception:
                    # Ignore errors here, we'll use what we have
                    pass

            files.append({
                "name": f.name,
                "display_name": display_name,
                "file_uri": f.name, 
                "mime_type": mime_type,
                "size_bytes": size_bytes,
                "create_time": create_time.isoformat() if create_time else None,
                "update_time": update_time.isoformat() if update_time else None,
                "state": state
            })
            
        return jsonify(files)
        return jsonify(files)
    except Exception as e:
        print(f"Error listing files in store: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/knowledge/stores/<path:store_name>/files/<path:document_name>', methods=['DELETE'])
def api_knowledge_file_delete(store_name, document_name):
    import logging
    client = get_genai_client()
    if not client:
        return jsonify({"error": "API Key not configured"}), 400

    logging.info(f"Requests to delete document {document_name} from store {store_name}")
    
    affected_agents = []
    try:
        # Step 0: SAFETY DANCE
        logging.info("Starting safety unbind sequence...")
        affected_agents = update_agents_store_binding(store_name, 'unbind')
        
        # Give Google API time to propagate the agent update/session invalidation
        if affected_agents:
            logging.info("Waiting 5s for agent unbind propagation...")
            import time
            time.sleep(5) 

        # Step 1: Get Document details
        doc_display_name = None
        try:
            doc = client.file_search_stores.documents.get(name=document_name)
            doc_display_name = doc.display_name
            logging.info(f"Found document: {doc_display_name}")
        except Exception as e:
            logging.warning(f"Could not fetch document details: {e}")

        # Step 2: Find and Delete the underlying File (Level 1)
        file_deleted = False
        if doc_display_name:
            # Retry loop for file deletion
            for attempt in range(3):
                try:
                    found_file = None
                    for f in client.files.list():
                        if f.display_name == doc_display_name:
                            found_file = f
                            break
                    
                    if found_file:
                        logging.info(f"Found underlying file {found_file.name}. Deleting (Attempt {attempt+1})...")
                        client.files.delete(name=found_file.name)
                        logging.info("✅ Underlying file deleted.")
                        file_deleted = True
                        break # Success
                    else:
                        logging.warning(f"No underlying file found with display_name='{doc_display_name}'")
                        break # Nothing to delete
                except Exception as e:
                    logging.error(f"Error deleting file (Attempt {attempt+1}): {e}")
                    if "FAILED_PRECONDITION" in str(e):
                         logging.info("Waiting 3s before retry...")
                         time.sleep(3)
                    else:
                         # If it's another error, maybe persistent?
                         time.sleep(1)

        # Step 3: Delete the Document (Level 2)
        try:
            client.file_search_stores.documents.delete(name=document_name)
            logging.info(f"✅ Document connection deleted: {document_name}")
        except Exception as e:
            if "NOT_FOUND" in str(e) or "404" in str(e):
                logging.info("Document not found (already deleted?)")
            else:
                try:
                    import requests
                    api_key = os.environ.get('GOOGLE_API_KEY')
                    if not api_key:
                        api_key = getattr(client, 'api_key', None)
                        if not api_key and os.path.exists(CONFIG_PATH):
                            with open(CONFIG_PATH, 'r') as f:
                                api_key = json.load(f).get('api_key')
                    url = f"https://generativelanguage.googleapis.com/v1beta/{document_name}?force=true&key={api_key}"
                    res = requests.delete(url)
                    if res.status_code == 200:
                        logging.info(f"✅ Document {document_name} deleted via REST API (force=true).")
                    else:
                        if file_deleted:
                            logging.warning(f"Document delete failed but file was deleted. REST status {res.status_code}: {res.text}")
                        else:
                            raise Exception(f"REST API failed with {res.status_code}: {res.text}")
                except Exception as re:
                    if file_deleted:
                        logging.warning(f"Document delete error ignored after file deletion: {re}")
                    else:
                        raise e

        return jsonify({"status": "deleted", "message": "File and Document deleted successfully"})

    except Exception as e:
        logging.error(f"Error deleting file/document: {str(e)}", exc_info=True)
        return jsonify({
            "error": "Erro ao excluir arquivo. O sistema tentou desvincular o agente mas falhou.",
            "details": str(e)
        }), 500
    finally:
        if affected_agents:
            import logging
            logging.info("Restoring agent bindings...")
            update_agents_store_binding(store_name, 'bind', target_agents=affected_agents)

# ============================================================================
# SCRAPING ENDPOINTS
# ============================================================================

def process_scraping_task(task_id: str, urls: list, store_name: str, preview_only: bool = False, recursive: bool = False, max_pages: int = 1000):
    """
    Processa tarefa de scraping em background
    
    Args:
        task_id: ID da tarefa
        urls: Lista de URLs para processar
        store_name: Nome da store para upload
        preview_only: Se True, apenas retorna o conteúdo sem fazer upload
        recursive: Se True, segue links internos
        max_pages: Número máximo de páginas para visitar (por URL raiz)
    """
    import logging
    import tempfile
    
    logging.basicConfig(filename='debug.log', level=logging.DEBUG)
    
    try:
        if not SCRAPING_AVAILABLE:
            scraping_tasks[task_id]['status'] = 'error'
            scraping_tasks[task_id]['error'] = 'Serviço de scraping não disponível'
            return
        
        scraper = ScraperFactory()
        
        # Fila de URLs para processar: [(url, depth, root_url)]
        url_queue = [(url, 0, url) for url in urls]
        processed_urls = set()
        visited_count_per_root = {url: 0 for url in urls}
        
        scraping_tasks[task_id]['status'] = 'processing'
        scraping_tasks[task_id]['progress']['total'] = len(urls)
        
        # Limitador de segurança geral
        GLOBAL_MAX_PAGES = 500 
        total_processed_global = 0

        while url_queue:
            # Pega próxima URL
            current_url, depth, root_url = url_queue.pop(0)
            
            # Verifica se já foi processada
            if current_url in processed_urls:
                continue
                
            # Verifica limites
            if recursive:
                 if visited_count_per_root.get(root_url, 0) >= max_pages:
                     logging.info(f"Limite de páginas ({max_pages}) atingido para raiz: {root_url}")
                     continue
                 if total_processed_global >= GLOBAL_MAX_PAGES:
                     logging.info(f"Limite global de páginas ({GLOBAL_MAX_PAGES}) atingido.")
                     break
            
            try:
                # Atualiza progresso
                scraping_tasks[task_id]['progress']['completed'] = total_processed_global
                scraping_tasks[task_id]['progress']['current_url'] = current_url
                if len(url_queue) + total_processed_global > scraping_tasks[task_id]['progress']['total']:
                     scraping_tasks[task_id]['progress']['total'] = len(url_queue) + total_processed_global + 1
                
                logging.info(f"Scraping URL ({depth}): {current_url}")
                
                # Executa scraping
                markdown_content, filename, scraper_type, internal_links = scraper.scrape_url(current_url)
                
                processed_urls.add(current_url)
                total_processed_global += 1
                if recursive:
                    visited_count_per_root[root_url] = visited_count_per_root.get(root_url, 0) + 1
                    
                    # Adiciona novos links à fila
                    for link in internal_links:
                        if link not in processed_urls and link not in [u[0] for u in url_queue]:
                             url_queue.append((link, depth + 1, root_url))
                
                logging.info(f"Scraping concluído: {filename} (tipo: {scraper_type}, links: {len(internal_links)})")
                
                # Se for apenas preview, retorna o conteúdo e pula upload
                if preview_only:
                    scraping_tasks[task_id]['results'].append({
                        'url': current_url,
                        'status': 'success',
                        'filename': filename,
                        'file_uri': '',
                        'scraper_type': scraper_type,
                        'markdown_content': markdown_content,
                        'preview': True
                    })
                    continue

                # === BACKUP: Salva cópia permanente antes de enviar para RAG ===
                try:
                    from datetime import datetime
                    backup_base_dir = os.path.join(PROJECT_ROOT, 'dados', 'scraped_backup')
                    os.makedirs(backup_base_dir, exist_ok=True)
                    
                    # Organiza por store
                    store_folder_name = store_name.replace('fileSearchStores/', '') if store_name else 'sem_store'
                    store_backup_dir = os.path.join(backup_base_dir, store_folder_name)
                    os.makedirs(store_backup_dir, exist_ok=True)
                    
                    # Adiciona timestamp ao nome do arquivo
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    base_name, ext = os.path.splitext(filename)
                    backup_filename = f"{base_name}_{timestamp}{ext}"
                    backup_file_path = os.path.join(store_backup_dir, backup_filename)
                    
                    with open(backup_file_path, 'w', encoding='utf-8') as f:
                        f.write(markdown_content)
                    
                    logging.info(f"✅ Backup salvo em: {backup_file_path}")
                except Exception as backup_e:
                    logging.error(f"Erro ao salvar backup físico: {backup_e}")
                # === FIM DO BACKUP ===

                # Salva arquivo temporário
                temp_dir = tempfile.gettempdir()
                temp_file_path = os.path.join(temp_dir, filename)
                
                with open(temp_file_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                
                logging.info(f"Arquivo salvo temporariamente: {temp_file_path}")
                
                # Upload para Google Files API
                client = get_genai_client()
                if not client:
                    raise Exception("API Key não configurada")
                
                logging.info(f"Fazendo upload para Google Files API: {filename}")
                
                file_uri = ""
                
                if store_name:
                    logging.info(f"Fazendo upload diretamente para store: {store_name}")
                    # Usa upload_to_file_search_store para compatibilidade
                    op = client.file_search_stores.upload_to_file_search_store(
                        file=temp_file_path,
                        file_search_store_name=store_name,
                        config={'mime_type': 'text/markdown', 'display_name': filename}
                    )
                    # URI real não é retornado imediatamente, usamos placeholder informativo
                    file_uri = f"store://{store_name}/{filename}"
                    logging.info(f"Upload iniciado para store: {store_name}")
                else:
                    uploaded_file = client.files.upload(
                        file=temp_file_path,
                        config={'mime_type': 'text/markdown', 'display_name': filename}
                    )
                    file_uri = uploaded_file.uri
                    logging.info(f"Upload concluído: {file_uri}")
                
                # === NEW: Sync to Local RAG (ChromaDB) ===
                try:
                    if store_name:
                        chroma_manager.index_document(
                            content=markdown_content,
                            store_name=store_name,
                            filename=filename
                        )
                except Exception as chroma_e:
                    logging.error(f"Failed to sync scraping result to ChromaDB: {chroma_e}")

                # Remove arquivo temporário
                try:
                    os.remove(temp_file_path)
                except:
                    pass
                
                # Adiciona resultado
                scraping_tasks[task_id]['results'].append({
                    'url': current_url,
                    'status': 'success',
                    'filename': filename,
                    'file_uri': file_uri,
                    'scraper_type': scraper_type,
                    'markdown_content': markdown_content if len(markdown_content) < 100000 else None # Opcional: limitar tamanho no retorno final se não for preview
                })
                
            except Exception as e:
                logging.error(f"Erro ao processar {current_url}: {str(e)}", exc_info=True)
                scraping_tasks[task_id]['results'].append({
                    'url': current_url,
                    'status': 'error',
                    'error': str(e)
                })
        
        # Finaliza tarefa
        scraping_tasks[task_id]['status'] = 'completed'
        scraping_tasks[task_id]['progress']['completed'] = total_processed_global
        scraping_tasks[task_id]['progress']['current_url'] = ''
        
        logging.info(f"Tarefa de scraping concluída: {task_id}")
        
    except Exception as e:
        logging.error(f"Erro fatal na tarefa de scraping {task_id}: {str(e)}", exc_info=True)
        scraping_tasks[task_id]['status'] = 'error'
        scraping_tasks[task_id]['error'] = str(e)

@app.route('/api/scraping/process', methods=['POST'])
def api_scraping_process():
    """
    Inicia processamento de scraping de URLs
    
    Entrada JSON:
    {
        "urls": ["https://example.com", ...],
        "store_name": "fileSearchStores/xyz" (opcional)
    }
    
    Retorna:
    {
        "task_id": "uuid",
        "total_urls": 2,
        "status": "processing"
    }
    """
    import logging
    import uuid
    import threading
    from urllib.parse import urlparse
    
    logging.basicConfig(filename='debug.log', level=logging.DEBUG)
    
    if not SCRAPING_AVAILABLE:
        return jsonify({"error": "Serviço de scraping não disponível"}), 503
    
    try:
        data = request.json
        urls = data.get('urls', [])
        store_name = data.get('store_name', '')
        preview_only = data.get('preview_only', False)
        recursive = data.get('recursive', False)
        
        # Validação
        if not urls or not isinstance(urls, list):
            return jsonify({"error": "URLs inválidas"}), 400
        
        # Valida formato das URLs
        valid_urls = []
        for url in urls:
            url = url.strip()
            if not url:
                continue
            
            # Adiciona https:// se não tiver protocolo
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Valida URL
            try:
                parsed = urlparse(url)
                if parsed.scheme and parsed.netloc:
                    valid_urls.append(url)
            except:
                pass
        
        if not valid_urls:
            return jsonify({"error": "Nenhuma URL válida fornecida"}), 400
        
        # Cria tarefa
        task_id = str(uuid.uuid4())
        scraping_tasks[task_id] = {
            "status": "initializing",
            "progress": {
                "completed": 0,
                "total": len(valid_urls),
                "current_url": ""
            },
            "results": [],
            "error": None
        }
        
        logging.info(f"Iniciando tarefa de scraping {task_id} com {len(valid_urls)} URLs (Preview: {preview_only})")
        
        # Inicia thread em background
        thread = threading.Thread(
            target=process_scraping_task,
            args=(task_id, valid_urls, store_name, preview_only, recursive)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "task_id": task_id,
            "total_urls": len(valid_urls),
            "status": "processing"
        })
        
    except Exception as e:
        logging.error(f"Erro ao iniciar scraping: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/scraping/confirm_upload', methods=['POST'])
def api_scraping_confirm_upload():
    """
    Confirma e realiza o upload de um conteúdo markdown para a store
    """
    import tempfile
    import logging
    from datetime import datetime
    
    # Configure logging to file
    logging.basicConfig(filename='debug.log', level=logging.DEBUG)
    
    try:
        data = request.json
        markdown_content = data.get('markdown_content')
        filename = data.get('filename')
        store_name = data.get('store_name')
        
        logging.info(f"Recebendo upload confirmado: {filename} para store {store_name}")
        
        if not markdown_content or not filename or not store_name:
            logging.error("Dados incompletos para upload")
            return jsonify({"error": "Dados incompletos"}), 400
        
        # === BACKUP: Salva cópia permanente antes de enviar para RAG ===
        backup_base_dir = os.path.join(os.path.dirname(__file__), '..', 'dados', 'scraped_backup')
        os.makedirs(backup_base_dir, exist_ok=True)
        
        # Organiza por store
        store_backup_dir = os.path.join(backup_base_dir, store_name.replace('fileSearchStores/', ''))
        os.makedirs(store_backup_dir, exist_ok=True)
        
        # Adiciona timestamp ao nome do arquivo para evitar sobrescrever
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name, ext = os.path.splitext(filename)
        backup_filename = f"{base_name}_{timestamp}{ext}"
        backup_file_path = os.path.join(store_backup_dir, backup_filename)
        
        # Salva backup
        with open(backup_file_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        logging.info(f"✅ Backup salvo em: {backup_file_path}")
        # === FIM DO BACKUP ===
            
        # Salva arquivo temporário para upload
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, filename)
        
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
            
        # Upload para Google Files API e Store
        client = get_genai_client()
        if not client:
            raise Exception("API Key não configurada")
            
        logging.info(f"Fazendo upload para store: {store_name}")
        
        # Usa upload_to_file_search_store para compatibilidade
        op = client.file_search_stores.upload_to_file_search_store(
            file=temp_file_path,
            file_search_store_name=store_name,
            config={'mime_type': 'text/markdown', 'display_name': filename}
        )
        
        logging.info(f"Operação de upload iniciada: {op}")
        
        # Remove arquivo temporário
        try:
            os.remove(temp_file_path)
        except:
            pass
            
        return jsonify({
            "status": "success",
            "message": "Arquivo adicionado à base e salvo em backup físico com sucesso"
        })
        
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        logging.error(f"Erro no upload confirmado: {error_msg}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/scraping/status/<task_id>', methods=['GET'])
def api_scraping_status(task_id):
    """
    Retorna status de uma tarefa de scraping
    
    Retorna:
    {
        "task_id": "uuid",
        "status": "processing" | "completed" | "error",
        "progress": {
            "completed": 1,
            "total": 2,
            "current_url": "https://example.com"
        },
        "results": [...],
        "error": "..." (se houver)
    }
    """
    task = scraping_tasks.get(task_id)
    if not task:
        return jsonify({"error": "Tarefa não encontrada"}), 404
    
    return jsonify({
        "task_id": task_id,
        **task
    })

@app.route('/api/scraping/cancel/<task_id>', methods=['POST'])
def api_scraping_cancel(task_id):
    """
    Cancela uma tarefa de scraping em andamento
    
    Nota: Apenas marca como cancelada, não interrompe thread
    """
    task = scraping_tasks.get(task_id)
    if not task:
        return jsonify({"error": "Tarefa não encontrada"}), 404
    
    if task['status'] == 'processing':
        task['status'] = 'cancelled'
        return jsonify({"status": "cancelled"})
    
    return jsonify({"status": task['status']})

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.errorhandler(500)
def handle_500_error(e):
    if request.path.startswith('/api/'):
        return jsonify({
            "error": "Erro interno do servidor", 
            "details": str(e)
        }), 500
    return "Internal Server Error", 500

@app.errorhandler(404)
def handle_404_error(e):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Endpoint não encontrado"}), 404
    return "Not Found", 404

if __name__ == '__main__':
    # Use uvicorn directly to run the app as ASGI for better async support on Windows
    import uvicorn
    from asgiref.wsgi import WsgiToAsgi
    asgi_app = WsgiToAsgi(app)
    uvicorn.run(asgi_app, host='127.0.0.1', port=3001)
    # app.run(host='127.0.0.1', port=3001, debug=True)
