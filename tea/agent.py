from google.adk.agents.llm_agent import Agent
from google.adk.tools.google_search_tool import GoogleSearchTool
from google.adk.tools.agent_tool import AgentTool
import re
import unicodedata
import os
import json

class TeaAgent(Agent):
    """Custom Agent class to align with 'tea' app name."""
    pass

# Inicializa a ferramenta de busca
search_tool = GoogleSearchTool()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(os.path.dirname(BASE_DIR), 'config', 'settings.json')

def _load_settings():
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
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

for entidade in entidades:
    agent_id = normalize_name(entidade)
    agent_cfg = (_settings.get('agents') or {}).get(agent_id) or {}
    model_name = _settings.get('model', 'gemini-2.5-flash')
    inst = agent_cfg.get('system_prompt') or (
        f'Você é um agente especialista em {entidade}. Atue EXCLUSIVAMENTE no contexto do Estado do Tocantins (Brasil). Não responda com informações federais ou de outros estados. Quando fizer buscas, inclua "Tocantins" e priorize fontes oficiais do Governo do Tocantins (portais *.to.gov.br, Diário Oficial do Tocantins, secretarias). Se a pergunta não for do escopo do Tocantins, explique o escopo e oriente a fonte oficial correta. Responda sempre em PT-BR.'
    )
    sub_agent = TeaAgent(
        model=model_name,
        name=agent_id,
        description=f'Especialista em {entidade}.',
        instruction=inst,
        tools=[search_tool]
    )
    agent_tool = AgentTool(agent=sub_agent)
    sub_agent_tools.append(agent_tool)
    sub_agents_map[agent_id] = sub_agent

# Agente Orquestrador
root_agent = TeaAgent(
    model=_settings.get('model', 'gemini-2.5-flash'),
    name='TEA_Orquestrador',
    description='Agente principal TEA que orquestra o atendimento.',
    instruction=(
        (_settings.get('root') or {}).get('system_prompt') or 'Você é o TEA, assistente do Governo do Tocantins. Sempre considere EXCLUSIVAMENTE o contexto do Estado do Tocantins (Brasil). Delegue para o agente especialista mais adequado usando as ferramentas disponíveis. Nas buscas, priorize fontes oficiais do Tocantins e inclua "Tocantins" nas consultas. Se a dúvida não for do escopo estadual, explique o escopo e oriente corretamente. Responda sempre em PT-BR e seja cortês.'
    ),
    tools=sub_agent_tools
)
