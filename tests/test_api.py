# test_api.py
import requests
import pprint

url = "http://127.0.0.1:8000/analyse"
file_path = r".\data\raw\variant_A_dataset_al_naseem_trading.csv" 

try:
    with open(file_path, 'rb') as f:
        files = {'file': (file_path, f, 'text/csv')}
        response = requests.post(url, files=files)
        
    print(f"Status Code: {response.status_code}\n")
    pprint.pprint(response.json())
except Exception as e:
    print(f"Error: {e}")
