#!/bin/bash

echo "🔍 ESPFinder Installation Script"
echo "================================="

# Check if git is installed
echo "Checking for git..."
if ! which git > /dev/null; then
    echo "❌ Git not found. Install with: sudo apt update && sudo apt install git"
    exit 1
fi
echo "✅ Git found"

# Check if docker is installed
echo "Checking for docker..."
if ! which docker > /dev/null; then
    echo "❌ Docker not found. Installing..."
    
    echo "Updating packages..."
    sudo apt update
    
    echo "Installing docker..."
    sudo apt install -y docker.io
    
    echo "Starting docker service..."
    sudo systemctl start docker
    sudo systemctl enable docker
    
    echo "Adding user to docker group..."
    sudo usermod -aG docker $USER
    
    echo "✅ Docker installed! You need to log out and log back in for docker group to take effect."
    echo "Then run this script again."
    exit 0
fi
echo "✅ Docker found"

# Check if docker-compose is installed
echo "Checking for docker-compose..."
if ! which docker-compose > /dev/null; then
    echo "Installing docker-compose..."
    sudo apt install -y docker-compose
fi
echo "✅ Docker-compose ready"

# Clone or update repo
INSTALL_DIR="$HOME/ESPFinder"
echo "Setting up ESPFinder in $INSTALL_DIR..."

if [ -d "$INSTALL_DIR" ]; then
    echo "Directory exists, updating..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "Cloning repository..."
    git clone https://github.com/lozaning/ESPFinder.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Setup environment
echo "Setting up environment..."
if [ ! -f "config/.env" ]; then
    cp config/.env.example config/.env
    echo "✅ Created config/.env"
fi

mkdir -p data/database data/images
echo "✅ Created data directories"

# Build and start
echo "Building and starting ESPFinder..."
docker-compose build
docker-compose up -d

echo ""
echo "🎉 ESPFinder is running!"
echo ""
echo "Commands:"
echo "  View logs: cd $INSTALL_DIR && docker-compose logs -f"
echo "  Stop:      cd $INSTALL_DIR && docker-compose down"
echo "  Restart:   cd $INSTALL_DIR && docker-compose restart"