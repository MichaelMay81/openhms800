#!/bin/bash
# OpenHMS-800: Phase 2 (Systemd Service Setup)
# To be run with sudo.

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (use sudo)."
  exit 1
fi

echo "OpenHMS-800: Finalizing Systemd Service..."

# 1. Detect service environment
# We assume this script is run from the directory where Phase 1 was executed.
CURRENT_DIR=$(pwd)
SERVICE_USER=$(stat -c '%U' .)

if [ "$SERVICE_USER" == "root" ]; then
    echo "Warning: Current directory is owned by root."
    echo "It is recommended to run Phase 1 (setup_app.sh) as a non-privileged user."
    read -p "Continue using 'root' as the service user? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 2. Ensure the service template exists
if [ ! -f "openhms-800.service" ]; then
    echo "Service template not found locally. Fetching from GitHub..."
    curl -sSL https://raw.githubusercontent.com/MichaelMay81/openhms800/master/openhms-800.service -o openhms-800.service
fi

# 3. Configure and install systemd service
echo "Configuring service for user $SERVICE_USER at $CURRENT_DIR..."

sed "s|SEARCH_DIR|$CURRENT_DIR|g; s|SEARCH_USER|$SERVICE_USER|g" openhms-800.service > openhms-800.service.tmp
cp openhms-800.service.tmp /etc/systemd/system/openhms-800.service
rm openhms-800.service.tmp

systemctl daemon-reload
systemctl enable openhms-800.service
systemctl start openhms-800.service

echo "Deployment complete."
echo "Check status with: systemctl status openhms-800"
