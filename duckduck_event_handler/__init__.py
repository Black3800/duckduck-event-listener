import json
import requests

def on_update_hsl(illuminationServiceURI, payload):
    data = json.loads(payload)
    r = requests.post(f"{illuminationServiceURI}/hsl", json=data)
    # print(r.text)
    return r.text

def on_update_cct(illuminationServiceURI, payload):
    data = json.loads(payload)
    r = requests.post(f"{illuminationServiceURI}/cct", json=data)
    # print(r.text)
    return r.text

def on_update_power(illuminationServiceURI, payload):
    data = json.loads(payload)
    r = requests.post(f"{illuminationServiceURI}/power", json=data)
    # print(r.text)
    return r.text