
import os
import asyncio
from litellm import completion
import time

# Configurando chave
os.environ["DEEPSEEK_API_KEY"] = "sk-7a7156a4c0e245a59fbca4febda7a759"

def test_deepseek():
    print("Iniciando teste de conexao com Deepseek via LiteLLM...")
    max_retries = 3
    for i in range(max_retries):
        try:
            print(f"Tentativa {i+1}/{max_retries}...")
            # Chamada sincrona padrao do litellm
            response = completion(
                model="deepseek/deepseek-chat", 
                messages=[{"role": "user", "content": "Oi, teste de conexao."}],
                timeout=120,  # Timeout aumentado
                num_retries=3
            )
            print("Sucesso!")
            print(response)
            return
        except Exception as e:
            print(f"Erro capturado na tentativa {i+1}: {e}")
            time.sleep(2)
    print("Todas as tentativas falharam.")

if __name__ == "__main__":
    test_deepseek()
