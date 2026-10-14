#!/usr/bin/env python3
"""
OpenHik-DVR - ActiveX-Free Modern HTML5 Web Dashboard (Zero External Dependencies)
Runs a lightweight local web server that restores browser viewing and playback for modern
browsers (Chrome, Firefox, Safari, Edge, iPhone, Android) without ActiveX plugins.
"""

from __future__ import annotations
import sys
import os
import time
import argparse
import json
import urllib.parse
from xml.sax.saxutils import escape
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))
from pure_hik_client import PureHikClient

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenHik-DVR Web Dashboard</title>
    <style>
        :root {
            --bg-main: #0f172a;
            --bg-card: #1e293b;
            --bg-card-hover: #334155;
            --accent: #38bdf8;
            --accent-green: #22c55e;
            --accent-orange: #f59e0b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border: #334155;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
        body { background-color: var(--bg-main); color: var(--text-main); min-height: 100vh; padding: 20px; }
        
        .header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 20px; border-bottom: 1px solid var(--border); margin-bottom: 24px; }
        .logo { display: flex; align-items: center; gap: 12px; }
        .logo h1 { font-size: 22px; font-weight: 700; color: var(--accent); }
        .badge { background: #0284c7; color: white; padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 600; text-transform: uppercase; }
        
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .stat-card { background: var(--bg-card); padding: 18px; border-radius: 12px; border: 1px solid var(--border); }
        .stat-title { font-size: 13px; color: var(--text-muted); margin-bottom: 8px; text-transform: uppercase; font-weight: 600; }
        .stat-value { font-size: 20px; font-weight: 700; color: var(--text-main); }
        .stat-sub { font-size: 12px; color: var(--text-muted); margin-top: 4px; }

        .tabs { display: flex; gap: 12px; margin-bottom: 20px; }
        .tab-btn { background: var(--bg-card); border: 1px solid var(--border); color: var(--text-muted); padding: 10px 20px; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; transition: 0.2s; }
        .tab-btn.active { background: var(--accent); color: #0f172a; border-color: var(--accent); }

        /* Camera Grid */
        .camera-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
        .cam-card { background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border); overflow: hidden; position: relative; }
        .cam-header { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: rgba(0,0,0,0.3); }
        .cam-title { font-size: 14px; font-weight: 600; color: var(--text-main); }
        .cam-status { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--accent-green); }
        .cam-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--accent-green); }
        
        .cam-preview { width: 100%; aspect-ratio: 16/9; background: #000; display: flex; justify-content: center; align-items: center; overflow: hidden; cursor: pointer; }
        .cam-preview img { width: 100%; height: 100%; object-fit: contain; }
        
        /* Search Section */
        .search-panel { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 24px; }
        .form-row { display: flex; gap: 16px; flex-wrap: wrap; align-items: flex-end; }
        .form-group { display: flex; flex-direction: column; gap: 6px; }
        .form-group label { font-size: 13px; font-weight: 600; color: var(--text-muted); }
        .form-group input, .form-group select { background: var(--bg-main); border: 1px solid var(--border); color: var(--text-main); padding: 10px 14px; border-radius: 8px; font-size: 14px; outline: none; }
        .btn-search { background: var(--accent); color: #0f172a; border: none; padding: 10px 24px; border-radius: 8px; font-size: 14px; font-weight: 700; cursor: pointer; }
        
        .records-table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px; }
        .records-table th { text-align: left; padding: 12px; background: rgba(0,0,0,0.2); color: var(--text-muted); border-bottom: 1px solid var(--border); }
        .records-table td { padding: 12px; border-bottom: 1px solid var(--border); color: var(--text-main); }
        .btn-dl { background: var(--bg-card-hover); color: var(--accent); padding: 6px 12px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: 600; border: 1px solid var(--border); }
        .btn-dl:hover { background: var(--accent); color: #0f172a; }

        .hidden { display: none; }
    </style>
</head>
<body>

    <div class="header">
        <div class="logo">
            <h1>OpenHik-DVR</h1>
            <span class="badge">ActiveX-Free Modern Dashboard</span>
        </div>
        <div style="font-size: 13px; color: var(--text-muted);">
            Auto-Refresh: <span style="color: var(--accent-green); font-weight: 600;">ACTIVE (2s)</span>
        </div>
    </div>

    <!-- Telemetry Cards -->
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-title">Device Model</div>
            <div class="stat-value" id="val-model">Loading...</div>
            <div class="stat-sub" id="val-firmware">-</div>
        </div>
        <div class="stat-card">
            <div class="stat-title">System Status</div>
            <div class="stat-value" id="val-cpu">-</div>
            <div class="stat-sub" id="val-uptime">-</div>
        </div>
        <div class="stat-card">
            <div class="stat-title">Storage Hard Disk</div>
            <div class="stat-value" id="val-storage">-</div>
            <div class="stat-sub" id="val-storage-status">-</div>
        </div>
        <div class="stat-card">
            <div class="stat-title">Active Cameras</div>
            <div class="stat-value" id="val-channels">-</div>
            <div class="stat-sub">16 Analog Channels Ready</div>
        </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="tabs">
        <button class="tab-btn active" onclick="switchTab('grid')">📷 Live Camera Grid</button>
        <button class="tab-btn" onclick="switchTab('search')">🔍 Search & Export Recordings</button>
    </div>

    <!-- Live Grid View -->
    <div id="view-grid" class="camera-grid"></div>

    <!-- Recording Search View -->
    <div id="view-search" class="hidden">
        <div class="search-panel">
            <div class="form-row">
                <div class="form-group">
                    <label>Camera Channel</label>
                    <select id="sel-channel"></select>
                </div>
                <div class="form-group">
                    <label>Date</label>
                    <input type="date" id="sel-date">
                </div>
                <button class="btn-search" onclick="doSearch()">Search Disks</button>
            </div>
            
            <table class="records-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Start Time</th>
                        <th>End Time</th>
                        <th>Estimated Size</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody id="records-body">
                    <tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 24px;">Select channel and date to query hard drive catalog.</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        let channelsData = [];

        function switchTab(tab) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            event.target.classList.add('active');
            if (tab === 'grid') {
                document.getElementById('view-grid').classList.remove('hidden');
                document.getElementById('view-search').classList.add('hidden');
            } else {
                document.getElementById('view-grid').classList.add('hidden');
                document.getElementById('view-search').classList.remove('hidden');
            }
        }

        async function loadTelemetry() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                document.getElementById('val-model').innerText = data.model || 'Hikvision DVR';
                document.getElementById('val-firmware').innerText = 'Firmware: ' + data.firmware;
                document.getElementById('val-cpu').innerText = 'CPU: ' + data.cpu_utilization + '%';
                document.getElementById('val-uptime').innerText = 'Uptime: ' + Math.floor(data.uptime_seconds / 3600) + ' hours';
                
                if (data.storage && data.storage.length > 0) {
                    const hdd = data.storage[0];
                    document.getElementById('val-storage').innerText = hdd.capacity_gb + ' GB';
                    document.getElementById('val-storage-status').innerText = 'Status: ' + hdd.status.toUpperCase();
                }
            } catch(e) {}
        }

        async function loadChannels() {
            try {
                const res = await fetch('/api/channels');
                channelsData = await res.json();
                document.getElementById('val-channels').innerText = channelsData.length + ' Channels';

                const grid = document.getElementById('view-grid');
                const sel = document.getElementById('sel-channel');
                grid.innerHTML = '';
                sel.innerHTML = '';

                channelsData.forEach(ch => {
                    // Option
                    const opt = document.createElement('option');
                    opt.value = ch.id;
                    opt.innerText = `Channel ${ch.id} (${ch.name})`;
                    sel.appendChild(opt);

                    // Card
                    const card = document.createElement('div');
                    card.className = 'cam-card';
                    card.innerHTML = `
                        <div class="cam-header">
                            <span class="cam-title">CH ${ch.id} - ${ch.name}</span>
                            <div class="cam-status"><span class="cam-dot"></span> LIVE</div>
                        </div>
                        <div class="cam-preview">
                            <img id="img-cam-${ch.id}" src="/api/snapshot?channel=${ch.id}&t=${Date.now()}" alt="Channel ${ch.id}">
                        </div>
                    `;
                    grid.appendChild(card);
                });
            } catch(e) {}
        }

        function refreshSnapshots() {
            channelsData.forEach(ch => {
                const img = document.getElementById(`img-cam-${ch.id}`);
                if (img) {
                    const nextImg = new Image();
                    nextImg.onload = () => { img.src = nextImg.src; };
                    nextImg.src = `/api/snapshot?channel=${ch.id}&t=${Date.now()}`;
                }
            });
        }

        async function doSearch() {
            const ch = document.getElementById('sel-channel').value;
            const dt = document.getElementById('sel-date').value;
            if (!dt) { alert("Please select a date."); return; }

            const tbody = document.getElementById('records-body');
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 24px;">Querying DVR hard disk catalog...</td></tr>';

            try {
                const res = await fetch(`/api/search?channel=${ch}&date=${dt}`);
                const data = await res.json();
                if (data.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--accent-orange); padding: 24px;">No recording segments found for this date.</td></tr>';
                    return;
                }

                tbody.innerHTML = '';
                data.forEach((seg, i) => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${i + 1}</td>
                        <td>${seg.start_time}</td>
                        <td>${seg.end_time}</td>
                        <td>${seg.size_mb > 0 ? seg.size_mb.toFixed(1) + ' MB' : 'N/A'}</td>
                        <td>
                            <a class="btn-dl" href="/api/download?uri=${encodeURIComponent(seg.playback_uri)}&filename=ch${ch}_${seg.start_time.replace(/[:]/g, '.')}.ps" target="_blank">Download PS</a>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            } catch(e) {
                tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: red; padding: 24px;">Error: ${e}</td></tr>`;
            }
        }

        // Set default date to today
        document.getElementById('sel-date').value = new Date().toISOString().split('T')[0];

        loadTelemetry();
        loadChannels();
        setInterval(refreshSnapshots, 2000);
        setInterval(loadTelemetry, 15000);
    </script>
