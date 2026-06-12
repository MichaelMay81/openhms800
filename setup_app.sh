#!/bin/bash
# OpenHMS-800: Phase 1 (Application Setup)
# To be run by the user who will own the service (non-sudo).

set -e

echo "OpenHMS-800: Starting Application Setup..."

# 1. System Checks
check_tools() {
    local tools=$1
    local hint=$2
    local failed=0
    for tool in $tools; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            echo "Error: $tool is not installed."
            failed=1
        fi
    done
    if [ "$failed" -eq 1 ]; then
        [ -n "$hint" ] && echo "Hint: $hint"
        exit 1
    fi
}

check_pkgs() {
    local pkgs=$1
    local hint=$2
    local failed=0
    for pkg in $pkgs; do
        if ! dpkg -s "$pkg" >/dev/null 2>&1; then
            echo "Error: package $pkg is not installed."
            failed=1
        fi
    done
    if [ "$failed" -eq 1 ]; then
        [ -n "$hint" ] && echo "Hint: $hint"
        exit 1
    fi
}

# Verify System Tools (Core, Rust, Build)
check_tools "python3 git uv rustc cargo pkg-config" "sudo apt install python3 git uv rustc cargo pkg-config"

# Verify System Packages (Build Essentials & Libraries)
check_pkgs "build-essential libffi-dev libssl-dev" "sudo apt install build-essential libffi-dev libssl-dev"

# 2. Resource Check (Memory + Swap)
MEM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
SWAP_KB=$(grep SwapTotal /proc/meminfo | awk '{print $2}')
TOTAL_KB=$((MEM_KB + SWAP_KB))
TARGET_KB=1572864  # 1.5 GB

if [ "$TOTAL_KB" -lt "$TARGET_KB" ]; then
    NEEDED_MB=$(( (TARGET_KB - TOTAL_KB) / 1024 ))
    echo "Warning: Total combined memory is low ($((TOTAL_KB/1024))MB)."
    echo "Building dependencies may fail on this platform."
    echo "Hint: Increase swap by at least ${NEEDED_MB}MB to reach 1.5GB combined."
    echo ""
fi

# 3. Setup VENV and install from GitHub
echo "Setting up virtual environment and installing openhms800..."
uv venv
source .venv/bin/activate
uv pip install git+https://github.com/MichaelMay81/openhms800.git

echo ""
echo "Phase 1 Complete."
echo "Now run the following command with sudo to finalize the installation:"
echo "sudo ./setup_systemd.sh"
