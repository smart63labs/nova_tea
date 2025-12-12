import os
import sys
import json
import importlib
import asyncio
import time

# Setup paths and load config/env BEFORE other imports
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

CONFIG_PATH = os.path.join(PROJECT_ROOT, 'dados', 'config.json')
AGENTS_DIR = os.path.join(PROJECT_ROOT, 'dados', 'agentes')
ENV_PATH = os.path.join(PROJECT_ROOT, 'tea', '.env')

# Load Key from JSON first to ensure it's in env before any google/agent import
if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            c = json.load(f)
            if c.get('api_key'):
                os.environ['GOOGLE_API_KEY'] = c.get('api_key')
    except:
        pass

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from google.genai import types, Client
from google.adk.runners import InMemoryRunner

tea_agent = importlib.import_module('tea.agent')

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
        "name": "TIA_Orquestrador",
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
    global tea_agent
    tea_agent = importlib.reload(tea_agent)

def build_runner():
    return InMemoryRunner(agent=tea_agent.root_agent if hasattr(tea_agent, 'root_agent') else tea_agent.agent, app_name='tia')

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev')

settings = load_settings()
runner = build_runner()
session_id = runner.session_service.create_session_sync(app_name='tia', user_id='user').id

def list_agents():
    ents = getattr(tea_agent, 'entidades', [])
    return [(tea_agent.normalize_name(e), e) for e in ents]

def get_agent_name_by_id(agent_id):
    raw = (agent_id or '').strip()
    if raw:
        m = (getattr(tea_agent, 'sub_agents_map', {}) or {})
        if raw in m:
            return raw, None
        norm = tea_agent.normalize_name(raw)
        if norm in m:
            return norm, None
    for aid, title in list_agents():
        if aid == raw:
            return aid, title
        if raw and tea_agent.normalize_name(title) == norm:
            return aid, title
    return None, None

@app.route('/')
def index():
    return redirect(url_for('chat'))

@app.route('/api/agents', methods=['GET'])
def api_agents_list():
    agents = list_agents()
    return jsonify([{'id': a[0], 'name': a[1]} for a in agents])

