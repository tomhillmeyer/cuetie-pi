#!/bin/bash
set -euo pipefail

REPO="tomhillmeyer/cuetie-pi"
INSTALL_DIR="/opt/cuetie-pi"

echo "======================================"
echo " Cutie Pi Installer"
echo "======================================"
echo ""

# ---- Detect mode ----
if [ -f "backend/main.py" ] && [ -d "frontend/dist" ]; then
  echo "==> Running from local release directory"
  SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
else
  echo "==> Downloading latest release..."
  VERSION="${1:-latest}"
  TARBALL="cuetie-pi.tar.gz"
  URL="https://github.com/$REPO/releases/$VERSION/download/$TARBALL"

  TMPDIR=$(mktemp -d)
  curl -fsSL "$URL" -o "$TMPDIR/$TARBALL"
  tar -xzf "$TMPDIR/$TARBALL" -C "$TMPDIR"
  SRC_DIR="$TMPDIR/$(ls "$TMPDIR" | grep cuetie-pi | head -1)"

  if [ -z "$SRC_DIR" ] || [ ! -d "$SRC_DIR" ]; then
    echo "ERROR: Could not extract release archive."
    exit 1
  fi
fi

# ---- Step 1: System packages ----
echo ""
echo "==> Installing system packages..."
sudo apt update
sudo apt install -y \
  mpv \
  weston \
  seatd \
  python3 \
  python3-venv \
  python3-pip \
  python3-dev \
  libevdev2 \
  pmount

# ---- Step 2: seatd ----
echo ""
echo "==> Enabling seatd..."
sudo systemctl enable --now seatd

# ---- Step 2b: udisks2 (USB auto-mount for media import) ----
echo ""
echo "==> Enabling udisks2..."
sudo systemctl enable --now udisks2 || true

# ---- Step 3: User groups ----
echo ""
echo "==> Adding user to required groups..."
sudo usermod -aG video "$USER"
sudo usermod -aG render "$USER"
sudo usermod -aG tty "$USER"
sudo usermod -aG input "$USER"

# ---- Step 4: Copy code ----
echo ""
echo "==> Installing to $INSTALL_DIR..."
sudo mkdir -p "$INSTALL_DIR"
sudo cp -r "$SRC_DIR"/* "$INSTALL_DIR/"
sudo chown -R "$USER:$USER" "$INSTALL_DIR"

# ---- Step 5: Python venv ----
echo ""
echo "==> Setting up Python virtual environment..."
cd "$INSTALL_DIR/backend"
rm -rf venv
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# ---- Step 6: .env ----
echo ""
echo "==> Creating default .env..."
if [ ! -f "$INSTALL_DIR/backend/.env" ]; then
  cat > "$INSTALL_DIR/backend/.env" << 'ENVEOF'
PORT=8000
MEDIA_DIR=./media
CUES_FILE=./cues.json
DISPLAY=:0
WAYLAND_DISPLAY=wayland-1
XDG_RUNTIME_DIR=/tmp/weston-runtime
OSC_PORT=5005
ENVEOF
fi
mkdir -p "$INSTALL_DIR/backend/media"

# ---- Step 7: Weston config ----
echo ""
echo "==> Installing Weston config..."
sudo mkdir -p /etc/xdg/weston
sudo cp "$INSTALL_DIR/backend/weston.ini" /etc/xdg/weston/weston.ini

# ---- Step 8: Systemd services ----
echo ""
echo "==> Installing systemd services..."

# Fix paths in service files for the install location
sed "s|/home/pi/cuetie-pi|$INSTALL_DIR|g; s|User=pi|User=$USER|g" \
  "$INSTALL_DIR/backend/weston.service" | \
  sudo tee /etc/systemd/system/weston.service > /dev/null

sed "s|/home/pi/cuetie-pi|$INSTALL_DIR|g; s|User=pi|User=$USER|g" \
  "$INSTALL_DIR/backend/cuetie-pi.service" | \
  sudo tee /etc/systemd/system/cuetie-pi.service > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable weston
sudo systemctl enable cuetie-pi

# ---- Step 9: GPU memory check ----
echo ""
echo "==> Checking GPU memory..."
GPU_MEM=""
if [ -f /boot/firmware/config.txt ]; then
  GPU_MEM=$(grep 'gpu_mem' /boot/firmware/config.txt || true)
elif [ -f /boot/config.txt ]; then
  GPU_MEM=$(grep 'gpu_mem' /boot/config.txt || true)
fi

if [ -z "$GPU_MEM" ]; then
  echo "WARNING: No gpu_mem setting found."
  echo "For reliable video playback, add the following to /boot/firmware/config.txt:"
  echo "  gpu_mem=256"
  echo "Then reboot."
elif [[ ! "$GPU_MEM" == *"256"* ]]; then
  echo "WARNING: Current GPU memory may be too low: $GPU_MEM"
  echo "Recommended: set gpu_mem=256 in /boot/firmware/config.txt and reboot."
else
  echo "GPU memory: $GPU_MEM"
fi

# ---- Step 10: Start services ----
echo ""
echo "==> Starting services..."
sudo systemctl start weston
sleep 3
sudo systemctl start cuetie-pi
sleep 2

# ---- Step 11: Verify ----
echo ""
echo "==> Verifying services..."
if systemctl is-active --quiet weston && systemctl is-active --quiet cuetie-pi; then
  HOST_IP=$(hostname -I | awk '{print $1}')
  echo ""
  echo "======================================"
  echo " INSTALLATION COMPLETE"
  echo "======================================"
  echo ""
  echo "  Open http://$HOST_IP:8000 in your browser"
  echo ""
  echo "  Supported browsers: Chrome, Firefox, Safari, Edge"
  echo ""
  echo "  The app will start automatically on boot."
  echo ""
  echo "  Useful commands:"
  echo "    View logs:     journalctl -u cuetie-pi -f"
  echo "    Restart:       sudo systemctl restart cuetie-pi"
  echo "    Update:        re-run this installer"
  echo ""
else
  echo "ERROR: One or more services failed to start."
  echo "  Check: journalctl -u weston -f"
  echo "  Check: journalctl -u cuetie-pi -f"
  exit 1
fi
