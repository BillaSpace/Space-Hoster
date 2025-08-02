#!/bin/bash

# Space Deployer Bot Deployment Script
# For Ubuntu VPS, Render, Heroku, Railway, etc.

echo "🚀 Starting Space Deployer Bot deployment..."

# Check if running on different platforms
if [ "$RAILWAY_ENVIRONMENT" ]; then
    echo "📡 Detected Railway deployment"
    export PLATFORM="railway"
elif [ "$RENDER" ]; then
    echo "📡 Detected Render deployment"
    export PLATFORM="render"
elif [ "$DYNO" ]; then
    echo "📡 Detected Heroku deployment"
    export PLATFORM="heroku"
else
    echo "📡 Detected VPS/Local deployment"
    export PLATFORM="vps"
fi

# Install system dependencies for VPS
if [ "$PLATFORM" = "vps" ]; then
    echo "📦 Installing system dependencies..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip nodejs npm openjdk-11-jdk maven docker.io
    
    # Start Docker service
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -aG docker $USER
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p uploads temp deployed_bots static logs

# Set environment variables
echo "⚙️ Setting up environment..."
if [ ! -f .env ]; then
    echo "Creating .env file template..."
    cat > .env << EOL
BOT_TOKEN=your_bot_token_here
MONGODB_URI=your_mongodb_uri_here
ADMIN_IDS=your_admin_ids_here
OWNER_ID=your_owner_id_here
DEV_ID=your_dev_id_here
LOGGER_ID=your_logger_id_here
EOL
    echo "⚠️  Please edit .env file with your actual values!"
fi

# Download welcome image if not exists
if [ ! -f static/welcome.jpg ]; then
    echo "🖼️  Downloading welcome image..."
    curl -o static/welcome.jpg "https://via.placeholder.com/800x400/0066cc/ffffff?text=Space+Deployer+Bot"
fi

# Set permissions
chmod +x main.py
chmod 755 deployed_bots uploads temp logs

echo "✅ Deployment setup complete!"

# Start the bot based on platform
case $PLATFORM in
    "railway"|"render"|"heroku")
        echo "☁️  Starting on cloud platform..."
        python3 main.py
        ;;
    "vps")
        echo "🖥️  Starting on VPS..."
        # Create systemd service
        sudo tee /etc/systemd/system/space-deployer.service > /dev/null <<EOF
[Unit]
Description=Space Deployer Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/python3 $(pwd)/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
        
        sudo systemctl daemon-reload
        sudo systemctl enable space-deployer
        sudo systemctl start space-deployer
        
        echo "✅ Space Deployer Bot service started!"
        echo "📊 Check status: sudo systemctl status space-deployer"
        echo "📋 View logs: sudo journalctl -u space-deployer -f"
        ;;
esac