</body>
</html>"""

class DashboardServer(BaseHTTPRequestHandler):
    client: PureHikClient = None

    def log_message(self, format, *args):
        pass # Suppress noisy request logs

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path in ("", "/"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode('utf-8'))

        elif path == "/api/status":
            try:
                info = self.client.get_device_info()
                stat = self.client.get_device_status()
                stors = self.client.get_storage()
                res = {
                    "model": info.model,
                    "firmware": info.firmware,
                    "cpu_utilization": stat.cpu_utilization,
                    "uptime_seconds": stat.uptime_seconds,
                    "storage": [{"name": s.name, "capacity_gb": round(s.capacity_gb, 1), "status": s.status} for s in stors]
                }
                data = json.dumps(res).encode('utf-8')
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_error(500, str(e))

        elif path == "/api/channels":
            try:
                chans = self.client.get_video_channels()
                res = [{"id": c.channel_id, "name": c.name, "enabled": c.enabled} for c in chans]
                data = json.dumps(res).encode('utf-8')
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_error(500, str(e))

        elif path == "/api/snapshot":
            cid = int(query.get("channel", [1])[0])
            snap = self.client.get_snapshot(cid)
            if snap:
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.end_headers()
                self.wfile.write(snap)
            else:
                self.send_error(404, "Snapshot unavailable")

        elif path == "/api/search":
            cid = int(query.get("channel", [1])[0])
            date_str = query.get("date", [""])[0]
            if not date_str:
                self.send_error(400, "Missing date parameter")
                return

            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                s_t = dt.replace(hour=0, minute=0, second=0)
                e_t = dt.replace(hour=23, minute=59, second=59)
                segs = self.client.search_recordings(cid, s_t, e_t, max_results=50)
                res = [{
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "playback_uri": s.playback_uri,
                    "size_mb": s.size_mb
                } for s in segs]
                data = json.dumps(res).encode('utf-8')
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_error(500, str(e))

        elif path == "/api/download":
            uri = query.get("uri", [""])[0]
            filename = query.get("filename", ["recording.ps"])[0]
            if not uri:
                self.send_error(400, "Missing uri parameter")
                return

            try:
                esc_uri = escape(uri)
                dl_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<downloadRequest version="1.0" xmlns="http://urn:selfextension:psiaext-ver10-xsd">
<playbackURI>{esc_uri}</playbackURI>
</downloadRequest>"""
                paths = ["/ISAPI/ContentMgmt/download", "/PSIA/Custom/SelfExt/ContentMgmt/download"]
                resp = None
                for p in paths:
                    try:
                        req = urllib.request.Request(
                            self.client.base_url + p,
                            data=dl_xml.encode('utf-8'),
                            headers={'Content-Type': 'application/xml', 'User-Agent': 'OpenHik-Client/1.0'}
                        )
                        resp = self.client.opener.open(req, timeout=10.0)
                        break
                    except urllib.error.HTTPError as e:
                        if e.code in (404, 405): continue
                        raise

                if not resp:
                    self.send_error(502, "DVR rejected download request")
                    return

                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                self.end_headers()

                with resp:
                    while True:
                        chunk = resp.read(256 * 1024)
                        if not chunk: break
                        self.wfile.write(chunk)
            except Exception as e:
                self.send_error(500, str(e))
        else:
            self.send_error(404, "Not Found")

