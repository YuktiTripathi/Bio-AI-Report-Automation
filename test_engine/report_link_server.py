#!/usr/bin/env python3
"""Permanent report links: store JSON, regenerate PDF on each open/download.

Scope:
  - You receive BioReport JSON (fetch/modify is elsewhere)
  - POST stores JSON and returns a permanent link
  - GET serves a PDF softcopy (view + download); PDF is not kept on disk

Usage (from repo root):
    source .venv/bin/activate
    unset PLAYWRIGHT_BROWSERS_PATH
    export BIOAI_PUBLIC_BASE_URL=http://127.0.0.1:8790   # later: https://reports.yourdomain.com
    PYTHONPATH=. python test_engine/report_link_server.py

API:
    POST /api/reports          JSON body → { record_id, url, patient, variant }
    GET  /r/{record_id}        application/pdf (inline; browser can download)
    GET  /r/{record_id}?dl=1   force download
    GET  /                     small status page
"""

from __future__ import annotations

import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

os.environ.pop("PLAYWRIGHT_BROWSERS_PATH", None)

from modules.bioai_report.pdf_renderer.exceptions import (  # noqa: E402
    PdfRenderDependencyError,
    PdfRendererError,
    PdfValidationError,
)
from modules.bioai_report.pdf_renderer.report_store import (  # noqa: E402
    exists as report_exists,
    load_report_json,
    save_report_json,
)
from modules.bioai_report.pdf_renderer.service import PdfRenderService  # noqa: E402
from modules.bioai_report.pdf_renderer.view_model import resolve_gender_variant  # noqa: E402
from modules.bioai_report.report_engine.models.report import BioReport  # noqa: E402

HOST = os.environ.get("BIOAI_LINK_HOST", "127.0.0.1")
PORT = int(os.environ.get("BIOAI_LINK_PORT", "8790"))
PUBLIC_BASE = os.environ.get("BIOAI_PUBLIC_BASE_URL", f"http://{HOST}:{PORT}").rstrip("/")

_RECORD_RE = re.compile(r"^/r/([A-Za-z0-9._-]+)/?$")


def _public_url(record_id: str) -> str:
    return f"{PUBLIC_BASE}/r/{quote(record_id)}"


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", (name or "report").strip()) or "report"
    return f"BIO-AI-report-{cleaned}.pdf"


def _patient_bits(payload: dict) -> tuple[str, str]:
    patient = payload.get("patient") or {}
    name = (patient.get("name") or "report").strip() or "report"
    variant = resolve_gender_variant(patient.get("gender"), patient.get("sex"))
    return name, variant


class ReportLinkHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/health"}:
            return self._health()
        match = _RECORD_RE.match(parsed.path)
        if match:
            force_dl = (parse_qs(parsed.query).get("dl") or ["0"])[0] in {"1", "true", "yes"}
            return self._serve_pdf(match.group(1), force_download=force_dl)
        self.send_error(404, "Not found")

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") != "/api/reports":
            self.send_error(404, "Not found")
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("JSON body must be an object")
            # Validate shape early (same contract as PDF renderer).
            BioReport.model_validate(payload)
            record_id = save_report_json(payload)
            name, variant = _patient_bits(payload)
            body = {
                "record_id": record_id,
                "url": _public_url(record_id),
                "patient": name,
                "variant": variant,
                "note": "Permanent link. PDF is generated on each open; only JSON is stored.",
            }
            return self._json(200, body)
        except (json.JSONDecodeError, ValueError, PdfValidationError) as exc:
            return self._text(400, str(exc))
        except Exception as exc:  # noqa: BLE001
            return self._text(500, f"Failed to register report: {exc}")

    def _health(self) -> None:
        html = f"""<!doctype html>
<html><head><meta charset="utf-8"/><title>Bio-AI report links</title>
<style>
  body{{font-family:system-ui,sans-serif;max-width:640px;margin:48px auto;padding:0 16px;color:#102826}}
  code{{background:#f2f5f4;padding:2px 6px;border-radius:6px}}
  li{{margin:8px 0}}
</style></head><body>
<h1>Bio-AI report links</h1>
<p>Store JSON, open a permanent PDF link anytime (regenerated from JSON).</p>
<ul>
  <li><code>POST {PUBLIC_BASE}/api/reports</code> — body: BioReport JSON → returns <code>url</code></li>
  <li><code>GET {PUBLIC_BASE}/r/&lt;record_id&gt;</code> — view/download PDF</li>
  <li><code>GET …/r/&lt;record_id&gt;?dl=1</code> — force download</li>
</ul>
</body></html>"""
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_pdf(self, record_id: str, *, force_download: bool) -> None:
        payload = load_report_json(record_id)
        if payload is None:
            return self._text(404, f"Unknown report: {record_id}")
        try:
            report = BioReport.model_validate(payload)
            pdf_bytes = PdfRenderService().render_pdf(report)
            name, _variant = _patient_bits(payload)
            filename = _safe_filename(name)
        except (PdfValidationError, PdfRenderDependencyError, PdfRendererError) as exc:
            return self._text(400, str(exc))
        except Exception as exc:  # noqa: BLE001
            return self._text(500, f"PDF render failed: {exc}")

        disposition = "attachment" if force_download else "inline"
        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header(
            "Content-Disposition",
            f"{disposition}; filename=\"{filename}\"; filename*=UTF-8''{quote(filename)}",
        )
        self.send_header("Content-Length", str(len(pdf_bytes)))
        self.send_header("Cache-Control", "private, no-store")
        self.end_headers()
        self.wfile.write(pdf_bytes)

    def _json(self, code: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _text(self, code: int, message: str) -> None:
        data = message.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> int:
    # Touch store dir early so operators see where JSON lands.
    from modules.bioai_report.pdf_renderer.report_store import store_dir

    print(f"Store directory: {store_dir()}")
    print(f"Public base URL: {PUBLIC_BASE}")
    print(f"Listening:       http://{HOST}:{PORT}/")
    server = ThreadingHTTPServer((HOST, PORT), ReportLinkHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
