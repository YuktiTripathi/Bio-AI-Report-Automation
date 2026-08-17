"""HTML → PDF renderer for BioReport (Figma-first templates)."""

from modules.bioai_report.pdf_renderer.service import PdfRenderService, render_bioreport_pdf

__all__ = ["PdfRenderService", "render_bioreport_pdf"]
