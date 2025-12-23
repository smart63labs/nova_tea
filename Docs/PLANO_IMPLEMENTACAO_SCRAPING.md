# Plano de Implementação: Funcionalidade de Scraping Híbrida

## Objetivo

Implementar uma funcionalidade de web scraping que permita aos usuários extrair conteúdo de URLs e convertê-lo automaticamente em arquivos Markdown para upload na Base de Conhecimento. A solução utilizará uma abordagem híbrida (Scrapy + Playwright) para maximizar compatibilidade e performance.

## Contexto do Projeto

O projeto ADK (Advanced Development Kit) é uma aplicação multi-agente baseada em Flask (backend) e React/TypeScript (frontend). A nova funcionalidade será integrada como uma aba adicional na seção "Configurações" do sistema.

### Arquitetura Atual
- **Backend**: Flask (`flask_app/app.py`)
- **Frontend**: React + TypeScript (`frontend/src/App.tsx`)
- **Base de Conhecimento**: Google File Search Stores (API Gemini)
- **Configurações**: Sistema de abas com múltiplas funcionalidades

---

## Proposta de Mudanças

### 1. Backend - Infraestrutura de Scraping

#### 📁 Nova Estrutura de Pastas

```
flask_app/
  services/
    scraping/
      __init__.py
      scraper_factory.py      # Factory pattern para seleção de scraper
      scrapy_scraper.py       # Scraper para sites estáticos
      playwright_scraper.py   # Scraper para sites JavaScript
      detector.py             # Detector de tipo de site
      markdown_converter.py   # Conversor HTML → Markdown
      config.py               # Configurações de scraping
```

#### 📄 [NOVO] `flask_app/services/scraping/__init__.py`

```python
"""
Serviço de scraping híbrido (Scrapy + Playwright)
"""
from .scraper_factory import ScraperFactory

__all__ = ['ScraperFactory']
```

#### 📄 [NOVO] `flask_app/services/scraping/detector.py`

**Responsabilidade**: Detectar se um site requer JavaScript (SPA) ou é estático

**Lógica**:
- Faz requisição HTTP simples
- Analisa presença de frameworks JS (React, Vue, Angular)
- Verifica se conteúdo principal está no HTML inicial
- Retorna: `'static'` ou `'dynamic'`

#### 📄 [NOVO] `flask_app/services/scraping/scrapy_scraper.py`

**Responsabilidade**: Scraping rápido de sites estáticos

**Características**:
- Usa Scrapy para performance máxima
- Extrai título, conteúdo principal, metadados
- Timeout de 10 segundos
- Respeita robots.txt
- User-Agent customizado

#### 📄 [NOVO] `flask_app/services/scraping/playwright_scraper.py`

**Responsabilidade**: Scraping de sites JavaScript/SPAs

**Características**:
- Usa Playwright em modo headless
- Aguarda carregamento completo do DOM
- Timeout de 30 segundos
- Extrai conteúdo após renderização JavaScript
- Suporte a scroll infinito (opcional)

#### 📄 [NOVO] `flask_app/services/scraping/markdown_converter.py`

**Responsabilidade**: Converter HTML extraído para Markdown

**Características**:
- Usa biblioteca `html2text`
- Preserva formatação (títulos, listas, links)
- Remove scripts, estilos e elementos desnecessários
- Adiciona metadados (URL, data de extração)

#### 📄 [NOVO] `flask_app/services/scraping/scraper_factory.py`

**Responsabilidade**: Orquestrar o processo de scraping

**Fluxo**:
1. Recebe URL(s)
2. Detecta tipo de site
3. Seleciona scraper apropriado (Scrapy ou Playwright)
4. Executa scraping
5. Converte para Markdown
6. Retorna conteúdo + metadados

#### 📄 [NOVO] `flask_app/services/scraping/config.py`

**Configurações**:
```python
SCRAPY_SETTINGS = {
    'USER_AGENT': 'ADK-Scraper/1.0',
    'ROBOTSTXT_OBEY': True,
    'CONCURRENT_REQUESTS': 5,
    'DOWNLOAD_TIMEOUT': 10
}

PLAYWRIGHT_SETTINGS = {
    'HEADLESS': True,
    'TIMEOUT': 30000,
    'WAIT_UNTIL': 'networkidle'
}
```

---

### 2. Backend - API Endpoints

#### 📄 [MODIFICAR] `flask_app/app.py`

Adicionar novos endpoints:

##### `POST /api/scraping/process`

**Entrada**:
```json
{
  "urls": ["https://example.com", "https://example2.com"],
  "store_name": "fileSearchStores/xyz123"
}
```

**Processamento**:
1. Valida URLs
2. Cria tarefa assíncrona para cada URL
3. Retorna `task_id` para acompanhamento

**Saída**:
```json
{
  "task_id": "uuid-123",
  "total_urls": 2,
  "status": "processing"
}
```

##### `GET /api/scraping/status/<task_id>`

**Saída**:
```json
{
  "task_id": "uuid-123",
  "status": "processing",
  "progress": {
    "completed": 1,
    "total": 2,
    "current_url": "https://example2.com"
  },
  "results": [
    {
      "url": "https://example.com",
      "status": "success",
      "filename": "example_com.md",
      "file_uri": "files/abc123"
    }
  ]
}
```

