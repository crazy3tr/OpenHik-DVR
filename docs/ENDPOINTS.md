# Hikvision ISAPI Endpoints Catalog

This document indexes the verified ISAPI endpoints tested across **Hikvision DS-7116HGHI-K1** and **DS-7116HQHI-K1** DVR platforms.

---

## 1. System & Device Telemetry

### `GET /ISAPI/System/deviceInfo`
Returns hardware serial numbers, device model, MAC address, and firmware versions.
```xml
<DeviceInfo version="1.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
    <deviceName>Embedded Net DVR</deviceName>
    <model>DS-7116HGHI-K1</model>
    <serialNumber>DS-7116HGHI-K10000000000AAAA000000000XXXX</serialNumber>
    <macAddress>00:11:22:33:44:55</macAddress>
    <firmwareVersion>V4.70.170</firmwareVersion>
    <encoderVersion>V5.0</encoderVersion>
    <deviceType>DVR</deviceType>
</DeviceInfo>
```

### `GET /ISAPI/System/status`
Returns real-time device health, CPU load, and uptime.
```xml
<DeviceStatus version="1.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
    <currentDeviceTime>2026-10-14T10:13:46+03:00</currentDeviceTime>
    <deviceUpTime>6216984</deviceUpTime>
    <CPUList>
        <CPU>
            <cpuUtilization>59</cpuUtilization>
        </CPU>
    </CPUList>
</DeviceStatus>
```

### `PUT /ISAPI/System/reboot`
Triggers an immediate remote hardware restart.

---

## 2. System Clock & NTP

### `GET /ISAPI/System/time`
Queries current device time and timezone offset.

### `PUT /ISAPI/System/time`
Sets hardware real-time clock (RTC).
```xml
<Time version="1.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
    <timeMode>manual</timeMode>
    <localTime>2026-10-14T12:00:00+03:00</localTime>
</Time>
```

---

## 3. Storage & Hard Drive Management

### `GET /ISAPI/ContentMgmt/Storage`
Queries SATA and NAS drive health, capacity, partition type, and free space.
```xml
<storage version="1.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
    <hddList>
        <hdd version="1.0">
            <id>1</id>
            <hddName>hdd1</hddName>
            <hddType>SATA</hddType>
            <status>ok</status>
            <capacity>5723166</capacity>
            <freeSpace>0</freeSpace>
            <property>RW</property>
        </hdd>
    </hddList>
    <workMode>quota</workMode>
</storage>
```

---

## 4. Video Inputs & Camera Names (OSD)

### `GET /ISAPI/System/Video/inputs/channels`
Lists all physical analog/IP camera channels.

### `PUT /ISAPI/System/Video/inputs/channels/{id}`
Updates camera channel OSD display name.
```xml
<VideoInputChannel version="1.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
    <id>1</id>
    <inputPort>1</inputPort>
    <name>Entrance Gate</name>
    <videoInputEnabled>true</videoInputEnabled>
</VideoInputChannel>
```

---

## 5. Streaming Profiles & Live Snapshots

### `GET /ISAPI/Streaming/channels`
Returns resolution, bitrate, frame rate, and compression codec for all tracks.

### `GET /ISAPI/Streaming/channels/{trackId}/picture`
Grabs an instantaneous full-resolution JPEG image from the camera stream.
- **Header:** `Content-Type: image/jpeg`
- **Track ID:** `101` for Channel 1 Main Stream, `301` for Channel 3 Main Stream, etc.

---

## 6. Recordings & Search Catalog

### `POST /ISAPI/ContentMgmt/search`
Searches historical footage on internal disk storage.

---

## 7. Direct HTTP Video Download

### `POST /ISAPI/ContentMgmt/download`
Initiates a high-speed HTTP chunked stream of the requested recording.
- **Payload:**
```xml
<downloadRequest version="1.0" xmlns="http://urn:selfextension:psiaext-ver10-xsd">
    <playbackURI>rtsp://host:port/Streaming/tracks/101/?starttime=...&endtime=...</playbackURI>
</downloadRequest>
```
