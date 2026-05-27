import hashlib
import json
import os
import subprocess
from pathlib import Path

CONFIG_FILE_NAME = "cuetiepi-config.json"
CONFIG_APPLIED_FILE = os.path.join(os.path.dirname(__file__), "config_applied.json")

_last_import_result: dict = {}


def get_last_import_result() -> dict:
    return dict(_last_import_result)


def _set_import_result(success: bool, message: str, details: str = ""):
    global _last_import_result
    _last_import_result = {
        "success": success,
        "message": message,
        "details": details,
    }


def _load_config_applied() -> dict:
    try:
        with open(CONFIG_APPLIED_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_config_applied(data: dict):
    try:
        with open(CONFIG_APPLIED_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _get_active_wifi_connection_name() -> str | None:
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show", "--active"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.strip().split("\n"):
            parts = line.split(":")
            if len(parts) == 2 and parts[1] == "802-11-wireless":
                return parts[0]
    except Exception:
        pass
    return None


def _get_ssid_from_connection(conn_name: str) -> str | None:
    try:
        result = subprocess.run(
            ["nmcli", "-g", "802-11-wireless.ssid", "connection", "show", conn_name],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            val = result.stdout.strip()
            if val:
                return val
    except Exception:
        pass
    return None


def _get_wifi_password(conn_name: str, ssid: str | None = None) -> str:
    try:
        result = subprocess.run(
            ["sudo", "nmcli", "-s", "-g", "802-11-wireless-security.psk",
             "connection", "show", conn_name],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            val = result.stdout.strip()
            if val and not _is_hex_psk(val):
                return val
    except Exception:
        pass
    if ssid:
        try:
            netplan_dir = Path("/etc/netplan")
            if netplan_dir.exists():
                for yaml_file in sorted(netplan_dir.iterdir()):
                    if yaml_file.suffix not in (".yaml", ".yml"):
                        continue
                    text = yaml_file.read_text()
                    lines = text.splitlines()
                    in_access_points = False
                    in_ssid_block = False
                    for i, line in enumerate(lines):
                        s = line.strip()
                        if s == "access-points:":
                            in_access_points = True
                            continue
                        if in_access_points:
                            if not s or s.startswith("#"):
                                continue
                            if not line.startswith(" ") and not line.startswith("-"):
                                in_access_points = False
                                in_ssid_block = False
                                continue
                            if s.startswith("- "):
                                continue
                            if s.rstrip().endswith(":"):
                                key = s.rstrip(":").strip("\"'")
                                if key == ssid:
                                    in_ssid_block = True
                                else:
                                    in_ssid_block = False
                                continue
                            if in_ssid_block and s.startswith("password:"):
                                val = s.split(":", 1)[1].strip().strip("\"'")
                                if val:
                                    return val
        except Exception:
            pass
    try:
        conn_file = Path(f"/etc/NetworkManager/system-connections/{conn_name}.nmconnection")
        if conn_file.exists():
            for line in conn_file.read_text().splitlines():
                line = line.strip()
                if line.startswith("psk="):
                    val = line.split("=", 1)[1].strip().strip('"')
                    if val:
                        return val
    except Exception:
        pass
    return ""


def _is_hex_psk(val: str) -> bool:
    return len(val) == 64 and all(c in "0123456789abcdefABCDEF" for c in val)


def _get_current_ssid() -> str | None:
    conn_name = _get_active_wifi_connection_name()
    if conn_name:
        ssid = _get_ssid_from_connection(conn_name)
        if ssid:
            return ssid
    try:
        result = subprocess.run(
            ["iwgetid", "-r"],
            capture_output=True, text=True, timeout=5,
        )
        ssid = result.stdout.strip()
        if ssid:
            return ssid
    except Exception:
        pass
    return None


def _get_wifi_interface() -> str | None:
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "DEVICE,TYPE", "device"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.strip().split("\n"):
            parts = line.split(":")
            if len(parts) == 2 and parts[1] == "wifi":
                return parts[0]
    except Exception:
        pass
    return None


def _get_current_port(env_path: str) -> int:
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("PORT="):
                    return int(line.split("=", 1)[1])
    except Exception:
        pass
    return 8000


def _apply_wifi(ssid: str, password: str) -> dict:
    iface = _get_wifi_interface()
    if not iface:
        return {"success": False, "message": "No wifi interface found"}
    try:
        existing = subprocess.run(
            ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"],
            capture_output=True, text=True, timeout=5,
        )
        wifi_cons = []
        for line in existing.stdout.strip().split("\n"):
            parts = line.split(":")
            if len(parts) >= 2 and parts[1] == "802-11-wireless":
                wifi_cons.append(parts[0])
        for conn_name in wifi_cons:
            subprocess.run(
                ["sudo", "nmcli", "connection", "delete", conn_name],
                capture_output=True, timeout=10,
            )
        if wifi_cons:
            print(f"[usb_config] Deleted {len(wifi_cons)} existing WiFi profile(s)", flush=True)
    except Exception as e:
        print(f"[usb_config] Failed to delete old WiFi profiles: {e}", flush=True)
        return {"success": False, "message": f"Failed to delete old profiles: {e}"}

    try:
        cmd = ["sudo", "nmcli", "device", "wifi", "connect", ssid, "ifname", iface]
        if password:
            cmd += ["password", password]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return {"success": False, "message": f"nmcli connect failed: {result.stderr.strip()}"}
    except Exception as e:
        return {"success": False, "message": f"nmcli connect error: {e}"}

    try:
        subprocess.run(
            ["sudo", "nmcli", "connection", "modify", ssid,
             "connection.autoconnect-priority", "100"],
            capture_output=True, timeout=10,
        )
    except Exception:
        pass

    print(f"[usb_config] WiFi switched to '{ssid}'", flush=True)
    return {"success": True, "message": f"Connected to '{ssid}', all prior WiFi profiles removed"}


def _apply_port(port: int, env_path: str) -> bool:
    try:
        path = Path(env_path)
        if not path.exists():
            return False
        lines = path.read_text().splitlines()
        found = False
        new_lines = []
        for line in lines:
            if line.strip().startswith("PORT="):
                new_lines.append(f"PORT={port}")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f"PORT={port}")
        path.write_text("\n".join(new_lines) + "\n")
        print(f"[usb_config] Port set to {port}, restarting service", flush=True)
        subprocess.run(
            ["sudo", "systemctl", "restart", "cuetie-pi"],
            timeout=10,
        )
        return True
    except Exception as e:
        print(f"[usb_config] Port change error: {e}", flush=True)
        return False


def _build_export_config(env_path: str) -> dict:
    config = {}
    conn_name = _get_active_wifi_connection_name()
    ssid = ""
    password = ""
    if conn_name:
        ssid = _get_ssid_from_connection(conn_name) or ""
        password = _get_wifi_password(conn_name, ssid) or ""
    config["wifi"] = {
        "ssid": ssid,
        "password": password,
    }
    port = _get_current_port(env_path)
    config["server"] = {
        "port": port,
    }
    return config


def _apply_config(config: dict, env_path: str) -> list[dict]:
    results = []
    if "wifi" in config:
        wifi = config["wifi"]
        ssid = wifi.get("ssid")
        password = wifi.get("password", "")
        if ssid:
            current_ssid = _get_current_ssid()
            if ssid != current_ssid:
                result = _apply_wifi(ssid, password)
                results.append({"action": "wifi", **result})
            else:
                results.append({"action": "wifi", "success": True, "message": f"Already connected to '{ssid}'"})

    if "server" in config:
        server = config["server"]
        port = server.get("port")
        if port:
            current_port = _get_current_port(env_path)
            if port != current_port:
                ok = _apply_port(port, env_path)
                results.append({"action": "port", "success": ok, "message": f"Port changed to {port}" if ok else "Port change failed"})

    return results


def _import_config(config_path: Path, uuid: str | None, env_path: str):
    try:
        content = config_path.read_text()
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        if uuid:
            applied = _load_config_applied()
            if applied.get(uuid) == content_hash:
                _set_import_result(True, "Config unchanged, skipping")
                return

        config = json.loads(content)

        if uuid:
            applied = _load_config_applied()
            applied[uuid] = content_hash
            _save_config_applied(applied)

        results = _apply_config(config, env_path)
        failures = [r for r in results if not r.get("success")]
        if failures:
            msgs = "; ".join(f"{r['action']}: {r.get('message', 'unknown error')}" for r in failures)
            _set_import_result(False, "Import completed with failures", msgs)
        else:
            _set_import_result(True, "Config applied successfully")

    except Exception as e:
        _set_import_result(False, "Import failed", str(e))
        print(f"[usb_config] Import failed: {e}", flush=True)


def _export_config(mount_point: str, uuid: str | None, env_path: str):
    config = _build_export_config(env_path)
    content = json.dumps(config, indent=2)
    config_path = Path(mount_point) / CONFIG_FILE_NAME
    config_path.write_text(content)
    _set_import_result(True, "Config exported to USB")
    print(f"[usb_config] Exported config to {mount_point}", flush=True)


def handle_partition_config(mount_point: str, uuid: str | None, env_path: str):
    config_path = Path(mount_point) / CONFIG_FILE_NAME
    if config_path.exists():
        _import_config(config_path, uuid, env_path)
    else:
        _export_config(mount_point, uuid, env_path)
