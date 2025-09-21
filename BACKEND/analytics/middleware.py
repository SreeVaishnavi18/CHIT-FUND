import time, os, subprocess
from collections import defaultdict
from django.http import JsonResponse
from django.utils import timezone
import jwt, pymongo
from django.conf import settings

# Mongo setup
client = pymongo.MongoClient(settings.MONGO_URI)
db = client.get_default_database()
traces = db.traces

request_times = defaultdict(list)
MAX_REQ_PER_IP_PER_SEC = 5
MAX_CONCURRENT_LOGINS = 10
current_logins = 0

import platform, subprocess, re, time

# simple in-memory cache to avoid repeated system calls (ttl seconds)
_MAC_CACHE = {}
_MAC_CACHE_TTL = 300  # seconds

from ipaddress import ip_address, IPv4Address

def is_private_ip(ip):
    try:
        a = ip_address(ip)
        return a.is_private
    except Exception:
        return False

def get_mac(ip):
    """
    Return MAC address for an IP on the local LAN, or None if not found.
    Works by: pinging IP (populate ARP), then querying ARP/ip neigh.
    Caches results for _MAC_CACHE_TTL seconds to avoid overhead.
    """
    now = time.time()
    cached = _MAC_CACHE.get(ip)
    if cached and now - cached['ts'] < _MAC_CACHE_TTL:
        return cached['mac']

    system = platform.system()
    mac = None

    # ping once (silently) to populate ARP
    try:
        if system == "Windows":
            subprocess.run(['ping', '-n', '1', '-w', '1000', ip],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
        else:
            # Linux/Mac: -c 1 count, -W/ -t timeout (platform differences)
            subprocess.run(['ping', '-c', '1', '-W', '1', ip],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
    except Exception:
        pass

    try:
        if system == "Windows":
            out = subprocess.check_output(['arp', '-a', ip], stderr=subprocess.DEVNULL).decode(errors='ignore')
            # Windows prints MAC like 00-11-22-33-44-55
            m = re.search(r'([0-9A-Fa-f]{2}(?:[-:][0-9A-Fa-f]{2}){5})', out)
            if m:
                mac = m.group(1).replace('-', ':').lower()
        else:
            # Try `ip neigh show <ip>` (Linux)
            try:
                out = subprocess.check_output(['ip', 'neigh', 'show', ip], stderr=subprocess.DEVNULL).decode(errors='ignore')
                m = re.search(r'lladdr\s+([0-9a-fA-F:]{17})', out)
                if m:
                    mac = m.group(1).lower()
            except (FileNotFoundError, subprocess.CalledProcessError):
                # fallback to arp -n
                out = subprocess.check_output(['arp', '-n', ip], stderr=subprocess.DEVNULL).decode(errors='ignore')
                m = re.search(r'([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})', out)
                if m:
                    mac = m.group(1).lower()
    except Exception:
        mac = None

    _MAC_CACHE[ip] = {'mac': mac, 'ts': time.time()}
    return mac


class CongestionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        global current_logins

        ip = request.META.get("REMOTE_ADDR", "unknown")
        # mac = get_mac_from_ip(ip) if ip.startswith("192.168.") else "n/a"
        # mac = "n/a"
        # if is_private_ip(ip):
        #     # only try MAC for private LAN IPs (avoid delays on public IPs)
        mac = get_mac(ip) or "unknown"

        path = request.path
        method = request.method
        start_time = time.time()

        if path.startswith("/analytics/admin-dashboard"):
            return self.get_response(request)

        # Rate limiting
        now = time.time()
        request_times[ip] = [t for t in request_times[ip] if now - t < 1]
        throttled = False
        if len(request_times[ip]) >= MAX_REQ_PER_IP_PER_SEC:
            throttled = True
            traces.insert_one({
                "ip": ip, "mac": mac, "path": path, "method": method,
                "status": 429, "throttled": True, "queue_wait_ms": 0,
                "timestamp": timezone.now(),
            })
            return JsonResponse({"error": "Too many requests"}, status=429)
        request_times[ip].append(now)

        # Queue for concurrent login congestion
        queue_start = time.time()
        if path.startswith("/users/login"):
            while current_logins >= MAX_CONCURRENT_LOGINS:
                time.sleep(0.05)
            current_logins += 1

        # Process response
        response = self.get_response(request)
        end_time = time.time()

        # Extract user info if available
        user_id, username, session_id = None, None, None
        token = request.META.get("HTTP_AUTHORIZATION", "").replace("Bearer ", "")
        if token:
            try:
                decoded = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
                user_id = decoded.get("user_id")
                username = decoded.get("username")
                session_id = decoded.get("jti") 
            except Exception:
                pass
        # if hasattr(request, "session"):
        #     session_id = request.session.session_key

        # Calculate metrics
        # request_size = len(request.body or b"") if request.method in ["POST", "PUT"] else 0
        request_size = int(request.META.get("CONTENT_LENGTH") or 0)
        response_size = len(response.content or b"")
        total_bandwidth = request_size + response_size
        response_time_ms = round((end_time - start_time) * 1000, 2)
        queue_wait_ms = round((start_time - queue_start) * 1000, 2)
        import pytz
        from django.utils import timezone

        system_tz = pytz.timezone("Asia/Kolkata")   # change to your system’s timezone
        
        # Save log
        traces.insert_one({
            "ip": ip,
            "mac": mac,
            "path": path,
            "method": method,
            "status": response.status_code,
            "throttled": throttled,
            "queue_wait_ms": queue_wait_ms,
            "timestamp": timezone.localtime(timezone.now(), system_tz),
            "user_id": user_id,
            "username": username,
            "session_id": session_id,
            "request_size": request_size,
            "response_size": response_size,
            "bandwidth_bytes": total_bandwidth,
            "request_start": start_time,
            "response_end": end_time,
            "response_time_ms": response_time_ms,
        })

        if path.startswith("/users/login"):
            current_logins = max(0, current_logins - 1)

        return response
