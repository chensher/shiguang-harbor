#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拾光星港 · 本地服务
- 提供游戏页面
- 把存档保存在同目录的 data.json（每次保存前自动备份到 data.backup.json）
- 代理 AI 接口请求（避免浏览器跨域限制，API Key 只在你本机与 AI 服务商之间传输）
只用 Python 自带库，无需安装任何依赖。
"""
import json, os, ssl, sys, socket, threading, webbrowser, urllib.request, urllib.error
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data.json")
BACKUP = os.path.join(ROOT, "data.backup.json")
LOCK = threading.Lock()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, fmt, *args):
        if args and "/api/" in str(args[0]):
            return
        super().log_message(fmt, *args)

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def do_GET(self):
        if self.path.startswith("/api/state"):
            with LOCK:
                if os.path.exists(DATA):
                    with open(DATA, "r", encoding="utf-8") as f:
                        try:
                            return self._json(200, {"ok": True, "state": json.load(f)})
                        except Exception:
                            return self._json(200, {"ok": True, "state": None, "warn": "data.json 损坏"})
            return self._json(200, {"ok": True, "state": None})
        if self.path.startswith("/api/ping"):
            return self._json(200, {"ok": True, "app": "shiguang"})
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/state"):
            raw = self._body()
            try:
                json.loads(raw.decode("utf-8"))
            except Exception:
                return self._json(400, {"ok": False, "error": "bad json"})
            with LOCK:
                if os.path.exists(DATA):
                    try:
                        os.replace(DATA, BACKUP)
                    except Exception:
                        pass
                tmp = DATA + ".tmp"
                with open(tmp, "wb") as f:
                    f.write(raw)
                os.replace(tmp, DATA)
            return self._json(200, {"ok": True})

        if self.path.startswith("/api/ai"):
            try:
                req = json.loads(self._body().decode("utf-8"))
                base = (req.get("baseUrl") or "").rstrip("/")
                if not base:
                    return self._json(400, {"ok": False, "error": "未配置接口地址"})
                url = base if base.endswith("/chat/completions") else base + "/chat/completions"
                data = json.dumps(req.get("body") or {}).encode("utf-8")
                r = urllib.request.Request(url, data=data, method="POST", headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + (req.get("key") or ""),
                })
                with urllib.request.urlopen(r, context=CTX, timeout=120) as resp:
                    out = resp.read().decode("utf-8")
                return self._json(200, {"ok": True, "data": json.loads(out)})
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "ignore")[:800]
                return self._json(200, {"ok": False, "error": f"HTTP {e.code}: {detail}"})
            except Exception as e:
                return self._json(200, {"ok": False, "error": f"{type(e).__name__}: {e}"})

        self._json(404, {"ok": False})


def free_port(start=8765):
    for p in range(start, start + 40):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return 0


if __name__ == "__main__":
    port = free_port()
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://localhost:{port}/"
    print("\n  ✦ 拾光星港 已启动")
    print(f"  ✦ 在浏览器打开: {url}")
    print("  ✦ 关闭此窗口即可退出游戏（进度已自动保存在 data.json）\n")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
