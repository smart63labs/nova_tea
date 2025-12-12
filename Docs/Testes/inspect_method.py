
import os
from google.genai import Client
from dotenv import load_dotenv

load_dotenv('tea/.env')
client = Client(api_key=os.getenv('GOOGLE_API_KEY'))

import inspect
print("Signature:", inspect.signature(client.file_search_stores.import_file))
