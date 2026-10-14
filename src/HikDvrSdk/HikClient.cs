using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Net;
using System.Text;
using System.Text.RegularExpressions;
using System.Xml;

namespace HikDvrSdk
{
    public class HikClient : IDisposable
    {
        private readonly string _host;
        private readonly int _port;
        private readonly string _user;
        private readonly string _password;
        private readonly string _baseUrl;
        private readonly CredentialCache _credentialCache;

        public HikClient(string host, int port = 80, string user = "admin", string password = "", bool useHttps = false)
        {
            _host = host;
            _port = port;
            _user = user;
            _password = password;
            string proto = useHttps ? "https" : "http";
            _baseUrl = string.Format(CultureInfo.InvariantCulture, "{0}://{1}:{2}", proto, _host, _port);

            _credentialCache = new CredentialCache();
            _credentialCache.Add(new Uri(_baseUrl), "Digest", new NetworkCredential(_user, _password));
        }

        private HttpWebRequest CreateRequest(string method, string path, string contentType = null)
        {
            var req = (HttpWebRequest)WebRequest.Create(_baseUrl + path);
            req.Method = method;
            req.Credentials = _credentialCache;
            req.UserAgent = "OpenHik-CSharp/1.0";
            req.Timeout = 15000;
            req.PreAuthenticate = false;
            if (!string.IsNullOrEmpty(contentType))
                req.ContentType = contentType;
            return req;
        }

        private string ExecuteRequest(string method, string path, string xmlBody = null)
        {
            var req = CreateRequest(method, path, "application/xml");
            if (!string.IsNullOrEmpty(xmlBody))
            {
                byte[] data = Encoding.UTF8.GetBytes(xmlBody);
                req.ContentLength = data.Length;
                using (var stream = req.GetRequestStream())
                {
                    stream.Write(data, 0, data.Length);
                }
            }

            using (var resp = (HttpWebResponse)req.GetResponse())
            using (var stream = resp.GetResponseStream())
            using (var reader = new StreamReader(stream, Encoding.UTF8))
            {
                return reader.ReadToEnd();
            }
        }

        private static string GetLocalTagText(XmlNode node, string localName)
        {
            if (node == null) return string.Empty;
            foreach (XmlNode child in node.ChildNodes)
            {
                if (child.LocalName == localName)
                    return child.InnerText.Trim();
                string nested = GetLocalTagText(child, localName);
                if (!string.IsNullOrEmpty(nested))
                    return nested;
            }
            return string.Empty;
        }

        public DeviceInfo GetDeviceInfo()
        {
            string xml = ExecuteRequest("GET", "/ISAPI/System/deviceInfo");
            var doc = new XmlDocument();
            doc.LoadXml(xml);

            return new DeviceInfo
            {
                Model = GetLocalTagText(doc.DocumentElement, "model"),
                SerialNumber = GetLocalTagText(doc.DocumentElement, "serialNumber"),
                FirmwareVersion = GetLocalTagText(doc.DocumentElement, "firmwareVersion"),
                MacAddress = GetLocalTagText(doc.DocumentElement, "macAddress"),
                DeviceType = GetLocalTagText(doc.DocumentElement, "deviceType"),
                EncoderVersion = GetLocalTagText(doc.DocumentElement, "encoderVersion")
            };
        }

        public DeviceStatus GetDeviceStatus()
        {
            string xml = ExecuteRequest("GET", "/ISAPI/System/status");
            var doc = new XmlDocument();
            doc.LoadXml(xml);

            string uptimeStr = GetLocalTagText(doc.DocumentElement, "deviceUpTime");
            string cpuStr = GetLocalTagText(doc.DocumentElement, "cpuUtilization");

            int uptime = 0;
            int.TryParse(uptimeStr, out uptime);

            int cpu = 0;
            int.TryParse(cpuStr, out cpu);

            return new DeviceStatus
            {
                CurrentTime = GetLocalTagText(doc.DocumentElement, "currentDeviceTime"),
                UptimeSeconds = uptime,
                CpuUtilization = cpu
            };
        }

        public List<DeviceStorage> GetStorage()
        {
            string xml = ExecuteRequest("GET", "/ISAPI/ContentMgmt/Storage");
            var doc = new XmlDocument();
            doc.LoadXml(xml);

            var list = new List<DeviceStorage>();
            var hddNodes = doc.GetElementsByTagName("hdd");
            foreach (XmlNode hdd in hddNodes)
            {
                string capStr = GetLocalTagText(hdd, "capacity");
                string freeStr = GetLocalTagText(hdd, "freeSpace");
                long cap = 0, free = 0;
                long.TryParse(capStr, out cap);
                long.TryParse(freeStr, out free);

                list.Add(new DeviceStorage
                {
                    Id = GetLocalTagText(hdd, "id"),
                    Name = GetLocalTagText(hdd, "hddName"),
                    Type = GetLocalTagText(hdd, "hddType"),
                    Status = GetLocalTagText(hdd, "status"),
                    CapacityMB = cap,
                    FreeSpaceMB = free
                });
            }
            return list;
        }

