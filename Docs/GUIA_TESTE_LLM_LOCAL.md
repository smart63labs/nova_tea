# Guia: Testando LLM Local via Docker

## Endpoint Configurado
```
http://localhost:12434/engines/v1
```

## 1. Verificar se o Container Docker está Rodando

```bash
# Listar containers ativos
docker ps

# Verificar logs do container
docker logs <container_name>
```

## 2. Testar Conectividade Básica

```bash
# Teste 1: Verificar se a porta está acessível
curl http://localhost:12434/engines/v1/models

# Teste 2: Listar modelos disponíveis
curl http://localhost:12434/v1/models

# Teste 3: Health check
curl http://localhost:12434/health
```

## 3. Testar Geração de Texto

```bash
# Formato OpenAI compatível
curl http://localhost:12434/engines/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma-2-9b",
    "messages": [{"role": "user", "content": "Olá!"}],
    "max_tokens": 50
  }'
```

## 4. Usar o Script de Teste Python

```bash
# Executar o script de teste
python test_local_llm.py
```

O script irá:
- ✓ Verificar conectividade
- ✓ Testar endpoints alternativos
- ✓ Fazer uma requisição de chat completa
- ✓ Mostrar a resposta do modelo

## 5. Configurar no Sistema TIA

Atualize `dados/models.json`:

```json
{
  "active_model_id": "gemma-2-9b-local",
  "models": [
    {
      "id": "gemma-2-9b-local",
      "name": "Gemma 2 (9B) Docker Local",
      "type": "local_gemma",
      "enabled": true,
      "description": "Modelo local rodando em Docker",
      "endpoint": "http://localhost:12434/engines/v1"
    }
  ]
}
```

## 6. Testar via Interface Web

1. Abra o sistema TIA
2. Vá em **Configurações** → **Modelos**
3. Selecione "Gemma 2 (9B) Docker Local"
4. Clique em **Testar Conexão**

## Troubleshooting

### Erro: Connection Refused
```bash
# Verificar se o container está rodando
docker ps | grep llm

# Verificar se a porta está mapeada corretamente
docker port <container_name>

# Reiniciar o container
docker restart <container_name>
```

### Erro: 404 Not Found
O endpoint pode estar diferente. Tente:
- `http://localhost:12434/v1/chat/completions`
- `http://localhost:12434/chat/completions`
- `http://localhost:12434/api/chat/completions`

### Erro: Timeout
```bash
# Aumentar timeout no código
# Verificar logs do container
docker logs -f <container_name>

# Verificar uso de recursos
docker stats <container_name>
```

## Exemplo de Docker Compose (se necessário)

```yaml
version: '3.8'
services:
  llm-server:
    image: ollama/ollama:latest
    ports:
      - "12434:11434"
    volumes:
      - ollama-data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0:11434

volumes:
  ollama-data:
```

## Comandos Úteis

```bash
# Baixar modelo no container
docker exec -it <container_name> ollama pull gemma:2b

# Listar modelos instalados
docker exec -it <container_name> ollama list

# Testar diretamente no container
docker exec -it <container_name> ollama run gemma:2b "Olá!"
```
