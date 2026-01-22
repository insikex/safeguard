#!/bin/bash
# ===========================================
# Safeguard Bot - Update Script
# ===========================================

set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║   🔄 SAFEGUARD BOT - Update Script                        ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Stop the bot
log_info "Stopping bot..."
sudo systemctl stop safeguard-bot || true

# Pull latest changes
log_info "Pulling latest changes..."
git pull origin main || git pull origin master

# Activate virtual environment
source venv/bin/activate

# Update dependencies
log_info "Updating dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Restart the bot
log_info "Starting bot..."
sudo systemctl start safeguard-bot

# Check status
sleep 2
sudo systemctl status safeguard-bot --no-pager

echo ""
log_info "Update complete!"
