import os
import time
import json
from google import genai
from google.genai import types

def test_file_upload_rag():
    # Load API Key from dados/config.json
    try:
        with open('dados/config.json', 'r') as f:
            config = json.load(f)
            api_key = config.get('api_key')
    except Exception as e:
        print(f"Error loading config: {e}")
        return

    if not api_key:
        print("Error: api_key not found in dados/config.json")
        return

    client = genai.Client(api_key=api_key)
    
    file_path = "test_file.txt"
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found")
        return

    try:
        print("Uploading file...")
        file_ref = client.files.upload(file=file_path)
        print(f"File uploaded: {file_ref.name}")
        
        # Wait for processing? Usually fast for small text files.
        # But let's check state just in case if it's needed, though generate_content handles it.
        
        prompt = "O que é o O-eDOCS?"
        model_name = "gemini-2.0-flash" 
        # Or try 'gemini-2.0-flash' if 1.5 fails
        
        print(f"Generating content with model {model_name}...")
        
        response = client.models.generate_content(
            model=model_name,
            contents=[file_ref, prompt]
        )
        
        print("Response received:")
        print(response.text)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_file_upload_rag()
