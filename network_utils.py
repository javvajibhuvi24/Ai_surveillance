import os
import subprocess
import socket
import tempfile
from concurrent.futures import ThreadPoolExecutor

def get_local_ip():
    try:
        # Create a dummy socket to find the correct local IP used for internet access
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def scan_wifi():
    """Scans for available Wi-Fi networks using Windows netsh."""
    try:
        result = subprocess.run(['netsh', 'wlan', 'show', 'networks'], capture_output=True, text=True, check=True)
        networks = []
        for line in result.stdout.split('\n'):
            line = line.strip()
            if line.startswith("SSID"):
                parts = line.split(":")
                if len(parts) > 1:
                    ssid = parts[1].strip()
                    if ssid and ssid not in networks:
                        networks.append(ssid)
        return networks
    except Exception as e:
        print(f"[WIFI] Scan error: {e}")
        return []

def connect_wifi(ssid, password):
    """Attempts to connect to a Wi-Fi network on Windows using an XML profile."""
    try:
        # Windows requires an XML profile to connect programmatically
        profile_xml = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig>
        <SSID>
            <name>{ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{password}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>"""
        
        # Save XML to a temporary file
        fd, path = tempfile.mkstemp(suffix=".xml")
        with os.fdopen(fd, 'w') as f:
            f.write(profile_xml)
            
        # Import profile
        import_res = subprocess.run(['netsh', 'wlan', 'add', 'profile', f'filename={path}'], capture_output=True, text=True)
        os.remove(path)
        
        if import_res.returncode != 0:
            return False, f"Failed to add profile: {import_res.stderr or import_res.stdout}"
            
        # Connect
        connect_res = subprocess.run(['netsh', 'wlan', 'connect', f'name={ssid}'], capture_output=True, text=True)
        if connect_res.returncode == 0:
            return True, "Connection request sent."
        else:
            return False, f"Failed to connect: {connect_res.stderr or connect_res.stdout}"
            
    except Exception as e:
        return False, str(e)


def _check_port(ip, port=554, timeout=0.5):
    """Checks if a port is open on a specific IP."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ip, port))
        s.close()
        return ip
    except Exception:
        s.close()
        return None

def discover_cameras():
    """Scans the local subnet for devices with port 554 (RTSP) open."""
    local_ip = get_local_ip()
    if local_ip == "127.0.0.1":
        return []
        
    subnet_base = ".".join(local_ip.split(".")[:3]) + "."
    target_ips = [f"{subnet_base}{i}" for i in range(1, 255)]
    
    discovered = []
    
    # Use thread pool to scan multiple IPs concurrently to speed up the process
    with ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(_check_port, target_ips)
        
    for res in results:
        if res:
            discovered.append(f"rtsp://{res}/stream1")
            
    return discovered
