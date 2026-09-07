"""SVG graph helpers for PDF score / percentile visuals."""

from __future__ import annotations

import base64
import math
from functools import lru_cache
from pathlib import Path


_DDT_ASSETS = Path(__file__).resolve().parents[1] / "static" / "assets" / "disease_detail"

# Figma gauge center discs (white → band color radial), baked as PNG for PDF.
_GAUGE_CENTER_PNG = {
    "Healthy": "gauge_center_healthy.png",
    "Increased Risk": "gauge_center_increased.png",
    "High Risk": "gauge_center_high.png",
    "Very High Risk": "gauge_center_very_high.png",
}


@lru_cache(maxsize=8)
def _gauge_center_data_uri(risk_label: str) -> str:
    name = _GAUGE_CENTER_PNG.get(risk_label, "gauge_center_healthy.png")
    path = _DDT_ASSETS / name
    if not path.is_file():
        # Fallback: solid SVG circle color handled by caller
        return ""
    b64 = base64.standard_b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def score_ring_svg(score: float | int | str, *, color: str = "#0b6e4f", size: int = 180) -> str:
    """Circular progress ring for metabolic / disease scores (0–100)."""
    try:
        value = max(0.0, min(100.0, float(score)))
    except (TypeError, ValueError):
        value = 0.0
    radius = 70
    circumference = 2 * math.pi * radius
    offset = circumference * (1 - value / 100.0)
    label = str(int(round(value))) if float(value).is_integer() else f"{value:.1f}"
    return f"""
<svg width="{size}" height="{size}" viewBox="0 0 180 180" role="img" aria-label="Score {label} out of 100">
  <circle cx="90" cy="90" r="{radius}" fill="none" stroke="#e6ebf0" stroke-width="14"/>
  <circle cx="90" cy="90" r="{radius}" fill="none" stroke="{color}" stroke-width="14"
          stroke-linecap="round"
          stroke-dasharray="{circumference:.2f}"
          stroke-dashoffset="{offset:.2f}"
          transform="rotate(-90 90 90)"/>
  <text x="90" y="86" text-anchor="middle" font-size="36" font-weight="800" fill="#1a2332">{label}</text>
  <text x="90" y="112" text-anchor="middle" font-size="14" fill="#6b778c">/ 100</text>
</svg>
""".strip()


def percentile_marker_pct(percentile: float | int | None) -> float:
    if percentile is None:
        return 0.0
    try:
        return max(0.0, min(100.0, float(percentile)))
    except (TypeError, ValueError):
        return 0.0


# Inner disc radial end-stops (Figma 451:4669 healthy → #309D69, 451:4816 increased → #F8D232)
_GAUGE_CENTER_FILLS = {
    "Healthy": "#309D69",
    "Increased Risk": "#F8D232",
    "High Risk": "#EAA546",
    "Very High Risk": "#C6203B",
}


def disease_score_gauge_svg(
    score: float | int | str,
    *,
    color: str = "#063533",
    fill_color: str | None = None,
    risk_label: str | None = None,
    size: int = 110,
) -> str:
    """Figma-style disease score gauge (451:4652 / 451:4799) — layered disc + ring + score /100."""
    try:
        value = max(0.0, min(100.0, float(score)))
    except (TypeError, ValueError):
        value = 0.0
    cx = cy = 55.0
    # Progress track sits between outer shell and center disc (≈81px / 109 ≈ r 40.5)
    radius = 40.5
    stroke_w = 7.4
    circumference = 2 * math.pi * radius
    offset = circumference * (1 - value / 100.0)
    label = str(int(round(value))) if float(value).is_integer() else f"{value:.1f}"
    center_fill = fill_color or _GAUGE_CENTER_FILLS.get(risk_label or "", color)
    center_uri = _gauge_center_data_uri(risk_label or "")
    # End-cap angle for the progress tip (12 o'clock → clockwise)
    tip_svg = ""
    if value > 0:
        tip_angle = -math.pi / 2 + (2 * math.pi * value / 100.0)
        tip_x = cx + radius * math.cos(tip_angle)
        tip_y = cy + radius * math.sin(tip_angle)
        tip_svg = (
            f'<circle cx="{tip_x:.3f}" cy="{tip_y:.3f}" r="3.2" fill="{color}"/>'
        )
    # Prefer baked PNG radial (PDF-safe). Solid fill is the fallback only.
    if center_uri:
        center_svg = (
            f'<image href="{center_uri}" xlink:href="{center_uri}" '
            f'x="{cx - 33.5:.3f}" y="{cy - 33.5:.3f}" width="67" height="67" '
            f'preserveAspectRatio="xMidYMid meet"/>'
        )
    else:
        center_svg = f'<circle cx="{cx}" cy="{cy}" r="33.5" fill="{center_fill}"/>'
    return f"""
<svg width="{size}" height="{size}" viewBox="0 0 110 110" role="img" aria-label="Score {label} out of 100"
     xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
  <!-- Outer shell (Figma #F5F5F5) -->
  <circle cx="{cx}" cy="{cy}" r="52" fill="#F5F5F5"/>
  <!-- Mid white disc -->
  <circle cx="{cx}" cy="{cy}" r="48.3" fill="#ffffff"/>
  <!-- Track + progress (butt caps match Figma) -->
  <circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="#E0E0E0" stroke-width="{stroke_w}"/>
  <circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="{color}" stroke-width="{stroke_w}"
          stroke-linecap="butt"
          stroke-dasharray="{circumference:.3f}"
          stroke-dashoffset="{offset:.3f}"
          transform="rotate(-90 {cx} {cy})"/>
  {tip_svg}
  <!-- Center fill (Figma radial white→band); PNG avoids PDF gradient banding -->
  {center_svg}
  <!-- Score typography: Inter Bold 28 / Regular 12, Figma tops ≈31.6 / 63.5 -->
  <text x="{cx}" y="54" text-anchor="middle"
        font-family="Inter, Helvetica, Arial, sans-serif"
        font-size="28" font-weight="700" fill="#063533">{label}</text>
  <text x="{cx}" y="72" text-anchor="middle"
        font-family="Inter, Helvetica, Arial, sans-serif"
        font-size="12" font-weight="400" fill="#000000">/100</text>
</svg>
""".strip()


