import asyncio
import logging
import signal
from aiohttp import web
import aiohttp_jinja2
import jinja2
import os

from .config import AppConfig
from .state import SharedState
from .mqtt import MQTTTask
from .inverter import InverterTask
from .web import setup_routes

def main():
    try:
        asyncio.run(run_main())
    except (KeyboardInterrupt, SystemExit):
        pass

async def run_main():
    # 1. Load Config
    config = AppConfig.load()

    # 2. Initialize State
    state = SharedState()
    await state.add_log("INFO", "OpenHMS-800 Service starting...")

    # 3. Setup Web App
    app = web.Application()
    app["state"] = state
    app["config"] = config

    # Setup Jinja2
    template_path = os.path.join(os.path.dirname(__file__), "templates")
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(template_path))

    setup_routes(app)

    # 4. Prepare Background Tasks
    inverter_task = InverterTask(config, state)
    mqtt_task = MQTTTask(config, state)

    # Setup Shutdown Handling
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    # Run the web server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", config.web_port)
    await site.start()

    await state.add_log("INFO", f"Web UI available at http://localhost:{config.web_port}")

    # Start background tasks
    bg_tasks = [
        asyncio.create_task(inverter_task.run()),
        asyncio.create_task(mqtt_task.run())
    ]

    # Wait for stop signal
    try:
        await stop_event.wait()
    except asyncio.CancelledError:
        pass

    await state.add_log("INFO", "Service shutting down gracefully...")
    
    # Signal tasks to stop
    inverter_task.stop()
    mqtt_task.stop()

    # Wait for tasks to finish (includes BLE disconnect sequence)
    await asyncio.gather(*bg_tasks, return_exceptions=True)
    await runner.cleanup()

if __name__ == "__main__":
    main()

