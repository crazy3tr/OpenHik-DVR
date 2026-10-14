#!/usr/bin/env python3
"""
OpenHik-DVR - Real-Time Event Listener Example
Listens to live push events (motion detection, tampering, video loss) via ISAPI alertStream.
"""

from __future__ import annotations
import sys
import os
import signal

# Add parent directory to path so pure_hik_client can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))
from pure_hik_client import PureHikClient

def main():
    DVR_HOST = "192.168.1.100"
    DVR_PORT = 80
    DVR_USER = "admin"
    DVR_PASS = "password123"

    print("==================================================")
    print("      OpenHik-DVR - Real-Time Event Listener      ")
    print("==================================================")
    print(f"Connecting to {DVR_HOST}:{DVR_PORT}...")

    client = PureHikClient(DVR_HOST, DVR_PORT, DVR_USER, DVR_PASS)
    try:
        info = client.get_device_info()
        print(f"Connected: {info.model} (FW: {info.firmware})")
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    print("Listening for real-time events (Press Ctrl+C to stop)...\n")

    def on_event(ev):
        state_str = "ACTIVE" if ev.is_active() else "CLEARED"
        event_name = ev.event_type.upper()
        if ev.is_motion():
            event_name = "MOTION DETECTED"
        elif ev.event_type == "videoloss":
            event_name = "VIDEO SIGNAL LOSS"
        elif ev.event_type == "shelteralarm":
            event_name = "CAMERA BLOCKED / TAMPER"

        print(f"[{ev.date_time}] Channel {ev.channel_id:02d} -> {event_name} ({state_str}) - {ev.description}")

    try:
        client.listen_events(on_event)
    except KeyboardInterrupt:
        print("\nListener stopped.")

if __name__ == '__main__':
    main()
