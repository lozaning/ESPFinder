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

# Function to install docker compose
install_docker_compose() {
    echo "Installing Docker Compose..."

    # Try to install Docker Compose v2 plugin (modern method)
    if sudo apt install -y docker-compose-plugin 2>/dev/null; then
        echo "✅ Installed Docker Compose v2 plugin"
        return 0
    fi

    # Fallback: install standalone docker-compose
    echo "Docker Compose plugin not available, installing standalone version..."

    # On Ubuntu 24+ with Python 3.12, we need python3-distutils for old docker-compose
    # Safe to install on any version, so just try it
    echo "Installing python3-distutils for docker-compose compatibility..."
    sudo apt install -y python3-distutils 2>/dev/null || echo "  (python3-distutils not available or already installed)"

    sudo apt install -y docker-compose || {
        echo "❌ Failed to install docker-compose"
        return 1
    }

    # Verify it works
    if docker-compose version >/dev/null 2>&1; then
        echo "✅ Installed docker-compose"
        return 0
    else
        echo "⚠️  docker-compose installed but not working, will use sudo"
        return 0
    fi
}

# Function to run docker compose commands
run_docker_compose() {
    # Try Docker Compose v2 (plugin)
    if sudo docker compose version >/dev/null 2>&1; then
        sudo docker compose "$@"
        return $?
    fi

    # Try standalone docker-compose
    if command_exists docker-compose; then
        if docker-compose version >/dev/null 2>&1; then
            docker-compose "$@"
        elif command_exists sg; then
            sg docker -c "docker-compose $*"
        else
            sudo docker-compose "$@"
        fi
        return $?
    fi

    # Neither found, install it
    echo "❌ Docker Compose not found."
    install_docker_compose || exit 1

    # Try again after installation
    if sudo docker compose version >/dev/null 2>&1; then
        sudo docker compose "$@"
    else
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