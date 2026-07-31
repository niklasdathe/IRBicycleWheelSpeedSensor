#!/usr/bin/env python3
"""Generate, verify and live-serve the KiCad-sourced interactive BOM."""

from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import subprocess
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PCB = ROOT / "hardware" / "ir_spoke_link" / "ir_spoke_link.kicad_pcb"
OUTPUT = ROOT / "docs" / "interactive_bom.html"
MANIFEST = ROOT / "docs" / "interactive_bom.json"
KICAD_PYTHON = Path(r"C:\Program Files\KiCad\10.0\bin\python.exe")
TOOL_VERSION = "v2.11.2"
TOOL_COMMIT = "de7fad7ead9b73cea7eb17afa02c6ce9ce17a6ab"
TOOL_ROOT = Path.home() / "Tools" / "InteractiveHtmlBom" / "2.11.2"
GENERATOR = TOOL_ROOT / "InteractiveHtmlBom" / "generate_interactive_bom.py"
GENERATOR_OPTIONS = (
    "--dark-mode",
    "--show-fabrication",
    "--highlight-pin1",
    "selected",
    "--checkboxes",
    "Sourced,Placed,Inspected",
    "--mark-when-checked",
    "Placed",
    "--bom-view",
    "top-bottom",
    "--layer-view",
    "F",
    "--include-tracks",
    "--include-nets",
    "--extra-fields",
    "Manufacturer,MPN,LCSC,JLCPCB",
    "--no-browser",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_generator() -> None:
    missing = [path for path in (KICAD_PYTHON, GENERATOR) if not path.is_file()]
    if missing:
        raise SystemExit(
            "InteractiveHtmlBom is not installed. Run "
            r"powershell -ExecutionPolicy Bypass -File "
            r"tools\setup_interactive_bom.ps1"
        )


def generate() -> dict[str, str]:
    require_generator()
    command = [
        str(KICAD_PYTHON),
        str(GENERATOR),
        *GENERATOR_OPTIONS,
        "--extra-data-file",
        str(PCB),
        "--dest-dir",
        str(OUTPUT.parent),
        "--name-format",
        OUTPUT.stem,
        str(PCB),
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    metadata = {
        "schema_version": 1,
        "generator": "openscopeproject/InteractiveHtmlBom",
        "generator_version": TOOL_VERSION,
        "generator_commit": TOOL_COMMIT,
        "source": str(PCB.relative_to(ROOT)).replace("\\", "/"),
        "source_sha256": sha256(PCB),
        "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/"),
        "output_sha256": sha256(OUTPUT),
        "options": list(GENERATOR_OPTIONS),
    }
    MANIFEST.write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"PASS: interactive BOM synced to {metadata['source_sha256'][:12]} "
        f"({OUTPUT.stat().st_size} bytes)"
    )
    return metadata


def check() -> dict[str, str]:
    if not MANIFEST.is_file() or not OUTPUT.is_file():
        raise SystemExit("Interactive BOM or sync manifest is missing")
    metadata = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = {
        "generator_version": TOOL_VERSION,
        "generator_commit": TOOL_COMMIT,
        "source": str(PCB.relative_to(ROOT)).replace("\\", "/"),
        "source_sha256": sha256(PCB),
        "output": str(OUTPUT.relative_to(ROOT)).replace("\\", "/"),
        "output_sha256": sha256(OUTPUT),
        "options": list(GENERATOR_OPTIONS),
    }
    mismatches = {
        key: {"recorded": metadata.get(key), "actual": value}
        for key, value in expected.items()
        if metadata.get(key) != value
    }
    if mismatches:
        raise SystemExit(
            "Interactive BOM is stale:\n" + json.dumps(mismatches, indent=2)
        )
    print("PASS: interactive BOM matches the current KiCad PCB")
    return metadata


class LiveState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.version = ""
        self.last_error = ""

    def update(self) -> None:
        with self.lock:
            self.version = sha256(OUTPUT)
            self.last_error = ""

    def error(self, message: str) -> None:
        with self.lock:
            self.last_error = message

    def payload(self) -> str:
        with self.lock:
            return json.dumps(
                {"version": self.version, "error": self.last_error}
            )


LIVE_RELOAD = """
<script id="ir-spoke-bom-live-reload">
(() => {
  let version = null;
  setInterval(async () => {
    try {
      const response = await fetch('/__ibom_version', {cache: 'no-store'});
      const state = await response.json();
      if (state.error) console.error(state.error);
      if (version === null) version = state.version;
      else if (state.version !== version) location.reload();
    } catch (_) {}
  }, 750);
})();
</script>
"""


def make_handler(state: LiveState):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(OUTPUT.parent), **kwargs)

        def do_GET(self) -> None:
            if self.path in ("/", ""):
                self.send_response(302)
                self.send_header("Location", "/interactive_bom.html")
                self.end_headers()
                return
            if self.path == "/__ibom_version":
                payload = state.payload().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            if self.path.split("?", 1)[0] == "/interactive_bom.html":
                page = OUTPUT.read_text(encoding="utf-8")
                page = page.replace("</body>", LIVE_RELOAD + "</body>")
                payload = page.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            super().do_GET()

        def log_message(self, message: str, *args) -> None:
            print("[ibom] " + (message % args))

    return Handler


def watch(state: LiveState, interval: float) -> None:
    last_mtime = PCB.stat().st_mtime_ns
    while True:
        time.sleep(interval)
        current = PCB.stat().st_mtime_ns
        if current == last_mtime:
            continue
        try:
            generate()
            state.update()
            last_mtime = current
        except Exception as exc:  # retry after the next complete save
            state.error(str(exc))
            print(f"Interactive BOM regeneration failed: {exc}")


def serve(port: int, open_browser: bool, interval: float) -> None:
    url = f"http://127.0.0.1:{port}/interactive_bom.html"
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/__ibom_version", timeout=0.5
        ):
            if open_browser:
                webbrowser.open(url)
            print(f"Interactive BOM watcher already running at {url}")
            return
    except (OSError, urllib.error.URLError):
        pass

    metadata = generate()
    state = LiveState()
    state.version = metadata["output_sha256"]
    thread = threading.Thread(
        target=watch, args=(state, interval), daemon=True
    )
    thread.start()
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", port), make_handler(state)
    )
    if open_browser:
        webbrowser.open(url)
    print(f"Watching {PCB} and serving {url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--generate", action="store_true")
    action.add_argument("--check", action="store_true")
    action.add_argument("--watch", action="store_true")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--open", action="store_true")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--interval", type=float, default=0.75)
    args = parser.parse_args()
    if args.watch or args.serve:
        serve(args.port, args.open, args.interval)
    elif args.check:
        check()
    else:
        generate()


if __name__ == "__main__":
    main()
