# OpenHMS-800 Unified Service

A lightweight, asynchronous service for monitoring Hoymiles HMS-800-2WB microinverters via Bluetooth Low Energy (BLE).

[![GitHub](https://img.shields.io/badge/GitHub-openhms800-blue?logo=github)](https://github.com/MichaelMay81/openhms800)

## Features
- **Real-time Monitoring:** Multi-channel PV and AC grid metrics.
- **Web Interface:** OpenDTU-inspired dashboard using `aiohttp` and `HTMX`.
- **Diagnostics:** Integrated system console and Raspberry Pi health monitoring.
- **Robust:** Automatic reconnection and persistent configuration.

## Installation
The service is designed for deployment on a Raspberry Pi. The installation is split into two phases:

### Phase 1: Application Setup (Run as the service user)
1. Create a directory and download the setup script:
   ```bash
   mkdir openhms800 && cd openhms800
   curl -sSL https://raw.githubusercontent.com/MichaelMay81/openhms800/master/setup_app.sh -o setup_app.sh
   chmod +x setup_app.sh
   ./setup_app.sh
   ```

### Phase 2: System Integration (Run with sudo)
1. Download and run the systemd setup script:
   ```bash
   curl -sSL https://raw.githubusercontent.com/MichaelMay81/openhms800/master/setup_systemd.sh -o setup_systemd.sh
   chmod +x setup_systemd.sh
   sudo ./setup_systemd.sh
   ```

The scripts will:
1. Verify system dependencies and resources.
2. Create a virtual environment and install the service from GitHub.
3. Configure the systemd service with dynamic paths and user detection.

## Configuration
Settings are managed in `config.json` (created in the installation directory). You can modify these via the **Settings** tab in the Web UI, which also includes a button to restart the service to apply changes.

## Architecture
1. **BLE Layer:** Polls the inverter for raw metrics.
2. **State Layer:** Normalizes and stores data in a structured, thread-safe container.
3. **Web/MQTT Layer:** Serves the UI and forwards metrics to your broker.
