from django.http import HttpResponse
from django.utils import timezone
import datetime
import pymongo
from django.conf import settings
import random

client = pymongo.MongoClient(settings.MONGO_URI)
db = client.get_default_database()
traces = db.traces

def admin_dashboard(request):
    ip = request.META.get("REMOTE_ADDR", "")
    if ip not in ("127.0.0.1", "::1"):  # restrict to localhost only
        return HttpResponse("Access denied", status=403)

    # Handle traffic simulation
    if request.GET.get("simulate") == "1":
        fake_paths = ["/users/login", "/users/register", "/auctions/join", "/products/list"]
        for i in range(30):  # push 30 fake requests
            traces.insert_one({
                "ip": f"192.168.1.{random.randint(2,50)}",
                "path": random.choice(fake_paths),
                "method": random.choice(["GET", "POST"]),
                "status": random.choice([200, 401, 429]),
                "throttled": random.choice([True, False]),
                "queue_wait_ms": random.randint(0, 200),
                "timestamp": timezone.now(),
                "user_id": str(random.randint(1000, 2000)),
                "username": random.choice(["alice", "bob", "charlie", "guest"])
            })

    from django.utils.timezone import make_aware

    cutoff = timezone.now() - datetime.timedelta(minutes=5)

    recent = list(traces.find({
        "timestamp": {"$gte": make_aware(cutoff) if cutoff.tzinfo is None else cutoff}
    }).sort("timestamp", -1).limit(200))

    # Stats
    total_requests = len(recent)
    throttled_count = sum(1 for r in recent if r.get("throttled"))
    unique_users = len(set(r.get("username") for r in recent if r.get("username")))
    unique_ips = len(set(r.get("ip") for r in recent if r.get("ip")))

    from django.utils.timezone import make_aware, is_naive

    now = timezone.now()
    cutoff_active = now - datetime.timedelta(minutes=2)

    active_users = set(
        r.get("username")
        for r in recent
        if r.get("username") and r.get("timestamp") and (
            r["timestamp"] if not is_naive(r["timestamp"]) else make_aware(r["timestamp"])
        ) >= cutoff_active
    )
    # Prepare chart data
    chart_labels = [r["timestamp"].strftime("%H:%M:%S") for r in reversed(recent)]
    chart_total = list(range(len(chart_labels)))
    chart_throttled = [1 if r.get("throttled") else 0 for r in reversed(recent)]

    # Build HTML
    html = f"""
    <html>
    <head>
    <title>Server Analytics Dashboard</title>
    <meta http-equiv="refresh" content="10">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
        font-family: Arial, sans-serif;
        background: #f8f9fa;
        padding: 20px;
        }}
        h2 {{
        color: #333;
        }}
        .stats {{
        margin-bottom: 20px;
        display: flex;
        gap: 20px;
        }}
        .card {{
        background: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
        min-width: 150px;
        text-align: center;
        }}
        .table-container {{
        max-height: 400px;   /* fixed table height */
        overflow-y: auto;    /* vertical scroll */
        border: 1px solid #ccc;
        border-radius: 6px;
        background: white;
        margin-top: 20px;
        }}
        table {{
        width: 100%;
        border-collapse: collapse;
        }}
        th, td {{
        padding: 8px 10px;
        border-bottom: 1px solid #ddd;
        text-align: center;
        }}
        th {{
        background: #343a40;
        color: white;
        position: sticky;
        top: 0;   /* keep header fixed while scrolling */
        }}
        tr:hover {{
        background: #f1f1f1;
        }}
        .ok {{ color: green; font-weight: bold; }}
        .fail {{ color: red; font-weight: bold; }}
        button {{
        padding: 10px 20px;
        background: #007bff;
        border: none;
        border-radius: 6px;
        color: white;
        font-weight: bold;
        cursor: pointer;
        }}
        button:hover {{
        background: #0056b3;
        }}
    </style>
    </head>
    <body>
    <h2>📊 Server Analytics Dashboard</h2>

    <div class="stats">
        <div class="card"><b>Total Requests</b><br>{total_requests}</div>
        <div class="card"><b>Throttled</b><br>{throttled_count}</div>
        <div class="card"><b>Unique Users</b><br>{unique_users}</div>
        <div class="card"><b>Unique IPs</b><br>{unique_ips}</div>
        <div class="card"><b>Active Users (2 min)</b><br>{len(active_users)}</div>
    </div>

    <form method="get">
        <button type="submit" name="simulate" value="1">🔥 Simulate Congestion</button>
    </form>

    <h3>📈 Requests vs Throttled</h3>
    <canvas id="reqChart" height="100"></canvas>
    <script>
        const ctx = document.getElementById('reqChart');
        new Chart(ctx, {{
        type: 'line',
        data: {{
            labels: {chart_labels},
            datasets: [
            {{
                label: 'Requests',
                data: {chart_total},
                borderColor: 'blue',
                fill: false
            }},
            {{
                label: 'Throttled',
                data: {chart_throttled},
                borderColor: 'red',
                fill: false
            }}
            ]
        }}
        }});
    </script>

    <h3>📋 Recent Requests (last 5 minutes)</h3>
    <div class="table-container">
        <table>
        <tr>
            <th>Time</th><th>User</th><th>User ID</th><th>IP</th>
            <th>Path</th><th>Method</th><th>Status</th>
            <th>Throttled</th><th>Queue Wait (ms)</th><th>Active</th>
        </tr>
    """

    for r in recent:
        user = r.get("username", "—")
        user_id = r.get("user_id", "—")
        throttled = "<span class='fail'>✔</span>" if r.get("throttled") else "<span class='ok'>✘</span>"
        active = "<span class='ok'>✔</span>" if user in active_users else "<span class='fail'>✘</span>"
        html += f"""
        <tr>
            <td>{r['timestamp'].strftime("%H:%M:%S")}</td>
            <td>{user}</td>
            <td>{user_id}</td>
            <td>{r['ip']}</td>
            <td>{r['path']}</td>
            <td>{r.get('method', '—')}</td>
            <td>{r['status']}</td>
            <td>{throttled}</td>
            <td>{r['queue_wait_ms']}</td>
            <td>{active}</td>
        </tr>
        """

    html += """
        </table>
    </div>
    </body>
    </html>
    """

    return HttpResponse(html)
