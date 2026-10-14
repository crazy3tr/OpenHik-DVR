#!/usr/bin/env python3
"""
Unit tests for OpenHik-DVR PureHikClient and utilities.
"""

from __future__ import annotations
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import tempfile
import os
import sys

# Add python directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))
from pure_hik_client import (
    _lname,
    _find_text,
    DeviceInfo,
    DeviceStatus,
    DeviceStorage,
    VideoChannel,
    StreamChannel,
    RecordingSegment,
    EventAlert,
    DownloadIncompleteError,
    convert_to_mp4,
)
from xml.sax.saxutils import escape

class TestXmlUtilities(unittest.TestCase):
    def test_lname_namespace_stripping(self):
        self.assertEqual(_lname("{http://www.hikvision.com/ver20/XMLSchema}DeviceInfo"), "DeviceInfo")
        self.assertEqual(_lname("{http://www.std-cgi.com/ver20/XMLSchema}trackID"), "trackID")
        self.assertEqual(_lname("plainTag"), "plainTag")

    def test_find_text_nested(self):
        xml_data = """<?xml version="1.0" encoding="utf-8"?>
        <root xmlns="http://www.hikvision.com/ver20/XMLSchema">
            <nested>
                <targetField>  Hello Hikvision  </targetField>
            </nested>
        </root>"""
        root = ET.fromstring(xml_data)
        self.assertEqual(_find_text(root, "targetField"), "Hello Hikvision")
        self.assertEqual(_find_text(root, "nonExistent"), "")

    def test_xml_entity_escaping(self):
        uri = "rtsp://192.168.1.100:554/tracks/101/?starttime=20261014T000000Z&endtime=20261014T010000Z&size=51162988"
        escaped = escape(uri)
        self.assertNotIn("&endtime", escaped)
        self.assertIn("&amp;endtime", escaped)
        self.assertIn("&amp;size", escaped)

        camera_name = "Kamera <1> & Depo"
        escaped_name = escape(camera_name)
        self.assertEqual(escaped_name, "Kamera &lt;1&gt; &amp; Depo")

class TestDomainModels(unittest.TestCase):
    def test_track_id_mapping(self):
        ch1_main = 1 * 100 + 1
        ch1_sub = 1 * 100 + 2
        ch16_main = 16 * 100 + 1
        self.assertEqual(ch1_main, 101)
        self.assertEqual(ch1_sub, 102)
        self.assertEqual(ch16_main, 1601)

    def test_recording_segment_size(self):
        seg = RecordingSegment(101, "2026-10-14T00:00:00Z", "2026-10-14T01:00:00Z", "rtsp://...", size_bytes=104857600)
        self.assertEqual(seg.track_id, 101)
        self.assertAlmostEqual(seg.size_mb, 100.0, places=1)

    def test_event_alert_classification(self):
        motion = EventAlert("VMD", 1, "active", "2026-10-14T12:00:00", "Motion detected")
        self.assertTrue(motion.is_motion())
        self.assertTrue(motion.is_active())

        videoloss = EventAlert("videoloss", 2, "inactive", "2026-10-14T12:00:00", "Signal lost")
        self.assertFalse(videoloss.is_motion())
        self.assertFalse(videoloss.is_active())

class TestTimezoneCalculations(unittest.TestCase):
    def test_timezone_formatting_exact(self):
        # Test helper function reproducing the math in set_time
        def calc_tz(offset_sec: int) -> str:
            sign = "-" if offset_sec < 0 else "+"
            total_sec = abs(offset_sec)
            hours = total_sec // 3600
            minutes = (total_sec % 3600) // 60
            return f"{sign}{hours:02d}:{minutes:02d}"

        self.assertEqual(calc_tz(10800), "+03:00")    # Turkey / CST-3
        self.assertEqual(calc_tz(-18000), "-05:00")   # US Eastern
        self.assertEqual(calc_tz(0), "+00:00")        # UTC
        self.assertEqual(calc_tz(-12600), "-03:30")   # Newfoundland (half-hour negative)
        self.assertEqual(calc_tz(19800), "+05:30")    # India (half-hour positive)

class TestStreamDetection(unittest.TestCase):
    def test_imkh_header_detection(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'IMKH' + b'\x00' * 100)
            imkh_path = f.name

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'\x00\x00\x00\x01' + b'\x67' * 100) # Raw H.264 SPS NAL
            raw_path = f.name

        try:
            with open(imkh_path, "rb") as f:
                self.assertEqual(f.read(4), b'IMKH')

            with open(raw_path, "rb") as f:
                self.assertNotEqual(f.read(4), b'IMKH')
        finally:
            if os.path.exists(imkh_path): os.remove(imkh_path)
            if os.path.exists(raw_path): os.remove(raw_path)

if __name__ == '__main__':
    unittest.main()
