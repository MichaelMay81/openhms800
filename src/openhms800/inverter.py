import asyncio
import traceback

from hiflow_ble.hiflow import HiFlow
from google.protobuf.json_format import MessageToDict
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
        
        failure_count = 0
        MAX_FAILURES = 5
        
        while self.running:
            try:
                await self.state.add_log("INFO", f"Connecting to Inverter {self.config.ble_address}...")
                
                async with HiFlow(
                    self.config.ble_address, 
                    sn=self.config.inverter_sn, 
                    pin=self.config.inverter_pin,
                    timeout=30
                ) as hf:
                    # Step 0: Extract encRand (V0 Handshake)
                    await hf.async_extract_enc_rand()
                    
                    # Step 1: CommCmd Handshake (Login/Pairing)
                    success = await hf.async_do_comm_cmd_handshake()
                    if not success:
                        raise Exception("Handshake failed")

                    failure_count = 0 # Reset failures on successful connection
                    await self.state.update_error("None")
                    await self.state.update_metrics(is_connected=True)

                    # Fetch static info once
                    try:
                        cfg = await hf.async_get_config()
                        app_info = await hf.async_app_information_data()
                        
                        cfg_dict = MessageToDict(cfg, preserving_proto_field_name=True) if cfg else {}
                        app_dict = MessageToDict(app_info, preserving_proto_field_name=True) if app_info else {}
                        dtu_info = app_dict.get("dtu_info", {})
                        
                        # Handle potential types (e.g. firmware version as int)
                        fw_ver = dtu_info.get("dtu_sw_version", "Unknown")
                        if not isinstance(fw_ver, str):
                            fw_ver = str(fw_ver)

                        await self.state.update_metrics(
                            inverter_info={
                                "inverter_sn": self.config.inverter_sn,
                                "hardware_model": "HMS-800-2WB",
                                "firmware_version": fw_ver,
                                "wifi_ssid": cfg_dict.get("wifi_ssid", "Unknown")
                            }
                        )
                    except Exception as e:
                        await self.state.add_log("WARNING", f"Could not fetch device info: {e}")

                    await self.state.add_log("INFO", "Connected and authenticated.")

                    while self.running:
                        try:
                            resp = await hf.async_get_real_data_new()
                            if resp:
                                data = MessageToDict(resp, preserving_proto_field_name=True)
                                await self._process_data(data)
                            await asyncio.sleep(self.config.scan_interval)
                        except Exception as e:
                            await self.state.add_log("ERROR", f"Poll error: {str(e)}")
                            break # Reconnect on error
            except Exception as e:
                failure_count += 1
                await self.state.update_error(str(e))
                await self.state.update_metrics(is_connected=False)
                
                # Exponential backoff: 10s, 20s, 40s, 80s... max 300s
                backoff = min(10 * (2 ** (failure_count - 1)), 300)
                
                if failure_count >= MAX_FAILURES:
                    await self.state.add_log("ERROR", f"Connection failed {failure_count} times. Sleeping for 5 minutes.")
                    backoff = 300
                    failure_count = 0 # Reset after long sleep
                else:
                    await self.state.add_log("ERROR", f"Connection failed: {str(e)}. Retrying in {backoff}s...")
                
                await asyncio.sleep(backoff)

    async def _process_data(self, data: dict):
        """Maps raw library dict to structured InverterMetrics."""
        sgs_list = data.get("sgs_data", [])
        pv_list = data.get("pv_data", [])
        
        metrics_update = {}
        
        if sgs_list:
            sgs = sgs_list[0]
            metrics_update["active_power"] = (sgs.get("active_power") or 0) / 10.0
            metrics_update["grid_voltage"] = (sgs.get("voltage") or 0) / 10.0
            metrics_update["temperature"] = (sgs.get("temperature") or 0) / 10.0

        pv_channels = []
        sum_daily = 0.0
        sum_total = 0.0
        sum_dc_power = 0.0
        for i, pv in enumerate(pv_list):
            d_raw = pv.get("energy_daily") or 0
            t_raw = pv.get("energy_total") or 0
            d_energy = d_raw / 1000.0
            t_energy = t_raw / 1000.0
            sum_daily += d_energy
            sum_total += t_energy
            dc_power = (pv.get("power") or 0) / 10.0
            sum_dc_power += dc_power
            pv_channels.append(PVChannel(
                id=i + 1,
                voltage=(pv.get("voltage") or 0) / 10.0,
                current=(pv.get("current") or 0) / 100.0,
                power=dc_power,
                daily_energy=d_energy,
                total_energy=t_energy
            ))
        metrics_update["pv_channels"] = pv_channels
        
        # Calculate efficiency
        ac_power = metrics_update.get("active_power", 0.0)
        if sum_dc_power > 0:
            metrics_update["efficiency"] = min((ac_power / sum_dc_power) * 100.0, 100.0)
        else:
            metrics_update["efficiency"] = 0.0

        # Use DTU level daily energy if available and non-zero, else use sum
        dtu_daily_raw = data.get("dtu_daily_energy") or 0
        dtu_daily = dtu_daily_raw / 1000.0
        metrics_update["daily_energy"] = dtu_daily if dtu_daily > 0 else sum_daily
        
        # We don't have dtuTotalEnergy in this firmware version/protobuf, so use sum of PV channels
        metrics_update["total_energy"] = sum_total

        await self.state.update_metrics(**metrics_update)
        await self.state.add_log("DEBUG", f"Metrics updated: {metrics_update.get('active_power')}W, Today: {metrics_update.get('daily_energy')}kWh")

    def stop(self):
        self.running = False
