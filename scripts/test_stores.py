import requests
import os
from dotenv import load_dotenv

# Carregar variaveis de ambiente se necessario (para API Key)
load_dotenv('assistente/.env')

try:
    response = requests.get('http://127.0.0.1:3001/api/knowledge/stores')
    print(f"Status Code: {response.status_code}")
    print(f"Content: {response.text}")
except Exception as e:
    print(f"Error: {e}")
