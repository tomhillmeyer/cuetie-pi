#!/bin/bash
set -e

PI_USER="${PI_USER:-pi}"
PI_PASS="${PI_PASS:-raspberry}"
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

echo "==> Restarting backend service..."
sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_HOST" \
  "echo '$PI_PASS' | sudo -S systemctl daemon-reload && sudo -S systemctl restart cuetie-pi"

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
