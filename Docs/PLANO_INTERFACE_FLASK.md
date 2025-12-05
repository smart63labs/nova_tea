# Plano de Implementação da Interface Flask

## Objetivos
- Criar interface de chat para o usuário.
- Criar tela de configurações para modelo de IA e chave.
- Criar telas de configuração para agentes: prompts de sistema e de usuário.

## Arquitetura
- `flask_app/app.py`: servidor Flask, rotas de chat e configurações.
- `flask_app/templates/`: páginas HTML (`chat`, `settings_model`, `agents`, `agent_detail`).
- `flask_app/static/style.css`: estilos.
- `config/settings.json`: persistência de modelo e prompts.
- `tea/.env`: chave da API.
- `tea/agent.py`: leitura dinâmica de `settings.json` para modelo e prompts.

## Fluxo de Chat
- Usuário envia mensagem e seleciona destino: `Auto` (orquestrador) ou um agente específico.
- Mensagem é enriquecida com `user_prompt` correspondente.
- Execução via `InMemoryRunner` do ADK.
- Resposta é renderizada no front.

## Configurações
- Tela de Modelo/Chave: salva `model` em `settings.json` e chave em `tea/.env`.
- Tela de Agentes: lista todos os agentes; cada agente possui edição de `system_prompt` e `user_prompt`.
- Ao salvar configurações, os agentes são recarregados.

## Validações
- Modelo deve existir na lista de modelos suportados.
- Chave não é exibida em logs.
- IDs de agentes usam `normalize_name` para consistência.

## Próximos Passos
- Adicionar histórico no chat.
- Suporte a uploads e RAG.
- Autenticação de usuário.
