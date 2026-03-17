#!/bin/bash

# --- Configuration ---
# Get the absolute path of the current directory
WORKDIR=$(pwd)
USER_NAME=$(whoami)
SERVICE_NAME="tronclass"

echo "🛠️  Starting installation for $SERVICE_NAME..."

# 1. Create the Service file
cat <<EOF > ${SERVICE_NAME}.service
[Unit]
Description=Run TronClass Gemini Automation
After=network.target

[Service]
Type=oneshot
User=${USER_NAME}
WorkingDirectory=${WORKDIR}
ExecStart=$(which python3) ${WORKDIR}/main.py
# If you use a venv, replace the line above with:
# ExecStart=${WORKDIR}/venv/bin/python3 ${WORKDIR}/main.py

[Install]
WantedBy=multi-user.target
EOF

# 2. Create the Timer file
cat <<EOF > ${SERVICE_NAME}.timer
[Unit]
Description=Run TronClass Bot daily at 8 AM

[Timer]
OnCalendar=*-*-* 08:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

echo "📂 Moving files to systemd directory..."
sudo mv ${SERVICE_NAME}.service /etc/systemd/system/
sudo mv ${SERVICE_NAME}.timer /etc/systemd/system/

echo "🔄 Reloading systemd and enabling timer..."
sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}.timer
sudo systemctl start ${SERVICE_NAME}.timer

echo "------------------------------------------------"
echo "✅ Installation Complete!"
echo "📅 Next run: \$(systemctl list-timers ${SERVICE_NAME}.timer | grep 'n/a' -v | tail -n 1)"
echo "📝 To check logs: journalctl -u ${SERVICE_NAME}.service"
echo "------------------------------------------------"