@app.route('/api/agents/apply_citation_policy', methods=['POST'])
def api_agents_apply_citation_policy():
    import logging
    if not os.path.exists(AGENTS_DIR):
        return jsonify({"updated": 0, "message": "Agentes não encontrados"}), 404
    citation_header = "POLÍTICA DE CITAÇÕES"
    citation_block = (
        "POLÍTICA DE CITAÇÕES (CONDICIONAL):\n"
        "1. Base de Conhecimento (File Search): NÃO inclua URL na fonte. Cite como: "
        "\"Fonte: [Nome do documento da base] — [Capítulo/Seção/Artigo/Parágrafo/Inciso/Alínea/Página, quando disponível]\" "
        "e indique o trecho/localização onde a informação foi encontrada.\n"
        "2. Legislação: Informe número da lei, artigo, parágrafo (§), inciso e alínea; "
        "indique a localização no documento (Capítulo/Seção/Título/Página) quando possível.\n"
        "3. Pesquisa na Web: Inclua a URL oficial e aplique a regra 2 quando se tratar de legislação."
    )
    updated = 0
    for fname in os.listdir(AGENTS_DIR):
        if not fname.endswith('.json'):
            continue
        fpath = os.path.join(AGENTS_DIR, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            sp = (data.get("system_prompt") or "").strip()
            up = (data.get("user_prompt") or "").strip()
            changed = False
            if citation_header not in sp:
                sp = (sp + "\n\n" + citation_block).strip()
                changed = True
            if "Regras de Citação:" not in up:
                up = (
                    up + "\n\nRegras de Citação:\n"
                    "- Se usou a Base: Fonte: [Nome do documento] — [Capítulo/Seção/Artigo/Parágrafo/Inciso/Alínea/Página, quando disponível].\n"
                    "- Se for legislação: inclua número da lei e referências a artigo, parágrafo (§), inciso e alínea, com localização no documento.\n"
                    "- Se usou Web: inclua a URL oficial."
                )
                changed = True
            if changed:
                data["system_prompt"] = sp
                data["user_prompt"] = up
                with open(fpath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                updated += 1
        except Exception as e:
            logging.error(f"Falha ao atualizar {fname}: {e}")
            continue
    try:
        reload_agents()
        global runner, session_id
        runner = build_runner()
        session_id = runner.session_service.create_session_sync(app_name='tia', user_id='user').id
    except Exception as e:
        logging.error(f"Falha ao recarregar agentes após aplicar política: {e}")
    return jsonify({"updated": updated})

@app.route('/chat', methods=['GET'])
def chat():
    agents = list_agents()
    return render_template('chat.html', agents=agents)

@app.route('/api/chat', methods=['POST'])
async def api_chat():
    target = request.form.get('target', 'auto')
    message = request.form.get('message', '').strip()
    cfg = load_settings()
    if target == 'auto':
        # Hot-reload system prompt for orchestrator
        root_sys = (cfg.get('root') or {}).get('system_prompt', '')
        if root_sys and hasattr(tea_agent, 'root_agent'):
             tea_agent.root_agent.instruction = root_sys

        up = (cfg.get('root') or {}).get('user_prompt', '')
        final_message = (up + '\n\n' + message).strip() if up else message
        used_runner = runner
    else:
        aid, title = get_agent_name_by_id(target)
        if not aid:
            return jsonify({"error": "agent_not_found"}), 404
        up = ((cfg.get('agents') or {}).get(aid) or {}).get('user_prompt', '')
        final_message = (up + '\n\n' + message).strip() if up else message
        used_agent = (getattr(tea_agent, 'sub_agents_map', {}) or {}).get(aid)
        if not used_agent:
            return jsonify({"error": "agent_unavailable"}), 404
        
        # Hot-reload instruction for specialist agent
        spec_sys = ((cfg.get('agents') or {}).get(aid) or {}).get('system_prompt', '')
        if spec_sys:
             used_agent.instruction = spec_sys

        used_runner = InMemoryRunner(agent=used_agent, app_name='tia')
        used_runner.session_service.create_session_sync(app_name='tia', user_id='user', session_id=session_id)
    events = []
    user_content = types.Content(role='user', parts=[types.Part(text=final_message)])
    
    # Executar o fluxo
    max_retries = 5
    retry_delay = 10

    for attempt in range(max_retries):
        try:
            events = []
            async for event in used_runner.run_async(user_id='user', session_id=session_id, new_message=user_content):
                events.append(event)
            break
        except Exception as e:
            print(f"Error in run_async (attempt {attempt+1}/{max_retries}): {e}")
            error_str = str(e)
            
            is_transient = "UNAVAILABLE" in error_str or "503" in error_str or "RESOURCE_EXHAUSTED" in error_str or "429" in error_str
            
            if is_transient and attempt < max_retries - 1:
                wait_time = retry_delay * (attempt + 1)
                print(f"Transient error. Waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue

            if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
                return jsonify({
                    "reply": "⚠️ **Sistema Sobrecarregado (Cota)**\n\nO limite de uso gratuito da Inteligência Artificial foi atingido. Por favor, aguarde cerca de 1 minuto e tente novamente.\n\n*(Erro 429: Resource Exhausted)*"
                })
            if "UNAVAILABLE" in error_str or "503" in error_str:
                return jsonify({
                    "reply": "⚠️ **Serviço Temporariamente Indisponível**\n\nOs servidores da IA (Google Gemini) estão sobrecarregados no momento. Por favor, tente novamente em alguns instantes.\n\n*(Erro 503: Model Overloaded)*"
                })
            return jsonify({
                "reply": "Desculpe, ocorreu um erro ao processar sua mensagem.",
                "error": str(e)
            })

    text = ''
    for ev in events[::-1]:
        if ev.is_final_response():
            if ev.content and ev.content.parts:
                parts = [p.text for p in ev.content.parts if getattr(p, 'text', None) and not getattr(p, 'thought', False)]
                text = ''.join(parts)
                break
    if not text:
        for ev in events[::-1]:
            if ev.content and ev.content.parts:
                parts = [p.text for p in ev.content.parts if getattr(p, 'text', None)]
                if parts:
                    text = ''.join(parts)
                    break
    return jsonify({"reply": text or ""})

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
            cfg['agents'] = data['agents']
            
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
        
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(current_data, f, ensure_ascii=False, indent=2)
        
    reload_agents()
    global runner, session_id
    runner = build_runner()
    session_id = runner.session_service.create_session_sync(app_name='tia', user_id='user').id
    
    return jsonify({"status": "success"})

@app.route('/settings/model', methods=['GET', 'POST'])
def settings_model():
    if request.method == 'POST':
        model = request.form.get('model', '').strip()
        key = request.form.get('api_key', '').strip()
        cfg = load_settings()
        if model:
            cfg['model'] = model
        if key:
            cfg['api_key'] = key
        save_settings(cfg)
        reload_agents()
        global runner, session_id
        runner = build_runner()
        session_id = runner.session_service.create_session_sync(app_name='tia', user_id='user').id
        return redirect(url_for('settings_model'))
    cfg = load_settings()
    current_key = cfg.get('api_key', '')
    return render_template('settings_model.html', model=cfg.get('model', ''), api_key=current_key)

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
            valid_names = set(s['name'] for s in stores)
            clean_orphaned_stores(valid_names)
            enforce_store_ownership(stores)
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
        
        # Upload directly to File Search Store to preserve display_name
        logging.info(f"Uploading file '{display_name}' directly to File Search Store {store_name}...")
        op = client.file_search_stores.upload_to_file_search_store(
            file=local_path,
            file_search_store_name=store_name,
            config={'display_name': display_name}
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
        return jsonify({"status": "uploaded", "message": "Arquivo enviado e indexado com nome original."})
        
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

@app.route('/favicon.ico')
def favicon():
    return '', 204

if __name__ == '__main__':
    # Use uvicorn directly to run the app as ASGI for better async support on Windows
    import uvicorn
    from asgiref.wsgi import WsgiToAsgi
    asgi_app = WsgiToAsgi(app)
    uvicorn.run(asgi_app, host='127.0.0.1', port=3001)
    # app.run(host='127.0.0.1', port=3001, debug=True)
