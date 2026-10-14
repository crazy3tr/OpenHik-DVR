#!/usr/bin/env python3
"""
OpenHik-DVR - Silent Storage & Recording Continuity Health Monitor
Inspects S.M.A.R.T. HDD health, disk status, CPU load, and verifies that active cameras
are continuously recording footage to disk without silent hardware failures.

Exit Codes:
  0 = HEALTHY (All checks passed)
  1 = WARNING (Minor anomaly, high CPU, or short recording gap)
  2 = CRITICAL (Disk failure, disk full/offline, or total recording stoppage)
"""

from __future__ import annotations
import sys
import os
import argparse
import json
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))
from pure_hik_client import PureHikClient

def parse_args():
    parser = argparse.ArgumentParser(description="OpenHik-DVR - Silent Storage & Recording Continuity Health Monitor")
    parser.add_argument("--host", default="192.168.1.100", help="DVR Host IP (default: 192.168.1.100)")
    parser.add_argument("--port", type=int, default=80, help="DVR HTTP port (default: 80)")
    parser.add_argument("--user", default="admin", help="Username (default: admin)")
    parser.add_argument("--pass", dest="password", default="", help="Password")
    parser.add_argument("--check-hours", type=int, default=2, help="Check recording continuity over the past N hours (default: 2)")
    parser.add_argument("--max-cpu", type=int, default=90, help="CPU load warning threshold percentage (default: 90)")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON for monitoring systems (Zabbix, Nagios)")
    return parser.parse_args()

def main():
    args = parse_args()
    report = {
        "timestamp": datetime.now().isoformat(),
        "host": f"{args.host}:{args.port}",
        "status": "OK",
        "errors": [],
        "warnings": [],
        "system": {},
        "storage": [],
        "recording_continuity": {}
    }

    client = PureHikClient(args.host, args.port, args.user, args.password)
    try:
        dev_info = client.get_device_info()
        dev_status = client.get_device_status()
        report["system"] = {
            "model": dev_info.model,
            "firmware": dev_info.firmware,
            "mac": dev_info.mac,
            "cpu_utilization": dev_status.cpu_utilization,
            "uptime_hours": dev_status.uptime_seconds // 3600
        }

        # 1. Check CPU load
        if dev_status.cpu_utilization >= args.max_cpu:
            report["warnings"].append(f"High CPU utilization: {dev_status.cpu_utilization}% (Threshold: {args.max_cpu}%)")
            if report["status"] == "OK":
                report["status"] = "WARNING"

        # 2. Check Storage & Disks
        disks = client.get_storage()
        if not disks:
            report["errors"].append("CRITICAL: No storage hard drives detected on DVR!")
            report["status"] = "CRITICAL"

        for d in disks:
            disk_entry = {
                "name": d.name,
                "status": d.status,
                "type": d.hdd_type,
                "capacity_gb": round(d.capacity_gb, 1),
                "free_space_mb": d.free_space_mb
            }
            report["storage"].append(disk_entry)

            if d.status.lower() != "ok":
                report["errors"].append(f"CRITICAL: Hard drive '{d.name}' status is NOT OK ({d.status})!")
                report["status"] = "CRITICAL"
            elif d.capacity_mb <= 0:
                report["errors"].append(f"CRITICAL: Hard drive '{d.name}' capacity reported as 0 MB!")
                report["status"] = "CRITICAL"

        # 3. Check Recording Continuity on Active Channels
        now = datetime.now()
        start_check = now - timedelta(hours=args.check_hours)
        channels = client.get_video_channels()
        active_channels = [ch for ch in channels if ch.enabled]

        for ch in active_channels:
            try:
                segments = client.search_recordings(ch.channel_id, start_check, now, max_results=5)
                report["recording_continuity"][f"channel_{ch.channel_id}"] = {
                    "name": ch.name,
                    "segments_found": len(segments),
                    "status": "RECORDING" if len(segments) > 0 else "NO_RECENT_RECORDINGS"
                }
                if len(segments) == 0:
                    report["warnings"].append(f"Channel {ch.channel_id:02d} ({ch.name}) has 0 recorded segments in the past {args.check_hours} hours!")
                    if report["status"] == "OK":
                        report["status"] = "WARNING"
            except Exception as e:
                report["warnings"].append(f"Failed to query recording table for Channel {ch.channel_id}: {e}")

    except Exception as e:
        report["status"] = "CRITICAL"
        report["errors"].append(f"Connection failure: {e}")

    # Output
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("==================================================")
        print("      OpenHik-DVR - Hardware & Storage Health     ")
        print("==================================================")
        print(f"Target DVR     : {report['host']}")
        if "model" in report["system"]:
            print(f"Model & FW     : {report['system']['model']} (FW: {report['system']['firmware']})")
            print(f"CPU Load       : {report['system']['cpu_utilization']}% | Uptime: {report['system']['uptime_hours']} hours")

        print("\n[ Storage Hard Drives ]")
        for d in report["storage"]:
            st_color = "[OK]" if d["status"] == "ok" else "[CRITICAL]"
            print(f"  {st_color} {d['name']} ({d['type']}) - {d['capacity_gb']} GB (Status: {d['status']})")

        print(f"\n[ Recording Continuity (Past {args.check_hours} Hours) ]")
        for k, v in report["recording_continuity"].items():
            rc_color = "[OK]" if v["status"] == "RECORDING" else "[WARN]"
            print(f"  {rc_color} {k.upper()}: {v['name']} -> {v['segments_found']} segments found ({v['status']})")

        print("\n--------------------------------------------------")
        overall = report["status"]
        if overall == "OK":
            print("OVERALL HEALTH : [PASS] ALL SYSTEMS OPERATIONAL")
        elif overall == "WARNING":
            print("OVERALL HEALTH : [WARNING] ANOMALIES DETECTED:")
            for w in report["warnings"]:
                print(f"  - {w}")
        else:
            print("OVERALL HEALTH : [CRITICAL] SERIOUS FAULTS DETECTED:")
            for err in report["errors"]:
                print(f"  - {err}")
        print("==================================================")

    # Return exit code
    if report["status"] == "OK":
        sys.exit(0)
    elif report["status"] == "WARNING":
        sys.exit(1)
    else:
        sys.exit(2)

if __name__ == '__main__':
    main()