##### `POST /api/scraping/cancel/<task_id>`

Cancela processamento em andamento.

---

### 3. Frontend - Interface de Scraping

#### 📄 [MODIFICAR] `frontend/src/App.tsx`

Adicionar nova aba "Scraping" no diálogo de Configurações:

**Localização**: Dentro do `<Tabs>` de configurações (linha ~686)

**Nova Aba**:
```tsx
<TabsTrigger value="scraping">
  <Globe className="h-4 w-4" /> Scraping
</TabsTrigger>
```

#### 📄 [NOVO] `frontend/src/components/ScrapingTab.tsx`

**Componente Principal**

**Funcionalidades**:
1. **Entrada de URLs**
   - Textarea para múltiplas URLs (uma por linha)
   - Validação de formato de URL
   - Contador de URLs válidas

2. **Seleção de Base de Conhecimento**
   - Dropdown com stores disponíveis
   - Opção de criar nova base

3. **Botão de Processar**
   - Inicia scraping
   - Mostra loading state

4. **Barra de Progresso**
   - Progresso em tempo real
   - URLs processadas / total
   - URL atual sendo processada

5. **Lista de Resultados**
   - ✅ Sucesso: mostra nome do arquivo gerado
   - ❌ Erro: mostra mensagem de erro
   - 🔗 Link para visualizar arquivo na base

6. **Preview de Markdown**
   - Accordion com preview de cada arquivo gerado
   - Usa ReactMarkdown para renderização

**Estados**:
```typescript
interface ScrapingState {
  urls: string[];
  selectedStore: string;
  taskId: string | null;
  status: 'idle' | 'processing' | 'completed' | 'error';
  progress: {
    completed: number;
    total: number;
    currentUrl: string;
  };
  results: ScrapingResult[];
}
```

#### 📄 [NOVO] `frontend/src/hooks/useScrapingProgress.ts`

**Hook Customizado**

**Responsabilidade**: Polling de status da tarefa

**Lógica**:
- Faz polling a cada 2 segundos
- Atualiza estado de progresso
- Para quando tarefa completa ou erro
- Retorna função de cancelamento

---

### 4. Integração com Base de Conhecimento

#### Fluxo de Upload Automático

1. **Scraping Completo** → Gera arquivo `.md` temporário
2. **Upload para Google Files API** → Retorna `file_uri`
3. **Adiciona à Store** → Vincula arquivo à base selecionada
4. **Notifica Frontend** → Atualiza lista de resultados

#### Tratamento de Erros

- **URL inválida**: Retorna erro antes de processar
- **Timeout**: Marca como falha e continua próxima URL
- **Erro de upload**: Tenta novamente (3 tentativas)
- **Store não encontrada**: Retorna erro e para processamento

---

## Dependências Necessárias

### Backend (Python)

Adicionar ao `requirements.txt`:

```txt
scrapy==2.11.0
playwright==1.40.0
html2text==2020.1.16
beautifulsoup4==4.12.0
lxml==4.9.3
```

### Instalação do Playwright

```bash
pip install playwright
playwright install chromium
```

### Frontend (TypeScript)

Já possui todas as dependências necessárias:
- `react-markdown` ✅
- `lucide-react` ✅

---

## Plano de Verificação

### 1. Testes Automatizados Backend

#### Teste de Detector

```bash
# Criar arquivo: flask_app/services/scraping/tests/test_detector.py
python -m pytest flask_app/services/scraping/tests/test_detector.py -v
```

**Casos de Teste**:
- Site estático (Wikipedia) → deve retornar `'static'`
- Site SPA (React app) → deve retornar `'dynamic'`
- URL inválida → deve lançar exceção

#### Teste de Scrapy Scraper

```bash
python -m pytest flask_app/services/scraping/tests/test_scrapy_scraper.py -v
```

**Casos de Teste**:
- Extração de título e conteúdo
- Timeout em site lento
- Respeito a robots.txt

#### Teste de Playwright Scraper

```bash
python -m pytest flask_app/services/scraping/tests/test_playwright_scraper.py -v
```

**Casos de Teste**:
- Extração de conteúdo JavaScript
- Aguardar carregamento completo
- Timeout

#### Teste de Conversor Markdown

```bash
python -m pytest flask_app/services/scraping/tests/test_markdown_converter.py -v
```

**Casos de Teste**:
- Conversão de HTML simples
- Preservação de formatação
- Remoção de scripts/estilos

### 2. Testes de Integração

#### Teste End-to-End da API

```bash
# Criar arquivo: flask_app/tests/test_scraping_api.py
python -m pytest flask_app/tests/test_scraping_api.py -v
```

**Casos de Teste**:
- POST /api/scraping/process com URLs válidas
- GET /api/scraping/status/<task_id>
- POST /api/scraping/cancel/<task_id>
- Upload automático para base de conhecimento

### 3. Testes Manuais (Frontend)

> [!IMPORTANT]
> **Pré-requisito**: Backend e Frontend devem estar rodando

