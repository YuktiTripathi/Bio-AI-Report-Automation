# Bio-AI PDF Renderer

Figma-first HTML → PDF pipeline for BioReport JSON.

## Layout source

- Slot inventory: `mapping/slot_inventory.yaml` (from `BIO-AI-report-M.pdf` / `BIO-AI-report-F.pdf`)
- Field matrix: `mapping/field_matrix.yaml`
- Replace with live Figma frames when the design file URL is available; keep the same `slot_id` names.

## Pipeline

1. `report_engine` builds BioReport JSON
2. `view_model.py` builds a gender-aware PDF view-model (`male` / `female`)
3. Validation gate blocks mismatched disease scores / tip leakage
4. Jinja HTML templates + SVG graphs render A4 pages
5. Playwright/Chromium prints `application/pdf`

## API

- `GET /bioai-report/content/{record_id}` → BioReport JSON
- `GET /bioai-report/pdf/{record_id}` → PDF download

## Offline render

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-pdf.txt
playwright install chromium

PYTHONPATH=. python test_engine/render_pdf.py test_engine/output_report_user1.json
PYTHONPATH=. python test_engine/render_pdf.py test_engine/output_report_user1.json --html-only
```

## Tests

```bash
PYTHONPATH=. pytest tests/test_pdf_mapping.py -v
```

## Schema extensions for PDF completeness

- `DiseaseSection.contributing_factors[]` — “What could be affecting your results?”
- `DiseaseHighlight.percentile` + `DiseaseHighlight.insights[]` — page 10 per-disease tips
