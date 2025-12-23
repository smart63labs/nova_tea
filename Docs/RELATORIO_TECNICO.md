# Documentação Técnica - Projeto TEA (Tocantins Estado Assistente)

**Data de Criação:** 05/12/2025  
**Versão:** 1.0  
**Desenvolvedor:** Assistente Trae (Pair Programmer)
**Link Documentação ADK:** [https://github.com/google/generative-ai-agent-development-kit](https://github.com/google/generative-ai-agent-development-kit) - https://google.github.io/adk-docs/get-started/python/#run-with-web-interface

---

## 1. Visão Geral do Projeto

O **TEA (Tocantins Estado Assistente)** é um sistema de assistência virtual inteligente projetado para facilitar o acesso a informações governamentais do Estado do Tocantins. O sistema utiliza Inteligência Artificial Generativa para interpretar perguntas dos cidadãos e direcioná-las a agentes especializados em cada órgão ou entidade governamental.

O objetivo principal é fornecer respostas precisas, contextualizadas e atualizadas (via pesquisa na web) sobre serviços, notícias e atribuições de Secretarias, Autarquias e outros órgãos estaduais.

---

## 2. Arquitetura do Sistema

O sistema foi construído utilizando o **Google Agent Development Kit (ADK)** e segue uma arquitetura **Multi-Agente Hierárquica**.

### 2.1. Componentes Principais

1.  **Agente Orquestrador (`TEA_Orquestrador`)**:
    *   **Função:** Atua como a porta de entrada e o "cérebro" central do sistema.
    *   **Responsabilidade:** Recebe a dúvida do usuário, analisa o contexto e decide qual agente especialista é o mais adequado para responder.
    *   **Modelo:** Gemini 2.5 Flash.
    *   **Instrução:** Delegar para especialistas ou lidar com dúvidas gerais.
    *   **Implementação:** Utiliza uma lista de ferramentas (`Tools`), onde cada ferramenta é um wrapper (`AgentTool`) para um agente especialista.

2.  **Agentes Especialistas (Sub-agentes)**:
    *   Foram criados **57 agentes especializados**, correspondendo a cada entidade governamental mapeada.
    *   **Função:** Fornecer informações profundas e específicas sobre sua área de atuação.
    *   **Ferramentas:** Todos possuem acesso à `GoogleSearchTool` para buscar informações em tempo real na internet.
    *   **Identificação:** Cada agente possui um ID normalizado (ex: `secretaria_da_saude`, `detran`) e instruções específicas.
    *   **Encapsulamento:** Cada agente é encapsulado em uma `AgentTool` para ser invocado pelo orquestrador.

### 2.2. Fluxo de Dados
1.  **Usuário** envia uma pergunta (ex: "Como renovar minha CNH?").
2.  **Orquestrador** analisa a intenção e identifica que o assunto pertence ao "Departamento Estadual de Trânsito".
3.  **Orquestrador** invoca a ferramenta (`AgentTool`) correspondente ao agente `detran`.
4.  **Agente Especialista** recebe a tarefa, usa a `GoogleSearchTool` se necessário para buscar os requisitos atuais de renovação e formula a resposta.
5.  **Resposta** é retornada ao usuário final através do Orquestrador.

---

## 3. Histórico de Desenvolvimento

### Fase 1: Configuração Inicial
*   Instalação do Python 3.13 e criação de ambiente virtual (`.venv`).
*   Instalação da biblioteca `google-adk`.
*   Configuração de credenciais (Google API Key).

### Fase 2: Criação do Agente Piloto
*   Criação do projeto base `tea` usando o CLI do ADK (`adk create tea`).
*   Configuração inicial de um agente simples com capacidade de busca na web.
*   Validação do ambiente de execução local (`adk web`).

### Fase 3: Expansão para Multi-Agentes
*   Levantamento de todas as Secretarias, Autarquias e Sites Especiais do Governo do Tocantins.
*   Refatoração do código `agent.py` para implementação dinâmica de agentes.
*   Implementação de lógica de normalização de nomes para IDs de agentes.
*   Configuração do Orquestrador para gerenciar a lista de sub-agentes.
*   **Correção Técnica:** Ajuste na implementação para encapsular sub-agentes em `AgentTool`, permitindo que o Orquestrador os invoque como ferramentas (resolvendo erro de validação do ADK).

---

## 4. Entidades Mapeadas (Agentes Criados)

O sistema conta atualmente com agentes para as seguintes entidades:

**Secretarias:**
*   Casa Civil, Casa Militar, Controladoria-Geral, Corpo de Bombeiros, Polícia Militar, Procuradoria-Geral.
*   Secretarias de: Administração, Agricultura, Cidadania e Justiça, Comunicação, Cultura, Educação, Fazenda, Igualdade Racial, Indústria e Comércio, Mulher, Pesca, Saúde, Segurança Pública, Cidades, Parcerias, Meio Ambiente, Planejamento, Trabalho, Turismo, Esportes, Povos Originários.
*   Secretarias Extraordinárias e Executivas.

**Autarquias:**
*   Agências: Regulação (ATR), Saneamento (ATS), Defesa Agropecuária (ADAPEC), Fomento, Metrologia, Mineração, TI (ATI), Transportes (Ageto).
*   Institutos: Natureza (Naturatins), Desenvolvimento Rural (Ruraltins), Gestão Previdenciária (Igeprev), Terras (Itertins).
*   Outros: Detran, Junta Comercial, Unitins, Companhia Imobiliária.

**Sites Especiais:**
*   Clube de Benefícios, Carteira do Autista, Diário Oficial, Observatórios, Vale Gás, Zoneamento Ecológico.

---

## 5. Oportunidades de Melhoria (Roadmap)

Para evoluir o sistema TEA, sugerem-se as seguintes melhorias:

### 5.1. Aprimoramento da Inteligência (RAG)
*   **Retrieval-Augmented Generation (RAG):** Implementar uma base de conhecimento vetorial com documentos oficiais (PDFs de leis, diários oficiais, manuais de serviço). Isso reduzirá a dependência de buscas na web e aumentará a precisão para questões burocráticas específicas.
*   **Base de Conhecimento Local:** Indexar os sites governamentais previamente para buscas mais rápidas.

### 5.2. Persistência e Contexto
*   **Histórico de Conversa:** Implementar banco de dados (ex: PostgreSQL ou Firestore) para salvar históricos de conversas, permitindo que o usuário retome atendimentos.
*   **Perfil do Usuário:** Permitir que o usuário salve preferências ou dados básicos (ex: cidade de residência) para respostas mais personalizadas.

### 5.3. Integrações de Serviços (Tools Avançadas)
*   **Consulta de Processos:** Criar ferramentas (`Tools`) que se conectem a APIs reais do governo para consultar status de protocolos, CNH, débitos de IPVA, etc.
*   **Agendamento:** Integração com sistemas de agendamento de serviços públicos.

### 5.4. Interface e Deploy
*   **Frontend Personalizado:** Desenvolver uma interface web ou aplicativo móvel com a identidade visual do Governo do Tocantins (substituindo a UI de teste do ADK).
*   **Canais de Atendimento:** Integrar o agente ao WhatsApp (via Twilio ou API Oficial) e Telegram para maior alcance.
*   **Deploy em Nuvem:** Implantar a solução no Google Cloud Run para escalabilidade e alta disponibilidade.

### 5.5. Monitoramento e Avaliação
*   **Dashboard de Analytics:** Monitorar quais órgãos são mais demandados e quais perguntas não estão sendo respondidas satisfatoriamente.
*   **Feedback do Usuário:** Implementar mecanismo de "joinha/negativo" nas respostas para reinar o modelo.
