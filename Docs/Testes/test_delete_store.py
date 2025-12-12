import requests
import json
import sys
import os

BASE_URL = "http://127.0.0.1:3001"

def test_delete_non_existent_store():
    print("Testing delete of non-existent store...")
    fake_store_name = "fileSearchStores/non-existent-store-12345"
    
    try:
        url = f"{BASE_URL}/api/knowledge/stores/{fake_store_name}"
        print(f"DELETE {url}")
        res = requests.delete(url)
        
        print(f"Status Code: {res.status_code}")
        print(f"Response: {res.text}")
        
        if res.status_code == 200:
            print("SUCCESS: Handled non-existent store gracefully.")
            try:
                data = res.json()
                if data.get('status') == 'success':
                    print("SUCCESS: JSON status is success.")
                else:
                    print("WARNING: JSON status not success.")
            except:
                print("ERROR: Response is not JSON.")
        else:
            print("FAILURE: Did not return 200 for non-existent store.")
            
    except Exception as e:
        print(f"Exception during test: {e}")

if __name__ == "__main__":
    test_delete_non_existent_store()
