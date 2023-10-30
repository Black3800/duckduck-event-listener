import paho.mqtt.client as mqtt
import json

from apscheduler.schedulers.background import BackgroundScheduler

from duckduck_event_handler import DuckDuckEventHandler


class DeviceConfig():
    def __init__(self, config_obj):
        self.code = config_obj["device_code"]
        self.key = config_obj["device_key"]
        self.username = config_obj["mqtt_username"]
        self.password = config_obj["mqtt_password"]
        self.mqtt_host = config_obj["mqtt_host"]
        self.mqtt_port = config_obj["mqtt_port"]
        self.illumination_service = config_obj["illumination_service"]

def get_device_config():
    f = open(".device_config", "r")
    return json.loads(f.read())

# The callback for when the client receives a CONNACK response from the server.
def on_connect(device_code, client, userdata, flags, reasonCode, properties):
    print("Connected with result code "+str(reasonCode))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe(f"{device_code}/#")

# The callback for when a PUBLISH message is received from the server.
def on_message(handler_instance, client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))
    subtopic = msg.topic.split("/")[1]
    if handler_instance.is_handling(subtopic):
        handler_instance.on_message(subtopic, msg.payload)
    else:
        print(f"unknown topic received: {msg.topic}")

device_config = DeviceConfig(get_device_config())

scheduler = BackgroundScheduler()

event_handler = DuckDuckEventHandler(device_config.illumination_service, scheduler)

client = mqtt.Client(client_id='', userdata=None, protocol=mqtt.MQTTv5)
client.on_connect = lambda c,u,f,r,p: on_connect(device_config.code, c, u, f, r, p)
client.on_message = lambda c,u,m: on_message(event_handler, c, u, m)

client.tls_set(tls_version=mqtt.ssl.PROTOCOL_TLS)
client.username_pw_set(device_config.username, device_config.password)
client.connect(host=device_config.mqtt_host, port=device_config.mqtt_port, keepalive=60)

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_forever()