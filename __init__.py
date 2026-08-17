"""Bio-AI report content engine — assessment → BioReport JSON → HTML PDF."""

from modules.bioai_report.pdf_renderer.service import PdfRenderService, render_bioreport_pdf
from modules.bioai_report.report_engine.builders.report_builder import build_bioreport
from modules.bioai_report.report_engine.models.report import BioReport

__all__ = ["BioReport", "build_bioreport", "PdfRenderService", "render_bioreport_pdf"]
