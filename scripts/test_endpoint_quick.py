import requests
import json

# Teste direto do endpoint
url = "http://localhost:12434/engines/v1/chat/completions"
payload = {
    "model": "ai/gemma3:latest",
    "messages": [{"role": "user", "content": "ping"}],
    "max_tokens": 1
}

print(f"🧪 Testando endpoint: {url}")
print(f"📦 Payload: {json.dumps(payload, indent=2)}")
print("=" * 60)

try:
    response = requests.post(url, json=payload, timeout=30)
    print(f"✅ Status: {response.status_code}")
    print(f"📄 Response: {response.text[:500]}")
    
    if response.status_code == 200:
        print("\n✅ SUCESSO! O endpoint está funcionando corretamente.")
    else:
        print(f"\n❌ ERRO: Status {response.status_code}")
        
except requests.exceptions.ConnectionError as e:
    print(f"❌ ERRO DE CONEXÃO: {e}")
    print("\n⚠️  Verifique:")
    print("   1. Docker está rodando?")
    print("   2. Container está na porta 12434?")
    print("   3. Endpoint correto: http://localhost:12434/engines/v1")
    
except requests.exceptions.Timeout:
    print("❌ TIMEOUT: O modelo demorou mais de 30s para responder")
    
except Exception as e:
    print(f"❌ ERRO: {type(e).__name__}: {e}")
