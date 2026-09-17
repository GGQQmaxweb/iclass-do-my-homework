#!/bin/bash

# --- Configuration ---
WORKDIR=$(pwd)
USER_NAME=$(whoami)
SERVICE_NAME="tronclass-bot"

if [ -d "${WORKDIR}/.venv" ]; then
    VENV_PATH="${WORKDIR}/.venv"
elif [ -d "${WORKDIR}/venv" ]; then
    VENV_PATH="${WORKDIR}/venv"
else
    VENV_PATH="${WORKDIR}/.venv"
fi

echo "🚀 Setting up systemd service for $SERVICE_NAME..."
echo "📂 Working directory: $WORKDIR"
echo "👤 User: $USER_NAME"
echo "🐍 Python venv: $VENV_PATH"

# 1. Check venv exists
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Virtual environment not found at $VENV_PATH. Creating one..."
    python3 -m venv "$VENV_PATH"
    "$VENV_PATH/bin/pip" install -r requirements.txt
fi

# 2. Generate the service file dynamically with current user and workdir
echo "⚙️  Generating ${SERVICE_NAME}.service..."
cat <<EOF > ${SERVICE_NAME}.service
[Unit]
Description=TronClass Discord Bot Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${USER_NAME}
WorkingDirectory=${WORKDIR}
ExecStart=${VENV_PATH}/bin/python3 ${WORKDIR}/bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 3. Copy to systemd directory and activate
echo "📂 Installing service to /etc/systemd/system/..."
sudo cp ${SERVICE_NAME}.service /etc/systemd/system/

echo "🔄 Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "▶️  Enabling and starting ${SERVICE_NAME}.service..."
sudo systemctl enable --now ${SERVICE_NAME}.service

echo "------------------------------------------------"
echo "✅ Done! Bot service has been installed and started."
echo "📝 Check status: sudo systemctl status ${SERVICE_NAME}.service"
echo "📝 Check logs:   journalctl -u ${SERVICE_NAME}.service -f"
echo "------------------------------------------------"
