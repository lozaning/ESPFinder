# ESPFinder

Automatically downloads internal photos from new FCC product filings and stores them in a database for analysis.

## Quick Start

### Docker Installation (Recommended)

Install with one command:

```bash
curl -sSL https://raw.githubusercontent.com/lozaning/ESPFinder/main/install.sh | bash
```

This will:
- Install Docker and Docker Compose if not present
- Clone the repository to `~/ESPFinder`
- Set up the environment
- Build and start the containers

### Proxmox LXC Container Installation

For deploying in a Proxmox LXC container (Ubuntu 25+):

```bash
wget -O - https://raw.githubusercontent.com/lozaning/ESPFinder/main/install-lxc.sh | bash
```

This installs ESPFinder natively without Docker, perfect for LXC containers. See [LXC Deployment Guide](docs/LXC-DEPLOYMENT.md) for details.

## Manual Installation

1. Clone the repository:
```bash
git clone https://github.com/lozaning/ESPFinder.git
cd ESPFinder
```

2. Copy environment file:
```bash
cp config/.env.example config/.env
```

3. Create data directories:
```bash
mkdir -p data/database data/images
```

4. Start with Docker Compose:
```bash
docker-compose up -d
```

## Usage

The system runs automatically and:
1. Checks for new FCC filings every day
2. Downloads PDFs containing internal photos
3. Extracts images from the PDFs
4. Stores everything in a local database

## Data Storage

- **Database**: `data/database/espfinder.db` (SQLite by default)
- **Images**: `data/images/{fcc_id}/` (organized by FCC ID)

## Configuration

Edit `config/.env` to customize:
- `DATABASE_URL` - Database connection string
- `DOWNLOAD_DELAY` - Delay between requests (seconds)
- `LOG_LEVEL` - Logging verbosity

## Commands

```bash
# View logs
docker-compose logs -f

# Stop the system
docker-compose down

# Restart
docker-compose restart

# Run manually
docker-compose run espfinder python -m src.main
```

## Architecture

- **FCC Scraper**: Monitors FCC database for new filings
- **PDF Processor**: Downloads and extracts images from PDFs  
- **Database**: SQLite/PostgreSQL for metadata storage
- **File Storage**: Local filesystem for images

## Web Interface

Access the web interface at `http://localhost:5000` (Docker) or `http://YOUR-IP:5000` (LXC) to:
- Browse all scraped products
- View extracted images
- Search by FCC ID, applicant, or product name
- Manually trigger scraper runs
- View system logs and statistics

## Deployment Options

- **Docker**: Best for development and quick testing ([install.sh](install.sh))
- **Proxmox LXC**: Best for production deployments in containers ([install-lxc.sh](install-lxc.sh))
- **Manual**: Full control over installation (see Manual Installation above)

See [LXC Deployment Guide](docs/LXC-DEPLOYMENT.md) for detailed LXC setup instructions.

## Future Features

- Computer vision for PCB component identification
- Advanced filtering and search
- Export capabilities
- Email notifications for new findings