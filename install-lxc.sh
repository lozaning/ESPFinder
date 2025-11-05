#!/bin/bash
#
# ESPFinder - Proxmox LXC Container Installation Script
# For Ubuntu 25.04+ LXC Containers
#
# Usage: wget -O - https://raw.githubusercontent.com/lozaning/ESPFinder/main/install-lxc.sh | bash
#        OR
#        curl -sSL https://raw.githubusercontent.com/lozaning/ESPFinder/main/install-lxc.sh | bash
#

set -e
set -o pipefail

# Ensure output is not buffered
export PYTHONUNBUFFERED=1

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
apt-get update -qq 2>&1 | grep -E "^(Err:|E:|W:)" || true

# Step 2: Detect Python version and install system dependencies
log_info "Detecting Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
log_info "Found Python $PYTHON_VERSION"

log_info "Installing system dependencies (this may take 2-5 minutes)..."
log_info "Installing: Python, build tools, Redis, Chrome dependencies..."

# Install base packages first
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 \
    python3-pip \
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
    libvulkan1 2>&1 | grep -E "^(Setting up|Processing|Unpacking|Preparing|Selecting)" | head -20 || true

# Try to install version-specific venv package (might not exist on all Ubuntu versions)
log_info "Attempting to install Python venv packages..."
apt-get install -y python3-venv 2>&1 | grep -E "^(Setting up|already)" || true

# Try version-specific venv package
if apt-cache search "python${PYTHON_VERSION}-venv" | grep -q "python${PYTHON_VERSION}-venv"; then
    log_info "Installing python${PYTHON_VERSION}-venv..."
    apt-get install -y python${PYTHON_VERSION}-venv 2>&1 | grep -E "^(Setting up|already)" || true
else
    log_warning "python${PYTHON_VERSION}-venv package not found, will use alternative method"
    # Try installing python3-full which includes ensurepip
    log_info "Installing python3-full as fallback..."
    apt-get install -y python3-full 2>&1 | grep -E "^(Setting up|already)" || true
fi

log_success "System dependencies installed"

# Step 3: Install Google Chrome (for Selenium)
log_info "Installing Google Chrome..."
if ! command -v google-chrome &> /dev/null; then
    log_info "Downloading Chrome package..."
    wget -q --show-progress -O /tmp/google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb 2>&1 | tail -3
    log_info "Installing Chrome package..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y /tmp/google-chrome.deb 2>&1 | grep -E "^(Setting up|Processing)" || true
    apt-get install -f -y 2>&1 | grep -E "^(Setting up|Processing)" || true
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
log_info "Cloning ESPFinder repository from GitHub..."
if [ -d "$INSTALL_DIR/.git" ]; then
    log_info "Repository already exists, pulling latest changes..."
    cd $INSTALL_DIR
    sudo -u espfinder git pull origin main 2>&1 | tail -5 || log_warning "Git pull failed, continuing..."
