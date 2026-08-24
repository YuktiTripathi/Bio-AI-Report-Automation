"""Shared limits and version labels used by the PDF view-model.

Content assembly lives in the upstream backend; this package only validates
and renders finished BioReport JSON.
"""

from __future__ import annotations

# --- Display limits (PDF view-model truncation) ---
TOP_LIFESTYLE_TIPS = 3
TOP_DIET_TIPS = 3
TOP_FOODS = 5
TOP_EXERCISE = 3
TOP_MONITORING = 2
TOP_ACTIONABLE_INSIGHTS = 5
TOP_STRENGTHS = 3
TOP_RISKS = 3
TOP_INSIGHTS_PER_RISK = 4
TOP_CONTRIBUTING_FACTORS = 3

# --- Version metadata ---
ENGINE_VERSION = "1.0.0"
TEMPLATE_VERSION = "1.0.0"
PDF_TEMPLATE_VERSION = "1.0.0"
