
import os
from google.genai import Client
from dotenv import load_dotenv

load_dotenv('tea/.env')
client = Client(api_key=os.getenv('GOOGLE_API_KEY'))

with open('sdk_attributes.txt', 'w') as f:
    f.write("Client attributes:\n")
    f.write(str(dir(client)) + "\n\n")
    
    fs = client.file_search_stores
    f.write("FileSearchStores attributes:\n")
    f.write(str(dir(fs)) + "\n\n")
    
    if hasattr(fs, 'documents'):
        f.write("FileSearchStores.documents attributes:\n")
        f.write(str(dir(fs.documents)) + "\n\n")


