from google.adk.agents.llm_agent import Agent
from google.adk.tools.google_search_tool import GoogleSearchTool
from google.adk.tools.agent_tool import AgentTool
from assistente.file_search_tool import FileSearchTool
from assistente.hybrid_search_tool import HybridSearchTool
from assistente.local_llm import LocalLLM
from google.adk.models.lite_llm import LiteLlm

import re
import unicodedata
import os
import json
from google.adk.utils.model_name_utils import is_gemini_model

class AssistenteAgent(Agent):
    """Custom Agent class to align with 'assistente' app name."""
    pass

# Inicializa a ferramenta de busca
search_tool = GoogleSearchTool()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Mudança para ler de dados/config.json
CONFIG_PATH = os.path.join(os.path.dirname(BASE_DIR), 'dados', 'config.json')
MODELS_PATH = os.path.join(os.path.dirname(BASE_DIR), 'dados', 'models.json')
AGENTS_DIR = os.path.join(os.path.dirname(BASE_DIR), 'dados', 'agentes')

def _load_settings():
    cfg = {}
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
    except Exception:
        pass
    
    # Load models config to check active model
    try:
        if os.path.exists(MODELS_PATH):
            with open(MODELS_PATH, 'r', encoding='utf-8') as f:
                models_cfg = json.load(f)
                if models_cfg.get('active_model_id'):
                    cfg['model'] = models_cfg.get('active_model_id')
                
                # Store full model info for lookup
                cfg['models_info'] = {m['id']: m for m in models_cfg.get('models', [])}
    except Exception:
        pass
        
    # Load orchestrator config from orquestrador.json
    try:
        orq_path = os.path.join(AGENTS_DIR, 'orquestrador.json')
        if os.path.exists(orq_path):
            with open(orq_path, 'r', encoding='utf-8') as f:
                root_data = json.load(f)
                cfg['root'] = {
                    'system_prompt': root_data.get('system_prompt', ''),
                    'user_prompt': root_data.get('user_prompt', '')
                }
    except Exception:
        pass
        
    return cfg

