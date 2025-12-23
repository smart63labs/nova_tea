# Guia de Uso: Funcionalidade de Web Scraping

## Visão Geral

A funcionalidade de Web Scraping permite extrair conteúdo de páginas web e adicioná-lo automaticamente à Base de Conhecimento do sistema. O sistema utiliza uma abordagem híbrida que detecta automaticamente se o site é estático ou requer JavaScript, selecionando o scraper mais adequado.

## Como Usar

### 1. Acessar a Funcionalidade

1. Abra a aplicação
2. Clique no botão **"Configurações"** no canto superior direito
3. Navegue para a aba **"Scraping"**

### 2. Inserir URLs

1. No campo **"URLs para Processar"**, digite as URLs que deseja processar
2. Insira **uma URL por linha**
3. O sistema mostra quantas URLs válidas foram detectadas

**Exemplo**:
```
https://pt.wikipedia.org/wiki/Inteligência_artificial
https://www.python.org/doc/
https://docs.python.org/3/tutorial/
```

### 3. Selecionar Base de Conhecimento

1. No dropdown **"Base de Conhecimento"**, selecione a base onde os arquivos serão adicionados
2. Se não houver bases disponíveis, crie uma na aba **"Bases de Conhecimento"**

### 4. Processar

1. Clique no botão **"Processar URLs"**
2. O sistema iniciará o processamento em background

### 5. Acompanhar Progresso

Durante o processamento, você verá:

- **Barra de Progresso**: Mostra quantas URLs foram processadas (ex: 2/5)
- **URL Atual**: Exibe qual URL está sendo processada no momento
- **Status**: Indica o estado atual (Processando, Concluído, Erro, etc.)
- **Lista de Resultados**: Mostra o status de cada URL processada
  - ✅ **Sucesso**: Nome do arquivo gerado e tipo de scraper usado
  - ❌ **Erro**: Mensagem de erro detalhada

### 6. Cancelar (Opcional)

- Durante o processamento, você pode clicar em **"Cancelar"** para interromper

### 7. Processar Novas URLs

- Após conclusão, clique em **"Processar Novas URLs"** para iniciar nova tarefa

---

## Tipos de Scraper

### Scrapy (Sites Estáticos)

**Usado para**: Sites com HTML renderizado no servidor

**Características**:
- ⚡ Muito rápido (assíncrono)
- 💾 Baixo consumo de recursos
- ⏱️ Timeout: 10 segundos

**Exemplos**: Wikipedia, blogs, documentação técnica, sites institucionais

### Playwright (Sites JavaScript)

**Usado para**: Sites com conteúdo carregado via JavaScript (SPAs)

**Características**:
- 🌐 Renderiza navegador completo
- 🔄 Aguarda carregamento de JavaScript
- ⏱️ Timeout: 30 segundos

**Exemplos**: Aplicações React, Vue, Angular, sites modernos

---

## Limitações

### Técnicas

- **Máximo de URLs simultâneas**: 5
- **Timeout**:
  - Sites estáticos: 10 segundos
  - Sites JavaScript: 30 segundos
- **Tamanho máximo de arquivo**: 5MB por arquivo Markdown
- **Sites não suportados**:
  - Sites com CAPTCHA
  - Sites que requerem autenticação/login
  - Sites com proteção anti-scraping agressiva

### Legais e Éticas

- ⚖️ **Respeite os termos de uso** dos sites
- 🤖 **Respeite robots.txt** (o sistema faz isso automaticamente)
- ⏰ **Evite scraping excessivo** do mesmo domínio
- 📜 **Use apenas para fins educacionais** ou com permissão

---

## Resolução de Problemas

### "Nenhuma URL válida fornecida"

**Causa**: URLs com formato inválido

**Solução**: Verifique se as URLs:
- Começam com `http://` ou `https://` (ou adicione automaticamente)
- Têm um domínio válido (ex: `example.com`)
- Não contêm caracteres especiais inválidos

### "Timeout ao acessar [URL]"

**Causa**: Site demorou muito para responder

**Solução**:
- Verifique se o site está online
- Tente novamente mais tarde
- Se persistir, o site pode ter proteção anti-scraping

### "Erro ao processar [URL]"

**Causa**: Vários motivos possíveis

**Solução**:
- Verifique a mensagem de erro específica
- Confirme se o site está acessível em um navegador
- Verifique se o site não requer login

### "Serviço de scraping não disponível"

**Causa**: Dependências não instaladas no backend

**Solução**:
- Verifique se as dependências foram instaladas:
  ```bash
  pip install scrapy playwright html2text beautifulsoup4 lxml
  playwright install chromium
  ```

---

## Formato dos Arquivos Gerados

Os arquivos Markdown gerados têm o seguinte formato:

```markdown
---
título: [Título da Página]
url: [URL Original]
data_extração: [Data e Hora]
fonte: Web Scraping
---

# [Título da Página]

**URL Original**: [URL]  
**Data de Extração**: [Data]

---

[Conteúdo extraído em Markdown]
```

---

## Boas Práticas

### ✅ Recomendado

- Processar URLs de documentação pública
- Usar para criar base de conhecimento de conteúdo educacional
- Processar poucas URLs por vez (1-5)
- Aguardar conclusão antes de processar novo lote

### ❌ Não Recomendado

- Fazer scraping de sites comerciais sem permissão
- Processar centenas de URLs simultaneamente
- Fazer scraping repetido do mesmo site em curto período
- Tentar fazer scraping de sites com CAPTCHA

---

## Exemplos de Uso

### Exemplo 1: Documentação Técnica

**URLs**:
```
https://docs.python.org/3/tutorial/
https://docs.python.org/3/library/
```

**Resultado**: 2 arquivos Markdown com conteúdo da documentação Python

### Exemplo 2: Artigos Wikipedia

**URLs**:
```
https://pt.wikipedia.org/wiki/Inteligência_artificial
https://pt.wikipedia.org/wiki/Aprendizado_de_máquina
```

**Resultado**: 2 arquivos Markdown com conteúdo dos artigos

### Exemplo 3: Blog Posts

**URLs**:
```
https://blog.example.com/post-1
https://blog.example.com/post-2
```

**Resultado**: 2 arquivos Markdown com conteúdo dos posts

---

## Suporte

Se encontrar problemas:

1. Verifique os logs do backend (`debug.log`)
2. Confirme que as dependências estão instaladas
3. Teste com URLs simples primeiro (ex: Wikipedia)
4. Verifique se a base de conhecimento está acessível

---

## Próximos Passos

Após o scraping:

1. Vá para a aba **"Bases de Conhecimento"**
2. Selecione a base onde fez upload
3. Verifique se os arquivos aparecem na lista
4. Teste fazendo perguntas ao agente associado à base