        public List<VideoChannel> GetVideoChannels()
        {
            var list = new List<VideoChannel>();
            // 1. Direct / Analog Video Inputs
            try
            {
                string xml = ExecuteRequest("GET", "/ISAPI/System/Video/inputs/channels");
                var doc = new XmlDocument();
                doc.LoadXml(xml);
                var chNodes = doc.GetElementsByTagName("VideoInputChannel");
                foreach (XmlNode ch in chNodes)
                {
                    string idStr = GetLocalTagText(ch, "id");
                    string enabledStr = GetLocalTagText(ch, "videoInputEnabled");
                    int id = 0;
                    int.TryParse(idStr, NumberStyles.Integer, CultureInfo.InvariantCulture, out id);

                    list.Add(new VideoChannel
                    {
                        Id = id,
                        Name = GetLocalTagText(ch, "name"),
                        Enabled = enabledStr.Equals("true", StringComparison.OrdinalIgnoreCase)
                    });
                }
            }
            catch { }

            // 2. NVR / Hybrid IP Digital Channels
            try
            {
                string xml = ExecuteRequest("GET", "/ISAPI/ContentMgmt/InputProxy/channels");
                var doc = new XmlDocument();
                doc.LoadXml(xml);
                var proxyNodes = doc.GetElementsByTagName("InputProxyChannel");
                foreach (XmlNode ch in proxyNodes)
                {
                    string idStr = GetLocalTagText(ch, "id");
                    int id = 0;
                    int.TryParse(idStr, NumberStyles.Integer, CultureInfo.InvariantCulture, out id);

                    bool exists = false;
                    for (int i = 0; i < list.Count; i++)
                    {
                        if (list[i].Id == id) { exists = true; break; }
                    }
                    if (!exists)
                    {
                        list.Add(new VideoChannel
                        {
                            Id = id,
                            Name = GetLocalTagText(ch, "name"),
                            Enabled = true
                        });
                    }
                }
            }
            catch { }

            return list;
        }

        public byte[] GetSnapshot(int channelId, int streamIndex = 1)
        {
            int trackId = channelId * 100 + streamIndex;
            string[] paths = new string[] {
                string.Format("/ISAPI/Streaming/channels/{0}/picture", trackId),
                string.Format("/ISAPI/Streaming/channels/{0}/picture", channelId)
            };

            foreach (string p in paths)
            {
                try
                {
                    var req = CreateRequest("GET", p);
                    using (var resp = (HttpWebResponse)req.GetResponse())
                    using (var ms = new MemoryStream())
                    {
                        resp.GetResponseStream().CopyTo(ms);
                        byte[] data = ms.ToArray();
                        if (data.Length > 2 && data[0] == 0xFF && data[1] == 0xD8)
                            return data;
                    }
                }
                catch
                {
                    continue;
                }
            }
            return null;
        }

        public List<RecordingSegment> SearchRecordings(int channelId, DateTime startTimeUtc, DateTime endTimeUtc, int maxResults = 500)
        {
            int trackId = channelId * 100 + 1;
            string startStr = startTimeUtc.ToString("yyyy-MM-ddTHH:mm:ssZ", CultureInfo.InvariantCulture);
            string endStr = endTimeUtc.ToString("yyyy-MM-ddTHH:mm:ssZ", CultureInfo.InvariantCulture);

            var list = new List<RecordingSegment>();
            int pos = 0;
            int pageSize = Math.Min(maxResults, 100);

            while (pos < maxResults)
            {
                int currentBatch = Math.Min(pageSize, maxResults - pos);
                string searchXml = string.Format(
                    CultureInfo.InvariantCulture,
                    "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" +
                    "<CMSearchDescription>\n" +
                    "<searchID>C1C1C1C1-0000-0000-0000-000000000001</searchID>\n" +
                    "<trackList><trackID>{0}</trackID></trackList>\n" +
                    "<timeSpanList><timeSpan><startTime>{1}</startTime><endTime>{2}</endTime></timeSpan></timeSpanList>\n" +
                    "<maxResults>{3}</maxResults>\n" +
                    "<searchResultPostion>{4}</searchResultPostion>\n" +
                    "<metadataList><metadataDescriptor>//recordType.meta.std-cgi.com</metadataDescriptor></metadataList>\n" +
                    "</CMSearchDescription>", trackId, startStr, endStr, currentBatch, pos);

                string xml = ExecuteRequest("POST", "/ISAPI/ContentMgmt/search", searchXml);
                var doc = new XmlDocument();
                doc.LoadXml(xml);

                string status = GetLocalTagText(doc.DocumentElement, "responseStatusStrg");
                var itemNodes = doc.GetElementsByTagName("searchMatchItem");
                if (itemNodes.Count == 0)
                    break;

                foreach (XmlNode item in itemNodes)
                {
                    string s = GetLocalTagText(item, "startTime");
                    string e = GetLocalTagText(item, "endTime");
                    string uri = GetLocalTagText(item, "playbackURI");

                    long sizeBytes = 0;
                    var match = Regex.Match(uri, @"[?&]size=(\d+)");
                    if (match.Success)
                        long.TryParse(match.Groups[1].Value, NumberStyles.Integer, CultureInfo.InvariantCulture, out sizeBytes);

                    if (!string.IsNullOrEmpty(uri))
                    {
                        list.Add(new RecordingSegment
                        {
                            TrackId = trackId,
                            StartTime = s,
                            EndTime = e,
                            PlaybackUri = uri,
                            SizeBytes = sizeBytes
                        });
                    }
                }

                pos += itemNodes.Count;
                if (!status.Equals("MORE", StringComparison.OrdinalIgnoreCase))
                    break;
            }

            return list;
        }

