# Documentação da Implementação de RAG Local

## Visão Geral

Foi implementada uma solução de **RAG (Retrieval-Augmented Generation)** híbrida no arquivo `tea/file_search_tool.py`. Esta implementação permite que o sistema utilize diferentes estratégias de busca dependendo do modelo de IA ativo:

1.  **Modelos Google Gemini**: Utiliza a infraestrutura de **File Search da API do Google Vertex AI/Gemini** (RAG na nuvem).
2.  **Outros Modelos (Local LLM / DeepSeek)**: Utiliza uma implementação de **busca local baseada em palavras-chave** (Keyword Search) operando diretamente sobre os arquivos em disco.

## Arquitetura e Componentes

A lógica central reside na classe `FileSearchTool` em `tea/file_search_tool.py`.

### 1. Detecção de Modelo
A ferramenta detecta automaticamente o tipo de modelo em execução através do método `process_llm_request`.
- Se o modelo for **Gemini** (`is_gemini_model`), a ferramenta configura o payload para usar o `file_search` nativo do Google.
- Se for **outro modelo**, ela expõe uma *Function Declaration* tradicional, permitindo que o modelo invoque a função `file_search` como uma ferramenta padrão.

### 2. Mecanismo de Busca Local
Quando acionada localmente (método `run_async`), a ferramenta executa o seguinte fluxo:

*   **Fonte de Dados**: A busca é realizada no diretório `dados/scraped_backup`. O sistema varre subdiretórios correspondentes aos nomes dos *datastores* configurados no agente.
*   **Tipos de Arquivo**: Processa arquivos `.md` e `.txt`.
*   **Algoritmo de Busca**:
    *   Tokeniza a consulta do usuário (palavras com 3+ caracteres).
    *   Calcula um **score** simples para cada arquivo baseado na frequência dos termos da busca no conteúdo (TF - Term Frequency).
    *   `_score_text(text, tokens)`: Soma quantas vezes cada token aparece no texto.
*   **Extração de Snippet**:
    *   Identifica a posição da melhor correspondência dos termos.
    *   Extrai um trecho de até **900 caracteres** ao redor dessa posição para fornecer contexto ao modelo.
*   **Ranking**: Retorna os `top_k` (padrão: 4) resultados mais relevantes ordenados pelo score.

### 3. Integração com Agentes (`tea/agent.py`)
No arquivo `tea/agent.py`, a instanciação das ferramentas segue uma lógica condicional:
- Agentes configurados com **Gemini** recebem a `FileSearchTool` configurada para nuvem.
- Agentes configurados com modelos locais tentam importar uma `LocalRagTool` (que seria uma especialização, possivelmente usando vetores).
    - *Nota*: A classe `FileSearchTool` já possui a capacidade de fallback local, podendo ser utilizada diretamente para modelos locais caso a `LocalRagTool` não esteja disponível.

## Estrutura de Diretórios
- **Código Fonte**: `tea/file_search_tool.py`
- **Backup de Dados**: `dados/scraped_backup/` (onde os textos dos sites e documentos 'scrapados' são armazenados).
- **Dependências**: O projeto inclui bibliotecas como `chromadb` e `sentence-transformers` no `requirements.txt`, indicando uma preparação para evoluir a busca local de "palavras-chave" para "busca vetorial" (Semantic Search) no futuro.

## Exemplo de Fluxo (Local)
1.  Usuário pergunta: *"Quais as competências da Secretaria da Fazenda?"*
2.  Modelo Local chama a ferramenta `file_search(query="competências secretaria fazenda")`.
3.  `FileSearchTool` varre a pasta `dados/scraped_backup/Secretaria da Fazenda`.
4.  Encontra `sobre.md`, calcula score alto para os termos.
5.  Retorna JSON com trecho: `"...A Secretaria da Fazenda tem por competência a gestão tributária..."`.
6.  Modelo usa o trecho para gerar a resposta final.
