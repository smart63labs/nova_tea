import requests

url = "http://127.0.0.1:3001/api/knowledge/stores/fileSearchStores/secretaria-da-fazenda-eij7m6bp2i0b/files"
try:
    resp = requests.get(url)
    print(resp.status_code)
    print(resp.text)
except Exception as e:
    print(e)
