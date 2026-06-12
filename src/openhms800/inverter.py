import asyncio
import traceback

from hms800_ble import HMS800Client
from .state import SharedState
from .config import AppConfig
from .models import PVChannel

class InverterTask:
    def __init__(self, config: AppConfig, state: SharedState):
        self.config = config
        self.state = state
        self.running = True

    async def run(self):
        await self.state.add_log("INFO", f"Starting Inverter Polling Task (Interval: {self.config.scan_interval}s)")
        
        while self.running:
            try:
                await self.state.add_log("INFO", f"Connecting to Inverter {self.config.ble_address}...")
                async with HMS800Client(
                    self.config.ble_address, 
                    self.config.inverter_sn, 
                    activation_id=self.config.activation_id
                ) as client:
                    await client.connect()
                    await self.state.update_metrics(is_connected=True)

                    # Fetch static info once
                    try:
                        cfg = await client._hf.async_get_config()
                        net = await client._hf.async_network_info()
                        # Assuming library provides this info in standard dict/protobuf
                        await self.state.update_metrics(
                            inverter_info={
                                "inverter_sn": self.config.inverter_sn,
                                "hardware_model": "HMS-800-2WB",
                                "wifi_ssid": net.get("ssid", "Unknown") if isinstance(net, dict) else "Unknown"
                            }
                        )
                    except Exception as e:
                        await self.state.add_log("WARNING", f"Could not fetch device info: {e}")

                    await self.state.add_log("INFO", "Connected and authenticated.")

                    while self.running:
                        try:
                            data = await client.get_real_data()
                            await self._process_data(data)
                            await asyncio.sleep(self.config.scan_interval)
                        except Exception as e:
                            await self.state.add_log("ERROR", f"Poll error: {str(e)}")
                            break # Reconnect on error
            except Exception as e:
                await self.state.update_metrics(is_connected=False)
                await self.state.add_log("ERROR", f"Connection failed: {str(e)}")
                await asyncio.sleep(10) # Wait before retry

    async def _process_data(self, data: dict):
        """Maps raw library dict to structured InverterMetrics."""
        sgs_list = data.get("sgsData", [])
        pv_list = data.get("pvData", [])
        
        metrics_update = {}
        
        if sgs_list:
            sgs = sgs_list[0]
            metrics_update["active_power"] = sgs.get("activePower", 0) / 10.0
            metrics_update["grid_voltage"] = sgs.get("voltage", 0) / 10.0
            metrics_update["temperature"] = sgs.get("temperature", 0) / 10.0

        pv_channels = []
        for i, pv in enumerate(pv_list):
            pv_channels.append(PVChannel(
                id=i + 1,
                voltage=pv.get("voltage", 0) / 10.0,
                current=pv.get("current", 0) / 10.0,
                power=pv.get("power", 0) / 10.0
            ))
        metrics_update["pv_channels"] = pv_channels
        
        if (daily := data.get("dtuDailyEnergy")) is not None:
            metrics_update["daily_energy"] = daily / 100.0

        await self.state.update_metrics(**metrics_update)
        await self.state.add_log("DEBUG", f"Metrics updated: {metrics_update.get('active_power')}W")

    def stop(self):
        self.running = False
