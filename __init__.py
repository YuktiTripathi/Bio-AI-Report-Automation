"""Bio-AI Report Automation — BioReport JSON → PDF → permanent link."""

from modules.bioai_report.pdf_renderer.service import PdfRenderService, render_bioreport_pdf
from modules.bioai_report.report_engine.models.report import BioReport

__all__ = ["BioReport", "PdfRenderService", "render_bioreport_pdf"]
