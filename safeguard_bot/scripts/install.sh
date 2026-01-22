#!/bin/bash
# ===========================================
# Safeguard Bot - Installation Script
# For Debian 13 / Ubuntu
# ===========================================

set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║   🛡️  SAFEGUARD BOT - Installation Script                ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    log_warn "Running as root. Consider using a non-root user."
fi

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

log_info "Project directory: $PROJECT_DIR"

# Step 1: Update system
log_info "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Step 2: Install Python and dependencies
log_info "Installing Python and required packages..."
sudo apt install -y python3 python3-pip python3-venv git

# Verify Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
log_info "Python version: $PYTHON_VERSION"

# Step 3: Create virtual environment
log_info "Creating virtual environment..."
cd "$PROJECT_DIR"

if [ -d "venv" ]; then
    log_warn "Virtual environment already exists. Skipping creation."
else
    python3 -m venv venv
    log_info "Virtual environment created."
fi

# Activate virtual environment
source venv/bin/activate

# Step 4: Install Python dependencies
log_info "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Step 5: Create .env file if not exists
if [ ! -f ".env" ]; then
    log_info "Creating .env file from template..."
    cp .env.example .env
    log_warn "Please edit .env file and add your BOT_TOKEN!"
else
    log_info ".env file already exists."
fi

# Step 6: Create systemd service
log_info "Creating systemd service..."

SERVICE_USER=$(whoami)
SERVICE_PATH="/etc/systemd/system/safeguard-bot.service"

sudo tee $SERVICE_PATH > /dev/null <<EOF
[Unit]
Description=Safeguard Telegram Bot
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

log_info "Systemd service created at $SERVICE_PATH"

# Reload systemd
sudo systemctl daemon-reload

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║   ✅ Installation Complete!                               ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "1. Edit .env file: nano $PROJECT_DIR/.env"
echo "2. Add your BOT_TOKEN from @BotFather"
echo "3. Start the bot: sudo systemctl start safeguard-bot"
echo "4. Enable auto-start: sudo systemctl enable safeguard-bot"
echo "5. Check status: sudo systemctl status safeguard-bot"
echo ""
log_info "Done!"
