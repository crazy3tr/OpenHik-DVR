using System;

namespace HikDvrSdk
{
    public class DeviceInfo
    {
        public string Model { get; set; }
        public string SerialNumber { get; set; }
        public string FirmwareVersion { get; set; }
        public string MacAddress { get; set; }
        public string DeviceType { get; set; }
        public string EncoderVersion { get; set; }

        public override string ToString()
        {
            return string.Format("{0} (FW: {1}, MAC: {2})", Model, FirmwareVersion, MacAddress);
        }
    }

    public class DeviceStatus
    {
        public string CurrentTime { get; set; }
        public int UptimeSeconds { get; set; }
        public int CpuUtilization { get; set; }

        public override string ToString()
        {
            return string.Format("CPU: {0}%, Uptime: {1}h, Time: {2}", CpuUtilization, UptimeSeconds / 3600, CurrentTime);
        }
    }

    public class DeviceStorage
    {
        public string Id { get; set; }
        public string Name { get; set; }
        public string Type { get; set; }
        public string Status { get; set; }
        public long CapacityMB { get; set; }
        public long FreeSpaceMB { get; set; }

        public double CapacityGB { get { return CapacityMB / 1024.0; } }

        public override string ToString()
        {
            return string.Format("{0} ({1:F1} GB) - Status: {2}", Name, CapacityGB, Status);
        }
    }

    public class VideoChannel
    {
        public int Id { get; set; }
        public string Name { get; set; }
        public bool Enabled { get; set; }

        public override string ToString()
        {
            return string.Format("Channel {0:D2}: {1} (Active: {2})", Id, Name, Enabled);
        }
    }

    public class RecordingSegment
    {
        public int TrackId { get; set; }
        public string StartTime { get; set; }
        public string EndTime { get; set; }
        public string PlaybackUri { get; set; }
        public long SizeBytes { get; set; }

        public double SizeMB { get { return SizeBytes / (1024.0 * 1024.0); } }

        public override string ToString()
        {
            return string.Format("[Track {0}] {1} -> {2} ({3:F2} MB)", TrackId, StartTime, EndTime, SizeMB);
        }
    }

    public class DownloadProgress
    {
        public long BytesDownloaded { get; set; }
        public double SpeedMBs { get; set; }
    }
}
