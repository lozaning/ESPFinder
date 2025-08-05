#!/bin/bash

REPO_URL="https://github.com/lozaning/ESPFinder.git"
INSTALL_DIR="$HOME/ESPFinder"
DOCKER_COMPOSE_VERSION="2.20.0"

echo "🔍 ESPFinder Installation Script"
echo "================================="

check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        echo "✅ $1 is installed"
        return 0
    else
        echo "❌ $1 is not installed"
        return 1
    fi
}

install_docker() {
    echo "📦 Installing Docker..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt-get >/dev/null 2>&1; then
            # Ubuntu/Debian
            echo "🔄 Updating package list..."
            sudo apt-get update -qq || { echo "❌ Failed to update package list"; exit 1; }
            
            echo "🔄 Installing prerequisites..."
            sudo DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates curl gnupg lsb-release || { echo "❌ Failed to install prerequisites"; exit 1; }
            
            echo "🔄 Adding Docker GPG key..."
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg || { echo "❌ Failed to add Docker GPG key"; exit 1; }
            
            echo "🔄 Adding Docker repository..."
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null || { echo "❌ Failed to add Docker repository"; exit 1; }
            
            echo "🔄 Updating package list with Docker repository..."
            sudo apt-get update -qq || { echo "❌ Failed to update package list with Docker repository"; exit 1; }
            
            echo "🔄 Installing Docker..."
            sudo DEBIAN_FRONTEND=noninteractive apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin || { echo "❌ Failed to install Docker"; exit 1; }
            
        elif command -v yum >/dev/null 2>&1; then
            # RHEL/CentOS/Fedora
            echo "🔄 Installing yum-utils..."
            sudo yum install -y yum-utils
            
            echo "🔄 Adding Docker repository..."
            sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
            
            echo "🔄 Installing Docker..."
            sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
            
        else
            echo "❌ Unsupported Linux distribution. Please install Docker manually."
            exit 1
        fi
        
        echo "🔄 Starting Docker service..."
        sudo systemctl start docker
        sudo systemctl enable docker
        
        echo "🔄 Adding user to docker group..."
        sudo usermod -aG docker $USER
        
        echo "✅ Docker installed successfully!"
        
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew >/dev/null 2>&1; then
            brew install --cask docker
        else
            echo "❌ Please install Homebrew first or install Docker Desktop manually"
            exit 1
        fi
    else
        echo "❌ Unsupported operating system. Please install Docker manually."
        exit 1
    fi
}

install_docker_compose() {
    if ! command -v docker-compose >/dev/null 2>&1; then
        echo "📦 Installing Docker Compose..."
        
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            sudo curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
            sudo chmod +x /usr/local/bin/docker-compose
        fi
    fi
}

clone_repo() {
    echo "📥 Cloning ESPFinder repository..."
    
    if [ -d "$INSTALL_DIR" ]; then
        echo "⚠️  Directory $INSTALL_DIR already exists. Updating..."
        cd "$INSTALL_DIR"
        git pull origin main
    else
        git clone "$REPO_URL" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi
}

setup_environment() {
    echo "⚙️  Setting up environment..."
    
    if [ ! -f "config/.env" ]; then
        cp config/.env.example config/.env
        echo "✅ Created config/.env file"
    fi
    
    mkdir -p data/database data/images
    echo "✅ Created data directories"
}

build_and_start() {
    echo "🐳 Building and starting ESPFinder..."
    
    docker-compose build
    docker-compose up -d
    
    echo "✅ ESPFinder is now running!"
    echo ""
    echo "📊 Check status with: cd $INSTALL_DIR && docker-compose logs -f"
    echo "🛑 Stop with: cd $INSTALL_DIR && docker-compose down"
    echo "🔄 Restart with: cd $INSTALL_DIR && docker-compose restart"
}

main() {
    echo "🔍 Checking prerequisites..."
    
    echo "➡️  Checking for git..."
    if ! check_command git; then
        echo "❌ Git is required but not installed. Please install git first."
        exit 1
    fi
    
    echo "➡️  Checking for docker..."
    if ! check_command docker; then
        echo "⚠️  Docker not found, installing..."
        install_docker
        echo "⚠️  Docker was just installed. You may need to log out and back in for group permissions to take effect."
        echo "   Run this script again after logging back in."
        exit 0
    fi
    
    echo "➡️  Checking for docker-compose..."
    if ! check_command docker-compose && ! docker compose version >/dev/null 2>&1; then
        install_docker_compose
    fi
    
    echo "✅ All prerequisites satisfied!"
    
    clone_repo
    setup_environment
    build_and_start
    
    echo ""
    echo "🎉 ESPFinder installation complete!"
    echo ""
    echo "🔗 Data will be stored in: $INSTALL_DIR/data"
    echo "📁 Images: $INSTALL_DIR/data/images"
    echo "🗄️  Database: $INSTALL_DIR/data/database"
    echo ""
    echo "To customize settings, edit: $INSTALL_DIR/config/.env"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi