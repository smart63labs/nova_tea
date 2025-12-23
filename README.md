# TIA: Tocantins Inteligência Artificial 🚀

A **TIA (Tocantins Inteligência Artificial)** é uma infraestrutura multi-agente robusta, projetada para servir como o ponto central de interação entre o cidadão e o Governo do Estado do Tocantins. Diferente de chatbots convencionais, a TIA utiliza uma arquitetura de orquestração dinâmica que permite a expansão modular de competências através de agentes especialistas independentes.

---

## �️ Arquitetura e Tecnologias

O sistema é dividido em três camadas principais, garantindo escalabilidade, fidelidade de dados e flexibilidade de modelos.

### 1. Frontend: Experiência do Usuário (UX)
Construído com tecnologias modernas para oferecer uma interface de alta performance e responsividade:
- **React 18 & TypeScript**: Desenvolvimento baseado em componentes com tipagem estrita, garantindo manutenibilidade.
- **Vite & Rolldown**: Pipeline de build ultra-rápido.
- **Design System Customizado**:
  - **Tailwind CSS**: Estilização utilitária para design consistente.
  - **Radix UI**: Primitivas de UI acessíveis para modais, abas e componentes complexos.
  - **Lucide React**: Iconografia semântica.
- **Rich Feedback**: Sistema de mensagens de carregamento dinâmicas que notificam o usuário sobre a etapa atual do processamento da IA (ex: consulta ao RAG, validação de fontes).

### 2. Backend: Orquestração e Lógica de Negócio
O motor do sistema, responsável por gerenciar a comunicação entre usuários, agentes e modelos:
- **Python (Flask)**: Servidor assíncrono que utiliza `asyncio` para lidar com múltiplas requisições simultâneas de streaming de IA.
- **Google ADK (Agent Development Kit)**: Framework central que define a lógica de "Runners" e "Sessions". Ele permite que cada conversa mantenha seu histórico e contexto isoladamente.
- **Service Layer**:
  - **Scraping Engine**: Baseada em Scrapy, permite alimentar a base de conhecimento com dados frescos dos portais oficiais.
  - **Session Management**: Controle de sessões em memória para respostas rápidas.

### 3. Camada de Inteligência (LLM Engine)
A TIA é agnóstica a modelos, permitindo o uso de diversas LLMs de forma simultânea ou alternada:

#### **Modelos em Nuvem (Cloud)**
- **Google Gemini (2.0/2.5 Flash & Pro)**: Integração nativa via Google GenAI SDK. Utilizado como modelo principal para orquestração devido à alta janela de contexto e capacidades de RAG (File Search).
- **DeepSeek V3**: Integrado via **LiteLLM**, oferecendo uma alternativa de alto raciocínio para questões complexas de legislação e tributação.

#### **Modelos Locais (Localhost / Docker)**
O sistema possui suporte nativo para inferência local, garantindo soberania de dados e redução de custos:
- **Gemma Local**: Implementado para rodar em containers Docker ou via **Ollama** (endpoint `http://localhost:12434`).
- **DeepSeek Local**: Suporte para modelos rodando localmente (ex: DeepSeek-V3-base) via integração LiteLLM Local.
- **Hot-Swapping**: O backend permite trocar o modelo ativo em tempo real através da API `/api/models`, sem necessidade de reiniciar os serviços.

---

## � O Coração do Sistema: Multi-Agent RAG

A TIA não responde apenas com base em sua memória de treinamento. Ela utiliza um fluxo de **RAG (Retrieval-Augmented Generation)** rigoroso:

1. **Triagem (Orquestrador)**: A TIA analisa a dúvida e identifica se deve respondê-la ou invocar um dos **57 Agentes Especialistas** (ex: Detran, SEFAZ, Saúde).
2. **Busca Semântica (File Search)**: O agente relevante acessa uma "Knowledge Store" (Base de Conhecimento) específica, contendo PDFs, Leis e Manuais formatados em Markdown.
3. **Restrição de Fontes**: O sistema é instruído a ignorar fontes de terceiros (blogs ou notícias) e focar apenas em domínios `*.to.gov.br` e `*.al.to.leg.br`.
4. **Padronização de Links**: Uma camada de pós-processamento converte automaticamente links obsoletos encontrados na base antiga para os novos links do Portal Unificado (ex: `sefaz.to.gov.br` → `to.gov.br/sefaz`).

---

## �️ Guia de Implementação Técnica

### Requisitos de Ambiente
- **Node.js 20+** e **Python 3.11+**
- **Docker** (Opcional, necessário para modelos locais)

### Fluxo de Inicialização
1. **Configuração de Agentes**: O script `atualizar_agentes.py` lê o `MAPEAMENTO_COMPETENCIAS.py` e gera os arquivos JSON individuais para cada secretaria, injetando as regras globais de tom de voz e citação.
2. **Setup do RAG**: Documentos MD são processados e enviados para as Stores via API, ficando disponíveis para o `File Search` do Gemini.
3. **Inferência**: O `app.py` recebe a mensagem via `/api/chat`, instancia o `InMemoryRunner` com o agente adequado e gerencia o streaming de eventos até a resposta final.

---

## �️ Segurança e Privacidade
- **Isolamento de Sessão**: Cada usuário possui um UUID de sessão único, impedindo vazamento de contexto entre conversas.
- **Filtragem de Alucinação**: Instruções rígidas de sistema proíbem a criação de links que não existam na base oficial, mitigando um dos problemas mais comuns em LLMs.

---

**TIA - Inteligência a serviço do cidadão do Tocantins.**
