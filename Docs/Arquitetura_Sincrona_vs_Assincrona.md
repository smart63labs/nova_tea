# Arquitetura de Backend: Sincronismo vs. Assincronismo na TIA

Este documento detalha a decisão técnica de utilizar uma arquitetura síncrona (com streaming) para o backend da TIA, em contrapartida ao modelo puramente assíncrono, visando a estabilidade e escalabilidade do sistema em produção.

## 1. O Contexto da Mudança
Inicialmente, o sistema foi projetado utilizando funções assíncronas (`async/await`). No entanto, durante a integração com bibliotecas de Inteligência Artificial modernas (como `LiteLLM` e `Google ADK`), identificamos conflitos críticos de **Event Loop**.

### Problema Identificado:
- **Erro**: `RuntimeError: bound to a different event loop`.
- **Causa**: Bibliotecas de IA muitas vezes geram seus próprios processos ou threads em segundo plano para monitoramento e logs. Em ambientes Flask/WSGI adaptados para ASGI (Uvicorn), esses processos tentavam acessar o loop de eventos principal de forma concorrente em threads não autorizadas, resultando em quedas aleatórias do servidor.

## 2. Solução Adotada: Síncrono com Streaming
Migramos o endpoint principal de chat (`/api/chat`) para uma função síncrona.

### Por que ainda funciona em "Tempo Real"?
Mesmo sendo uma função síncrona, utilizamos um **Gerador de Python** (`yield`) e o protocolo **SSE (Server-Sent Events)**. 
- O backend processa cada pedaço da resposta da IA e o envia imediatamente ao frontend.
- O Flask gerencia o paralelismo através de **Threads**, garantindo que uma requisição não bloqueie a outra.

## 3. Comparativo Técnico

| Aspecto | Modelo Assíncrono (Original) | Modelo Síncrono (Atual) |
| :--- | :--- | :--- |
| **Streaming** | Suportado | **Suportado** |
| **Estabilidade** | Instável em ambientes Windows/Flask | **Alta Estabilidade** |
| **Conflitos de Libs** | Frequentes com LiteLLM/RAG | **Inexistentes** |
| **Depuração** | Complexa (Tracebacks de Event Loop) | **Simples e Direta** |
| **Escalabilidade** | Alta densidade por processo | **Escalabilidade Horizontal** |

## 4. Visão de Futuro: Milhares de Usuários Simultâneos
Para um sistema que atenderá milhares de cidadãos simultaneamente, a arquitetura atual é a mais recomendada por ser **Isolada**.

### Estratégia de Escalabilidade:
1. **Verticalização Individual**: Cada thread atua de forma independente. O erro de um usuário não afeta o "loop" global, protegendo a sessão dos demais.
2. **Escalonamento Horizontal**: A aplicação está pronta para ser replicada (Docker/Kubernetes). Como não dependemos de um loop central complexo, podemos subir dezenas de instâncias idênticas em um cluster, distribuindo a carga de milhares de usuários via um **Load Balancer** (Nginx/Cloudflare).
3. **Gargalo de IA**: O limite real de escalabilidade de um sistema de IA não é o código do servidor, mas sim o **Rate Limit** das APIs das LLMs (Gemini, etc.) ou o **TFLOPS das GPUs** em modelos locais. O modelo síncrono garante que o servidor de rede não seja um ponto de falha enquanto aguardamos o processamento da IA.

## 5. Resumo da Decisão
A segurança operacional e a integridade da resposta ao cidadão foram priorizadas. O modelo atual oferece **estabilidade industrial**, mantendo a agilidade do streaming exigida por interfaces de chat modernas.

---
**Data**: 22 de Dezembro de 2025  
**Responsável**: Engenharia de IA / ADK Development Team
