#!/bin/bash
#
# ESPFinder - Proxmox LXC Container Installation Script
# For Ubuntu 25.04+ LXC Containers
#
# Usage: wget -O - https://raw.githubusercontent.com/lozaning/ESPFinder/main/install-lxc.sh | bash
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/espfinder"
DATA_DIR="/var/lib/espfinder"
CONFIG_DIR="/etc/espfinder"
SYSTEMD_DIR="/etc/systemd/system"
PYTHON_VERSION="3.11"
REDIS_PORT="6379"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "This script must be run as root (use sudo)"
    exit 1
fi

log_info "Starting ESPFinder LXC Container Installation"
log_info "Target directory: $INSTALL_DIR"
echo ""

# Step 1: Update system
log_info "Updating package lists..."
apt-get update -qq

# Step 2: Install system dependencies
log_info "Installing system dependencies..."
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    gcc \
    g++ \
    make \
    libpq-dev \
    redis-server \
    wget \
    curl \
    gnupg \
    unzip \
    git \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    > /dev/null 2>&1

log_success "System dependencies installed"

# Step 3: Install Google Chrome (for Selenium)
log_info "Installing Google Chrome..."
if ! command -v google-chrome &> /dev/null; then
    wget -q -O /tmp/google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq /tmp/google-chrome.deb > /dev/null 2>&1 || true
    apt-get install -f -y -qq > /dev/null 2>&1
    rm /tmp/google-chrome.deb
    log_success "Google Chrome installed"
else
    log_info "Google Chrome already installed"
fi

# Step 4: Create application user
log_info "Creating espfinder user..."
if ! id -u espfinder > /dev/null 2>&1; then
    useradd -r -s /bin/bash -d $INSTALL_DIR -m espfinder
    log_success "User 'espfinder' created"
else
    log_info "User 'espfinder' already exists"
fi

# Step 5: Create directory structure
log_info "Creating directory structure..."
mkdir -p $INSTALL_DIR
mkdir -p $DATA_DIR/{database,images}
mkdir -p $CONFIG_DIR
mkdir -p /var/log/espfinder

# Set permissions
chown -R espfinder:espfinder $INSTALL_DIR
chown -R espfinder:espfinder $DATA_DIR
chown -R espfinder:espfinder /var/log/espfinder
chmod 755 $DATA_DIR
chmod 755 $CONFIG_DIR

log_success "Directory structure created"

# Step 6: Clone repository
log_info "Cloning ESPFinder repository..."
if [ -d "$INSTALL_DIR/.git" ]; then
    log_info "Repository already exists, pulling latest changes..."
    cd $INSTALL_DIR
    sudo -u espfinder git pull origin main > /dev/null 2>&1 || log_warning "Git pull failed, continuing..."
