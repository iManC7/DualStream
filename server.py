import json
import mimetypes
import os
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

APP_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = Path("/tmp/DualStreamHLS")
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 10000))

mimetypes.add_type("application/vnd.apple.mpegurl", ".m3u8")
mimetypes.add_type("video/mp2t", ".ts")

state_lock = threading.Lock()
state = {
    "status": "idle",
    "message": "جاهز — أدخل رابطَي الصوت والفيديو ثم اضغط تشغيل.",
    "started_at": None,
    "last_error": "",
}
ffmpeg_proc = None
ffmpeg_log = None
server = None


def find_ffmpeg():
    return shutil.which("ffmpeg") or "ffmpeg"


def set_state(status, message, error=""):
    with state_lock:
        state["status"] = status
        state["message"] = message
        state["last_error"] = error


def cleanup_segments():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for item in OUTPUT_DIR.glob("*"):
        if item.is_file():
            try:
                item.unlink()
            except OSError:
                pass


def stop_stream(clean=True):
    global ffmpeg_proc, ffmpeg_log
    proc = ffmpeg_proc
    if proc and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=4)
        except Exception:
            try:
                proc.kill()
                proc.wait(timeout=2)
            except Exception:
                pass
    ffmpeg_proc = None
    if ffmpeg_log:
        try:
            ffmpeg_log.close()
        except Exception:
            pass
        ffmpeg_log = None
    if clean:
        cleanup_segments()
    set_state("stopped", "تم إيقاف البث وتنظيف المقاطع المؤقتة.")


def build_input_args(stream_url):
    parsed = urlparse(stream_url)
    
    headers_list = [
        "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept: */*",
        "Accept-Language: en-US,en;q=0.9",
    ]
    headers_str = "\r\n".join(headers_list) + "\r\n"

    args = [
        "-thread_queue_size", "4096",
        "-rw_timeout", "15000000",
        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "10",
        "-headers", headers_str,
    ]

    # دعم تنسيقات HLS و TS عبر الـ Worker Proxy
    args.extend([
        "-extension_picky", "0",
        "-http_persistent", "0"
    ])

    args.extend(["-i", stream_url])
    return args


def launch_stream(audio, video, segment_seconds=4, list_size=8):
    global ffmpeg_proc, ffmpeg_log
    
    stop_stream(clean=True)
    time.sleep(0.5)

    ffmpeg = find_ffmpeg()
    if not audio.startswith(("http://", "https://")) or not video.startswith(("http://", "https://")):
        raise RuntimeError("تأكد من أن رابطَي المصدرين يبدآن بـ http:// أو https://.")
    
    cleanup_segments()
    log_path = OUTPUT_DIR / "ffmpeg.log"
    ffmpeg_log = open(log_path, "w", encoding="utf-8", errors="replace")

    command = [
        ffmpeg, "-hide_banner", "-loglevel", "warning", "-stats",
    ]

    command.extend(build_input_args(audio))
    command.extend(build_input_args(video))

    command.extend([
        "-map", "1:v:0", "-map", "0:a:0",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
        "-max_muxing_queue_size", "8192",
        "-f", "hls",
        "-hls_time", str(segment_seconds),
        "-hls_list_size", str(list_size),
        "-hls_delete_threshold", "1",
        "-hls_flags", "delete_segments+omit_endlist+program_date_time",
        "-hls_segment_filename", str(OUTPUT_DIR / "segment_%05d.ts"),
        str(OUTPUT_DIR / "index.m3u8"),
    ])

    ffmpeg_proc = subprocess.Popen(
        command, stdout=ffmpeg_log, stderr=subprocess.STDOUT
    )
    with state_lock:
        state["status"] = "starting"
        state["message"] = "جارٍ الاتصال بالمصدرين وتجهيز مقاطع البث..."
        state["started_at"] = time.time()
        state["last_error"] = ""
    threading.Thread(target=watch_stream, daemon=True).start()


def watch_stream():
    global ffmpeg_proc, ffmpeg_log
    deadline = time.time() + 50
    playlist = OUTPUT_DIR / "index.m3u8"
    while time.time() < deadline:
        proc = ffmpeg_proc
        if not proc:
            return
        code = proc.poll()
        if code is not None:
            error = ""
            try:
                error = (OUTPUT_DIR / "ffmpeg.log").read_text(encoding="utf-8", errors="replace")[-2500:]
            except Exception:
                pass
            set_state("error", f"توقف FFmpeg قبل جاهزية البث (رمز الخروج {code}). راجع روابط المصدرين.", error)
            return
        segments = list(OUTPUT_DIR.glob("segment_*.ts"))
        if playlist.exists() and len(segments) >= 2:
            set_state("running", "البث يعمل السحابي جاهز.")
            return
        time.sleep(0.4)
    if ffmpeg_proc and ffmpeg_proc.poll() is None:
        set_state("running", "FFmpeg يعمل السحابي جاهز.")
    else:
        set_state("error", "لم يتمكن FFmpeg من بدء البث.")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def add_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def send_json(self, code, obj):
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.add_cors()
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self):
        self.send_response(204)
        self.add_cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        host_header = self.headers.get("Host", f"localhost:{PORT}")
        protocol = "https" if "render.com" in host_header else "http"
        base_url = f"{protocol}://{host_header}"

        path = urlparse(self.path).path
        if path == "/api/status":
            proc = ffmpeg_proc
            if proc and proc.poll() is not None and state["status"] in ("running", "starting"):
                set_state("error", f"توقف FFmpeg (رمز الخروج {proc.returncode}).")
            self.send_json(200, {
                **state,
                "ffmpeg_found": True,
                "stream_url": f"{base_url}/hls/index.m3u8",
            })
            return
        if path == "/api/log":
            log_path = OUTPUT_DIR / "ffmpeg.log"
            content = "لا يوجد سجل متاح حالياً."
            if log_path.exists():
                try:
                    content = log_path.read_text(encoding="utf-8", errors="replace")
                except Exception as e:
                    content = f"خطأ في قراءة السجل: {e}"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.add_cors()
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
            return
        if path.startswith("/hls/"):
            name = path.removeprefix("/hls/")
            if name not in ("index.m3u8",) and not (name.startswith("segment_") and name.endswith(".ts")):
                self.send_error(404)
                return
            file_path = OUTPUT_DIR / name
            if not file_path.is_file():
                self.send_error(404)
                return
            content = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(str(file_path))[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.add_cors()
            self.end_headers()
            self.wfile.write(content)
            return
        self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except Exception:
            self.send_json(400, {"error": "بيانات الطلب غير صالحة."})
            return
        if path == "/api/start":
            try:
                segment_seconds = int(payload.get("segment_seconds", 4))
                list_size = int(payload.get("list_size", 8))
                launch_stream(str(payload.get("audio", "")).strip(), str(payload.get("video", "")).strip(), segment_seconds, list_size)
                self.send_json(200, {"ok": True, "message": "تم بدء تشغيل FFmpeg."})
            except Exception as exc:
                set_state("error", str(exc), str(exc))
                self.send_json(400, {"ok": False, "error": str(exc)})
            return
        if path == "/api/stop":
            stop_stream(clean=True)
            self.send_json(200, {"ok": True, "message": "تم إيقاف البث."})
            return
        self.send_error(404)


def main():
    global server
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"DualStream Cloud Server يعمل على المخرج {PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_stream(clean=True)
        server.server_close()


if __name__ == "__main__":
    main()