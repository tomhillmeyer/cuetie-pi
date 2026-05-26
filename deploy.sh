#!/bin/bash
set -e

PI_USER="${PI_USER:-pi}"
PI_PASS="${PI_PASS:?Set PI_PASS (e.g. PI_PASS=raspberry ./deploy.sh)}"
PI_HOST="${PI_HOST:?Set PI_HOST (e.g. PI_HOST=192.168.1.50 ./deploy.sh)}"
PI_PATH="${PI_PATH:-/home/pi/cuetie-pi}"

echo "==> Deploying to $PI_HOST..."

echo "==> Building frontend..."
cd frontend
npm run build
cd ..

echo "==> Syncing code to Pi (preserving media, cues, and .env)..."
sshpass -p "$PI_PASS" rsync -avz --delete \
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

echo "==> Syncing weston config..."
sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" \
  "echo '$PI_PASS' | sudo -S mkdir -p /etc/xdg/weston"
sshpass -p "$PI_PASS" rsync -avz \
  --rsh="ssh -o StrictHostKeyChecking=no" \
  backend/weston.ini "$PI_USER@$PI_HOST:$PI_PATH/backend/weston.ini"
sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" \
  "echo '$PI_PASS' | sudo -S cp $PI_PATH/backend/weston.ini /etc/xdg/weston/weston.ini"

echo "==> Syncing weston systemd unit..."
sshpass -p "$PI_PASS" rsync -avz \
  --rsh="ssh -o StrictHostKeyChecking=no" \
  backend/weston.service "$PI_USER@$PI_HOST:$PI_PATH/backend/weston.service"
sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" \
  "echo '$PI_PASS' | sudo -S cp $PI_PATH/backend/weston.service /etc/systemd/system/weston.service"

echo "==> Syncing cuetie-pi systemd unit..."
sshpass -p "$PI_PASS" rsync -avz \
  --rsh="ssh -o StrictHostKeyChecking=no" \
  backend/cuetie-pi.service "$PI_USER@$PI_HOST:$PI_PATH/backend/cuetie-pi.service"
sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" \
  "echo '$PI_PASS' | sudo -S cp $PI_PATH/backend/cuetie-pi.service /etc/systemd/system/cuetie-pi.service"

echo "==> Ensuring seatd is installed and running..."
sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" \
  "echo '$PI_PASS' | sudo -S apt install -y seatd && \
   echo '$PI_PASS' | sudo -S systemctl enable --now seatd"

echo "==> Installing pmount for USB import..."
sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" \
  "echo '$PI_PASS' | sudo -S apt install -y pmount"

echo "==> Restarting services..."
sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" \
  "echo '$PI_PASS' | sudo -S systemctl daemon-reload"
sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" \
  "echo '$PI_PASS' | sudo -S systemctl restart weston"
sleep 2
sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" \
  "echo '$PI_PASS' | sudo -S systemctl restart cuetie-pi"

sleep 2

echo "==> Verifying service is running..."
sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" \
  "systemctl is-active cuetie-pi"

echo ""
echo "=== DEPLOY COMPLETE ==="
echo "URL: http://$PI_HOST:8000"
echo ""
echo "To test status:"
echo "  curl http://$PI_HOST:8000/api/status"