# Figma Health Trends 373:97792 — band fills use 50% opacity over dark card.
_TREND_BANDS = (
    (0, 25, "#12673F"),    # Healthy
    (25, 50, "#F8D232"),   # Increased Risk
    (50, 75, "#FC943A"),   # High Risk
    (75, 100, "#CC203B"),  # Very High Risk
)
_TREND_BAND_OPACITY = 0.5

# Dot fill matches risk band (Figma ellipses 373:97823 / 373:978xx).
_TREND_DOT_COLORS = (
    (25, "#12673F"),
    (50, "#F8D232"),
    (75, "#FC943A"),
    (100, "#CC203B"),
)


def _trend_dot_color(score: float) -> str:
    s = max(0.0, min(100.0, float(score)))
    for hi, color in _TREND_DOT_COLORS:
        if s <= hi:
            return color
    return _TREND_DOT_COLORS[-1][1]


def trend_line_chart_svg(
    points: list[tuple[str, float]],
    *,
    width: int = 236,
    height: int = 102,
) -> str:
    """Risk-score line chart matching Figma Health Trends cards (373:97792)."""
    if not points:
        points = [("—", 0.0)]

    # Layout mirrors Figma widget: y-labels | plot (204×67) | date labels under guides.
    pad_l, pad_r, pad_t, pad_b = 28, 6, 4, 16
    plot_w = max(1.0, width - pad_l - pad_r)
    plot_h = max(1.0, height - pad_t - pad_b)

    def y_for(score: float) -> float:
        s = max(0.0, min(100.0, float(score)))
        return pad_t + plot_h * (1.0 - s / 100.0)

    n = len(points)
    # Inset points slightly from plot edges (Figma years column px-[24px]).
    inset = min(24.0, plot_w * 0.12)
    xs: list[float] = []
    for i in range(n):
        if n == 1:
            xs.append(pad_l + plot_w / 2)
        else:
            xs.append(pad_l + inset + ((plot_w - 2 * inset) * i / (n - 1)))

    band_rects = []
    for lo, hi, color in _TREND_BANDS:
        y_top = y_for(hi)
        y_bot = y_for(lo)
        band_rects.append(
            f'<rect x="{pad_l:.1f}" y="{y_top:.1f}" width="{plot_w:.1f}" '
            f'height="{max(0.5, y_bot - y_top):.1f}" fill="{color}" '
            f'fill-opacity="{_TREND_BAND_OPACITY}"/>'
        )

    grid_labels = []
    for score in (100, 75, 50, 25, 0):
        y = y_for(score)
        grid_labels.append(
            f'<text x="{pad_l - 5:.1f}" y="{y + 2.2:.1f}" text-anchor="end" '
            f'font-family="Inter, Helvetica, Arial, sans-serif" font-size="6.3" '
            f'font-weight="500" fill="#ffffff" letter-spacing="-0.16">{score}</text>'
        )
        if score in (0, 100):
            grid_labels.append(
                f'<line x1="{pad_l:.1f}" y1="{y:.1f}" x2="{pad_l + plot_w:.1f}" '
                f'y2="{y:.1f}" stroke="#ffffff" stroke-opacity="0.35" stroke-width="0.55"/>'
            )

    poly = " ".join(f"{xs[i]:.1f},{y_for(points[i][1]):.1f}" for i in range(n))
    dots = []
    date_labels = []
    for i, (label, score) in enumerate(points):
        x, y = xs[i], y_for(score)
        # Vertical guide from top of plot through the point to baseline.
        dots.append(
            f'<line x1="{x:.1f}" y1="{pad_t:.1f}" x2="{x:.1f}" y2="{pad_t + plot_h:.1f}" '
            f'stroke="#ffffff" stroke-opacity="0.45" stroke-width="0.7" stroke-linecap="round"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.1" fill="{_trend_dot_color(score)}"/>'
        )
        date_labels.append(
            f'<text x="{x:.1f}" y="{height - 2:.1f}" text-anchor="middle" '
            f'font-family="Inter, Helvetica, Arial, sans-serif" font-size="6.3" '
            f'font-weight="500" fill="#ffffff" letter-spacing="-0.16">{label}</text>'
        )

    risk_cy = pad_t + plot_h / 2
    risk_label = (
        f'<text x="8" y="{risk_cy:.1f}" text-anchor="middle" '
        f'font-family="Inter, Helvetica, Arial, sans-serif" font-size="6.3" '
        f'font-weight="500" fill="#ffffff" letter-spacing="-0.16" '
        f'transform="rotate(-90 8 {risk_cy:.1f})">Risk Scores</text>'
    )

    return f"""
<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}"
     xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Health trend chart">
  {''.join(band_rects)}
  {''.join(grid_labels)}
  {risk_label}
  <polyline fill="none" stroke="#ffffff" stroke-opacity="0.5" stroke-width="0.7"
            stroke-linejoin="round" stroke-linecap="round" points="{poly}"/>
  {''.join(dots)}
  {''.join(date_labels)}
</svg>
""".strip()
