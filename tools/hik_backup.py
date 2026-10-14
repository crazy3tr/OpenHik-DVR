#!/usr/bin/env python3
"""
OpenHik-DVR - Automated Multi-Channel Backup & Archiving Utility
Downloads footage directly from Hikvision DVR hard disks via HTTP ISAPI and remuxes to MP4.
"""

import os
import sys
import time
import argparse
from datetime import datetime, timedelta
from pure_hik_client import PureHikClient, convert_to_mp4

def parse_args():
    parser = argparse.ArgumentParser(description="OpenHik-DVR - Turnkey Archiver & Backup Tool")
    parser.add_argument("--host", default="192.168.1.100", help="DVR Host IP (default: 192.168.1.100)")
    parser.add_argument("--port", type=int, default=80, help="DVR HTTP port (default: 80)")
    parser.add_argument("--user", default="admin", help="Username (default: admin)")
    parser.add_argument("--pass", dest="password", default="", help="Password")
    parser.add_argument("--channel", type=int, default=1, help="Channel number (1-based, default: 1)")
    parser.add_argument("--days", type=int, default=1, help="Number of past days to process (default: 1)")
    parser.add_argument("--date", help="Specific date to process (YYYY-MM-DD)")
    parser.add_argument("--out", default="kayitlar", help="Output directory (default: kayitlar)")
    parser.add_argument("--limit-mbps", type=float, default=0.0, help="Bandwidth limit in Mbps (0 = unlimited)")
    parser.add_argument("--mode", choices=["download", "list"], default="download", help="Action mode (list/download)")
    parser.add_argument("--keep-raw", action="store_true", help="Keep raw PS stream after MP4 remuxing")
    return parser.parse_args()

def main():
    args = parse_args()
    os.makedirs(args.out, exist_ok=True)

    print("==================================================")
    print("      OpenHik-DVR - Fast Hard Disk Archiver       ")
    print("==================================================")
    print(f"Target DVR : {args.host}:{args.port}")
    print(f"Channel    : {args.channel}")
    print(f"Mode       : {args.mode.upper()}")
    print("Connecting...")

    client = PureHikClient(args.host, args.port, args.user, args.password)
    try:
        info = client.get_device_info()
        print(f"Connected  : {info.model} (FW: {info.firmware})")
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    # Determine date list
    dates_to_query = []
    if args.date:
        dates_to_query.append(datetime.strptime(args.date, "%Y-%m-%d"))
    else:
        today = datetime.now()
        for d in range(args.days):
            dates_to_query.append(today - timedelta(days=d))

    total_files = 0
    downloaded_files = 0

    for d in dates_to_query:
        start_t = d.replace(hour=0, minute=0, second=0, microsecond=0)
        end_t = d.replace(hour=23, minute=59, second=59, microsecond=0)
        date_str = d.strftime("%Y-%m-%d")
        print(f"\nScanning Channel {args.channel} records for {date_str}...")

        try:
            segments = client.search_recordings(args.channel, start_t, end_t, max_results=100)
        except Exception as e:
            print(f"  Search error: {e}")
            continue

        if not segments:
            print("  No recordings found for this date.")
            continue

        print(f"  Found {len(segments)} recording segments.")

        for idx, seg in enumerate(segments, 1):
            total_files += 1
            # Clean timestamp labels
            s_label = seg.start_time.replace(":", ".").replace("Z", "")
            e_label = seg.end_time.replace(":", ".").replace("Z", "")
            base_name = f"ch{args.channel:02d}_{s_label}-{e_label}"
            raw_path = os.path.join(args.out, f"{base_name}.ps")
            mp4_path = os.path.join(args.out, f"{base_name}.mp4")

            if args.mode == "list":
                size_info = f"{seg.size_mb:.1f} MB" if seg.size_mb > 0 else "N/A"
                print(f"  [{idx:02d}] {seg.start_time} -> {seg.end_time} | Est. Size: {size_info}")
                continue

            # Skip existing files
            if os.path.exists(mp4_path) and os.path.getsize(mp4_path) > 100 * 1024:
                print(f"  [{idx:02d}] {base_name}.mp4 already exists. Skipping.")
                continue

            print(f"\n  [{idx:02d}/{len(segments)}] Downloading {base_name}...")
            
            def progress(downloaded_b, speed_mbs):
                mb = downloaded_b / (1024.0 * 1024.0)
                sys.stdout.write(f"\r     Downloaded: {mb:.1f} MB | Speed: {speed_mbs:.2f} MB/s")
                sys.stdout.flush()

            try:
                t0 = time.time()
                bytes_dl = client.download_recording(seg.playback_uri, raw_path, progress_callback=progress, limit_mbps=args.limit_mbps)
                elapsed = max(0.001, time.time() - t0)
                print(f"\n     Finished in {elapsed:.1f}s (Avg: {bytes_dl/(1024*1024)/elapsed:.2f} MB/s)")

                # Remux to standard MP4
                print("     Remuxing to standard MP4 with ffmpeg...")
                if convert_to_mp4(raw_path, mp4_path):
                    print("     Conversion successful!")
                    downloaded_files += 1
                    if not args.keep_raw and os.path.exists(raw_path):
                        os.remove(raw_path)
                else:
                    print("     [WARNING] FFmpeg remux failed, keeping raw .ps file.")
            except Exception as e:
                print(f"\n     Download failed: {e}")

    print("\n==================================================")
    print(f"Process complete. Total processed: {total_files}, Downloaded: {downloaded_files}")
    print("==================================================")

if __name__ == '__main__':
    main()
