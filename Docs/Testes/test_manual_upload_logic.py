
import os
import time
from google.genai import Client
from dotenv import load_dotenv

load_dotenv('tea/.env')
api_key = os.getenv('GOOGLE_API_KEY')
client = Client(api_key=api_key)

try:
    # 1. Create a store
    print("Creating test store...")
    store = client.file_search_stores.create(config={'display_name': 'TEST_MANUAL_LOGIC_STORE'})
    print(f"Store created: {store.name}")

    # 2. Create a dummy file
    filename = "test_persistence_doc.txt"
    with open(filename, "w") as f:
        f.write("This is a test document to verify persistence logic.")

    try:
        # 3. Upload file (Simulating Step 1 of app.py)
        print("Uploading file to Files API...")
        uploaded_file = client.files.upload(file=filename)
        print(f"File uploaded: {uploaded_file.name}")

        # 4. Attach to store (Simulating Step 2 of app.py)
        print(f"Attaching file {uploaded_file.name} to store {store.name}...")
        client.file_search_stores.import_file(
            file_search_store_name=store.name,
            file_name=uploaded_file.name
        )
        print("✅ File attached successfully.")

        # 5. Verify persistence
        print("Verifying file presence in store...")
        time.sleep(2) # Give it a moment
        files_in_store = list(client.file_search_stores.files.list(file_search_store_id=store_id))
        found = any(f.name == uploaded_file.name for f in files_in_store)
        
        if found:
            print("✅ SUCCESS: File found in store listing.")
        else:
            print("❌ FAILURE: File NOT found in store listing.")

    finally:
        # Cleanup
        print("Cleaning up...")
        if os.path.exists(filename):
            os.remove(filename)
        client.file_search_stores.delete(name=store.name)
        # Note: In a real app we might not delete the store, but here we clean up.
        # We can't delete the file from Files API easily without the ID, but uploaded_file has it.
        try:
            client.files.delete(name=uploaded_file.name)
        except:
            pass
        print("Cleanup done.")

except Exception as e:
    print(f"Error: {e}")
