"""HTTP routes for BioReport JSON and generated PDF download.

Frontend contracts:

    GET /bioai-report/content/{record_id}  → BioReport JSON
    GET /bioai-report/pdf/{record_id}      → application/pdf download
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from common.responses import success_response
from core.dependencies import get_current_user
from core.exceptions import AppError
from db.session import get_db
from modules.bioai_report.pdf_renderer.exceptions import (
    PdfRenderDependencyError,
    PdfRendererError,
    PdfValidationError,
)
from modules.bioai_report.pdf_renderer.service import PdfRenderService
from modules.bioai_report.report_engine.api.dependencies import (
    get_bioreport_service,
    get_pdf_render_service,
)
from modules.bioai_report.report_engine.exceptions import KnowledgeBaseError, ReportEngineError
from modules.bioai_report.report_engine.services.report_service import BioReportService

router = APIRouter(prefix="/bioai-report", tags=["bioai-report"])


async def _generate_report(
    *,
    record_id: str,
    assessment_type_code: str | None,
    db: AsyncSession,
    report_service: BioReportService,
):
    rid = (record_id or "").strip()
    if not rid:
        raise AppError(status_code=422, error_code="INVALID_STATE", message="record_id is required")

    try:
        return await report_service.generate_for_record(
            record_id=rid,
            assessment_type_code=assessment_type_code,
            db=db,
        )
    except KnowledgeBaseError as exc:
        raise AppError(
            status_code=422,
            error_code="INVALID_STATE",
            message=str(exc),
        ) from exc
    except ReportEngineError as exc:
        raise AppError(
            status_code=500,
            error_code="INTERNAL_ERROR",
            message=str(exc),
        ) from exc
    except ValueError as exc:
        raise AppError(
            status_code=422,
            error_code="INVALID_STATE",
            message=str(exc),
        ) from exc


@router.get("/content/{record_id}")
async def get_bioreport_content(
    record_id: str,
    assessment_type_code: str | None = Query(
        default=None,
        description=(
            "Optional MetSights assessment type code (e.g. 1=Basic, 2=Pro). "
            "Not required from the frontend for normal Bio-AI reports."
        ),
    ),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
    report_service: BioReportService = Depends(get_bioreport_service),
):
    """Return one complete BioReport JSON for ``record_id``."""
    report = await _generate_report(
        record_id=record_id,
        assessment_type_code=assessment_type_code,
        db=db,
        report_service=report_service,
    )
    return success_response(report.to_dict())


@router.get("/pdf/{record_id}")
async def get_bioreport_pdf(
    record_id: str,
    assessment_type_code: str | None = Query(
        default=None,
        description="Optional MetSights assessment type code.",
    ),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
    report_service: BioReportService = Depends(get_bioreport_service),
    pdf_service: PdfRenderService = Depends(get_pdf_render_service),
):
    """Generate and download the Bio-AI HTML PDF for ``record_id``.

    Pipeline:
    1. Assemble BioReport JSON (same as /content)
    2. Build gender-aware PDF view-model + validation gate
    3. Render HTML templates → Chromium PDF bytes
    4. Return ``application/pdf`` attachment
    """
    report = await _generate_report(
        record_id=record_id,
        assessment_type_code=assessment_type_code,
        db=db,
        report_service=report_service,
    )
    rid = (record_id or "").strip()
    try:
        pdf_bytes = await pdf_service.render_pdf_async(report)
    except PdfValidationError as exc:
        raise AppError(
            status_code=422,
            error_code="INVALID_STATE",
            message=f"PDF mapping validation failed: {exc}",
        ) from exc
    except PdfRenderDependencyError as exc:
        raise AppError(
            status_code=503,
            error_code="INTERNAL_ERROR",
            message=str(exc),
        ) from exc
    except PdfRendererError as exc:
        raise AppError(
            status_code=500,
            error_code="INTERNAL_ERROR",
            message=str(exc),
        ) from exc

    filename = f"BioAI_Report_{rid}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
