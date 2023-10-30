import json
import requests

def on_update_hsl(illuminationServiceURI, payload):
    data = json.loads(payload)
    r = requests.post(f"{illuminationServiceURI}/hsl", json=data)
    print(r.text)