#!/usr/bin/env bash
set -euo pipefail

echo "Stopping NOFX service (if present)..."
sudo systemctl stop nofx || true
sudo systemctl disable nofx || true
sudo systemctl daemon-reload || true

echo "Removing NOFX systemd unit and data..."
sudo rm -f /etc/systemd/system/nofx.service
sudo rm -rf /opt/nofx
sudo rm -f /var/log/nofx.log

if [ -d /etc/nginx/conf.d ]; then
  sudo rm -f /etc/nginx/conf.d/nofx.conf
fi
if [ -d /etc/nginx/sites-enabled ]; then
  sudo rm -f /etc/nginx/sites-enabled/nofx.conf
fi

echo "NOFX cleanup complete."
echo "If you have custom Nginx rules for /nofx, remove them manually and reload Nginx."
