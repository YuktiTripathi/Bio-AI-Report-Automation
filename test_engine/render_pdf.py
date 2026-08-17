#!/usr/bin/env python3
"""Offline BioReport JSON → HTML PDF renderer.

Usage (from repo root):
    PYTHONPATH=. python test_engine/render_pdf.py test_engine/output_report_user1.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from modules.bioai_report.pdf_renderer.service import PdfRenderService  # noqa: E402
from modules.bioai_report.report_engine.models.report import BioReport  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render BioReport JSON to PDF")
    parser.add_argument("bioreport_json", help="Path to BioReport JSON")
    parser.add_argument(
        "-o",
        "--output",
        help="Output PDF path (default: output_<name>.pdf beside input)",
    )
    parser.add_argument(
        "--html-only",
        action="store_true",
        help="Write HTML instead of PDF (no Playwright required)",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.bioreport_json).expanduser()
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path
    if not input_path.is_file():
        print(f"Input not found: {input_path}", file=sys.stderr)
        return 1

    report = BioReport.model_validate(json.loads(input_path.read_text(encoding="utf-8")))
    service = PdfRenderService()

    if args.html_only:
        output = Path(args.output) if args.output else input_path.with_suffix(".html")
        output.write_text(service.build_html(report), encoding="utf-8")
        print(f"HTML written: {output.resolve()}")
        return 0

    output = Path(args.output) if args.output else input_path.with_name(
        f"output_{input_path.stem}.pdf" if not input_path.name.startswith("output_")
        else f"{input_path.stem}.pdf"
    )
    if not output.is_absolute():
        output = Path.cwd() / output
    service.write_pdf(report, output)
    print(f"PDF written: {output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
