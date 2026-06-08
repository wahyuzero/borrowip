#!/bin/bash
# BorrowIP Termux installer
# Usage: curl -sL https://raw.githubusercontent.com/wahyuzero/borrowip/main/scripts/install-termux.sh | bash

set -e

echo "📡 Installing BorrowIP on Termux..."

# Update packages
pkg update -y

# Install dependencies
pkg install openssh python -y

# Install borrowip
pip install borrowip[client]

echo ""
echo "✅ BorrowIP installed!"
echo ""
echo "Setup SSH key (if you don't have one):"
echo "  ssh-keygen -t ed25519"
echo "  ssh-copy-id user@your-vps-ip"
echo ""
echo "Then connect:"
echo "  borrowip init"
echo "  borrowip connect BIP-xxxx@your-vps-ip"
