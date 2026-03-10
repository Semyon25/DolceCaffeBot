import json
import os
from datetime import date
from config import schedule_file


def load_schedule():

    if schedule_file is None or not os.path.exists(schedule_file):
        return {}

    with open(schedule_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return {date.fromisoformat(k): v for k, v in data.items()}


def save_schedule(schedule):
    if schedule_file is None:
        return

    data = {d.isoformat(): name for d, name in schedule.items()}

    os.makedirs(os.path.dirname(schedule_file), exist_ok=True)

    with open(schedule_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
