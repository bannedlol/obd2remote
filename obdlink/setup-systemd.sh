#!/usr/bin/env bash
set -euo pipefail

# Simple setup script to install and enable the obdlink systemd service
# Usage: sudo ./setup-systemd.sh

SERVICE=obdlink.service
SRC_DIR=$(cd "$(dirname "$0")" && pwd)

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root: sudo $0"
  exit 1
fi

# Ensure journald directory exists for logs (optional)
mkdir -p /var/log

# Copy service unit
cp -f "$SRC_DIR/$SERVICE" /etc/systemd/system/$SERVICE

# Reload and enable
systemctl daemon-reload
systemctl enable --now $SERVICE

# Show status
systemctl status $SERVICE --no-pager

echo "\nDone. Follow logs with: journalctl -u $SERVICE -f"
