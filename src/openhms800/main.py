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
    except KeyboardInterrupt:
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

    # Run the web server and background tasks concurrently
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", config.web_port)

    await state.add_log("INFO", f"Web UI available at http://localhost:{config.web_port}")

    # Start tasks
    tasks = [
        site.start(),
        inverter_task.run(),
        mqtt_task.run()
    ]

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        await state.add_log("INFO", "Service shutting down...")
    finally:
        inverter_task.stop()
        mqtt_task.stop()
        await runner.cleanup()

