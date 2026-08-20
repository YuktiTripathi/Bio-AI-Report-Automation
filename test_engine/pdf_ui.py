#!/usr/bin/env python3
"""Simple local UI: upload BioReport JSON → download PDF.

Usage (from repo root):
    source .venv/bin/activate
    unset PLAYWRIGHT_BROWSERS_PATH
    PYTHONPATH=. python test_engine/pdf_ui.py

Open:
    http://127.0.0.1:8787/
"""

from __future__ import annotations

import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Prefer the default Playwright browser cache (macOS/Linux).
os.environ.pop("PLAYWRIGHT_BROWSERS_PATH", None)

from modules.bioai_report.pdf_renderer.exceptions import (  # noqa: E402
    PdfRenderDependencyError,
    PdfRendererError,
    PdfValidationError,
)
from modules.bioai_report.pdf_renderer.service import PdfRenderService  # noqa: E402
from modules.bioai_report.pdf_renderer.view_model import resolve_gender_variant  # noqa: E402
from modules.bioai_report.report_engine.models.report import BioReport  # noqa: E402

HOST = "127.0.0.1"
PORT = 8787

_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Bio-AI PDF</title>
  <style>
    :root {
      --bg: #041716;
      --bg-2: #0a2a27;
      --card: #0e2f2c;
      --text: #f2f7f6;
      --muted: #8eaaa6;
      --accent: #3dd68c;
      --accent-ink: #04241c;
      --line: rgba(255,255,255,0.10);
      --danger: #ff7a86;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif;
      color: var(--text);
      background:
        radial-gradient(720px 360px at 12% -8%, rgba(61,214,140,0.16), transparent 58%),
        radial-gradient(640px 320px at 95% 8%, rgba(198,32,59,0.12), transparent 52%),
        linear-gradient(180deg, var(--bg-2), var(--bg));
      display: grid;
      place-items: center;
      padding: 32px 16px;
    }
    .shell {
      width: min(520px, 100%);
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 14px;
      color: var(--muted);
      font-size: 0.78rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    .brand-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--accent);
      box-shadow: 0 0 0 4px rgba(61,214,140,0.18);
    }
    .card {
      background: linear-gradient(180deg, rgba(255,255,255,0.03), transparent 40%), var(--card);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 28px 26px 24px;
      box-shadow: 0 24px 60px rgba(0,0,0,0.38);
    }
    h1 {
      margin: 0 0 8px;
      font-size: 1.55rem;
      font-weight: 650;
      letter-spacing: -0.03em;
      line-height: 1.15;
    }
    .sub {
      margin: 0 0 22px;
      color: var(--muted);
      font-size: 0.95rem;
      line-height: 1.5;
    }
    .drop {
      position: relative;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 8px;
      min-height: 148px;
      padding: 24px 20px;
      border: 1.5px dashed rgba(255,255,255,0.20);
      border-radius: 16px;
      background: rgba(0,0,0,0.22);
      text-align: center;
      cursor: pointer;
      transition: border-color .15s ease, background .15s ease, transform .15s ease;
    }
    .drop:hover,
    .drop.drag {
      border-color: rgba(61,214,140,0.7);
      background: rgba(61,214,140,0.08);
    }
    .drop.drag { transform: scale(1.01); }
    .drop-icon {
      width: 42px;
      height: 42px;
      border-radius: 12px;
      display: grid;
      place-items: center;
      background: rgba(61,214,140,0.12);
      color: var(--accent);
      font-size: 1.25rem;
      margin-bottom: 4px;
    }
    .drop strong {
      display: block;
      font-size: 1rem;
      font-weight: 650;
    }
    .drop .hint {
      color: var(--muted);
      font-size: 0.86rem;
      line-height: 1.4;
    }
    .drop .file-name {
      margin-top: 4px;
      max-width: 100%;
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(255,255,255,0.06);
      color: var(--text);
      font-size: 0.82rem;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .drop .file-name:empty { display: none; }
    /* Fully hide native file control (display:none alone can still leak UI in some browsers). */
    .file-input {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      opacity: 0;
      cursor: pointer;
      font-size: 0;
    }
    .meta {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 16px;
      min-height: 28px;
    }
    .chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(255,255,255,0.06);
      border: 1px solid var(--line);
      color: var(--muted);
      font-size: 0.82rem;
    }
    .chip b { color: var(--text); font-weight: 650; }
    .chip.ready {
      border-color: rgba(61,214,140,0.35);
      background: rgba(61,214,140,0.10);
    }
    button#go {
      margin-top: 18px;
      width: 100%;
      border: 0;
      border-radius: 12px;
      padding: 14px 16px;
      font-size: 1rem;
      font-weight: 700;
      letter-spacing: -0.01em;
      color: var(--accent-ink);
      background: var(--accent);
      cursor: pointer;
      transition: filter .15s ease, transform .1s ease;
    }
    button#go:hover:not(:disabled) { filter: brightness(1.05); }
    button#go:active:not(:disabled) { transform: translateY(1px); }
    button#go:disabled {
      opacity: 0.4;
      cursor: not-allowed;
      filter: none;
    }
    .status {
      margin-top: 12px;
      color: var(--muted);
      font-size: 0.86rem;
      min-height: 1.2em;
      text-align: center;
    }
    .err {
      margin-top: 12px;
      color: #ffe1e4;
      background: rgba(255,122,134,0.12);
      border: 1px solid rgba(255,122,134,0.35);
      border-radius: 12px;
      padding: 10px 12px;
      font-size: 0.86rem;
      display: none;
      white-space: pre-wrap;
    }
  </style>