else
    rm -rf $INSTALL_DIR/*
    sudo -u espfinder git clone https://github.com/lozaning/ESPFinder.git $INSTALL_DIR > /dev/null 2>&1
    log_success "Repository cloned"
fi

cd $INSTALL_DIR

# Step 7: Set up Python virtual environment
log_info "Setting up Python virtual environment..."
sudo -u espfinder python3 -m venv $INSTALL_DIR/venv
log_success "Virtual environment created"

# Step 8: Install Python dependencies
log_info "Installing Python dependencies (this may take a few minutes)..."
sudo -u espfinder $INSTALL_DIR/venv/bin/pip install --quiet --upgrade pip > /dev/null 2>&1
sudo -u espfinder $INSTALL_DIR/venv/bin/pip install --quiet -r $INSTALL_DIR/requirements.txt

log_success "Python dependencies installed"

# Step 9: Configure Redis
log_info "Configuring Redis..."
systemctl enable redis-server > /dev/null 2>&1
systemctl start redis-server > /dev/null 2>&1
log_success "Redis configured and started"

# Step 10: Create configuration file
log_info "Creating configuration file..."
cat > $CONFIG_DIR/espfinder.env <<EOF
# ESPFinder Configuration
# Generated: $(date)

# Database Configuration
DATABASE_URL=sqlite:///$DATA_DIR/database/espfinder.db

# Data Storage
DATA_DIR=$DATA_DIR

# Scraping Configuration
DOWNLOAD_DELAY=1.0
MAX_RETRIES=3

# Redis Configuration
REDIS_URL=redis://localhost:$REDIS_PORT/0

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/espfinder/espfinder.log

# Flask Configuration
FLASK_ENV=production
FLASK_APP=src.web.app
EOF

chown espfinder:espfinder $CONFIG_DIR/espfinder.env
chmod 640 $CONFIG_DIR/espfinder.env
log_success "Configuration file created at $CONFIG_DIR/espfinder.env"

# Step 11: Initialize database
log_info "Initializing database..."
cd $INSTALL_DIR
sudo -u espfinder bash -c "export $(cat $CONFIG_DIR/espfinder.env | xargs) && $INSTALL_DIR/venv/bin/python -c 'from src.database.models import init_db; init_db()'" 2>/dev/null || true
log_success "Database initialized"

# Step 12: Create systemd service for web interface
log_info "Creating systemd service for web interface..."
cat > $SYSTEMD_DIR/espfinder-web.service <<EOF
[Unit]
Description=ESPFinder Web Interface
After=network.target redis-server.service
Wants=redis-server.service

[Service]
Type=simple
User=espfinder
Group=espfinder
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$CONFIG_DIR/espfinder.env
ExecStart=$INSTALL_DIR/venv/bin/python -m src.web.app
Restart=always
RestartSec=10
StandardOutput=append:/var/log/espfinder/web.log
StandardError=append:/var/log/espfinder/web-error.log

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$DATA_DIR /var/log/espfinder

[Install]
WantedBy=multi-user.target
EOF

log_success "Web service created"

# Step 13: Create systemd service for scraper (one-shot)
log_info "Creating systemd service for scraper..."
cat > $SYSTEMD_DIR/espfinder-scraper.service <<EOF
[Unit]
Description=ESPFinder FCC Scraper
After=network.target redis-server.service
Wants=redis-server.service

[Service]
Type=oneshot
User=espfinder
Group=espfinder
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$CONFIG_DIR/espfinder.env
ExecStart=$INSTALL_DIR/venv/bin/python -m src.main
StandardOutput=append:/var/log/espfinder/scraper.log
StandardError=append:/var/log/espfinder/scraper-error.log

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$DATA_DIR /var/log/espfinder
EOF

log_success "Scraper service created"

# Step 14: Create systemd timer for automatic scraping
log_info "Creating systemd timer for automatic scraping..."
cat > $SYSTEMD_DIR/espfinder-scraper.timer <<EOF
[Unit]
Description=ESPFinder Scraper Timer (runs daily)
Requires=espfinder-scraper.service

[Timer]
OnCalendar=daily
OnBootSec=5min
Persistent=true

[Install]
WantedBy=timers.target
EOF

log_success "Scraper timer created (runs daily)"

# Step 15: Enable and start services
log_info "Enabling and starting services..."
systemctl daemon-reload

# Start web service
systemctl enable espfinder-web.service > /dev/null 2>&1
systemctl start espfinder-web.service

# Enable timer (but don't start scraper immediately)
systemctl enable espfinder-scraper.timer > /dev/null 2>&1
systemctl start espfinder-scraper.timer > /dev/null 2>&1

log_success "Services enabled and started"

# Step 16: Create convenience scripts
log_info "Creating convenience scripts..."

cat > /usr/local/bin/espfinder <<'EOF'
#!/bin/bash
# ESPFinder management script

case "$1" in
    start)
        systemctl start espfinder-web
        echo "Web interface started"
        ;;
    stop)
        systemctl stop espfinder-web
        echo "Web interface stopped"
        ;;
    restart)
        systemctl restart espfinder-web
        echo "Web interface restarted"
        ;;
    status)
        systemctl status espfinder-web --no-pager
        ;;
    scrape)
        systemctl start espfinder-scraper
        echo "Scraper started (check logs with: espfinder logs-scraper)"
        ;;
    logs)
        journalctl -u espfinder-web -f
        ;;
    logs-scraper)
        journalctl -u espfinder-scraper -f
        ;;
    update)
        cd /opt/espfinder
        sudo -u espfinder git pull
        sudo -u espfinder /opt/espfinder/venv/bin/pip install -r requirements.txt
        systemctl restart espfinder-web
        echo "ESPFinder updated and restarted"
        ;;
    *)
        echo "ESPFinder Management Tool"
        echo ""
        echo "Usage: espfinder [command]"
        echo ""
        echo "Commands:"
        echo "  start         - Start web interface"
        echo "  stop          - Stop web interface"
        echo "  restart       - Restart web interface"
        echo "  status        - Show web service status"
        echo "  scrape        - Run scraper manually"
        echo "  logs          - View web interface logs"
        echo "  logs-scraper  - View scraper logs"
        echo "  update        - Update to latest version"
        echo ""
        ;;
esac
EOF

chmod +x /usr/local/bin/espfinder
log_success "Management script created at /usr/local/bin/espfinder"

# Wait for web service to start
log_info "Waiting for web service to start..."
sleep 5

# Check service status
if systemctl is-active --quiet espfinder-web; then
    log_success "Web service is running"
else
    log_warning "Web service may not have started correctly. Check logs with: journalctl -u espfinder-web"
fi

# Final summary
echo ""
echo "=========================================="
log_success "ESPFinder Installation Complete!"
echo "=========================================="
echo ""
echo "Installation Details:"
echo "  - Application: $INSTALL_DIR"
echo "  - Data: $DATA_DIR"
echo "  - Config: $CONFIG_DIR/espfinder.env"
echo "  - Logs: /var/log/espfinder/"
echo ""
echo "Services:"
echo "  - Web Interface: http://$(hostname -I | awk '{print $1}'):5000"
echo "  - Auto-scraper: Runs daily (via systemd timer)"
echo ""
echo "Management Commands:"
echo "  espfinder start          - Start web interface"
echo "  espfinder stop           - Stop web interface"
echo "  espfinder restart        - Restart web interface"
echo "  espfinder status         - Show service status"
echo "  espfinder scrape         - Run scraper manually"
echo "  espfinder logs           - View web logs"
echo "  espfinder logs-scraper   - View scraper logs"
echo "  espfinder update         - Update to latest version"
echo ""
echo "Configuration:"
echo "  Edit: $CONFIG_DIR/espfinder.env"
echo "  Then: systemctl restart espfinder-web"
echo ""
echo "First Steps:"
echo "  1. Access web interface at http://YOUR-LXC-IP:5000"
echo "  2. Run initial scrape: espfinder scrape"
echo "  3. Check logs: espfinder logs"
echo ""
log_success "Happy scraping!"
