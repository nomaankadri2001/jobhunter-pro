#!/usr/bin/env python3
"""
JobHunter Pro - Production Server
Runs locally AND on Railway (always online).
API key stored as environment variable on Railway,
or in .groq_key file locally.
"""

import http.server
import json
import os
import urllib.request
import urllib.error
import webbrowser
import threading
import time
from pathlib import Path

PORT = int(os.environ.get("PORT", 7432))
KEY_FILE = Path(__file__).parent / ".groq_key"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"
STATIC_DIR = Path(__file__).parent / "static"


def get_api_key():
    # Railway/production: use environment variable
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if key:
        return key
    # Local: use file
    if KEY_FILE.exists():
        return KEY_FILE.read_text().strip()
    return ""


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def log_message(self, f, *a):
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        # Serve index.html for root
        if self.path == "/" or self.path == "":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self):
        if self.path == "/api/chat":
            self._chat()
        elif self.path == "/api/key":
            self._save_key()
        elif self.path == "/api/parse-resume":
            self._parse_resume()
        else:
            self.send_error(404)

    def _chat(self):
        body = self._read_json()
        key = get_api_key()
        if not key:
            return self._json({"error": "No API key configured."}, 400)

        payload = json.dumps({
            "model": MODEL,
            "messages": [{"role": "user", "content": body.get("prompt", "")}],
            "max_tokens": 1500,
            "temperature": 0.7
        }).encode()

        req = urllib.request.Request(
            GROQ_URL, data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
                "User-Agent": "python-httpx/0.24.0"
            }, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read())
                self._json({"text": d["choices"][0]["message"]["content"]})
        except urllib.error.HTTPError as e:
            raw = e.read().decode()
            try:
                msg = json.loads(raw).get("error", {}).get("message", raw)
            except:
                msg = raw
            self._json({"error": f"({e.code}) {msg}"}, 400)
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def _parse_resume(self):
        """Extract text from uploaded PDF or DOCX resume"""
        content_type = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)

        text = ""
        try:
            if "application/pdf" in content_type or raw[:4] == b"%PDF":
                text = self._extract_pdf(raw)
            elif "application/vnd.openxmlformats" in content_type or raw[:2] == b"PK":
                text = self._extract_docx(raw)
            else:
                # Try as plain text
                text = raw.decode("utf-8", errors="ignore")
        except Exception as e:
            return self._json({"error": f"Could not parse file: {e}"}, 400)

        if not text.strip():
            return self._json({"error": "Could not extract text from file."}, 400)

        self._json({"text": text.strip()})

    def _extract_pdf(self, data):
        """Extract text from PDF bytes without external libraries"""
        import re
        text_parts = []
        # Find all text streams in PDF
        content = data.decode("latin-1", errors="ignore")
        # Extract text between BT and ET markers
        streams = re.findall(r'BT(.*?)ET', content, re.DOTALL)
        for stream in streams:
            # Find Tj and TJ operators
            parts = re.findall(r'\((.*?)\)\s*Tj', stream)
            parts += re.findall(r'\[(.*?)\]\s*TJ', stream)
            for p in parts:
                cleaned = re.sub(r'\\[0-9]{3}', ' ', p)
                cleaned = cleaned.replace('\\n', '\n').replace('\\r', '\n')
                cleaned = re.sub(r'\\(.)', r'\1', cleaned)
                text_parts.append(cleaned)
        result = ' '.join(text_parts)
        # Clean up
        result = re.sub(r'\s+', ' ', result)
        return result

    def _extract_docx(self, data):
        """Extract text from DOCX bytes"""
        import zipfile
        import io
        import re
        try:
            z = zipfile.ZipFile(io.BytesIO(data))
            xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
            # Remove XML tags, keep text
            text = re.sub(r'<w:br[^/]*/>', '\n', xml)
            text = re.sub(r'<w:p[ >]', '\n', text)
            text = re.sub(r'<[^>]+>', '', text)
            text = re.sub(r'&amp;', '&', text)
            text = re.sub(r'&lt;', '<', text)
            text = re.sub(r'&gt;', '>', text)
            text = re.sub(r'[ \t]+', ' ', text)
            text = re.sub(r'\n{3,}', '\n\n', text)
            return text.strip()
        except Exception as e:
            raise Exception(f"DOCX parse error: {e}")

    def _save_key(self):
        # Only works locally (Railway uses env var)
        if os.environ.get("RAILWAY_ENVIRONMENT"):
            return self._json({"error": "On Railway, set GROQ_API_KEY in environment variables."}, 400)
        body = self._read_json()
        key = body.get("key", "").strip()
        if not key:
            KEY_FILE.unlink(missing_ok=True)
        else:
            KEY_FILE.write_text(key)
        self._json({"ok": True})

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length))

    def _json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


def open_browser():
    time.sleep(0.9)
    webbrowser.open(f"http://localhost:{PORT}")


if __name__ == "__main__":
    os.chdir(Path(__file__).parent)
    STATIC_DIR.mkdir(exist_ok=True)

    is_railway = bool(os.environ.get("RAILWAY_ENVIRONMENT"))
    has_key = bool(get_api_key())

    print("\n" + "=" * 46)
    print("  JobHunter Pro")
    print("=" * 46)
    print(f"  Mode   : {'Railway (online)' if is_railway else 'Local'}")
    print(f"  URL    : http://localhost:{PORT}")
    print(f"  API Key: {'✓ configured' if has_key else '✗ not set'}")
    if not is_railway:
        print("  Opening browser...")
    print("  Ctrl+C to stop")
    print("=" * 46 + "\n")

    if not is_railway:
        threading.Thread(target=open_browser, daemon=True).start()

    try:
        httpd = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    except OSError as e:
        if "Address already in use" in str(e):
            webbrowser.open(f"http://localhost:{PORT}")
        else:
            raise