else
    rm -rf $INSTALL_DIR/*
    log_info "This may take a minute..."
    sudo -u espfinder git clone https://github.com/lozaning/ESPFinder.git $INSTALL_DIR 2>&1 | grep -E "^(Cloning|remote:|Receiving)" || true
    log_success "Repository cloned"
fi

cd $INSTALL_DIR

# Step 7: Set up Python virtual environment
log_info "Setting up Python virtual environment..."

# Ensure ensurepip is available
if ! python3 -m ensurepip --version &>/dev/null; then
    log_warning "ensurepip not available, installing python${PYTHON_VERSION}-venv..."
    # Try version-specific package first
    if apt-cache search python${PYTHON_VERSION}-venv | grep -q "python${PYTHON_VERSION}-venv"; then
        apt-get install -y python${PYTHON_VERSION}-venv 2>&1 | grep -E "^(Setting up|Processing)" || true
    else
        log_warning "python${PYTHON_VERSION}-venv not found, trying alternative method..."
        # Install full distutils if venv package doesn't exist
        apt-get install -y python${PYTHON_VERSION}-full python3-full 2>&1 | grep -E "^(Setting up|Processing)" || true
    fi
fi

# Create virtual environment
if ! sudo -u espfinder python3 -m venv $INSTALL_DIR/venv 2>&1; then
    log_error "Failed to create virtual environment with venv module"
    log_info "Trying alternative method with --without-pip..."
    sudo -u espfinder python3 -m venv --without-pip $INSTALL_DIR/venv
    # Install pip manually
    log_info "Installing pip manually..."
    curl -sS https://bootstrap.pypa.io/get-pip.py | sudo -u espfinder $INSTALL_DIR/venv/bin/python
fi

log_success "Virtual environment created"

# Step 8: Install Python dependencies
log_info "Installing Python dependencies (this may take 3-5 minutes)..."
log_info "Upgrading pip..."
sudo -u espfinder $INSTALL_DIR/venv/bin/pip install --quiet --upgrade pip 2>&1 | tail -2
log_info "Installing packages: requests, beautifulsoup4, flask, selenium, pymupdf, opencv..."
sudo -u espfinder $INSTALL_DIR/venv/bin/pip install -r $INSTALL_DIR/requirements.txt 2>&1 | grep -E "^(Collecting|Installing collected|Successfully installed)" | head -30 || echo "Installing packages..."

log_success "Python dependencies installed"

# Step 9: Configure Redis
log_info "Configuring Redis..."
systemctl enable redis-server 2>&1 | grep -v "^$" || true
systemctl start redis-server 2>&1 | grep -v "^$" || true
if systemctl is-active --quiet redis-server; then
    log_success "Redis configured and started"
else
    log_warning "Redis may not have started (will retry later)"
fi

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
log_info "Starting web interface service..."
systemctl enable espfinder-web.service 2>&1 | grep -v "^$" || true
systemctl start espfinder-web.service 2>&1 | grep -v "^$" || true

# Enable timer (but don't start scraper immediately)
log_info "Enabling automatic scraper timer..."
systemctl enable espfinder-scraper.timer 2>&1 | grep -v "^$" || true
systemctl start espfinder-scraper.timer 2>&1 | grep -v "^$" || true

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
sleep 3

# Check service status with detailed feedback
log_info "Checking service status..."
if systemctl is-active --quiet espfinder-web; then
    log_success "Web service is running"

    # Try to get the IP address
    IP_ADDR=$(hostname -I | awk '{print $1}' || echo "YOUR-IP")

    # Check if port 5000 is listening
    sleep 2
    if netstat -tuln 2>/dev/null | grep -q ":5000 " || ss -tuln 2>/dev/null | grep -q ":5000 "; then
        log_success "Web interface is listening on port 5000"
    else
        log_warning "Port 5000 not yet open, may need a moment to start"
    fi
else
    log_warning "Web service may not have started correctly"
    log_info "Check logs with: journalctl -u espfinder-web -n 50"
    log_info "Or try: systemctl restart espfinder-web"
fi

# Final summary
IP_ADDR=$(hostname -I | awk '{print $1}' || echo "YOUR-IP")

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
echo "  - Web Interface: ${GREEN}http://$IP_ADDR:5000${NC}"
echo "  - Auto-scraper: Runs daily (via systemd timer)"
echo ""
echo "Management Commands:"
echo "  ${BLUE}espfinder status${NC}         - Show service status"
echo "  ${BLUE}espfinder scrape${NC}         - Run scraper manually"
echo "  ${BLUE}espfinder logs${NC}           - View web logs"
echo "  ${BLUE}espfinder logs-scraper${NC}   - View scraper logs"
echo "  ${BLUE}espfinder restart${NC}        - Restart web interface"
echo "  ${BLUE}espfinder update${NC}         - Update to latest version"
echo ""
echo "Configuration:"
echo "  Edit: $CONFIG_DIR/espfinder.env"
echo "  Then: systemctl restart espfinder-web"
echo ""
echo "First Steps:"
echo "  1. ${GREEN}Access web interface:${NC} http://$IP_ADDR:5000"
echo "  2. ${GREEN}Run initial scrape:${NC} espfinder scrape"
echo "  3. ${GREEN}Check logs:${NC} espfinder logs"
echo ""
echo "Troubleshooting:"
echo "  If web interface not accessible:"
echo "    - Check status: espfinder status"
echo "    - View logs: journalctl -u espfinder-web -n 50"
echo "    - Restart: systemctl restart espfinder-web"
echo ""
log_success "Happy scraping!"
echo ""
