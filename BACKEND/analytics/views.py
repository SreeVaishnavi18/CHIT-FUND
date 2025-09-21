from django.http import HttpResponse
from django.utils import timezone
from django.utils.timezone import make_aware, is_naive, localtime
import datetime, random, pytz, uuid

# Assuming you have MongoDB collection `traces`
from django.conf import settings
import pymongo

client = pymongo.MongoClient(settings.MONGO_URI)
db = client.get_default_database()
traces = db.traces


def admin_dashboard(request):
    ip = request.META.get("REMOTE_ADDR", "")
    if ip not in ("127.0.0.1", "::1"):  # restrict to localhost only
        return HttpResponse("Access denied", status=403)

    system_tz = pytz.timezone("Asia/Kolkata")

    # 🔹 Handle traffic simulation
    if request.GET.get("simulate") == "1":
        fake_paths = ["/users/login", "/users/register", "/auctions/join", "/products/list"]
        for i in range(30):  # push 30 fake requests
            traces.insert_one({
                "ip": f"192.168.1.{random.randint(2,50)}",
                "path": random.choice(fake_paths),
                "method": random.choice(["GET", "POST"]),
                "status": random.choice([200, 401, 429]),
                "queue_wait_ms": random.randint(0, 200),
                "timestamp": timezone.localtime(timezone.now(), system_tz),
                "user_id": str(random.randint(1000, 2000)),
                "username": random.choice(["alice", "bob", "charlie", "guest"]),
                "session_id": str(uuid.uuid4()),   # Generate random session ID
                "mac": "—",  # placeholder (MAC not available via HTTP)
                "request_size": random.randint(500, 5000),
                "response_size": random.randint(500, 10000),
                "bandwidth_bytes": random.randint(1000, 20000),
                "response_time_ms": random.randint(10, 300),
            })

    # 🔹 Cutoff for last 5 minutes (IST)
    cutoff = timezone.localtime(timezone.now(), system_tz) - datetime.timedelta(minutes=5)

    # 🔹 Fetch recent requests
    recent = list(traces.find({
        "timestamp": {"$gte": cutoff},
         "ip": {"$nin": ["127.0.0.1", "::1"]}
    }).sort("timestamp", -1).limit(200))

    def to_ist(dt):
        """Ensure datetime is timezone aware & converted to IST"""
        if not dt:
            return None
        if is_naive(dt):
            dt = make_aware(dt, timezone.utc)
        return localtime(dt, system_tz)

    # 🔹 Chart labels in IST
    chart_labels = [
        to_ist(r["timestamp"]).strftime("%H:%M:%S")
        for r in reversed(recent) if r.get("timestamp")
    ]

    # 🔹 Stats
    total_requests = len(recent)
    throttled_count = sum(1 for r in recent if r.get("throttled"))
    unique_users = len(set(r.get("username") for r in recent if r.get("username")))
    unique_ips = len(set(r.get("ip") for r in recent if r.get("ip")))

    # 🔹 Active users in last 2 minutes
    now = timezone.localtime(timezone.now(), system_tz)
    cutoff_active = now - datetime.timedelta(minutes=2)

    active_users = set(
        r.get("username")
        for r in recent
        if r.get("username") and r.get("timestamp") and to_ist(r["timestamp"]) >= cutoff_active
    )

    # 🔹 Chart data
    chart_total = list(range(len(chart_labels)))
    chart_throttled = [1 if r.get("throttled") else 0 for r in reversed(recent)]

    # 🔹 Build HTML
    html = f"""
    <html>
    <head>
    <title>Server Analytics Dashboard</title>
    <meta http-equiv="refresh" content="10">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: "Segoe UI", Tahoma, sans-serif;
            background: linear-gradient(135deg, #f0f4f8, #dfe9f3);
            padding: 30px;
            margin: 0;
            color: #222;
        }}
        h2 {{
            color: #2c3e50;
            margin-bottom: 20px;
        }}
        .stats {{
            margin-bottom: 30px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 20px;
        }}
        .card {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.08);
            text-align: center;
            transition: transform 0.2s ease;
        }}
        .card:hover {{
            transform: translateY(-4px);
        }}
        .card b {{
            display: block;
            font-size: 15px;
            margin-bottom: 6px;
            color: #555;
        }}
        .card span {{
            font-size: 20px;
            font-weight: bold;
            color: #007bff;
        }}
        .table-container {{
            max-height: 450px;
            overflow-y: auto;
            border-radius: 8px;
            background: white;
            margin-top: 25px;
            box-shadow: 0 3px 8px rgba(0,0,0,0.05);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px 14px;
            border-bottom: 1px solid #e0e0e0;
            text-align: center;
            font-size: 14px;
        }}
        th {{
            background: #007bff;
            color: white;
            position: sticky;
            top: 0;
            font-size: 13px;
            letter-spacing: 0.5px;
        }}
        tr:nth-child(even) {{
            background: #f9fbfd;
        }}
        tr:hover {{
            background: #f1f6fc;
        }}
        .ok {{ color: #28a745; font-weight: bold; }}
        .fail {{ color: #dc3545; font-weight: bold; }}
        button {{
            padding: 10px 20px;
            background: linear-gradient(90deg, #007bff, #0056b3);
            border: none;
            border-radius: 8px;
            color: white;
            font-weight: bold;
            cursor: pointer;
            margin: 15px 0;
            transition: background 0.2s ease;
        }}
        button:hover {{
            background: linear-gradient(90deg, #0056b3, #003d80);
        }}
    </style>
    </head>
    <body>
    <h2>📊 Server Analytics Dashboard</h2>

    <div class="stats">
        <div class="card"><b>Total Requests</b><span>{total_requests}</span></div>
        <div class="card"><b>Unique Users</b><span>{unique_users}</span></div>
        <div class="card"><b>Unique IPs</b><span>{unique_ips}</span></div>
        <div class="card"><b>Active Users (2 min)</b><span>{len(active_users)}</span></div>
    </div>

    <form method="get">
        <button type="submit" name="simulate" value="1">🔥 Simulate Congestion</button>
    </form>

    <h3>📋 Recent Requests (last 5 minutes)</h3>
    <div class="table-container">
        <table>
        <tr>
            <th>Time</th><th>User</th><th>User ID</th><th>IP</th>
            <th>Path</th><th>Method</th><th>Status</th>
            <th>Queue Wait (ms)</th><th>Active</th>
            <th>MAC</th><th>Session ID</th>
            <th>Req Size (B)</th><th>Res Size (B)</th>
            <th>Bandwidth (B)</th><th>Resp Time (ms)</th>
        </tr>
    """

    for r in recent:
        user = r.get("username", "—")
        user_id = r.get("user_id", "—")
        active = "<span class='ok'>✔</span>" if user in active_users else "<span class='fail'>✘</span>"
        html += f"""
        <tr>
            <td>{to_ist(r['timestamp']).strftime("%H:%M:%S")}</td>
            <td>{user}</td>
            <td>{user_id}</td>
            <td>{r.get('ip', '—')}</td>
            <td>{r.get('path', '—')}</td>
            <td>{r.get('method', '—')}</td>
            <td>{r.get('status', '—')}</td>
            <td>{r.get('queue_wait_ms', '—')}</td>
            <td>{active}</td>
            <td>{r.get("mac", "—")}</td>
            <td>{r.get("session_id", "—")}</td>
            <td>{r.get("request_size", "—")}</td>
            <td>{r.get("response_size", "—")}</td>
            <td>{r.get("bandwidth_bytes", "—")}</td>
            <td>{r.get("response_time_ms", "—")}</td>
        </tr>
        """

    html += """
        </table>
    </div>
    </body>
    </html>
    """


    return HttpResponse(html)
