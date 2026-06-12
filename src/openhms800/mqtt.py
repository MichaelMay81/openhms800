import asyncio
import json
import aiomqtt
from .config import AppConfig
from .state import SharedState

class MQTTTask:
    def __init__(self, config: AppConfig, state: SharedState):
        self.config = config
        self.state = state
        self.running = True

    async def run(self):
        if not self.config.mqtt_enabled:
            await self.state.add_log("INFO", "MQTT disabled, skipping.")
            return

        await self.state.add_log("INFO", f"Starting MQTT publisher to {self.config.mqtt_broker}...")
        
        while self.running:
            try:
                auth = None
                if self.config.mqtt_username:
                    auth = aiomqtt.UsernamePassword(self.config.mqtt_username, self.config.mqtt_password)

                async with aiomqtt.Client(
                    hostname=self.config.mqtt_broker, 
                    port=self.config.mqtt_port,
                    identifier=self.config.mqtt_client_id,
                    username=self.config.mqtt_username,
                    password=self.config.mqtt_password,
                    keepalive=self.config.mqtt_keepalive
                ) as client:
                    await self.state.add_log("INFO", f"MQTT Connected to {self.config.mqtt_broker}:{self.config.mqtt_port}.")
                    while self.running:
                        # 1. Publish Status (Always send)
                        await client.publish(
                            f"{self.config.mqtt_prefix}/{self.config.inverter_sn}/status",
                            "online" if self.state.metrics.is_connected else "offline",
                            qos=self.config.mqtt_qos
                        )
                        
                        # 2. Publish Metrics only if connected
                        if self.state.metrics.is_connected:
                            payload = self.state.metrics.model_dump_json()
                            await client.publish(
                                f"{self.config.mqtt_prefix}/{self.config.inverter_sn}/data", 
                                payload,
                                qos=self.config.mqtt_qos
                            )
                            await self.state.add_log("DEBUG", f"Published to {self.config.mqtt_prefix}/{self.config.inverter_sn}/data")
                        else:
                            await self.state.add_log("DEBUG", "Inverter offline, sending heartbeat only.")

                        await asyncio.sleep(self.config.scan_interval)
            except Exception as e:
                await self.state.add_log("ERROR", f"MQTT error: {e}. Retrying in 10s...")
                await asyncio.sleep(10)
    
    def stop(self):
        self.running = False
