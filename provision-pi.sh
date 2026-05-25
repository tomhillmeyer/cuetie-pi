#!/bin/bash
set -e

PI_USER="${PI_USER:-pi}"
PI_PASS="${PI_PASS:?Set PI_PASS (e.g. PI_PASS=raspberry ./provision-pi.sh)}"
PI_HOST="${PI_HOST:?Set PI_HOST (e.g. PI_HOST=192.168.1.50 ./provision-pi.sh)}"
PI_PATH="${PI_PATH:-/home/pi/cuetie-pi}"
SSHPASS="sshpass -p $PI_PASS"
SSH="$SSHPASS ssh -o StrictHostKeyChecking=no $PI_USER@$PI_HOST"

echo "======================================"
echo " Cutie Pi Provisioning Script"
echo " Target: $PI_HOST"
echo "======================================"
echo ""

echo "==> Step 1: Installing/updating system packages..."
$SSH "echo '$PI_PASS' | sudo -S apt update && \
  echo '$PI_PASS' | sudo -S apt install -y \
    mpv \
    weston \
    seatd \
    python3 \
    python3-venv \
    python3-pip \
    python3-dev \
    libevdev2"

echo ""
echo "==> Step 1b: Enabling seatd service..."
$SSH "echo '$PI_PASS' | sudo -S systemctl enable --now seatd"

echo ""
echo "==> Step 2: Ensuring user '$PI_USER' is in required groups (video/render/tty/seat)..."
$SSH "echo '$PI_PASS' | sudo -S usermod -aG video \$USER && \
      echo '$PI_PASS' | sudo -S usermod -aG render \$USER && \
      echo '$PI_PASS' | sudo -S usermod -aG tty \$USER"
$SSH "groups"

echo ""
echo "==> Step 3: Checking GPU memory configuration..."
GPU_MEM=""
if $SSH "grep -q 'gpu_mem' /boot/firmware/config.txt 2>/dev/null"; then
  GPU_MEM=$($SSH "grep gpu_mem /boot/firmware/config.txt")
elif $SSH "grep -q 'gpu_mem' /boot/config.txt 2>/dev/null"; then
  GPU_MEM=$($SSH "grep gpu_mem /boot/config.txt")
fi

if [ -n "$GPU_MEM" ]; then
  echo "Current GPU memory setting: $GPU_MEM"
else
  echo "WARNING: No gpu_mem setting found. For reliable video playback, you need:"
  echo "         gpu_mem=256 in /boot/firmware/config.txt"
  echo ""
  read -p "Add gpu_mem=256 now? (requires reboot) [y/N] " -n 1 -r
  echo ""
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    if $SSH "[ -f /boot/firmware/config.txt ]"; then
      $SSH "echo '$PI_PASS' | sudo -S sh -c 'echo \"gpu_mem=256\" >> /boot/firmware/config.txt'"
    else
      $SSH "echo '$PI_PASS' | sudo -S sh -c 'echo \"gpu_mem=256\" >> /boot/config.txt'"
    fi
    echo "Added gpu_mem=256. A reboot will be required for this to take effect."
  fi
fi

echo ""
echo "==> Step 4: Syncing codebase to Pi..."
cd /Users/tomhillmeyer/Documents/dev/cuetie-pi
$SSHPASS rsync -avz \
  --rsh="ssh -o StrictHostKeyChecking=no" \
  --exclude='.git/' \
  --exclude='backend/venv/' \
  --exclude='backend/__pycache__/' \
  --exclude='backend/media/' \
  --exclude='backend/cues.json' \
  --exclude='backend/.env' \
  --exclude='frontend/node_modules/' \
  --exclude='.DS_Store' \
  ./ "$PI_USER@$PI_HOST:$PI_PATH/"

echo ""
echo "==> Step 5: Setting up Python virtual environment..."
$SSH "cd $PI_PATH/backend && \
      rm -rf venv && \
      python3 -m venv venv && \
      ./venv/bin/pip install --upgrade pip && \
      ./venv/bin/pip install -r requirements.txt"

echo ""
echo "==> Step 6: Setting up .env file if not exists..."
$SSH "cd $PI_PATH/backend && \
      if [ ! -f .env ]; then \
        echo 'Creating default .env file...' && \
        echo 'PORT=8000' > .env && \
        echo 'MEDIA_DIR=./media' >> .env && \
        echo 'CUES_FILE=./cues.json' >> .env && \
        echo 'DISPLAY=:0' >> .env && \
        echo 'WAYLAND_DISPLAY=wayland-1' >> .env && \
        echo 'XDG_RUNTIME_DIR=/tmp/weston-runtime' >> .env; \
      else \
        echo 'Existing .env found - preserving it.'; \
      fi && \
      mkdir -p media"

echo ""
echo "==> Step 7: Installing Weston Wayland compositor..."
$SSH "echo '$PI_PASS' | sudo -S mkdir -p /etc/xdg/weston"
$SSHPASS rsync -avz \
  --rsh="ssh -o StrictHostKeyChecking=no" \
  backend/weston.ini "$PI_USER@$PI_HOST:$PI_PATH/backend/weston.ini"
$SSH "echo '$PI_PASS' | sudo -S cp $PI_PATH/backend/weston.ini /etc/xdg/weston/weston.ini"

$SSHPASS rsync -avz \
  --rsh="ssh -o StrictHostKeyChecking=no" \
  backend/weston.service "$PI_USER@$PI_HOST:$PI_PATH/backend/weston.service"
$SSH "echo '$PI_PASS' | sudo -S cp $PI_PATH/backend/weston.service /etc/systemd/system/weston.service && \
      echo '$PI_PASS' | sudo -S systemctl daemon-reload && \
      echo '$PI_PASS' | sudo -S systemctl enable weston"

echo ""
echo "==> Step 8: Installing cuetie-pi systemd service..."
$SSHPASS rsync -avz \
  --rsh="ssh -o StrictHostKeyChecking=no" \
  backend/cuetie-pi.service "$PI_USER@$PI_HOST:$PI_PATH/backend/cuetie-pi.service"

$SSH "echo '$PI_PASS' | sudo -S cp $PI_PATH/backend/cuetie-pi.service /etc/systemd/system/cuetie-pi.service && \
      echo '$PI_PASS' | sudo -S systemctl daemon-reload && \
      echo '$PI_PASS' | sudo -S systemctl enable cuetie-pi"

echo ""
echo "==> Step 9: Starting services (Weston first, then cuetie-pi)..."
$SSH "echo '$PI_PASS' | sudo -S systemctl start weston"
sleep 3
$SSH "echo '$PI_PASS' | sudo -S systemctl start cuetie-pi"

sleep 2

echo ""
echo "==> Step 10: Verifying services..."
$SSH "systemctl is-active weston && systemctl is-active cuetie-pi"

echo ""
echo "======================================"
echo " PROVISIONING COMPLETE"
echo "======================================"
echo ""
echo "Service URL: http://$PI_HOST:8000"
echo ""
echo "Useful commands:"
echo "  Check status:  curl http://$PI_HOST:8000/api/status"
echo "  View logs:     journalctl -u cuetie-pi -f"
echo "  Restart:       sudo systemctl restart cuetie-pi"
echo ""
if [ -z "$GPU_MEM" ] || [[ ! $GPU_MEM == *"256"* ]]; then
  echo "NOTE: Consider setting gpu_mem=256 in /boot/firmware/config.txt and rebooting"
  echo "for best video playback performance."
  echo ""
fi
