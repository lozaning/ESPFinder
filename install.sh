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

    # Update package lists
    sudo apt update -qq

    # Try to install Docker Compose v2 plugin from official Docker repo
    echo "Attempting to install Docker Compose v2 plugin..."
    if sudo apt install -y docker-compose-plugin 2>/dev/null && sudo docker compose version >/dev/null 2>&1; then
        echo "✅ Installed Docker Compose v2 plugin"
        return 0
    fi

    # On Ubuntu 24+, python3-distutils doesn't exist and old docker-compose is broken
    # We need to manually install Docker Compose v2 from GitHub
    echo "Docker Compose plugin not available from apt."
    echo "Installing Docker Compose v2 manually..."

    # Detect architecture
    ARCH=$(uname -m)
    case $ARCH in
        x86_64)
            COMPOSE_ARCH="x86_64"
            ;;
        aarch64|arm64)
            COMPOSE_ARCH="aarch64"
            ;;
        armv7l)
            COMPOSE_ARCH="armv7"
            ;;
        *)
            echo "❌ Unsupported architecture: $ARCH"
            return 1
            ;;
    esac

    # Download and install Docker Compose v2
    COMPOSE_VERSION="v2.24.5"
    COMPOSE_URL="https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-${COMPOSE_ARCH}"

    echo "Downloading Docker Compose ${COMPOSE_VERSION} for ${COMPOSE_ARCH}..."
    sudo curl -SL "$COMPOSE_URL" -o /usr/local/bin/docker-compose || {
        echo "❌ Failed to download Docker Compose"
        return 1
    }

    sudo chmod +x /usr/local/bin/docker-compose

    # Create symlink for 'docker compose' command
    sudo mkdir -p /usr/local/lib/docker/cli-plugins
    sudo ln -sf /usr/local/bin/docker-compose /usr/local/lib/docker/cli-plugins/docker-compose

    # Verify it works
    if docker-compose version >/dev/null 2>&1; then
        echo "✅ Docker Compose v2 installed successfully"
        docker-compose version
        return 0
    elif /usr/local/bin/docker-compose version >/dev/null 2>&1; then
        echo "✅ Docker Compose v2 installed successfully"
        /usr/local/bin/docker-compose version
        return 0
    else
        echo "❌ Docker Compose installation failed"
        return 1
    fi
}

# Function to run docker compose commands
run_docker_compose() {
    # Try Docker Compose v2 (plugin) - 'docker compose' subcommand
    if sudo docker compose version >/dev/null 2>&1; then
        sudo docker compose "$@"
        return $?
    fi

    # Try standalone docker-compose v2 from manual install
    if [ -x "/usr/local/bin/docker-compose" ] && /usr/local/bin/docker-compose version >/dev/null 2>&1; then
        /usr/local/bin/docker-compose "$@"
        return $?
    fi

    # Check if docker-compose exists in PATH and works
    if command_exists docker-compose; then
        # Test if it actually works (not broken by missing distutils)
        if docker-compose version >/dev/null 2>&1; then
            docker-compose "$@"
            return $?
        elif sudo docker-compose version >/dev/null 2>&1; then
            sudo docker-compose "$@"
            return $?
        else
            # docker-compose exists but is broken (Ubuntu 24 + Python 3.12 issue)
            echo "⚠️  docker-compose is installed but broken, attempting to fix..."
            install_docker_compose || exit 1

            # Try again after fix
            if sudo docker compose version >/dev/null 2>&1; then
                sudo docker compose "$@"
            elif [ -x "/usr/local/bin/docker-compose" ]; then
                /usr/local/bin/docker-compose "$@"
            elif sudo docker-compose version >/dev/null 2>&1; then
                sudo docker-compose "$@"
            else
                echo "❌ Failed to get working Docker Compose"
                exit 1
            fi
            return $?
        fi
    fi

    # Neither found, install it
    echo "❌ Docker Compose not found."
    install_docker_compose || exit 1

    # Try again after installation
    if sudo docker compose version >/dev/null 2>&1; then
        sudo docker compose "$@"
    elif [ -x "/usr/local/bin/docker-compose" ]; then
        /usr/local/bin/docker-compose "$@"
    elif sudo docker-compose version >/dev/null 2>&1; then
        sudo docker-compose "$@"
    else
        echo "❌ Failed to get working Docker Compose"
        exit 1
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