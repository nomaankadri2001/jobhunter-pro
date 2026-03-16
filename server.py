#!/usr/bin/env python3
import http.server, json, os, urllib.request, urllib.error
import webbrowser, threading, time
from pathlib import Path

PORT = int(os.environ.get("PORT", 7432))
KEY_FILE = Path(__file__).parent / ".groq_key"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"
BASE_DIR = Path(__file__).parent

def get_api_key():
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if key: return key
    if KEY_FILE.exists(): return KEY_FILE.read_text().strip()
    return ""

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)
    def log_message(self, f, *a): pass
    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()
    def do_GET(self):
        if self.path == "/" or self.path == "": self.path = "/index.html"
        super().do_GET()
    def do_POST(self):
        if self.path == "/api/chat": self._chat()
        elif self.path == "/api/key": self._save_key()
        elif self.path == "/api/parse-resume": self._parse_resume()
        else: self.send_error(404)

    def _chat(self):
        body = self._read_json()
        key = get_api_key()
        if not key: return self._json({"error": "No API key configured."}, 400)
        payload = json.dumps({
            "model": MODEL,
            "messages": [{"role": "user", "content": body.get("prompt", "")}],
            "max_tokens": 1500, "temperature": 0.7
        }).encode()
        req = urllib.request.Request(GROQ_URL, data=payload, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "User-Agent": "python-httpx/0.24.0"
        }, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read())
                self._json({"text": d["choices"][0]["message"]["content"]})
        except urllib.error.HTTPError as e:
            raw = e.read().decode()
            try: msg = json.loads(raw).get("error", {}).get("message", raw)
            except: msg = raw
            self._json({"error": f"({e.code}) {msg}"}, 400)
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def _parse_resume(self):
        content_type = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        text = ""
        try:
            if raw[:4] == b"%PDF" or "pdf" in content_type:
                text = self._extract_pdf(raw)
            elif raw[:2] == b"PK" or "docx" in content_type or "openxml" in content_type:
                text = self._extract_docx(raw)
            else:
                text = raw.decode("utf-8", errors="ignore")
        except Exception as e:
            return self._json({"error": f"Could not parse: {e}"}, 400)
        if not text.strip(): return self._json({"error": "No text found in file."}, 400)
        self._json({"text": text.strip()})

    def _extract_pdf(self, data):
        import re
        content = data.decode("latin-1", errors="ignore")
        text_parts = []
        for stream in re.findall(r'BT(.*?)ET', content, re.DOTALL):
            for p in re.findall(r'\((.*?)\)\s*Tj', stream) + re.findall(r'\[(.*?)\]\s*TJ', stream):
                cleaned = re.sub(r'\\[0-9]{3}', ' ', p)
                cleaned = cleaned.replace('\\n', '\n').replace('\\r', '\n')
                cleaned = re.sub(r'\\(.)', r'\1', cleaned)
                text_parts.append(cleaned)
        return re.sub(r'\s+', ' ', ' '.join(text_parts))

    def _extract_docx(self, data):
        import zipfile, io, re
        z = zipfile.ZipFile(io.BytesIO(data))
        xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
        text = re.sub(r'<w:br[^/]*/>', '\n', xml)
        text = re.sub(r'<w:p[ >]', '\n', text)
        text = re.sub(r'<[^>]+>', '', text)
        for e, r in [('&amp;','&'),('&lt;','<'),('&gt;','>')]:
            text = text.replace(e, r)
        return re.sub(r'\n{3,}', '\n\n', re.sub(r'[ \t]+', ' ', text)).strip()

    def _save_key(self):
        if os.environ.get("GROQ_API_KEY"):
            return self._json({"error": "Key is set via environment variable on Railway."}, 400)
        body = self._read_json()
        key = body.get("key", "").strip()
        if not key: KEY_FILE.unlink(missing_ok=True)
        else: KEY_FILE.write_text(key)
        self._json({"ok": True})

    def _read_json(self):
        return json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))

    def _json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code); self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers(); self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

if __name__ == "__main__":
    os.chdir(BASE_DIR)
    has_key = bool(get_api_key())
    is_local = not os.environ.get("GROQ_API_KEY")

    print(f"\n  JobHunter Pro")
    print(f"  Binding: 0.0.0.0:{PORT}")
    print(f"  Key: {'configured' if has_key else 'NOT SET'}\n")

    if is_local:
        threading.Thread(target=lambda: (time.sleep(1), webbrowser.open(f"http://localhost:{PORT}")), daemon=True).start()

    http.server.HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
