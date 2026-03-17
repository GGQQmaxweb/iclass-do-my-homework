#!/bin/bash

# --- Configuration ---
WORKDIR=$(pwd)
USER_NAME=$(whoami)
SERVICE_NAME="tronclass"
VENV_PATH="${WORKDIR}/venv"

echo "🚀 Starting full installation for $SERVICE_NAME..."

# 1. Ensure Python 3 and venv are installed on the system
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install it first."
    exit 1
fi

# 2. Create requirements.txt if it doesn't exist
if [ ! -f "requirements.txt" ]; then
    echo "📄 Creating requirements.txt..."
    cat <<EOF > requirements.txt
google-generativeai
requests
EOF
fi

# 3. Setup Virtual Environment
echo "🐍 Setting up virtual environment in $VENV_PATH..."
python3 -m venv "$VENV_PATH"

# 4. Install Requirements
echo "📦 Installing dependencies..."
"$VENV_PATH/bin/pip" install --upgrade pip
"$VENV_PATH/bin/pip" install -r requirements.txt

# 5. Create the Service file (pointing to VENV)
echo "⚙️  Generating systemd service..."
cat <<EOF > ${SERVICE_NAME}.service
[Unit]
Description=Run TronClass Gemini Automation
After=network.target

[Service]
Type=oneshot
User=${USER_NAME}
WorkingDirectory=${WORKDIR}
# We use the python binary INSIDE the venv
ExecStart=${VENV_PATH}/bin/python3 ${WORKDIR}/main.py

[Install]
WantedBy=multi-user.target
EOF

# 6. Create the Timer file
cat <<EOF > ${SERVICE_NAME}.timer
[Unit]
Description=Run TronClass Bot daily at 8 AM

[Timer]
OnCalendar=*-*-* 08:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

# 7. Move files and activate
echo "📂 Moving files to systemd directory..."
sudo mv ${SERVICE_NAME}.service /etc/systemd/system/
sudo mv ${SERVICE_NAME}.timer /etc/systemd/system/

echo "🔄 Reloading systemd and enabling timer..."
sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}.timer
sudo systemctl start ${SERVICE_NAME}.timer

echo "------------------------------------------------"
echo "✅ Done! Everything is isolated in the venv."
echo "📅 Scheduled to run daily at 08:00."
echo "📝 Check logs: journalctl -u ${SERVICE_NAME}.service"
echo "------------------------------------------------"
