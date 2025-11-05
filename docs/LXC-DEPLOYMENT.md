# ESPFinder - Proxmox LXC Container Deployment Guide

This guide explains how to deploy ESPFinder in a Proxmox LXC container running Ubuntu 25.04+.

## Quick Install

For a fresh Ubuntu 25 LXC container, run this one-liner as root:

```bash
wget -O - https://raw.githubusercontent.com/lozaning/ESPFinder/main/install-lxc.sh | bash
```

Or download and inspect first:

```bash
wget https://raw.githubusercontent.com/lozaning/ESPFinder/main/install-lxc.sh
chmod +x install-lxc.sh
sudo ./install-lxc.sh
```

## What Gets Installed

The installation script will:

1. **System Dependencies**
   - Python 3.11+ and development tools
   - Google Chrome (for Selenium web scraping)
   - Redis server (for task queue)
   - Required system libraries

2. **Application Structure**
   - Application code: `/opt/espfinder`
   - Data storage: `/var/lib/espfinder`
   - Configuration: `/etc/espfinder/espfinder.env`
   - Logs: `/var/log/espfinder/`

3. **System Services**
   - `espfinder-web.service` - Flask web interface (port 5000)
   - `espfinder-scraper.service` - FCC scraper (one-shot)
   - `espfinder-scraper.timer` - Daily automatic scraping

4. **Management Tools**
   - `/usr/local/bin/espfinder` - Convenience management script

## Proxmox LXC Container Setup

### Create the LXC Container

1. In Proxmox web interface, create a new LXC container:
   - **Template**: Ubuntu 25.04 (or latest Ubuntu)
   - **Resources**:
     - CPU: 2 cores minimum
     - RAM: 2GB minimum (4GB recommended)
     - Storage: 20GB minimum (grows with image collection)
   - **Network**: Bridge with static IP or DHCP

2. **Container Options**:
   - Features: Enable "Nesting" if you want Docker support later
   - Features: Enable "FUSE" for better filesystem support
   - Start at boot: Enabled (recommended)

3. Start the container and enter via console or SSH

### Run Installation

```bash
# Update the container
apt update && apt upgrade -y

# Run the installer
wget -O - https://raw.githubusercontent.com/lozaning/ESPFinder/main/install-lxc.sh | bash
```

Installation takes approximately 5-10 minutes depending on network speed.

## Post-Installation

### Access the Web Interface

After installation, access the web interface at:

```
http://YOUR-LXC-IP:5000
```

To find your LXC IP:
```bash
hostname -I
```

### Run Initial Scrape

The scraper runs automatically daily, but you can trigger it manually:

```bash
espfinder scrape
```

Watch the scraper logs:
```bash
espfinder logs-scraper
```

### Management Commands

The `espfinder` command provides easy management:

```bash
espfinder start          # Start web interface
espfinder stop           # Stop web interface
espfinder restart        # Restart web interface
espfinder status         # Show service status
espfinder scrape         # Run scraper manually
espfinder logs           # View web logs (follow mode)
espfinder logs-scraper   # View scraper logs (follow mode)
espfinder update         # Update to latest version
```

## Configuration

### Edit Configuration

Configuration is stored in `/etc/espfinder/espfinder.env`:

```bash
nano /etc/espfinder/espfinder.env
```

Key settings:

```bash
# Database (default SQLite, can use PostgreSQL)
DATABASE_URL=sqlite:////var/lib/espfinder/database/espfinder.db

# Data storage location
DATA_DIR=/var/lib/espfinder

# Scraping behavior
DOWNLOAD_DELAY=1.0      # Delay between requests (be polite!)
MAX_RETRIES=3           # Retry failed downloads

# Redis
REDIS_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/espfinder/espfinder.log
```

After editing, restart services:

```bash
systemctl restart espfinder-web
```

### Change Scrape Schedule

Edit the timer unit:

```bash
systemctl edit espfinder-scraper.timer
```

Change `OnCalendar=daily` to your preferred schedule:
- `OnCalendar=hourly` - Run every hour
- `OnCalendar=weekly` - Run weekly
- `OnCalendar=*-*-* 02:00:00` - Run daily at 2 AM

Then reload:
```bash
systemctl daemon-reload
systemctl restart espfinder-scraper.timer
```

## Networking & Firewall

### Port Forwarding (Optional)

To access from outside your network, configure port forwarding in Proxmox:

1. Proxmox host firewall rules, or
2. Use `iptables` to forward host port to LXC container:

```bash
# On Proxmox host
iptables -t nat -A PREROUTING -p tcp --dport 8080 -j DNAT --to-destination LXC-IP:5000
```

### Reverse Proxy (Recommended)

For production use, put a reverse proxy in front:

```nginx
# Nginx example
server {
    listen 80;
    server_name espfinder.example.com;

    location / {
        proxy_pass http://LXC-IP:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## Database Options

### Using SQLite (Default)

SQLite is configured by default and works well for small to medium deployments:

```bash
DATABASE_URL=sqlite:////var/lib/espfinder/database/espfinder.db
```

### Switching to PostgreSQL

For better performance with large datasets:

1. Install PostgreSQL in another container or use external database

2. Update configuration:

```bash
nano /etc/espfinder/espfinder.env
```

Change:
```bash
DATABASE_URL=postgresql://username:password@postgres-host:5432/espfinder
```

3. Restart service:
```bash
systemctl restart espfinder-web
```

The database will be automatically initialized on first run.

## Monitoring & Logs

### View Logs

```bash
# Web interface logs
journalctl -u espfinder-web -f