def _load_agent_config(agent_id):
    try:
        agent_path = os.path.join(AGENTS_DIR, f'{agent_id}.json')
        if os.path.exists(agent_path):
            with open(agent_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

_settings = _load_settings()

def normalize_name(name):
    """Normaliza o nome para ser usado como ID do agente (sem acentos, minúsculo, snake_case)."""
    n = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('utf-8')
    n = n.lower()
    n = re.sub(r'[^a-z0-9]+', '_', n)
    n = n.strip('_')
    return n[:60]  # Limita a 60 caracteres para evitar erro de limite da API (max 64)

# Lista de entidades para criar agentes
entidades = [
    # Secretarias
    "Casa Civil",
    "Casa Militar",
    "Controladoria-Geral do Estado",
    "Corpo de Bombeiros Militar",
    "Polícia Militar",
    "Procuradoria-Geral do Estado",
    "Secretaria Executiva da Governadoria",
    "Secretaria Extraordinária de Desenvolvimento da Região Metropolitana de Palmas",
    "Secretaria Extraordinária de Participações Sociais e Políticas de Governo",
    "Secretaria Extraordinária de Representação em Brasília",
    "Secretaria da Administração",
    "Secretaria da Agricultura e Pecuária",
    "Secretaria da Cidadania e Justiça",
    "Secretaria da Comunicação",
    "Secretaria da Cultura",
    "Secretaria da Educação",
    "Secretaria da Fazenda",
    "Secretaria da Igualdade Racial",
    "Secretaria da Indústria, Comércio e Serviços",
    "Secretaria da Mulher",
    "Secretaria da Pesca e Aquicultura",
    "Secretaria da Saúde",
    "Secretaria da Segurança Pública",
    "Secretaria das Cidades, Habitação e Desenvolvimento Regional",
    "Secretaria de Parcerias e Investimentos",
    "Secretaria do Meio Ambiente e Recursos Hídricos",
    "Secretaria do Planejamento e Orçamento",
    "Secretaria do Trabalho e Desenvolvimento Social",
    "Secretaria do Turismo",
    "Secretaria dos Esportes e Juventude",
    "Secretaria dos Povos Originários e Tradicionais",
    
    # Autarquias
    "Agência Tocantinense de Regulação, Controle e Fiscalização de Serviços Públicos",
    "Agência Tocantinense de Saneamento",
    "Agência de Defesa Agropecuária",
    "Agência de Fomento",
    "Agência de Metrologia",
    "Agência de Mineração",
    "Agência de Tecnologia da Informação",
    "Agência de Transportes, Obras e Infraestrutura",
    "Companhia Imobiliária de Participações, Investimentos e Parcerias",
    "Departamento Estadual de Trânsito",
    "Fundação de Amparo à Pesquisa",
    "Instituto Natureza do Tocantins",
    "Instituto de Desenvolvimento Rural",
    "Instituto de Gestão Previdenciária",
    "Instituto de Terras do Estado do Tocantins",
    "Junta Comercial",
    "Universidade Estadual do Tocantins",
    
    # Sites especiais
    "CLUBE DE BENEFÍCIOS",
    "Carteira de identificação da pessoa autista",
    "Diário Oficial",
    "ESSA TERRA É NOSSA",
    "Observatório do Lago",
    "Observatório do Turismo",
    "PROGRAMA VALE GÁS",
    "Turismo",
    "Zoneamento Ecológico Econômico do Tocantins"
]

sub_agent_tools = []
sub_agents_map = {}

# Ensure agents directory exists
os.makedirs(AGENTS_DIR, exist_ok=True)

for entidade in entidades:
    agent_id = normalize_name(entidade)
    
    # Load specific agent config or create default if not exists
    agent_cfg = _load_agent_config(agent_id)
    
    model_name = _settings.get('model', 'gemini-2.5-flash')

    # Determine if local model or LiteLLM model
    model_instance = model_name
    models_info = _settings.get('models_info', {})
    if model_name in models_info:
        m_info = models_info[model_name]
        m_type = m_info.get('type', '')
        
        if m_type.startswith('local_'):
            endpoint = m_info.get('endpoint', 'http://localhost:12434/v1')
            model_hash = m_info.get('model_hash')  # Get the actual model identifier
            model_instance = LocalLLM(
                model=model_name, 
                endpoint=endpoint,
                model_hash=model_hash  # Pass model_hash to use in API calls
            )
        elif m_type == 'litellm' or m_type == 'litellm_local':
            # Configurar chave de API se necessário
            api_key = m_info.get('api_key')
            api_key_env = m_info.get('api_key_env')
            m_name = m_info.get('model_name', model_name)
            
            if api_key:
                if not api_key_env:
                    if 'groq' in m_name: api_key_env = 'GROQ_API_KEY'
                    elif 'deepseek' in m_name: api_key_env = 'DEEPSEEK_API_KEY'
                    elif 'openrouter' in m_name: api_key_env = 'OPENROUTER_API_KEY'
                    else: api_key_env = 'DEEPSEEK_API_KEY'
                os.environ[api_key_env] = api_key
            
            kwargs = {
                "model": m_info.get('model_name', model_name),
                "timeout": 120,
                "max_retries": 5
            }
            if m_info.get('api_base'):
                kwargs["api_base"] = m_info.get('api_base')
                
            model_instance = LiteLlm(**kwargs)
    
    inst = agent_cfg.get('system_prompt', '')
    
    # If config didn't exist, create it with default values
    if not agent_cfg:
        try:
            with open(os.path.join(AGENTS_DIR, f'{agent_id}.json'), 'w', encoding='utf-8') as f:
                json.dump({
                    "name": entidade,
                    "system_prompt": "",
                    "user_prompt": "",
                    "enabled": True
                }, f, ensure_ascii=False, indent=2)
        except:
            pass

    # Check if enabled (default to True if not specified)
    is_enabled = agent_cfg.get('enabled', True)
    is_gemini = is_gemini_model(model_name)
    
    # Configure tools based on settings
    current_tools = []

    # Get settings based on model type (with legacy fallback)
    if is_gemini:
        enable_web = agent_cfg.get('gemini_enable_web', agent_cfg.get('enable_web_search', True))
        fs_stores = agent_cfg.get('gemini_file_search_stores', agent_cfg.get('file_search_stores', []))
    else:
        enable_web = agent_cfg.get('others_enable_web', agent_cfg.get('enable_web_search', False))
        fs_stores = agent_cfg.get('others_file_search_stores', agent_cfg.get('file_search_stores', []))

    # Configurar Busca Híbrida (RAG + Web Fallback)
    # Sempre usamos HybridSearchTool para evitar conflitos no Gemini
    # e permitir o fallback solicitado pelo usuário.
    h_search = HybridSearchTool(
        file_search_store_names=fs_stores,
        enable_web=enable_web
    )
    current_tools.append(h_search)



    sub_agent = AssistenteAgent(
        model=model_instance,
        name=agent_id,
        description=f'Especialista em {entidade}.',
        instruction=inst,
        tools=current_tools
    )
    
    sub_agents_map[agent_id] = sub_agent
    
    # Only add to tools list if enabled
    if is_enabled:
        agent_tool = AgentTool(agent=sub_agent)
        sub_agent_tools.append(agent_tool)

# Agente Orquestrador
root_model_name = _settings.get('model', 'gemini-2.5-flash')
root_model_instance = root_model_name
models_info = _settings.get('models_info', {})
if root_model_name in models_info:
    m_info = models_info[root_model_name]
    m_type = m_info.get('type', '')
    
    if m_type.startswith('local_'):
        endpoint = m_info.get('endpoint', 'http://localhost:12434/v1')
        model_hash = m_info.get('model_hash')
        root_model_instance = LocalLLM(model=root_model_name, endpoint=endpoint, model_hash=model_hash)
    elif m_type == 'litellm' or m_type == 'litellm_local':
        # Configurar chave de API se necessário
        api_key = m_info.get('api_key')
        api_key_env = m_info.get('api_key_env')
        m_name = m_info.get('model_name', root_model_name)

        if api_key:
            # Se não houver env_var explícito, tenta detectar pelo nome
            if not api_key_env:
                if 'groq' in m_name: api_key_env = 'GROQ_API_KEY'
                elif 'deepseek' in m_name: api_key_env = 'DEEPSEEK_API_KEY'
                elif 'openrouter' in m_name: api_key_env = 'OPENROUTER_API_KEY'
                else: api_key_env = 'DEEPSEEK_API_KEY' # Default fallback
            
            os.environ[api_key_env] = api_key
        
        kwargs = {
            "model": m_name,
            "timeout": 120,
            "max_retries": 5
        }
        if m_info.get('api_base'):
            kwargs["api_base"] = m_info.get('api_base')
            
        root_model_instance = LiteLlm(**kwargs)

root_inst = ((_settings.get('root') or {}).get('system_prompt', ''))
root_agent = AssistenteAgent(
    model=root_model_instance,
    name='ASSISTENTE_Orquestrador',
    description='Agente principal Assistente que orquestra o atendimento.',
    instruction=root_inst,
    tools=sub_agent_tools
)

