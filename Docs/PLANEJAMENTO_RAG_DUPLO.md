# Planejamento: Implementação de RAG Duplo (Web Search + File Search)

Este documento descreve o plano para implementar a capacidade de busca híbrida (Internet e Arquivos) nos agentes do sistema TEA, configurável individualmente.

## 1. Objetivo
Permitir que cada agente especialista possa utilizar:
1.  **Google Search (Web):** Para informações em tempo real e públicas.
2.  **Gemini File Search (RAG):** Para informações específicas contidas em documentos oficiais (PDFs, manuais, leis) indexados no Google Gemini.

O administrador do sistema poderá ativar um, outro, ou ambos para cada agente.

## 2. Arquitetura

### 2.1. Nova Ferramenta: `FileSearchTool`
Será criada uma classe Python `FileSearchTool` em `tea/file_search_tool.py` que estende `BaseTool` do ADK.
*   **Responsabilidade:** Envolver a configuração `types.FileSearch` da API Gemini.
*   **Parâmetros:** Recebe uma lista de `file_search_store_names` (Corpora).

### 2.2. Configuração dos Agentes (JSON)
Os arquivos de definição dos agentes (`dados/agentes/*.json`) receberão novos campos opcionais:

```json
{
  "name": "Secretaria da Fazenda",
  "system_prompt": "...",
  "enabled": true,
  
  "enable_web_search": true,        // Habilita busca na internet (Default: true)
  "file_search_stores": [           // Lista de Stores para busca em arquivos
    "projects/.../locations/.../ragCorpora/..."
  ]
}
```

### 2.3. Lógica de Inicialização (`tea/agent.py`)
O script de inicialização dos agentes será refatorado para:
1.  Ler as configurações `enable_web_search` e `file_search_stores`.
2.  Instanciar a lista de ferramentas (`tools`) dinamicamente para cada agente.
3.  Permitir o uso simultâneo de ambas as ferramentas se configurado.

## 3. Etapas de Implementação

### Passo 1: Criação da Classe `FileSearchTool`
*   Arquivo: `tea/file_search_tool.py`
*   Código compatível com `google-genai` e ADK.

### Passo 2: Atualização do Carregador de Agentes
*   Arquivo: `tea/agent.py`
*   Lógica para instanciar `GoogleSearchTool` apenas se `enable_web_search` for `true`.
*   Lógica para instanciar `FileSearchTool` se `file_search_stores` estiver preenchido.

### Passo 3: Atualização do Template
*   Arquivo: `dados/agentes/_template.json`
*   Adicionar os campos novos para facilitar a criação de novos agentes.

## 4. Referências
*   Baseado na implementação de referência em `Docs/ask-the-manual`.
*   Documentação Gemini API: File Search.
