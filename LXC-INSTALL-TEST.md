# LXC Installation Testing & Validation Guide

## Pre-Installation Cleanup

If you have a previous failed installation, clean it up first:

```bash
# Stop services
systemctl stop espfinder-web espfinder-scraper.timer 2>/dev/null || true

# Remove files
rm -rf /opt/espfinder
rm -rf /var/lib/espfinder
rm -rf /etc/espfinder
rm -rf /var/log/espfinder
rm /etc/systemd/system/espfinder-*
rm /etc/sudoers.d/espfinder
rm /usr/local/bin/espfinder

# Remove user
userdel -r espfinder 2>/dev/null || true

# Reload systemd
systemctl daemon-reload
```

## Installation

Run the updated installer:

```bash
curl -sSL https://raw.githubusercontent.com/lozaning/ESPFinder/claude/proxmox-lxc-install-script-011CUp7n1B1BYqgUWBmDpekz/install-lxc.sh | bash
```

## Expected Output

You should see:

1. ✅ System dependencies installed (~2-5 minutes)
2. ✅ Google Chrome installed
3. ✅ Python virtual environment created (with fallbacks if needed)
4. ✅ Python dependencies installed (~3-5 minutes)
5. ✅ Redis configured and started
6. ✅ Configuration file created
7. ✅ Services enabled and started
8. ✅ Web interface listening on port 5000

## Validation Tests

### 1. Check Service Status

```bash
espfinder status
```

**Expected:** Service should be "active (running)"

If not running, check logs:

```bash
journalctl -u espfinder-web -n 50 --no-pager
```

### 2. Check Web Interface

```bash
curl http://localhost:5000/plain/status
```

**Expected output:**
```
=== ESPFINDER SYSTEM STATUS ===

=== DATABASE STATS ===
Products: 0
Photos: 0
PDFs Total: 0
PDFs Downloaded: 0
PDFs Processed: 0

=== SERVICE STATUS ===
espfinder-web: active
espfinder-scraper: inactive
redis-server: active

=== FILE SYSTEM ===
Data directory: /var/lib/espfinder
Data dir exists: Yes
Database dir exists: True
Images dir exists: True
FCC ID directories: 0
```

### 3. Check Environment Variables

```bash
sudo -u espfinder bash -c 'cd /opt/espfinder && source /etc/espfinder/espfinder.env && env | grep -E "(DATABASE_URL|DATA_DIR|FLASK_ENV)"'
```

**Expected:**
```
DATABASE_URL=sqlite:////var/lib/espfinder/database/espfinder.db
DATA_DIR=/var/lib/espfinder
FLASK_ENV=production
```

### 4. Check Database

```bash
ls -la /var/lib/espfinder/database/
```

**Expected:** Should see `espfinder.db` file

### 5. Test Web Interface in Browser

Open: `http://YOUR-LXC-IP:5000`

**Expected:**
- Dashboard loads successfully
- Shows "0 Products" and "0 Photos"
- No errors in browser console

### 6. Test Manual Scraper Trigger

```bash
espfinder scrape
```

Then check logs:

```bash
espfinder logs-scraper
```

**Expected:** Scraper runs and attempts to connect to FCC website

### 7. Test API Endpoints

```bash
# Test stats API
curl http://localhost:5000/api/stats

# Test containers/services API
curl http://localhost:5000/api/containers

# Test trigger scrape API
curl -X GET http://localhost:5000/api/trigger-scrape
```

**Expected:** All return JSON responses without errors

### 8. Check File Permissions

```bash
ls -la /opt/espfinder/ | head -20
ls -la /var/lib/espfinder/
ls -la /etc/espfinder/
```

**Expected:** All owned by `espfinder:espfinder`

### 9. Test Logs Endpoint

```bash
curl http://localhost:5000/debug/logs?service=espfinder-web&lines=50
```

**Expected:** Shows recent web service logs

### 10. Verify Sudoers Configuration

```bash
sudo -u espfinder sudo -l
```

