from google.adk.agents.llm_agent import Agent
from google.adk.tools.google_search_tool import GoogleSearchTool
from google.adk.tools.agent_tool import AgentTool
from tea.file_search_tool import FileSearchTool

import re
import unicodedata
import os
import json

class TiaAgent(Agent):
    """Custom Agent class to align with 'tia' app name."""
    pass

# Inicializa a ferramenta de busca
search_tool = GoogleSearchTool()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Mudança para ler de dados/config.json
CONFIG_PATH = os.path.join(os.path.dirname(BASE_DIR), 'dados', 'config.json')
AGENTS_DIR = os.path.join(os.path.dirname(BASE_DIR), 'dados', 'agentes')

def _load_settings():
    cfg = {}
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
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
    
    # Configure tools based on settings
    current_tools = []
    
    # 2. File Search (RAG) - Priority over Web Search due to API conflict
    fs_stores = agent_cfg.get('file_search_stores', [])
    has_rag = False
    if fs_stores and len(fs_stores) > 0:
        # Ensure we are passing strings
        valid_stores = [str(s) for s in fs_stores if s]
        if valid_stores:
            rag_tool = FileSearchTool(file_search_store_names=valid_stores)
            current_tools.append(rag_tool)
            has_rag = True

    # 1. Web Search
    enable_web = agent_cfg.get('enable_web_search', True)
    if enable_web:
        # User requested to keep Web Search enabled by default even with RAG
        # Warning: Some API versions might conflict, but we enable it as requested.
        current_tools.append(search_tool)
        if has_rag:
            pass # No longer disabling logic

    sub_agent = TiaAgent(
        model=model_name,
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
root_model = _settings.get('model', 'gemini-2.5-flash')

root_inst = ((_settings.get('root') or {}).get('system_prompt', ''))
root_agent = TiaAgent(
    model=root_model,
    name='TIA_Orquestrador',
    description='Agente principal TIA que orquestra o atendimento.',
    instruction=root_inst,
    tools=sub_agent_tools
)

