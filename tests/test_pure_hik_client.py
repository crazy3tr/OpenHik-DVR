#!/usr/bin/env python3
"""
Unit tests for OpenHik-DVR PureHikClient using mocked ISAPI HTTP responses.
"""

from __future__ import annotations
import unittest
from unittest.mock import MagicMock, patch
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import urllib.request
import urllib.error
import tempfile
import io
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))
from pure_hik_client import (
    PureHikClient,
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

class MockHttpResponse:
    def __init__(self, data: bytes, status: int = 200, headers: dict | None = None):
        self._data = io.BytesIO(data)
        self.status = status
        self.headers = headers or {'Content-Type': 'application/xml'}

    def read(self, amt: int | None = None) -> bytes:
        if amt is None:
            return self._data.read()
        return self._data.read(amt)

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

class TestPureHikClientMocked(unittest.TestCase):
    def setUp(self):
        self.client = PureHikClient("192.168.1.100", 80, "admin", "password123")
        self.client.opener = MagicMock()

    def test_get_device_info(self):
        xml_resp = b"""<?xml version="1.0" encoding="UTF-8"?>
<DeviceInfo xmlns="http://www.hikvision.com/ver20/XMLSchema">
    <model>DS-7116HGHI-MOCK</model>
    <serialNumber>DS-7116HGHI-K10000000000AAAA000000000XXXX</serialNumber>
    <firmwareVersion>V4.70.170</firmwareVersion>
    <macAddress>00:11:22:33:44:55</macAddress>
    <deviceType>DVR</deviceType>
    <encoderVersion>V5.0</encoderVersion>
</DeviceInfo>"""
        self.client.opener.open.return_value = MockHttpResponse(xml_resp)

        info = self.client.get_device_info()
        self.assertEqual(info.model, "DS-7116HGHI-MOCK")
        self.assertEqual(info.firmware, "V4.70.170")
        self.assertEqual(info.mac, "00:11:22:33:44:55")
        self.assertEqual(info.device_type, "DVR")

    def test_search_recordings_pagination_and_size(self):
        page1_xml = b"""<?xml version="1.0" encoding="utf-8"?>
<CMSearchResult xmlns="http://www.std-cgi.com/ver20/XMLSchema">
    <responseStatusStrg>MORE</responseStatusStrg>
    <numOfMatches>2</numOfMatches>
    <matchList>
        <searchMatchItem>
            <trackID>101</trackID>
            <startTime>2026-10-14T10:00:00Z</startTime>
            <endTime>2026-10-14T10:30:00Z</endTime>
            <playbackURI>rtsp://192.168.1.100:554/tracks/101/?starttime=20261014T100000Z&amp;endtime=20261014T103000Z&amp;size=52428800</playbackURI>
        </searchMatchItem>
    </matchList>
</CMSearchResult>"""

        page2_xml = b"""<?xml version="1.0" encoding="utf-8"?>
<CMSearchResult xmlns="http://www.std-cgi.com/ver20/XMLSchema">
    <responseStatusStrg>OK</responseStatusStrg>
    <numOfMatches>2</numOfMatches>
    <matchList>
        <searchMatchItem>
            <trackID>101</trackID>
            <startTime>2026-10-14T10:30:00Z</startTime>
            <endTime>2026-10-14T11:00:00Z</endTime>
            <playbackURI>rtsp://192.168.1.100:554/tracks/101/?starttime=20261014T103000Z&amp;endtime=20261014T110000Z&amp;size=26214400</playbackURI>
        </searchMatchItem>
    </matchList>
</CMSearchResult>"""

        self.client.opener.open.side_effect = [
            MockHttpResponse(page1_xml),
            MockHttpResponse(page2_xml)
        ]

        t0 = datetime(2026, 10, 14, 10, 0, 0)
        t1 = datetime(2026, 10, 14, 11, 0, 0)
        results = self.client.search_recordings(channel_id=1, start_time=t0, end_time=t1, max_results=50)

        self.assertEqual(len(results), 2)
        self.assertEqual(self.client.opener.open.call_count, 2)
        self.assertEqual(results[0].size_bytes, 52428800)
        self.assertAlmostEqual(results[0].size_mb, 50.0, places=1)
        self.assertEqual(results[1].size_bytes, 26214400)
        self.assertAlmostEqual(results[1].size_mb, 25.0, places=1)

    def test_download_recording_verification(self):
        fake_stream = b"IMKH" + (b"\x00" * 4096)
        expected_size = len(fake_stream)
        uri = f"rtsp://192.168.1.100:554/tracks/101/?starttime=20261014T100000Z&endtime=20261014T103000Z&size={expected_size}"

        self.client.opener.open.return_value = MockHttpResponse(fake_stream)

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            downloaded = self.client.download_recording(uri, tmp_path, verify_size=True)
            self.assertEqual(downloaded, expected_size)
            self.assertEqual(os.path.getsize(tmp_path), expected_size)

            # Test size mismatch raises DownloadIncompleteError
            wrong_size_uri = f"rtsp://192.168.1.100:554/tracks/101/?starttime=20261014T100000Z&endtime=20261014T103000Z&size=999999"
            self.client.opener.open.return_value = MockHttpResponse(fake_stream)
            with self.assertRaises(DownloadIncompleteError):
                self.client.download_recording(wrong_size_uri, tmp_path, verify_size=True)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_get_video_channels_hybrid_and_error_handling(self):
        analog_xml = b"""<?xml version="1.0" encoding="utf-8"?>
<VideoInputChannelList xmlns="http://www.hikvision.com/ver20/XMLSchema">
    <VideoInputChannel>
        <id>1</id>
        <name>Analog Cam 1</name>
        <videoInputEnabled>true</videoInputEnabled>
    </VideoInputChannel>
</VideoInputChannelList>"""

        ip_xml = b"""<?xml version="1.0" encoding="utf-8"?>
<InputProxyChannelList xmlns="http://www.hikvision.com/ver20/XMLSchema">
    <InputProxyChannel>
        <id>1</id>
        <name>IP Cam Front</name>
    </InputProxyChannel>
</InputProxyChannelList>"""

        self.client.opener.open.side_effect = [
            MockHttpResponse(analog_xml),
            MockHttpResponse(ip_xml)
        ]

        channels = self.client.get_video_channels()
        self.assertEqual(len(channels), 2)
        self.assertEqual(channels[0].channel_id, 1)
        self.assertEqual(channels[0].channel_type, "analog")
        self.assertEqual(channels[1].channel_id, 1)
        self.assertEqual(channels[1].channel_type, "ip")

    def test_get_video_channels_auth_failure_propagates(self):
        err = urllib.error.HTTPError("http://...", 401, "Unauthorized", {}, None)
        self.client.opener.open.side_effect = err

        with self.assertRaises(urllib.error.HTTPError):
            self.client.get_video_channels()

    def test_get_video_channels_connection_failure_propagates(self):
        import socket
        # Test socket error / connection refused propagates without NameError
        sock_err = urllib.error.URLError(socket.error("Connection refused"))
        self.client.opener.open.side_effect = sock_err

        with self.assertRaises(urllib.error.URLError):
            self.client.get_video_channels()

    def test_set_channel_name_xml_escaping(self):
        self.client.opener.open.return_value = MockHttpResponse(b"<ResponseStatus>OK</ResponseStatus>")
        ok = self.client.set_channel_name(1, "Gate <1> & Office")
        self.assertTrue(ok)

        # Inspect the request sent to opener
        req = self.client.opener.open.call_args[0][0]
        data_sent = req.data.decode('utf-8')
        self.assertIn("Gate &lt;1&gt; &amp; Office", data_sent)
        self.assertNotIn("Gate <1> & Office", data_sent)

    def test_set_time_payload_and_timezone(self):
        self.client.opener.open.return_value = MockHttpResponse(b"<ResponseStatus>OK</ResponseStatus>")
        tz = timezone(timedelta(hours=3))
        target_time = datetime(2026, 10, 14, 15, 30, 0, tzinfo=tz)

        ok = self.client.set_time(target_time)
        self.assertTrue(ok)

        req = self.client.opener.open.call_args[0][0]
        data_sent = req.data.decode('utf-8')
        self.assertIn("<localTime>2026-10-14T15:30:00+03:00</localTime>", data_sent)
        self.assertIn("<timeMode>manual</timeMode>", data_sent)

    def test_event_alert_classification(self):
        motion = EventAlert("VMD", 1, "active", "2026-10-14T12:00:00", "Motion detected")
        self.assertTrue(motion.is_motion())
        self.assertTrue(motion.is_active())

        videoloss = EventAlert("videoloss", 2, "inactive", "2026-10-14T12:00:00", "Signal lost")
        self.assertFalse(videoloss.is_motion())
        self.assertFalse(videoloss.is_active())

if __name__ == '__main__':
    unittest.main()