#### Passos para Teste Manual:

1. **Iniciar Backend**
   ```bash
   cd C:\Users\88417646191\Documents\ADK
   python flask_app/app.py
   ```

2. **Iniciar Frontend**
   ```bash
   cd C:\Users\88417646191\Documents\ADK\frontend
   npm run dev
   ```

3. **Acessar Interface**
   - Abrir navegador em `http://localhost:8080` (ou porta indicada)
   - Clicar em "Configurações"
   - Navegar para aba "Scraping"

4. **Testar Scraping de Site Estático**
   - Inserir URL: `https://pt.wikipedia.org/wiki/Intelig%C3%AAncia_artificial`
   - Selecionar base de conhecimento existente
   - Clicar em "Processar"
   - **Resultado Esperado**: 
     - Barra de progresso aparece
     - Arquivo `wikipedia_inteligencia_artificial.md` é criado
     - Preview mostra conteúdo formatado
     - Arquivo aparece na aba "Base de Conhecimento"

5. **Testar Scraping de Múltiplas URLs**
   - Inserir 3 URLs diferentes (uma por linha)
   - Processar
   - **Resultado Esperado**:
     - Progresso mostra "1/3", "2/3", "3/3"
     - Todos os arquivos são criados
     - Lista de resultados mostra status de cada URL

6. **Testar Tratamento de Erro**
   - Inserir URL inválida: `https://site-que-nao-existe-123456.com`
   - Processar
   - **Resultado Esperado**:
     - Erro é exibido na lista de resultados
     - Ícone de erro (❌) aparece
     - Mensagem de erro é clara

7. **Testar Cancelamento**
   - Inserir 5 URLs
   - Iniciar processamento
   - Clicar em "Cancelar" após 2 URLs processadas
   - **Resultado Esperado**:
     - Processamento para
     - URLs já processadas permanecem na lista
     - Status muda para "cancelado"

### 4. Verificação de Integração com Base de Conhecimento

#### Usando MCP Chrome DevTools

```bash
# Verificar console do navegador em http://localhost:8080
# Procurar por erros relacionados a upload de arquivos
```

**Passos**:
1. Fazer scraping de uma URL
2. Ir para aba "Base de Conhecimento"
3. Verificar se arquivo aparece na lista
4. Clicar no arquivo para visualizar
5. **Resultado Esperado**: Conteúdo Markdown renderizado corretamente

---

## Limitações e Boas Práticas

### Limitações

1. **Rate Limiting**: Máximo de 5 URLs simultâneas para evitar sobrecarga
2. **Timeout**: 10s para Scrapy, 30s para Playwright
3. **Tamanho de Arquivo**: Máximo de 5MB por arquivo Markdown
4. **Sites Protegidos**: Sites com CAPTCHA ou autenticação não funcionarão

### Boas Práticas

1. **Respeitar robots.txt**: Scrapy configurado para obedecer
2. **User-Agent Identificável**: `ADK-Scraper/1.0`
3. **Delay entre Requisições**: 1 segundo entre URLs do mesmo domínio
4. **Limpeza de Arquivos Temporários**: Deletar após upload bem-sucedido

---

## Cronograma de Implementação

### Fase 1: Backend Infraestrutura (Estimativa: 2-3 horas)
- [ ] Criar estrutura de pastas
- [ ] Implementar detector de tipo de site
- [ ] Implementar Scrapy scraper
- [ ] Implementar Playwright scraper
- [ ] Implementar conversor Markdown
- [ ] Implementar factory pattern

### Fase 2: Backend API (Estimativa: 1-2 horas)
- [ ] Criar endpoints de scraping
- [ ] Implementar sistema de tarefas assíncronas
- [ ] Integrar com upload para base de conhecimento
- [ ] Adicionar logging e tratamento de erros

### Fase 3: Frontend Interface (Estimativa: 2-3 horas)
- [ ] Criar componente ScrapingTab
- [ ] Implementar formulário de entrada
- [ ] Criar barra de progresso
- [ ] Implementar lista de resultados
- [ ] Adicionar preview de Markdown
- [ ] Integrar com API backend

### Fase 4: Testes (Estimativa: 2 horas)
- [ ] Escrever testes unitários backend
- [ ] Escrever testes de integração
- [ ] Executar testes manuais frontend
- [ ] Validar integração com base de conhecimento

### Fase 5: Documentação (Estimativa: 30 minutos)
- [ ] Documentar API endpoints
- [ ] Criar guia de uso para usuários
- [ ] Documentar limitações

**Tempo Total Estimado**: 7-10 horas

---

## Próximos Passos

1. ✅ Revisar este plano com o usuário
2. ⏳ Aguardar aprovação
3. ⏳ Iniciar implementação Fase 1
4. ⏳ Testes incrementais a cada fase
5. ⏳ Deploy e validação final

---

## Observações Finais

- A solução híbrida garante **máxima compatibilidade** com diferentes tipos de sites
- O sistema de **detecção automática** torna a experiência transparente para o usuário
- A **integração nativa** com a base de conhecimento elimina passos manuais
- O **feedback em tempo real** melhora a experiência do usuário

