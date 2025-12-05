import os
import sys
import json
import importlib
import asyncio
import time
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import time
from dotenv import load_dotenv
from google.genai import types
from google.adk.runners import InMemoryRunner

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
tea_agent = importlib.import_module('tea.agent')
CONFIG_PATH = os.path.join(PROJECT_ROOT, 'config', 'settings.json')
ENV_PATH = os.path.join(PROJECT_ROOT, 'tea', '.env')

def load_settings():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"model": "gemini-2.5-flash", "agents": {}, "root": {"system_prompt": "", "user_prompt": ""}}

def save_settings(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

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
    return InMemoryRunner(agent=tea_agent.root_agent if hasattr(tea_agent, 'root_agent') else tea_agent.agent, app_name='tea')

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev')

load_dotenv(dotenv_path=ENV_PATH)
settings = load_settings()
runner = build_runner()
session_id = runner.session_service.create_session_sync(app_name='tea', user_id='user').id

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

@app.route('/chat', methods=['GET'])
def chat():
    agents = list_agents()
    return render_template('chat.html', agents=agents)

@app.route('/api/chat', methods=['POST'])
def api_chat():
    target = request.form.get('target', 'auto')
    message = request.form.get('message', '').strip()
    cfg = load_settings()
    if target == 'auto':
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
        used_runner = InMemoryRunner(agent=used_agent, app_name='tea')
        used_runner.session_service.create_session_sync(app_name='tea', user_id='user', session_id=session_id)
    events = []
    user_content = types.Content(role='user', parts=[types.Part(text=final_message)])
    
    try:
        for event in used_runner.run(user_id='user', session_id=session_id, new_message=user_content):
            events.append(event)
    except Exception as e:
        print(f"Error in run: {e}")
        return jsonify({"error": str(e)}), 500

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

@app.route('/settings/model', methods=['GET', 'POST'])
def settings_model():
    if request.method == 'POST':
        model = request.form.get('model', '').strip()
        key = request.form.get('api_key', '').strip()
        cfg = load_settings()
        if model:
            cfg['model'] = model
        save_settings(cfg)
        if key:
            set_env_key(key)
        reload_agents()
        global runner, session_id
        runner = build_runner()
        session_id = runner.session_service.create_session_sync(app_name='tea', user_id='user').id
        return redirect(url_for('settings_model'))
    cfg = load_settings()
    current_key = os.getenv('GOOGLE_API_KEY', '')
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
        session_id = runner.session_service.create_session_sync(app_name='tea', user_id='user').id
        return redirect(url_for('agent_detail', agent_id=agent_id))
    return render_template('agent_detail.html', agent_id=aid, title=title, system_prompt=rec.get('system_prompt', ''), user_prompt=rec.get('user_prompt', ''))

@app.route('/favicon.ico')
def favicon():
    return '', 204

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
