import os
import socket
from pathlib import Path

import cues

from PIL import Image, ImageDraw, ImageFont
import qrcode


def get_primary_ip() -> list[str]:
    ips = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            primary = s.getsockname()[0]
            ips.append(primary)
    except Exception:
        pass
    if not ips:
        try:
            for iface in socket.if_nameindex():
                name = iface[1]
                if name == "lo":
                    continue
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    ip = s.getsockname()[0]
                    s.close()
                    if ip not in ips:
                        ips.append(ip)
                except Exception:
                    pass
        except Exception:
            pass
    return ips


def _load_font(size: int):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in paths:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _hex_color(rgb: tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


CUE_FILE = Path(__file__).parent / "cues.json"
PORT = os.getenv("PORT", "8000")


def generate(logo_path: str, output_path: str, status_text: str = "") -> tuple[int, int]:
    width, height = 1920, 1080
    ips = get_primary_ip()
    if not ips:
        ips = ["127.0.0.1"]
    primary_ip = ips[0]
    cue_list = cues.load_cues(str(CUE_FILE)) if CUE_FILE.exists() else []

    BG = (0, 0, 0)
    WHITE = (255, 255, 255)

    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    font_large = _load_font(48)
    font_qr_label = _load_font(20)
    font_body = _load_font(20)

    mid = width // 2

    # --- Logo ---
    logo = None
    if Path(logo_path).exists():
        try:
            logo = Image.open(logo_path)
            max_w = width // 3
            max_h = height // 4
            logo.thumbnail((max_w, max_h), Image.LANCZOS)
        except Exception:
            logo = None

    y = int(height * 0.12)
    left_cx = mid // 2

    if logo:
        lx = left_cx - logo.width // 2
        if logo.mode == "RGBA":
            bg_part = Image.new("RGBA", img.size, BG + (255,))
            bg_part.paste(logo, (lx, y), logo)
            img = Image.alpha_composite(img.convert("RGBA"), bg_part).convert("RGB")
            draw = ImageDraw.Draw(img)
        else:
            img.paste(logo, (lx, y))
        y += logo.height + 50
    else:
        tb = draw.textbbox((0, 0), "Cutie Pi", font=font_large)
        draw.text((left_cx - tb[2] // 2, y), "Cutie Pi", fill=WHITE, font=font_large)
        y += 60

    # QR code
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(f"http://{primary_ip}:{PORT}")
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color=_hex_color(WHITE), back_color=_hex_color(BG))
    qr_size = min(200, height // 4)
    qr_img = qr_img.resize((qr_size, qr_size), Image.NEAREST)
    qx = left_cx - qr_size // 2
    img.paste(qr_img, (qx, y))
    y += qr_size + 15

    # URL label below QR
    url = f"{primary_ip}:{PORT}"
    ub = draw.textbbox((0, 0), url, font=font_qr_label)
    draw.text((left_cx - ub[2] // 2, y), url, fill=WHITE, font=font_qr_label)

    # --- Right column: cue list ---
    y2 = int(height * 0.08)
    rx = mid + 60

    if cue_list:
        for i, cue in enumerate(cue_list[:30]):
            label = cue.get("label", cue.get("filename", "?"))
            line = f"{i + 1}. {label}"
            draw.text((rx, y2), line, fill=WHITE, font=font_body)
            y2 += 32

    # --- Version footer ---
    ver_path = Path(__file__).parent.parent / "frontend" / "package.json"
    version = "?"
    try:
        import json
        version = json.loads(ver_path.read_text()).get("version", "?")
    except Exception:
        pass
    ver_text = f"v{version}"
    vb = draw.textbbox((0, 0), ver_text, font=font_body)
    draw.text((width - vb[2] - 10, height - vb[3] - 10), ver_text, fill=(100, 100, 100), font=font_body)

    # Bottom-center status text (above version)
    if status_text:
        font_status = _load_font(24)
        sb = draw.textbbox((0, 0), status_text, font=font_status)
        status_y = height - sb[3] - 50
        draw.text((mid - sb[2] // 2, status_y), status_text, fill=(255, 0, 102), font=font_status)

    img.save(output_path, "PNG")
    return (width, height)