**Expected output should include:**
```
User espfinder may run the following commands:
    (ALL) NOPASSWD: /usr/bin/systemctl start espfinder-scraper
    (ALL) NOPASSWD: /usr/bin/systemctl stop espfinder-scraper
    (ALL) NOPASSWD: /usr/bin/systemctl restart espfinder-scraper
    (ALL) NOPASSWD: /usr/bin/systemctl status espfinder-scraper
    (ALL) NOPASSWD: /usr/bin/systemctl is-active *
    (ALL) NOPASSWD: /usr/bin/journalctl *
```

## Common Issues & Solutions

### Issue: Web service won't start

```bash
# Check the actual error
journalctl -u espfinder-web -n 100 --no-pager

# Check if port 5000 is already in use
ss -tuln | grep 5000

# Try running manually to see error
cd /opt/espfinder
sudo -u espfinder bash
source /etc/espfinder/espfinder.env
./venv/bin/python -m src.web.app
```

### Issue: Import errors

```bash
# Verify all packages installed
cd /opt/espfinder
./venv/bin/pip list

# Reinstall dependencies
sudo -u espfinder ./venv/bin/pip install -r requirements.txt
```

### Issue: Database errors

```bash
# Reinitialize database
cd /opt/espfinder
sudo -u espfinder bash -c "export $(cat /etc/espfinder/espfinder.env | xargs) && ./venv/bin/python -c 'from src.database.models import init_db; init_db()'"
```

### Issue: Permission denied errors

```bash
# Fix ownership
chown -R espfinder:espfinder /opt/espfinder
chown -R espfinder:espfinder /var/lib/espfinder
chown -R espfinder:espfinder /var/log/espfinder

# Restart service
systemctl restart espfinder-web
```

## What Was Fixed

### Major Changes:

1. **Environment Loading**
   - Created `.env` symlink so app can find config
   - Made `load_dotenv()` conditional to avoid errors
   - Fixed paths to work in LXC environment

2. **Docker Dependencies Removed**
   - App now detects if running in Docker or LXC
   - All docker commands replaced with systemd equivalents for LXC
   - `/api/trigger-scrape` uses `systemctl start` for LXC
   - `/api/logs` uses `journalctl` for LXC
   - `/api/containers` shows systemd services for LXC

3. **Path Fixes**
   - Removed hard-coded `/app/data/sample_pdfs`
   - All paths now use environment variables
   - Works with `/var/lib/espfinder` data directory

4. **Permissions**
   - Added sudoers rules for espfinder user
   - Can start/stop scraper service
   - Can view logs and service status
   - No password required for these operations

5. **Debug Mode**
   - Disabled in production (checks FLASK_ENV)
   - Prevents Flask reloader issues

## Success Criteria

Installation is successful if:

- [ ] Web interface loads at `http://YOUR-IP:5000`
- [ ] Status page shows database stats
- [ ] No errors in `journalctl -u espfinder-web`
- [ ] Can trigger scraper from web interface
- [ ] Can view logs from web interface
- [ ] Database file exists and is writable
- [ ] All files owned by espfinder user
- [ ] Service restarts automatically on failure

## Next Steps After Successful Install

1. **Access Web Interface**: `http://YOUR-LXC-IP:5000`
2. **Run First Scrape**: Click "Trigger Scrape" or run `espfinder scrape`
3. **Check Results**: Browse to /products and /photos pages
4. **Configure Automatic Scraping**: Timer already set to run daily
5. **Monitor**: Use `espfinder logs` to watch activity

## Getting Help

If problems persist:

1. Collect diagnostics:
```bash
echo "=== System Info ===" > diagnostic.txt
uname -a >> diagnostic.txt
python3 --version >> diagnostic.txt
echo "" >> diagnostic.txt

echo "=== Service Status ===" >> diagnostic.txt
systemctl status espfinder-web --no-pager >> diagnostic.txt
echo "" >> diagnostic.txt

echo "=== Logs ===" >> diagnostic.txt
journalctl -u espfinder-web -n 100 --no-pager >> diagnostic.txt
echo "" >> diagnostic.txt

echo "=== Environment ===" >> diagnostic.txt
cat /etc/espfinder/espfinder.env >> diagnostic.txt
echo "" >> diagnostic.txt

echo "=== Permissions ===" >> diagnostic.txt
ls -la /opt/espfinder/ | head -20 >> diagnostic.txt
ls -la /var/lib/espfinder/ >> diagnostic.txt
```

2. Share the `diagnostic.txt` file
