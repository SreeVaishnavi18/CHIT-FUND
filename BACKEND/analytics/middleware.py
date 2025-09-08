import time
from collections import defaultdict
from django.http import JsonResponse
from django.utils import timezone
import jwt
import pymongo
from django.conf import settings

# Mongo setup
client = pymongo.MongoClient(settings.MONGO_URI)
db = client.get_default_database()
traces = db.traces

request_times = defaultdict(list)
MAX_REQ_PER_IP_PER_SEC = 5
MAX_CONCURRENT_LOGINS = 10
current_logins = 0

class CongestionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        global current_logins


        ip = request.META.get("REMOTE_ADDR", "unknown")
        path = request.path
        now = time.time()
        if path.startswith("/analytics/admin-dashboard"):  # or whatever your route is
            return self.get_response(request)
        # Rate limit
        request_times[ip] = [t for t in request_times[ip] if now - t < 1]
        throttled = False
        if len(request_times[ip]) >= MAX_REQ_PER_IP_PER_SEC:
            throttled = True
            traces.insert_one({
                "ip": ip, "path": path, "status": 429,
                "throttled": True, "queue_wait_ms": 0,
                "timestamp": timezone.now()
            })
            return JsonResponse({"error": "Too many requests"}, status=429)
        request_times[ip].append(now)

        # Queue for login congestion
        queue_start = time.time()
        if path.startswith("/users/login"):
            while current_logins >= MAX_CONCURRENT_LOGINS:
                time.sleep(0.05)
            current_logins += 1

        response = self.get_response(request)

        # Extract user info if available
        user_id = None
        username = None
        token = request.META.get("HTTP_AUTHORIZATION", "").replace("Bearer ", "")
        if token:
            try:
                decoded = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
                user_id = decoded.get("user_id")
                username = decoded.get("username")
            except Exception:
                pass  # ignore if invalid

        # Log event with user info
        traces.insert_one({
            "ip": ip,
            "path": path,
            "status": response.status_code,
            "throttled": throttled,
            "queue_wait_ms": queue_start,
            "timestamp": timezone.now(),
            "user_id": user_id,
            "username": username
        })

        return response