import json
import requests
from datetime import datetime

class DuckDuckEventHandler:

    def __init__(self, illuminationServiceURI, scheduler, mqttPublish, device_code):
        self.illuminationServiceURI = illuminationServiceURI
        self.scheduler = scheduler
        self.scheduler.start()
        self.handlers = {
            "hsl": self.on_update_hsl,
            "cct": self.on_update_cct,
            "power": self.on_update_power,
            "create-alarm": self.on_create_alarm,
            "update-alarm": self.on_update_alarm,
            "delete-alarm": self.on_delete_alarm
        }
        self.mqttPublish = mqttPublish
        self.device_code = device_code

    def is_handling(self, subtopic):
        return subtopic in self.handlers

    def on_message(self, subtopic, payload):
        self.handlers[subtopic](payload)

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
        
    def trigger_alarm(self, id):
        self.mqttPublish(self.device_code + "/trigger-alarm", json.dumps({
            "id": id
        }))

    def dim_light(self):
        r = requests.post(f"{self.illuminationServiceURI}/dim")
        self.mqttPublish(self.device_code + "/sweet-dreams", json.dumps({
            "audioUrl": "kkk"
        }))
        return r.text
    
    def light_off(self):
        r = requests.post(f"{self.illuminationServiceURI}/power", json={
            'on': False
        })
        self.mqttPublish(self.device_code + "/sweet-dreams", json.dumps({}))
        return r.text

    def on_create_alarm(self, payload):
        data = json.loads(payload)
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

        self.scheduler.add_job(
            self.dim_light,
            "cron",
            id='d' + data["id"],
            day_of_week=self.format_cron_day(data["repeat_days"]),
            hour=bed["hours"],
            minute=bed["minutes"] - 1
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

    def start_sunrise(self, time_unit):
        r = requests.post(f"{self.illuminationServiceURI}/sunrise", json={"time_unit": time_unit})
        return r.text