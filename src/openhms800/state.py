import time
import asyncio
import os
from typing import List
from .models import InverterMetrics, LogEntry, InverterInfo

class SharedState:
    def __init__(self, log_file="service.log"):
        self.metrics = InverterMetrics()
        self.inverter_info = InverterInfo()
        self.log_file = log_file
        self.lock = asyncio.Lock()

    async def update_metrics(self, inverter_info=None, **kwargs):
        async with self.lock:
            # Update metrics
            data = self.metrics.model_dump()
            data.update(kwargs)
            data["last_update"] = time.time()
            self.metrics = InverterMetrics.model_validate(data)

            # Update inverter_info
            if inverter_info:
                info_data = self.inverter_info.model_dump()
                info_data.update(inverter_info)
                info_data["last_update"] = time.time()
                self.inverter_info = InverterInfo.model_validate(info_data)

    async def add_log(self, level: str, message: str):
        async with self.lock:
            timestamp = time.time()
            entry = f"{timestamp}|{level}|{message}\n"
            with open(self.log_file, "a") as f:
                f.write(entry)
            print(f"[{level}] {message}")

    @property
    def logs(self) -> List[LogEntry]:
        entries = []
        if os.path.exists(self.log_file):
            with open(self.log_file, "r") as f:
                # Get last 100 lines
                lines = f.readlines()[-100:]
                for line in lines:
                    parts = line.strip().split("|")
                    if len(parts) == 3:
                        entries.append(LogEntry(timestamp=float(parts[0]), level=parts[1], message=parts[2]))
        return entries
