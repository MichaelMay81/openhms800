import time
import asyncio
import os
from typing import List
from .models import InverterMetrics, LogEntry, InverterInfo

class SharedState:
    def __init__(self):
        self.metrics = InverterMetrics()
        self.inverter_info = InverterInfo()
        self._logs: List[LogEntry] = []
        self.max_logs = 200
        self.last_error = "None"
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

    async def update_error(self, error_msg: str):
        async with self.lock:
            self.last_error = error_msg

    async def add_log(self, level: str, message: str):

        async with self.lock:
            timestamp = time.time()
            entry = LogEntry(timestamp=timestamp, level=level, message=message)
            self._logs.append(entry)
            
            # Keep only the last N logs
            if len(self._logs) > self.max_logs:
                self._logs = self._logs[-self.max_logs:]
                
            print(f"[{level}] {message}")

    @property
    def logs(self) -> List[LogEntry]:
        # Return a copy to avoid modification during iteration
        return list(self._logs)
