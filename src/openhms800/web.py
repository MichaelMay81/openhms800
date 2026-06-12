import datetime
import asyncio
from aiohttp import web
import aiohttp_jinja2
import jinja2
from .state import SharedState
from .config import AppConfig

async def get_dashboard_context(request):
    state: SharedState = request.app["state"]
    last_update_str = "Never"
    if state.metrics.last_update > 0:
        last_update_str = datetime.datetime.fromtimestamp(state.metrics.last_update).strftime("%H:%M:%S")
    return {
        "metrics": state.metrics,
        "last_update_str": last_update_str
    }

async def get_logs_context(request):
    state: SharedState = request.app["state"]
    logs_data = []
    for log in state.logs:
        logs_data.append({
            "time_str": datetime.datetime.fromtimestamp(log.timestamp).strftime("%H:%M:%S"),
            "level": log.level,
            "message": log.message
        })
    return {"logs": logs_data}

async def handle_dashboard(request):
    context = await get_dashboard_context(request)
    if "HX-Request" in request.headers:
        return aiohttp_jinja2.render_template("dashboard.html", request, context)
    return aiohttp_jinja2.render_template("base.html", request, {"page": "dashboard", **context})

async def handle_logs(request):
    context = await get_logs_context(request)
    if "HX-Request" in request.headers:
        return aiohttp_jinja2.render_template("logs.html", request, context)
    return aiohttp_jinja2.render_template("base.html", request, {"page": "logs", **context})

async def handle_settings(request):
    config = request.app["config"]
    if "HX-Request" in request.headers:
        return aiohttp_jinja2.render_template("settings.html", request, {"config": config})
    return aiohttp_jinja2.render_template("base.html", request, {"page": "settings", "config": config})

async def api_settings_post(request):
    data = await request.post()
    config = request.app["config"]
    state = request.app["state"]
    
    try:
        # Update config object
        config.ble_address = data.get("ble_address", config.ble_address)
        config.inverter_sn = data.get("inverter_sn", config.inverter_sn)
        config.activation_id = data.get("activation_id", config.activation_id)
        config.scan_interval = int(data.get("scan_interval", config.scan_interval))
        config.mqtt_enabled = data.get("mqtt_enabled") == "on"
        config.mqtt_broker = data.get("mqtt_broker", config.mqtt_broker)
        config.mqtt_port = int(data.get("mqtt_port", config.mqtt_port))
        config.mqtt_client_id = data.get("mqtt_client_id", config.mqtt_client_id)
        config.mqtt_prefix = data.get("mqtt_prefix", config.mqtt_prefix)
        config.mqtt_username = data.get("mqtt_username") or None
        config.mqtt_password = data.get("mqtt_password") or None
        
        # Save to disk
        config.save()
        await state.add_log("INFO", "Configuration updated and saved to disk.")
        
        return web.Response(text="<span style='color: var(--accent-green);'>Configuration saved! Restart service to apply.</span>", content_type='text/html')
    except Exception as e:
        return web.Response(text=f"<span style='color: var(--error-color);'>Error: {str(e)}</span>", content_type='text/html')

async def api_restart(request):
    state = request.app["state"]
    await state.add_log("WARNING", "Restart requested via Web UI...")
    
    # Schedule restart after a small delay to allow response to be sent
    async def do_restart():
        await asyncio.sleep(1)
        import sys
        import os
        await state.add_log("INFO", "Re-executing process...")
        # If run with -m service.main, we need to reconstruct the call
        # os.execv expects the executable path and a list of arguments starting with the executable
        python = sys.executable
        os.environ['PYTHONPATH'] = os.getcwd()
        os.execv(python, [python, '-m', 'service.main'])

    asyncio.create_task(do_restart())
    return web.Response(text="<span style='color: var(--accent-blue);'>Restarting... please refresh in a few seconds.</span>", content_type='text/html')

from .health import get_system_health

async def handle_health(request):
    health = get_system_health()
    if "HX-Request" in request.headers:
        return aiohttp_jinja2.render_template("health.html", request, {"health": health})
    return aiohttp_jinja2.render_template("base.html", request, {"page": "health", "health": health})

# ... update setup_routes ...
async def handle_info(request):
    state = request.app["state"]
    if "HX-Request" in request.headers:
        return aiohttp_jinja2.render_template("info.html", request, {"info": state.inverter_info})
    return aiohttp_jinja2.render_template("base.html", request, {"page": "info", "info": state.inverter_info})

def setup_routes(app: web.Application):
    app.router.add_get("/", handle_dashboard)
    app.router.add_get("/logs", handle_logs)
    app.router.add_get("/health", handle_health)
    app.router.add_get("/info", handle_info)
    app.router.add_get("/settings", handle_settings)
    
    # API endpoints
    app.router.add_get("/api/dashboard", handle_dashboard)
    app.router.add_get("/api/logs_page", handle_logs)
    app.router.add_get("/api/health", handle_health)
    app.router.add_get("/api/info", handle_info)
    app.router.add_get("/api/settings", handle_settings)
    app.router.add_post("/api/settings", api_settings_post)
    app.router.add_post("/api/restart", api_restart)
