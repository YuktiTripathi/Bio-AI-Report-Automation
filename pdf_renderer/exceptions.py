"""Errors raised by the PDF renderer."""

from __future__ import annotations


class PdfRendererError(Exception):
    """Base PDF renderer error."""


class PdfValidationError(PdfRendererError):
    """Raised when BioReport → PDF mapping fails validation (blocks unsafe PDF)."""


class PdfRenderDependencyError(PdfRendererError):
    """Raised when Playwright / Chromium is unavailable."""
