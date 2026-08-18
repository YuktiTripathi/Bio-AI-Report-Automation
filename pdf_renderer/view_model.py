"""Build a validated PDF view-model from BioReport (gender-aware, disease_id keyed)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from modules.bioai_report.pdf_renderer import config as pdf_config
from modules.bioai_report.pdf_renderer.exceptions import PdfValidationError
from modules.bioai_report.report_engine import config as engine_config
from modules.bioai_report.report_engine.models.report import BioReport, DiseaseSection


def _blank(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, str) and not value.strip():
        return "—"
    return str(value)


def _format_age(age: float | int | None) -> str:
    if age is None:
        return "—"
    if isinstance(age, float) and age.is_integer():
        return f"{int(age)} years"
    return f"{age} years"


def _format_assessment_date(raw: str | None) -> str:
    if not raw or not str(raw).strip():
        return "—"
    text = str(raw).strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
    ):
        try:
            normalized = text.replace("Z", "+0000")
            if fmt.endswith("%z") and ":" == normalized[-3:-2]:
                normalized = normalized[:-3] + normalized[-2:]
            dt = datetime.strptime(normalized, fmt)
            return dt.strftime("%b %d, %Y")
        except ValueError:
            continue
    return text


def resolve_gender_variant(gender: str | None, sex: str | None) -> str:
    raw = (gender or sex or "").strip().lower()
    if raw in {"female", "f", "woman", "2"}:
        return "female"
    return "male"


def honorific_for_variant(variant: str) -> str:
    return "Ms." if variant == "female" else "Mr."


def disease_order_for_variant(variant: str) -> tuple[str, ...]:
    return (
        pdf_config.DISEASE_ORDER_FEMALE
        if variant == "female"
        else pdf_config.DISEASE_ORDER_MALE
    )


def index_order_for_variant(variant: str) -> tuple[str, ...]:
    return (
        pdf_config.INDEX_ORDER_FEMALE
        if variant == "female"
        else pdf_config.INDEX_ORDER_MALE
    )


def risk_color(risk: str | None, score: int | None = None) -> str:
    label = (risk or "").strip().lower()
    mapping = {
        "healthy": "#2ecc71",
        "increased": "#f1c40f",
        "increased risk": "#f1c40f",
        "high": "#e67e22",
        "high risk": "#e67e22",
        "very high": "#e74c3c",
        "very high risk": "#e74c3c",
    }
    if label in mapping:
        return mapping[label]
    if score is None:
        return "#95a5a6"
    for name, lo, hi, color in pdf_config.RISK_BANDS:
        if lo <= int(score) <= hi:
            return color
    return "#95a5a6"


def lifestyle_meter_index(value: float | int | None) -> int | None:
    """Map lifestyle_contribution to a 0–4 meter index; None if unknown."""
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return 0
    if number <= 25:
        return 1
    if number <= 50:
        return 2
    if number <= 75:
        return 3
    return 4


def _ordinal(n: float | int | None) -> str:
    if n is None:
        return "—"
    value = int(round(float(n)))
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


@dataclass
class DiseaseCardVM:
    disease_id: str
    title: str
    overview: str
    score: int
    risk: str
    band: str
    percentile: float | int | None
    percentile_label: str
    lifestyle_contribution: float | int | None
    lifestyle_meter_index: int | None
    contributing_factors: list[str]
    risk_color: str
    insights: list[str] = field(default_factory=list)


@dataclass
class PdfViewModel:
    variant: str
    honorific: str
    page_count: int
    disease_page_range: str
    patient_name: str
    patient_age: str
    patient_gender: str
    assessment_date: str
    metabolic_score: str
    metabolic_age: str
    overall_status: str
    bmi: str
    height: str
    weight: str
    record_id: str
    index_diseases: list[dict[str, Any]]
    glance_diseases: list[DiseaseCardVM]
    top_risks: list[DiseaseCardVM]
    disease_pages: list[DiseaseCardVM]
    tests_page1: dict[str, list[str]]
    tests_page2: dict[str, list[str]]
    template_version: str
    engine_version: str
    generated_at: str | None
    risk_bands: list[dict[str, Any]] = field(default_factory=list)
    lifestyle_levels: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return payload


def canonicalize_disease_id(disease_id: str) -> str:
    """Map upstream aliases (e.g. pcos) to PDF catalog ids (pcos_pcod)."""
    return pdf_config.DISEASE_ID_ALIASES.get(disease_id, disease_id)


def _section_map(report: BioReport) -> dict[str, DiseaseSection]:
    return {
        canonicalize_disease_id(section.disease_id): section
        for section in report.disease_sections
    }


def _card_from_section(
    section: DiseaseSection,
    *,
    disease_id: str | None = None,
    insights: list[str] | None = None,
) -> DiseaseCardVM:
    score = int(section.current_status.score)
    canonical_id = disease_id or canonicalize_disease_id(section.disease_id)
    title = pdf_config.DISEASE_DISPLAY_NAMES.get(canonical_id) or section.title
    return DiseaseCardVM(
        disease_id=canonical_id,
        title=title,
        overview=section.overview or "",
        score=score,
        risk=section.current_status.risk,
        band=section.current_status.band,
        percentile=section.current_status.percentile,
        percentile_label=_ordinal(section.current_status.percentile),
        lifestyle_contribution=section.current_status.lifestyle_contribution,
        lifestyle_meter_index=lifestyle_meter_index(
            section.current_status.lifestyle_contribution
        ),
        contributing_factors=list(section.contributing_factors or []),
        risk_color=risk_color(section.current_status.risk, score),
        insights=list(insights or []),
    )


def validate_view_model(report: BioReport, vm: PdfViewModel) -> None:
    """Hard gate — raise if rendered values would disagree with BioReport JSON."""
    errors: list[str] = []
    by_id = _section_map(report)

    expected_variant = resolve_gender_variant(report.patient.gender, report.patient.sex)
    if vm.variant != expected_variant:
        errors.append(
            f"gender variant mismatch: view={vm.variant} patient={expected_variant}"
        )

    if len(vm.disease_pages) != len(
        [d for d in disease_order_for_variant(vm.variant) if d in by_id]
    ):
        errors.append(
            f"disease page count mismatch: rendered={len(vm.disease_pages)} "
            f"available_for_variant={len([d for d in disease_order_for_variant(vm.variant) if d in by_id])}"
        )

    seen_tips: dict[str, set[str]] = {}
    for page in vm.disease_pages:
        source = by_id.get(page.disease_id)
        if source is None:
            errors.append(f"unknown disease_id on page: {page.disease_id}")
            continue
        if page.score != int(source.current_status.score):
            errors.append(
                f"{page.disease_id}: score {page.score} != json {source.current_status.score}"
            )
        if page.title != source.title:
            display = pdf_config.DISEASE_DISPLAY_NAMES.get(page.disease_id)
            if display is None or page.title != display:
                errors.append(f"{page.disease_id}: title mismatch")
        if page.risk != source.current_status.risk:
            errors.append(f"{page.disease_id}: risk mismatch")
        tip_set = set(page.insights)
        for other_id, other_tips in seen_tips.items():
            leaked = tip_set & other_tips
            # Only flag if tip exists solely on another disease in JSON and not this one.
            if not leaked:
                continue
            source_tips = set(
                list(source.lifestyle.tips)
                + list(source.nutrition.recommendations)
                + list(source.lifestyle.exercise)
            )
            foreign = leaked - source_tips
            if foreign:
                errors.append(
                    f"cross-disease tip leakage on {page.disease_id} from {other_id}: {sorted(foreign)[:2]}"
                )
        seen_tips[page.disease_id] = tip_set

    for risk in vm.top_risks:
        source = by_id.get(risk.disease_id)
        if source is None:
            errors.append(f"top risk unknown disease_id: {risk.disease_id}")
            continue
        if risk.score != int(source.current_status.score):
            errors.append(f"top risk {risk.disease_id}: score mismatch")
        for tip in risk.insights:
            allowed = set(
                list(source.lifestyle.tips)
                + list(source.nutrition.recommendations)
                + list(source.lifestyle.exercise)
            )
            if tip not in allowed:
                errors.append(
                    f"top risk {risk.disease_id}: insight not from disease arrays: {tip!r}"
                )

    if "pcos_pcod" in {p.disease_id for p in vm.disease_pages} and vm.variant == "male":
        errors.append("male variant must not render pcos_pcod")

    if errors:
        raise PdfValidationError("; ".join(errors))


def build_pdf_view_model(report: BioReport) -> PdfViewModel:
    """Assemble gender-aware PDF view-model and validate against BioReport."""
    patient = report.patient
    variant = resolve_gender_variant(patient.gender, patient.sex)
    by_id = _section_map(report)
    order = disease_order_for_variant(variant)
    index_order = index_order_for_variant(variant)

    disease_pages = [
        _card_from_section(by_id[disease_id], disease_id=disease_id)
        for disease_id in order
        if disease_id in by_id
    ]

    glance = list(disease_pages)

    # Catalog page lists the variant's full covered set (Figma timeline), not only scored ones.
    index_diseases: list[dict[str, Any]] = []
    for disease_id in index_order:
        title = pdf_config.DISEASE_DISPLAY_NAMES.get(disease_id)
        if title is None and disease_id in by_id:
            title = by_id[disease_id].title
        if not title:
            continue
        index_diseases.append({"disease_id": disease_id, "title": title})

    allowed_ids = set(order)
    top_risks: list[DiseaseCardVM] = []
    for highlight in report.executive_summary.top_disease_risks:
        highlight_id = canonicalize_disease_id(highlight.disease_id)
        if highlight_id not in allowed_ids:
            continue
        section = by_id.get(highlight_id)
        if section is None:
            continue
        insights = list(highlight.insights) if highlight.insights else []
        if not insights:
            insights = list(
                list(section.lifestyle.tips)
                + list(section.nutrition.recommendations)
                + list(section.lifestyle.exercise)
            )[: engine_config.TOP_INSIGHTS_PER_RISK]
        card = _card_from_section(section, disease_id=highlight_id, insights=insights)
        # Prefer highlight percentile when present.
        if highlight.percentile is not None:
            card.percentile = highlight.percentile
            card.percentile_label = _ordinal(highlight.percentile)
        top_risks.append(card)

    gender_label = (patient.gender or patient.sex or "—").strip()
    if gender_label and gender_label != "—":
        gender_label = gender_label[:1].upper() + gender_label[1:].lower()

    # Front matter: cover, welcome, TOC, index, health, glance, risks, divider (8),
    # then disease details, then back cover. (Tests Covered + Risk Overview removed.)
    page_count = 8 + len(disease_pages) + 1
    disease_start = 9
    disease_end = 8 + len(disease_pages)

    if variant == "female":
        tests1 = pdf_config.TESTS_COVERED_FEMALE_PAGE1
        tests2 = pdf_config.TESTS_COVERED_FEMALE_PAGE2
    else:
        tests1 = pdf_config.TESTS_COVERED_MALE_PAGE1
        tests2 = pdf_config.TESTS_COVERED_MALE_PAGE2

    vm = PdfViewModel(
        variant=variant,
        honorific=honorific_for_variant(variant),
        page_count=page_count,
        disease_page_range=f"{disease_start}-{disease_end}",
        patient_name=_blank(patient.name),
        patient_age=_format_age(patient.age),
        patient_gender=_blank(gender_label),
        assessment_date=_format_assessment_date(patient.assessment_date),
        metabolic_score=_blank(patient.metabolic_score),
        metabolic_age=_blank(patient.metabolic_age),
        overall_status=_blank(patient.metabolic_health_status),
        bmi=_blank(patient.bmi),
        height=_blank(patient.height),
        weight=_blank(patient.weight),
        record_id=_blank(report.report_metadata.record_id or patient.record_id),
        index_diseases=index_diseases,
        glance_diseases=glance,
        top_risks=top_risks,
        disease_pages=disease_pages,
        tests_page1=tests1,
        tests_page2=tests2,
        template_version=pdf_config.PDF_TEMPLATE_VERSION,
        engine_version=report.report_metadata.engine_version,
        generated_at=report.report_metadata.generated_at,
        risk_bands=[
            {"label": name, "lo": lo, "hi": hi, "color": color}
            for name, lo, hi, color in pdf_config.RISK_BANDS
        ],
        lifestyle_levels=list(pdf_config.LIFESTYLE_METER_LEVELS),
    )
    validate_view_model(report, vm)
    return vm