# Scraper logs
journalctl -u espfinder-scraper -f

# Or use convenience commands
espfinder logs
espfinder logs-scraper

# View log files directly
tail -f /var/log/espfinder/web.log
tail -f /var/log/espfinder/scraper.log
```

### Service Status

```bash
# Check all services
systemctl status espfinder-web
systemctl status espfinder-scraper.timer
systemctl status redis-server

# Or use convenience command
espfinder status
```

### Disk Usage

Monitor data directory growth:

```bash
du -sh /var/lib/espfinder/*
```

## Backup & Restore

### Backup

```bash
# Stop services
systemctl stop espfinder-web

# Backup data directory
tar -czf espfinder-backup-$(date +%Y%m%d).tar.gz \
    /var/lib/espfinder \
    /etc/espfinder

# Restart services
systemctl start espfinder-web
```

### Restore

```bash
# Stop services
systemctl stop espfinder-web

# Restore from backup
tar -xzf espfinder-backup-YYYYMMDD.tar.gz -C /

# Fix permissions
chown -R espfinder:espfinder /var/lib/espfinder

# Restart services
systemctl start espfinder-web
```

## Updating

Update to the latest version:

```bash
espfinder update
```

Or manually:

```bash
cd /opt/espfinder
sudo -u espfinder git pull
sudo -u espfinder /opt/espfinder/venv/bin/pip install -r requirements.txt
systemctl restart espfinder-web
```

## Troubleshooting

### Web Interface Not Starting

```bash
# Check service status
systemctl status espfinder-web

# Check logs
journalctl -u espfinder-web -n 50

# Test manually
cd /opt/espfinder
sudo -u espfinder /opt/espfinder/venv/bin/python -m src.web.app
```

### Scraper Failing

```bash
# Check if Chrome is installed
google-chrome --version

# Check scraper logs
journalctl -u espfinder-scraper -n 100

# Test manually
cd /opt/espfinder
sudo -u espfinder bash -c "export $(cat /etc/espfinder/espfinder.env | xargs) && /opt/espfinder/venv/bin/python -m src.main"
```

### Redis Connection Issues

```bash
# Check Redis status
systemctl status redis-server

# Test Redis connection
redis-cli ping
# Should return: PONG
```

### Database Issues

```bash
# Check database file permissions
ls -la /var/lib/espfinder/database/

# Reinitialize database (WARNING: Deletes all data)
rm /var/lib/espfinder/database/espfinder.db
cd /opt/espfinder
sudo -u espfinder bash -c "export $(cat /etc/espfinder/espfinder.env | xargs) && /opt/espfinder/venv/bin/python -c 'from src.database.models import init_db; init_db()'"
```

### Port 5000 Already in Use

Change the port in `/opt/espfinder/src/web/app.py`:

```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)  # Changed from 5000
```

Then restart:
```bash
systemctl restart espfinder-web
```

## Resource Management

### Limit Memory Usage

Edit service file:

```bash
systemctl edit espfinder-web
```

Add:
```ini
[Service]
MemoryLimit=1G
MemoryHigh=800M
```

### CPU Limits

```ini
[Service]
CPUQuota=50%
```

Reload and restart:
```bash
systemctl daemon-reload
systemctl restart espfinder-web
```

## Security Considerations

### Firewall Rules

Only expose port 5000 to trusted networks:

```bash
# Allow from specific network
ufw allow from 192.168.1.0/24 to any port 5000

# Or use iptables
iptables -A INPUT -p tcp -s 192.168.1.0/24 --dport 5000 -j ACCEPT
iptables -A INPUT -p tcp --dport 5000 -j DROP
```

### File Permissions

The installer sets secure permissions:
- Application files: owned by `espfinder` user
- Data directory: writable only by `espfinder` user
- Config file: readable only by `espfinder` user (640)

### Service Hardening

The systemd services include security settings:
- `NoNewPrivileges=true` - Prevent privilege escalation
- `PrivateTmp=true` - Isolated /tmp
- `ProtectSystem=strict` - Read-only system files
- `ProtectHome=true` - No access to home directories

## Uninstallation

To completely remove ESPFinder:

```bash
# Stop and disable services
systemctl stop espfinder-web espfinder-scraper.timer
systemctl disable espfinder-web espfinder-scraper.timer

# Remove service files
rm /etc/systemd/system/espfinder-*
systemctl daemon-reload

# Remove application
rm -rf /opt/espfinder

# Remove data (WARNING: Deletes all scraped data)
rm -rf /var/lib/espfinder

# Remove config
rm -rf /etc/espfinder

# Remove logs
rm -rf /var/log/espfinder

# Remove management script
rm /usr/local/bin/espfinder

# Optionally remove user
userdel espfinder

# Optionally remove Redis if not needed
apt remove redis-server
```

## Support

For issues or questions:
- GitHub Issues: https://github.com/lozaning/ESPFinder/issues
- Documentation: https://github.com/lozaning/ESPFinder

## License

This software is provided as-is. Use responsibly and in compliance with FCC website terms of service.
