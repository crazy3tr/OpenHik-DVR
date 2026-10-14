#!/usr/bin/env python3
"""
OpenHik-DVR - Smart Telegram & Webhook Motion Alert Bot (Zero External Dependencies)
Listens for real-time motion detection events, captures full-res snapshots, and delivers
instant photo alerts directly to Telegram or custom Webhook endpoints.
"""

import sys
import os
import time
import argparse
import urllib.request
import urllib.parse
import json
import uuid

# Add parent directory so pure_hik_client can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))
from pure_hik_client import PureHikClient

def send_telegram_photo(token: str, chat_id: str, photo_bytes: bytes, caption: str) -> bool:
    """Sends a photo to Telegram Bot API using pure urllib multipart/form-data."""
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    
    # Build multipart payload
    body = bytearray()
    
    # chat_id field
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(b'Content-Disposition: form-data; name="chat_id"\r\n\r\n')
    body.extend(f"{chat_id}\r\n".encode())
    
    # caption field
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(b'Content-Disposition: form-data; name="caption"\r\n\r\n')
    body.extend(f"{caption}\r\n".encode())
    
    # photo file field
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(b'Content-Disposition: form-data; name="photo"; filename="motion.jpg"\r\n')
    body.extend(b'Content-Type: image/jpeg\r\n\r\n')
    body.extend(photo_bytes)
    body.extend(b"\r\n")
    
    # closing boundary
    body.extend(f"--{boundary}--\r\n".encode())
    
    req = urllib.request.Request(
        url,
        data=bytes(body),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "OpenHik-MotionBot/1.0"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"Telegram send error: {e}")
        return False

def send_webhook(url: str, channel_id: int, date_time: str, description: str) -> bool:
    """Sends JSON notification to Webhook endpoint (Discord, Slack, Home Assistant, etc.)."""
    payload = {
        "event": "motion_detection",
        "channel": channel_id,
        "time": date_time,
        "description": description,
        "content": f"🚨 Motion Alert on Camera {channel_id} at {date_time}"
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "OpenHik-MotionBot/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status in (200, 204)
    except Exception as e:
        print(f"Webhook send error: {e}")
        return False

def parse_args():
    parser = argparse.ArgumentParser(description="OpenHik-DVR - Smart Telegram & Webhook Motion Notification Bot")
    parser.add_argument("--host", default="192.168.1.100", help="DVR Host IP (default: 192.168.1.100)")
    parser.add_argument("--port", type=int, default=80, help="DVR HTTP port (default: 80)")
    parser.add_argument("--user", default="admin", help="DVR Username (default: admin)")
    parser.add_argument("--pass", dest="password", default="", help="DVR Password")
    parser.add_argument("--telegram-token", help="Telegram Bot Token (e.g. 123456:ABC-DEF...)")
    parser.add_argument("--telegram-chat-id", help="Telegram Chat ID (e.g. 987654321)")
    parser.add_argument("--webhook-url", help="Webhook URL for Discord/Slack/Home Assistant")
    parser.add_argument("--cooldown", type=int, default=30, help="Notification cooldown in seconds per channel (default: 30)")
    parser.add_argument("--channels", default="all", help="Monitored channels, e.g. '1,2,3' or 'all' (default: all)")
    parser.add_argument("--save-dir", default="motion_captures", help="Directory to save local snapshots (default: motion_captures)")
    return parser.parse_args()

def main():
    args = parse_args()
    os.makedirs(args.save_dir, exist_ok=True)

    monitored_channels = None
    if args.channels.lower() != "all":
        monitored_channels = {int(c.strip()) for c in args.channels.split(",") if c.strip().isdigit()}

    print("==================================================")
    print("      OpenHik-DVR - Telegram Motion Alert Bot     ")
    print("==================================================")
    print(f"Target DVR     : {args.host}:{args.port}")
    print(f"Cooldown       : {args.cooldown} seconds per channel")
    print(f"Channels       : {args.channels}")
    print(f"Telegram Alert : {'ENABLED' if args.telegram_token and args.telegram_chat_id else 'DISABLED'}")
    print(f"Webhook Alert  : {'ENABLED' if args.webhook_url else 'DISABLED'}")
    print("Connecting...")

    client = PureHikClient(args.host, args.port, args.user, args.password)
    try:
        info = client.get_device_info()
        print(f"Connected to   : {info.model} (FW: {info.firmware})\n")
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    last_alert_time = {}

    def on_event(ev):
        # Filter for active motion detection events
        if not ev.is_motion() or not ev.is_active():
            return

        if monitored_channels and ev.channel_id not in monitored_channels:
            return

        now = time.time()
        last_t = last_alert_time.get(ev.channel_id, 0)
        if now - last_t < args.cooldown:
            return # Cooldown active, skip duplicate notifications

        last_alert_time[ev.channel_id] = now
        print(f"\n🚨 [{ev.date_time}] Motion Detected on Camera {ev.channel_id:02d}!")

        # Grab high-resolution snapshot
        print(f"   Grabbing live snapshot from Camera {ev.channel_id}...")
        snap = client.get_snapshot(ev.channel_id)
        if snap:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"motion_ch{ev.channel_id:02d}_{timestamp_str}.jpg"
            file_path = os.path.join(args.save_dir, file_name)
            with open(file_path, "wb") as f:
                f.write(snap)
            print(f"   Snapshot saved: {file_path}")

            # Send Telegram photo
            if args.telegram_token and args.telegram_chat_id:
                caption = f"🚨 *Motion Alert!*\n\n📷 *Camera:* Channel {ev.channel_id:02d}\n⏰ *Time:* {ev.date_time}\n📝 *Event:* {ev.description}"
                print("   Dispatching Telegram photo alert...")
                ok = send_telegram_photo(args.telegram_token, args.telegram_chat_id, snap, caption)
                if ok:
                    print("   Telegram alert delivered successfully!")

        # Send Webhook
        if args.webhook_url:
            print("   Dispatching Webhook event...")
            send_webhook(args.webhook_url, ev.channel_id, ev.date_time, ev.description)

    print("Bot is listening for motion events (Press Ctrl+C to exit)...")
    try:
        client.listen_events(on_event)
    except KeyboardInterrupt:
        print("\nBot stopped.")

if __name__ == '__main__':
    from datetime import datetime
    main()
