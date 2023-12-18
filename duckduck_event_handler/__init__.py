import json
import requests
from datetime import datetime
from websocket import create_connection

class DuckDuckEventHandler:

    def __init__(self, illuminationServiceURI, serverURI, scheduler, mqttPublish, device_code, device_secret):
        self.illuminationServiceURI = illuminationServiceURI
        self.serverURI = serverURI
        self.scheduler = scheduler
        self.scheduler.start()
        self.handlers = {
            "register": self.on_register,
            "hsl": self.on_update_hsl,
            "cct": self.on_update_cct,
            "power": self.on_update_power,
            "create-alarm": self.on_create_alarm,
            "update-alarm": self.on_update_alarm,
            "delete-alarm": self.on_delete_alarm,
            "update-sweet-dreams": self.on_update_sweet_dreams,
        }
        self.mqttPublish = mqttPublish
        self.device_code = device_code
        self.device_secret = device_secret
        self.SWEET_DREAMS_ACTIVE = True
        self.DIM_MINS = 1
        self.LULLABY = "https://storage.googleapis.com/duckduck-bucket/lullaby-song/Instrument/acoustic-guitar-loop.mp3"
        self.fetch_sweet_dreams()
        self.fetch_alarms()

    def login(self):
        login_r = requests.post(f"{self.serverURI}/device-login", json={
            "device_code": self.device_code,
            "secret": self.device_secret
        })
        if login_r.status_code != 200:
            print("Device login failed", self.device_code)
            return
        token = json.loads(login_r.content)
        self.token = token["data"]["token"]

    def fetch_sweet_dreams(self):
        self.login()
        data = requests.get(f"{self.serverURI}/alarms",
                         headers={
                             "Authorization": f"Bearer {self.token}"
                         }
                         )
        data = json.loads(data.content)
        data = data["data"]
        print(self.SWEET_DREAMS_ACTIVE, self.DIM_MINS, self.LULLABY)

    def fetch_alarms(self):
        self.login()
        data = requests.get(f"{self.serverURI}/alarms",
                         headers={
                             "Authorization": f"Bearer {self.token}"
                         }
                         )
        data = json.loads(data.content)
        data = data["data"]
        self.clear_all_alarm()
        for alarm in data:
            self.on_create_alarm(json.dumps(alarm))

    def is_handling(self, subtopic):
        return subtopic in self.handlers
    
    def ws_send(self, topic, payload):
        ws = create_connection("ws://localhost:8080")
        ws.send(json.dumps({
            "topic": f"{self.device_code}/{topic}",
            "payload": json.loads(payload)
        }))
        ws.close()

    def on_message(self, subtopic, payload):
        self.ws_send(subtopic, payload)
        self.handlers[subtopic](payload)

    def on_register(self, payload):
        self.fetch_sweet_dreams()
        self.fetch_alarms()

    def on_update_hsl(self, payload):
        data = json.loads(payload)
        r = requests.post(f"{self.illuminationServiceURI}/hsl", json=data)
        # print(r.text)
        return r.text

    def on_update_cct(self, payload):
        data = json.loads(payload)
        data["temp"] = data["temp"]/50 - 60
        r = requests.post(f"{self.illuminationServiceURI}/cct", json=data)
        # print(r.text)
        return r.text

    def on_update_power(self, payload):
        data = json.loads(payload)
        r = requests.post(f"{self.illuminationServiceURI}/power", json=data)
        # print(r.text)
        return r.text

    def format_cron_day(self, day_list):
        if len(day_list) == 7:
            return "*"
        else:
            return ",".join(day_list)
        
    def backward_one_day(self, day_list):
        days = {"sun": "sat", "mon": "sun", "tue": "mon", "wed": "tue", "thu": "wed", "fri": "thu", "sat": "fri"}
        new_day_list= []
        for day in day_list:
            new_day_list.append(days[day])
        return new_day_list
        
    def trigger_alarm(self, id):
        self.ws_send("trigger-alarm", json.dumps({
            "id": id
        }))

    def dim_light(self):
        r = requests.post(f"{self.illuminationServiceURI}/dim")
        payload = {
            "audioUrl": self.LULLABY
        }
        print("sending ", payload)
        self.ws_send("sweet-dreams", json.dumps(payload))
        return r.text
    
    def light_off(self):
        r = requests.post(f"{self.illuminationServiceURI}/power", json={
            'on': False
        })
        self.ws_send("sweet-dreams", json.dumps({}))
        return r.text

    def on_create_alarm(self, payload):
        data = json.loads(payload)
        active = data["is_active"]["status"]
        if not active:
            return
        
        bed = data["bed_time"]
        wake = data["wake_up_time"]

        self.scheduler.add_job(
            self.trigger_alarm,
            "cron",
            id='w' + data["id"],
            day_of_week=self.format_cron_day(data["repeat_days"]),
            hour=wake["hours"],
            minute=wake["minutes"],
            args=[data["id"]]
        )

        dim_minutes = bed["minutes"] - self.DIM_MINS
        dim_hours = bed["hours"] - 1 if dim_minutes < 0 else bed["hours"]
        dim_days = self.backward_one_day(data["repeat_days"]) if dim_hours < 0 else data["repeat_days"]

        dim_minutes %= 60
        dim_hours %= 24

        self.scheduler.add_job(
            self.dim_light,
            "cron",
            id='d' + data["id"],
            day_of_week=self.format_cron_day(dim_days),
            hour=dim_hours,
            minute=dim_minutes
        )

        self.scheduler.add_job(
            self.light_off,
            "cron",
            id='o' + data["id"],
            day_of_week=self.format_cron_day(data["repeat_days"]),
            hour=bed["hours"],
            minute=bed["minutes"]
        )

        start = data["sunrise"]["start_time"]
        peak = data["sunrise"]["peak_time"]
        if start != None and peak != None:
            start = datetime(2023, 10, 31, start["hours"], start["minutes"])
            peak = datetime(2023, 10, 31, peak["hours"], peak["minutes"])

            if start > peak:
                start = datetime(2023, 10, 30, start.hour, start.minute)

            diff = (peak - start).seconds
            time_unit = diff / 185
            self.scheduler.add_job(
                self.start_sunrise,
                "cron",
                id='s' + data["id"],
                day_of_week=self.format_cron_day(data["repeat_days"]),
                hour=start.hour,
                minute=start.minute,
                args=[time_unit]
            )
            print(self.scheduler.get_jobs())
        # print(r.text)

    def on_update_alarm(self, payload):
        self.on_delete_alarm(payload)
        self.on_create_alarm(payload)

    def on_delete_alarm(self, payload):
        data = json.loads(payload)
        
        if self.scheduler.get_job("w" + data["id"]) != None:
            self.scheduler.remove_job("w" + data["id"])
        if self.scheduler.get_job("d" + data["id"]) != None:
            self.scheduler.remove_job("d" + data["id"])
        if self.scheduler.get_job("o" + data["id"]) != None:
            self.scheduler.remove_job("o" + data["id"])
        if self.scheduler.get_job("s" + data["id"]) != None:
            self.scheduler.remove_job("s" + data["id"])

    def clear_all_alarm(self):
        print(self.scheduler.get_jobs())
        jobs = self.scheduler.get_jobs()
        for job in jobs:
            print(job)

    def on_update_sweet_dreams(self, payload):
        data = json.loads(payload)
        self.SWEET_DREAMS_ACTIVE = data["dim_light"]["active"]
        self.DIM_MINS = data["dim_light"]["duration"]
        self.LULLABY = data["current_lullaby_song_path"]

    def start_sunrise(self, time_unit):
        r = requests.post(f"{self.illuminationServiceURI}/sunrise", json={"time_unit": time_unit})
        return r.text