</head>
<body>
  <div class="shell">
    <div class="brand"><span class="brand-dot" aria-hidden="true"></span> Metsights · Bio-AI</div>
    <main class="card">
      <h1>Report PDF generator</h1>
      <p class="sub">Upload a BioReport JSON. Gender is detected from the file, then the matching male or female PDF is built.</p>

      <div class="drop" id="drop" role="button" tabindex="0" aria-label="Choose or drop JSON file">
        <div class="drop-icon" aria-hidden="true">↑</div>
        <strong>Choose or drop JSON</strong>
        <div class="hint">.json BioReport file</div>
        <div class="file-name" id="filename"></div>
        <input class="file-input" id="file" type="file" accept=".json,application/json" />
      </div>

      <div class="meta" id="meta"></div>
      <button id="go" type="button" disabled>Generate PDF</button>
      <div class="status" id="status"></div>
      <div class="err" id="err"></div>
    </main>
  </div>

  <script>
    const fileInput = document.getElementById('file');
    const drop = document.getElementById('drop');
    const go = document.getElementById('go');
    const meta = document.getElementById('meta');
    const status = document.getElementById('status');
    const err = document.getElementById('err');
    const filenameEl = document.getElementById('filename');
    let jsonText = null;
    let suggestedName = 'BIO-AI-report.pdf';

    function showError(msg) {
      err.style.display = msg ? 'block' : 'none';
      err.textContent = msg || '';
    }

    function inspect(text) {
      const data = JSON.parse(text);
      const p = data.patient || (data.executive_summary && data.executive_summary.patient) || {};
      const name = (p.name || 'report').toString().trim() || 'report';
      const sex = ((p.sex || p.gender || '') + '').toLowerCase();
      const variant = (sex === 'female' || sex === 'f' || sex === 'woman') ? 'female' : 'male';
      const safe = name.replace(/[^A-Za-z0-9._-]+/g, '_');
      suggestedName = `BIO-AI-report-${safe}.pdf`;
      meta.innerHTML =
        `<span class="chip ready">Patient <b>${name}</b></span>` +
        `<span class="chip ready">Variant <b>${variant}</b></span>`;
      return true;
    }

    function setFile(file) {
      showError('');
      status.textContent = '';
      if (!file) return;
      filenameEl.textContent = file.name;
      const reader = new FileReader();
      reader.onload = () => {
        try {
          jsonText = String(reader.result || '');
          inspect(jsonText);
          go.disabled = false;
        } catch (e) {
          jsonText = null;
          go.disabled = true;
          meta.innerHTML = '';
          filenameEl.textContent = '';
          showError('Invalid JSON: ' + (e.message || e));
        }
      };
      reader.readAsText(file);
    }

    fileInput.addEventListener('change', () => setFile(fileInput.files[0]));
    drop.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        fileInput.click();
      }
    });
    ['dragenter','dragover'].forEach(ev => drop.addEventListener(ev, e => {
      e.preventDefault(); drop.classList.add('drag');
    }));
    ['dragleave','drop'].forEach(ev => drop.addEventListener(ev, e => {
      e.preventDefault(); drop.classList.remove('drag');
    }));
    drop.addEventListener('drop', e => {
      const f = e.dataTransfer.files && e.dataTransfer.files[0];
      if (f) setFile(f);
    });

    go.addEventListener('click', async () => {
      if (!jsonText) return;
      showError('');
      go.disabled = true;
      status.textContent = 'Generating PDF… this can take a few seconds';
      try {
        const res = await fetch('/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: jsonText,
        });
        if (!res.ok) {
          const msg = await res.text();
          throw new Error(msg || ('HTTP ' + res.status));
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = suggestedName;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        status.textContent = 'Done — PDF downloaded.';
      } catch (e) {
        showError(String(e.message || e));
        status.textContent = '';
      } finally {
        go.disabled = !jsonText;
      }
    });
  </script>
</body>
</html>
"""



def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", (name or "report").strip()) or "report"
    return f"BIO-AI-report-{cleaned}.pdf"


class PdfUiHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:  # quieter console
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/", "/index.html"}:
            body = _PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404, "Not found")

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/generate":
            self.send_error(404, "Not found")
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
            report = BioReport.model_validate(data)
            patient = report.patient
            variant = resolve_gender_variant(patient.gender, patient.sex)
            pdf_bytes = PdfRenderService().render_pdf(report)
            filename = _safe_filename(patient.name or "report")
        except (json.JSONDecodeError, PdfValidationError, PdfRenderDependencyError, PdfRendererError) as exc:
            self._error(400, str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            self._error(500, f"Render failed: {exc}")
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header(
            "Content-Disposition",
            f"attachment; filename=\"{filename}\"; filename*=UTF-8''{quote(filename)}",
        )
        self.send_header("Content-Length", str(len(pdf_bytes)))
        self.send_header("X-Report-Variant", variant)
        self.end_headers()
        self.wfile.write(pdf_bytes)

    def _error(self, code: int, message: str) -> None:
        body = message.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    server = ThreadingHTTPServer((HOST, PORT), PdfUiHandler)
    print(f"Bio-AI PDF UI: http://{HOST}:{PORT}/")
    print("Drop a BioReport JSON → Generate PDF (gender from JSON). Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
