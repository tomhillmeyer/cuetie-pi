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

echo "==> Backing up cues and media on Pi..."
_ssh "cp $PI_PATH/backend/cues.json /tmp/cues.json.bak 2>/dev/null; cp -r $PI_PATH/backend/media /tmp/media.bak 2>/dev/null; true"

echo "==> Syncing code to Pi (preserving media, cues, and .env)..."
rsync -avz --delete --rsh="$RSYNC_RSH" \
  --exclude='.git/' \
  --exclude='backend/venv/' \
  --exclude='backend/__pycache__/' \
  --exclude='backend/media/' \
  --exclude='backend/cues.json' \
  --exclude='backend/.env' \
  --exclude='backend/imported_devices.json' \
  --exclude='backend/config_applied.json' \
  --exclude='backend/splash.png' \
  --exclude='frontend/node_modules/' \
  --exclude='out/' \
  --exclude='scripts/' \
  --exclude='*.tar.gz' \
  --exclude='CONTEXT.md' \
  --exclude='build-spec.md' \
  --exclude='testing.md' \
  --exclude='.DS_Store' \
  ./ "$PI_USER@$PI_HOST:$PI_PATH/"

echo "==> Restoring cues and media if missing..."
_ssh "test -f $PI_PATH/backend/cues.json || cp /tmp/cues.json.bak $PI_PATH/backend/cues.json 2>/dev/null; test -d $PI_PATH/backend/media || cp -r /tmp/media.bak $PI_PATH/backend/media 2>/dev/null; true"

echo "==> Ensuring .env exists..."
_ssh "test -f $PI_PATH/backend/.env || cp $PI_PATH/backend/.env.example $PI_PATH/backend/.env"

echo "==> Ensuring Python venv exists..."
_ssh "test -d $PI_PATH/backend/venv || (cd $PI_PATH/backend && python3 -m venv venv)"
echo "==> Installing/upgrading Python dependencies..."
_ssh "cd $PI_PATH/backend && ./venv/bin/pip install -r requirements.txt"

echo "==> Configuring sudoers for USB config management..."
_ssh "echo '$PI_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl daemon-reload, /usr/bin/systemctl restart cuetie-pi, /usr/bin/nmcli, /usr/bin/udisksctl' > /tmp/cuetie-sudoers"
_ssh "$(_sudocmd cp /tmp/cuetie-sudoers /etc/sudoers.d/cuetie-pi)"
_ssh "$(_sudocmd chmod 440 /etc/sudoers.d/cuetie-pi)"
_ssh "rm /tmp/cuetie-sudoers"

echo "==> Syncing weston config..."
_ssh "$(_sudocmd mkdir -p /etc/xdg/weston)"
_ssh "$(_sudocmd cp $PI_PATH/backend/weston.ini /etc/xdg/weston/weston.ini)"

echo "==> Syncing systemd units..."
_ssh "$(_sudocmd cp $PI_PATH/backend/weston.service /etc/systemd/system/weston.service)"
_ssh "$(_sudocmd cp $PI_PATH/backend/cuetie-pi.service /etc/systemd/system/cuetie-pi.service)"

echo "==> Ensuring seatd is installed..."
_ssh "$(_sudocmd apt install -y seatd)" || true
_ssh "$(_sudocmd systemctl enable --now seatd)" || true

echo "==> Installing pmount and udisks2..."
_ssh "$(_sudocmd apt install -y pmount udisks2)" || true

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