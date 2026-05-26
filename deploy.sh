#!/bin/bash
set -e

PI_USER="${PI_USER:-pi}"
PI_HOST="${PI_HOST:?Set PI_HOST (e.g. PI_HOST=192.168.1.50 ./deploy.sh)}"
PI_PATH="${PI_PATH:-/home/pi/cuetie-pi}"

echo "==> Deploying to $PI_USER@$PI_HOST..."

echo "==> Building frontend..."
cd "$(dirname "$0")/frontend"
npm run build
cd ..

SSH_OPTS="-o StrictHostKeyChecking=no"

if [ -n "${PI_PASS:-}" ]; then
  RSYNC_RSH="sshpass -p $PI_PASS ssh $SSH_OPTS"
  SSH_CMD="sshpass -p $PI_PASS ssh $SSH_OPTS"
  _sudocmd() { echo "echo '$PI_PASS' | sudo -S $*"; }
else
  RSYNC_RSH="ssh $SSH_OPTS"
  SSH_CMD="ssh $SSH_OPTS"
  _sudocmd() { echo "sudo $*"; }
fi

_ssh() { $SSH_CMD "$PI_USER@$PI_HOST" "$*"; }

echo "==> Syncing code to Pi (preserving media, cues, and .env)..."
rsync -avz --delete --rsh="$RSYNC_RSH" \
  --exclude='.git/' \
  --exclude='backend/venv/' \
  --exclude='backend/__pycache__/' \
  --exclude='backend/media/' \
  --exclude='backend/cues.json' \
  --exclude='backend/.env' \
  --exclude='frontend/node_modules/' \
  --exclude='out/' \
  --exclude='scripts/' \
  --exclude='*.tar.gz' \
  --exclude='CONTEXT.md' \
  --exclude='build-spec.md' \
  --exclude='testing.md' \
  --exclude='.DS_Store' \
  ./ "$PI_USER@$PI_HOST:$PI_PATH/"

echo "==> Syncing weston config..."
_ssh "$(_sudocmd mkdir -p /etc/xdg/weston)"
_ssh "$(_sudocmd cp $PI_PATH/backend/weston.ini /etc/xdg/weston/weston.ini)"

echo "==> Syncing systemd units..."
_ssh "$(_sudocmd cp $PI_PATH/backend/weston.service /etc/systemd/system/weston.service)"
_ssh "$(_sudocmd cp $PI_PATH/backend/cuetie-pi.service /etc/systemd/system/cuetie-pi.service)"

echo "==> Ensuring seatd is installed..."
_ssh "$(_sudocmd apt install -y seatd)" || true
_ssh "$(_sudocmd systemctl enable --now seatd)" || true

echo "==> Installing pmount..."
_ssh "$(_sudocmd apt install -y pmount)" || true

echo "==> Restarting services..."
_ssh "$(_sudocmd systemctl daemon-reload)"
_ssh "$(_sudocmd systemctl restart weston)"
sleep 2
_ssh "$(_sudocmd systemctl restart cuetie-pi)"

sleep 2

echo "==> Verifying..."
_ssh "systemctl is-active cuetie-pi"

echo ""
echo "=== DEPLOY COMPLETE ==="
echo "URL: http://$PI_HOST:8000"
echo ""
echo "Examples:"
echo "  PI_HOST=192.168.1.50                    ./deploy.sh   (SSH keys)"
echo "  PI_PASS=raspberry PI_HOST=192.168.1.50  ./deploy.sh   (password)"