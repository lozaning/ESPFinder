#!/bin/bash
set -e  # Exit on any error

echo "🔍 ESPFinder Installation Script"
echo "================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to run docker commands, handling group permissions
run_docker() {
    if docker ps >/dev/null 2>&1; then
        docker "$@"
    elif command_exists newgrp; then
        sg docker -c "docker $*"
    else
        sudo docker "$@"
    fi
}

# Function to run docker compose commands
run_docker_compose() {
    if docker compose version >/dev/null 2>&1; then
        run_docker compose "$@"
    elif command_exists docker-compose; then
        if docker-compose ps >/dev/null 2>&1; then
            docker-compose "$@"
        elif command_exists newgrp; then
            sg docker -c "docker-compose $*"
        else
            sudo docker-compose "$@"
        fi
    else
        echo "❌ Docker Compose not found. Installing..."
        sudo apt install -y docker-compose || {
            echo "❌ Failed to install docker-compose"
            exit 1
        }
        sudo docker-compose "$@"
    fi
}

# Check if git is installed
echo "Checking for git..."
if ! command_exists git; then
    echo "❌ Git not found. Installing..."
    sudo apt update || { echo "❌ Failed to update packages"; exit 1; }
    sudo apt install -y git || { echo "❌ Failed to install git"; exit 1; }
fi
echo "✅ Git found"

# Check if docker is installed
echo "Checking for docker..."
DOCKER_INSTALLED=false
if ! command_exists docker; then
    echo "❌ Docker not found. Installing..."

    echo "Updating packages..."
    sudo apt update || { echo "❌ Failed to update packages"; exit 1; }

    echo "Installing docker..."
    sudo apt install -y docker.io || { echo "❌ Failed to install docker"; exit 1; }

    echo "Starting docker service..."
    sudo systemctl start docker || { echo "⚠️  Failed to start docker service"; }
    sudo systemctl enable docker || { echo "⚠️  Failed to enable docker service"; }

    echo "Adding user to docker group..."
    sudo usermod -aG docker $USER || { echo "⚠️  Failed to add user to docker group"; }

    DOCKER_INSTALLED=true
    echo "✅ Docker installed!"
else
    echo "✅ Docker found"
fi

# Verify docker is running
echo "Verifying docker daemon..."
if ! sudo docker ps >/dev/null 2>&1; then
    echo "❌ Docker daemon is not running or not accessible"
    exit 1
fi
echo "✅ Docker daemon running"

# Clone or update repo
INSTALL_DIR="$HOME/ESPFinder"
echo "Setting up ESPFinder in $INSTALL_DIR..."

if [ -d "$INSTALL_DIR" ]; then
    echo "Directory exists, updating..."
    cd "$INSTALL_DIR" || { echo "❌ Failed to enter directory"; exit 1; }
    git pull || { echo "⚠️  Failed to pull updates, continuing anyway..."; }
else
    echo "Cloning repository..."
    git clone https://github.com/lozaning/ESPFinder.git "$INSTALL_DIR" || { echo "❌ Failed to clone repository"; exit 1; }
    cd "$INSTALL_DIR" || { echo "❌ Failed to enter directory"; exit 1; }
fi

# Setup environment
echo "Setting up environment..."
if [ ! -f "config/.env" ]; then
    if [ -f "config/.env.example" ]; then
        cp config/.env.example config/.env
        echo "✅ Created config/.env"
    else
        echo "⚠️  config/.env.example not found, skipping..."
    fi
fi

mkdir -p data/database data/images
echo "✅ Created data directories"

# Build and start
echo "Building and starting ESPFinder..."
echo "This may take a few minutes on first run..."

run_docker_compose build || { echo "❌ Failed to build containers"; exit 1; }
run_docker_compose up -d || { echo "❌ Failed to start containers"; exit 1; }

# Wait a moment for containers to start
sleep 3

# Check container status
echo ""
echo "Checking container status..."
run_docker_compose ps

echo ""
echo "🎉 ESPFinder installation complete!"
echo ""
echo "Access the web interface at: http://localhost:5000"
echo ""
echo "Useful commands:"
echo "  View logs:   cd $INSTALL_DIR && docker compose logs -f"
echo "  Stop:        cd $INSTALL_DIR && docker compose down"
echo "  Restart:     cd $INSTALL_DIR && docker compose restart"
echo "  Run scraper: cd $INSTALL_DIR && docker compose run espfinder python -m src.main"
echo ""

if [ "$DOCKER_INSTALLED" = true ]; then
    echo "📝 Note: Docker was just installed. If you see permission errors, you may need to:"
    echo "   1. Log out and log back in, OR"
    echo "   2. Run: newgrp docker"
    echo ""
fi