import requests
import json

# Configuração
ENDPOINT = "http://localhost:12434/engines/v1/chat/completions"
MODEL_HASH = "ai/gemma3:latest"

def test_local_llm():
    """Testa o LLM local com uma pergunta simples"""
    
    print("🧪 Testando LLM Local")
    print("=" * 60)
    print(f"Endpoint: {ENDPOINT}")
    print(f"Model: {MODEL_HASH}")
    print("=" * 60)
    
    payload = {
        "model": MODEL_HASH,
        "messages": [
            {
                "role": "user",
                "content": "Qual a capital do Brasil?"
            }
        ],
        "stream": False  # Desabilita streaming para teste simples
    }
    
    try:
        print("\n📤 Enviando requisição...")
        response = requests.post(ENDPOINT, json=payload, timeout=30)
        
        print(f"✅ Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Extrai a resposta
            if 'choices' in data and len(data['choices']) > 0:
                message = data['choices'][0]['message']['content']
                
                print("\n" + "=" * 60)
                print("📝 RESPOSTA DO MODELO:")
                print("=" * 60)
                print(message)
                print("=" * 60)
                
                # Mostra métricas
                if 'timings' in data:
                    timings = data['timings']
                    print(f"\n⏱️  MÉTRICAS:")
                    print(f"   Tokens gerados: {timings.get('predicted_n', 'N/A')}")
                    print(f"   Velocidade: {timings.get('predicted_per_second', 'N/A'):.2f} tokens/s")
                    print(f"   Tempo total: {(timings.get('predicted_ms', 0) + timings.get('prompt_ms', 0)) / 1000:.2f}s")
                
                return True
            else:
                print("❌ Resposta sem conteúdo")
                print(json.dumps(data, indent=2))
                return False
        else:
            print(f"❌ Erro: {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Timeout - O modelo demorou muito para responder")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Erro de conexão - Verifique se o Docker está rodando")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_adk_format():
    """Testa com formato que o ADK usaria"""
    
    print("\n\n🔧 Testando formato ADK")
    print("=" * 60)
    
    # Simula como o ADK chamaria
    payload = {
        "model": MODEL_HASH,
        "messages": [
            {
                "role": "system",
                "content": "Você é um assistente útil."
            },
            {
                "role": "user",
                "content": "Liste 3 capitais brasileiras."
            }
        ],
        "max_tokens": 100,
        "temperature": 0.7,
        "stream": False
    }
    
    try:
        response = requests.post(ENDPOINT, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            message = data['choices'][0]['message']['content']
            print(f"✅ Resposta: {message}")
            return True
        else:
            print(f"❌ Erro: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    print("🚀 TESTE DE LLM LOCAL\n")
    
    # Teste básico
    test1 = test_local_llm()
    
    # Teste com formato ADK
    test2 = test_with_adk_format()
    
    print("\n" + "=" * 60)
    print("📊 RESULTADO FINAL:")
    print("=" * 60)
    print(f"   Teste Básico: {'✅ PASSOU' if test1 else '❌ FALHOU'}")
    print(f"   Teste ADK: {'✅ PASSOU' if test2 else '❌ FALHOU'}")
    print("=" * 60)
    
    if test1 and test2:
        print("\n✨ Todos os testes passaram! O modelo está pronto para uso.")
    else:
        print("\n⚠️  Alguns testes falharam. Verifique a configuração.")