        public long DownloadRecording(string playbackUri, string destinationFilePath, Action<DownloadProgress> progressCallback = null, bool verifySize = true)
        {
            long expectedSize = 0;
            var sizeMatch = Regex.Match(playbackUri, @"[?&]size=(\d+)");
            if (sizeMatch.Success)
                long.TryParse(sizeMatch.Groups[1].Value, NumberStyles.Integer, CultureInfo.InvariantCulture, out expectedSize);

            string escapedUri = System.Security.SecurityElement.Escape(playbackUri);
            string dlXml = string.Format(
                CultureInfo.InvariantCulture,
                "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" +
                "<downloadRequest version=\"1.0\" xmlns=\"http://urn:selfextension:psiaext-ver10-xsd\">\n" +
                "<playbackURI>{0}</playbackURI>\n" +
                "</downloadRequest>", escapedUri);

            byte[] bodyData = Encoding.UTF8.GetBytes(dlXml);
            string[] paths = new string[] {
                "/ISAPI/ContentMgmt/download",
                "/PSIA/Custom/SelfExt/ContentMgmt/download"
            };

            HttpWebResponse resp = null;
            foreach (string p in paths)
            {
                try
                {
                    var req = CreateRequest("POST", p, "application/xml");
                    req.ContentLength = bodyData.Length;
                    using (var stream = req.GetRequestStream())
                    {
                        stream.Write(bodyData, 0, bodyData.Length);
                    }
                    resp = (HttpWebResponse)req.GetResponse();
                    break;
                }
                catch (WebException ex)
                {
                    var httpResp = ex.Response as HttpWebResponse;
                    if (httpResp != null && ((int)httpResp.StatusCode == 404 || (int)httpResp.StatusCode == 405))
                        continue;
                    throw;
                }
            }

            if (resp == null)
                throw new InvalidOperationException("DVR rejected download endpoints");

            long total = 0;
            var sw = Stopwatch.StartNew();

            using (resp)
            using (var inStream = resp.GetResponseStream())
            using (var outStream = new FileStream(destinationFilePath, FileMode.Create, FileAccess.Write, FileShare.None))
            {
                byte[] buffer = new byte[256 * 1024];
                int read;
                while ((read = inStream.Read(buffer, 0, buffer.Length)) > 0)
                {
                    outStream.Write(buffer, 0, read);
                    total += read;

                    if (progressCallback != null)
                    {
                        double sec = Math.Max(0.001, sw.Elapsed.TotalSeconds);
                        progressCallback(new DownloadProgress
                        {
                            BytesDownloaded = total,
                            SpeedMBs = (total / (1024.0 * 1024.0)) / sec
                        });
                    }
                }
            }

            if (verifySize && expectedSize > 0 && total < expectedSize)
            {
                throw new IOException(string.Format(CultureInfo.InvariantCulture,
                    "Download interrupted: received {0} bytes, expected {1} bytes", total, expectedSize));
            }

            return total;
        }

        public static bool ConvertToMp4(string inputPsPath, string outputMp4Path, double fps = 25.0, string ffmpegPath = "ffmpeg")
        {
            try
            {
                bool isImkh = false;
                if (File.Exists(inputPsPath))
                {
                    using (var fs = new FileStream(inputPsPath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
                    {
                        byte[] magic = new byte[4];
                        if (fs.Read(magic, 0, 4) == 4)
                        {
                            if (magic[0] == 0x49 && magic[1] == 0x4D && magic[2] == 0x4B && magic[3] == 0x48)
                                isImkh = true;
                        }
                    }
                }

                string args = isImkh
                    ? string.Format(CultureInfo.InvariantCulture, "-y -i \"{0}\" -c copy \"{1}\" -loglevel error -nostats", inputPsPath, outputMp4Path)
                    : string.Format(CultureInfo.InvariantCulture, "-y -r {0:F2} -i \"{1}\" -c copy \"{2}\" -loglevel error -nostats", fps, inputPsPath, outputMp4Path);

                var psi = new ProcessStartInfo
                {
                    FileName = ffmpegPath,
                    Arguments = args,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    RedirectStandardError = true,
                    RedirectStandardOutput = false
                };

                using (var p = Process.Start(psi))
                {
                    // Read stderr to avoid OS pipe deadlock
                    string err = p.StandardError.ReadToEnd();
                    p.WaitForExit();
                    return p.ExitCode == 0;
                }
            }
            catch
            {
                return false;
            }
        }

        public void Dispose()
        {
        }
    }
}
