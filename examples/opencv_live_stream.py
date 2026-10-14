#!/usr/bin/env python3
"""
OpenHik-DVR - OpenCV RTSP Live Stream & AI Detection Template
Demonstrates how to pull live low-latency video streams from Hikvision cameras into OpenCV
for real-time computer vision, YOLO object detection, license plate recognition, and analytics.

Requirements:
  pip install opencv-python
"""

from __future__ import annotations
import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))
from pure_hik_client import PureHikClient

def main():
    try:
        import cv2
    except ImportError:
        print("OpenCV is required for this example. Please run: pip install opencv-python")
        return

    # Configuration - Change to your Hikvision DVR details:
    DVR_HOST = "192.168.1.100"
    DVR_PORT = 80
    DVR_USER = "admin"
    DVR_PASS = "password123"
    RTSP_PORT = 554
    CHANNEL_ID = 1
    STREAM_PROFILE = 1  # 1 = Main Stream (Full HD), 2 = Sub Stream (Faster for AI/YOLO)

    client = PureHikClient(DVR_HOST, DVR_PORT, DVR_USER, DVR_PASS)
    rtsp_url = client.get_rtsp_url(CHANNEL_ID, STREAM_PROFILE, RTSP_PORT)

    print("==================================================")
    print("      OpenHik-DVR - OpenCV Live Stream Demo       ")
    print("==================================================")
    print(f"Camera Channel : {CHANNEL_ID} ({'Main Stream' if STREAM_PROFILE == 1 else 'Sub Stream'})")
    print(f"Connecting to  : {rtsp_url[:35]}... (credentials masked)")
    print("Force TCP Transport enabled to avoid UDP packet loss.")
    print("Press 'q' in the video window to exit.")
    print("==================================================")

    # Force FFmpeg backend in OpenCV to use TCP transport (prevents frame corruption/smearing)
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    # Set small buffer size to reduce latency lag
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        print("Error: Could not open RTSP video stream. Verify RTSP port 554 is open on DVR.")
        return

    prev_time = time.time()
    frame_count = 0
    fps = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Warning: Dropped frame or stream disconnected. Reconnecting...")
            time.sleep(1)
            continue

        frame_count += 1
        now = time.time()
        if now - prev_time >= 1.0:
            fps = frame_count / (now - prev_time)
            frame_count = 0
            prev_time = now

        # --- AI / Computer Vision Hook ---
        # Here you can plug in any AI model:
        # results = yolo_model(frame)
        # ---------------------------------

        # Draw HUD overlays on frame
        h, w = frame.shape[:2]
        cv2.putText(frame, f"OpenHik-DVR CH {CHANNEL_ID:02d} | {w}x{h} | {fps:.1f} FPS", 
                    (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)

        cv2.imshow(f"OpenHik-DVR - Camera {CHANNEL_ID}", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Stream closed.")

if __name__ == '__main__':
    main()
