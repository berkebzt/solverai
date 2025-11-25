#!/bin/bash

# Ollama GPU VM Startup Script for Google Cloud
# This script installs NVIDIA drivers, Docker, and Ollama with GPU support

set -e

echo "Starting Ollama GPU VM setup..."

# Update system
apt-get update
apt-get upgrade -y

# Install NVIDIA drivers
echo "Installing NVIDIA drivers..."
apt-get install -y linux-headers-$(uname -r)

# Add NVIDIA package repositories
distribution=$(. /etc/os-release;echo $ID$VERSION_ID | sed -e 's/\.//g')
wget https://developer.download.nvidia.com/compute/cuda/repos/$distribution/x86_64/cuda-keyring_1.0-1_all.deb
dpkg -i cuda-keyring_1.0-1_all.deb
apt-get update

# Install CUDA
apt-get install -y cuda-drivers-535

# Install Ollama
echo "Installing Ollama..."
curl -fsSL https://ollama.ai/install.sh | sh

# Configure Ollama to listen on all interfaces
mkdir -p /etc/systemd/system/ollama.service.d
cat > /etc/systemd/system/ollama.service.d/override.conf << EOF
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
EOF

# Reload and start Ollama
systemctl daemon-reload
systemctl enable ollama
systemctl restart ollama

# Wait for Ollama to start
sleep 10

# Pull the Llama 3.1 model
echo "Pulling Llama 3.1 8B model (this will take ~10 minutes)..."
ollama pull llama3.1:8b

echo "Ollama setup complete!"
echo "GPU info:"
nvidia-smi

echo "Ollama status:"
systemctl status ollama