def parse_args():
    parser = argparse.ArgumentParser(description="OpenHik-DVR - ActiveX-Free Modern HTML5 Web Dashboard")
    parser.add_argument("--host", default="192.168.1.100", help="DVR Host IP (default: 192.168.1.100)")
    parser.add_argument("--port", type=int, default=80, help="DVR HTTP port (default: 80)")
    parser.add_argument("--user", default="admin", help="Username (default: admin)")
    parser.add_argument("--pass", dest="password", default="", help="Password")
    parser.add_argument("--bind", default="0.0.0.0", help="Web dashboard bind IP (default: 0.0.0.0)")
    parser.add_argument("--web-port", type=int, default=8080, help="Web dashboard port (default: 8080)")
    return parser.parse_args()

def main():
    args = parse_args()
    client = PureHikClient(args.host, args.port, args.user, args.password)
    DashboardServer.client = client

    server_address = (args.bind, args.web_port)
    httpd = HTTPServer(server_address, DashboardServer)

    print("==================================================")
    print("      OpenHik-DVR - Modern HTML5 Web Dashboard    ")
    print("==================================================")
    print(f"Target DVR     : {args.host}:{args.port}")
    print(f"Web Dashboard  : http://localhost:{args.web_port}")
    print(f"Network Access : http://{args.bind}:{args.web_port}")
    print("Zero ActiveX / Works in Chrome, Edge, Safari, iOS, Android")
    print("==================================================")
    print("Server running... (Press Ctrl+C to stop)")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard...")
        httpd.server_close()

if __name__ == '__main__':
    main()
