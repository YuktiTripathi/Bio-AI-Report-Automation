"""PDF renderer configuration and gender-variant disease/test catalogs."""

from __future__ import annotations

from pathlib import Path

from modules.bioai_report.report_engine import config as engine_config

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"
MAPPING_DIR = PACKAGE_DIR / "mapping"

PDF_TEMPLATE_VERSION = engine_config.PDF_TEMPLATE_VERSION

DISEASE_ORDER_MALE: tuple[str, ...] = (
    "metabolic_syndrome",
    "dyslipidemia",
    "cardiac_health",
    "oxidative_stress",
    "nafld",
    "hypertension",
    "obesity",
    "thyroid_health",
    "type2_diabetes",
)

# Figma female At A Glance (451:2): 10 diseases incl. metabolic_syndrome + pcos_pcod.
DISEASE_ORDER_FEMALE: tuple[str, ...] = (
    "metabolic_syndrome",
    "dyslipidemia",
    "cardiac_health",
    "oxidative_stress",
    "nafld",
    "hypertension",
    "obesity",
    "thyroid_health",
    "type2_diabetes",
    "pcos_pcod",
)

# Matches Figma Lifestyle Diseases Covered timeline (node 451:5615).
INDEX_ORDER_MALE: tuple[str, ...] = (
    "metabolic_syndrome",
    "dyslipidemia",
    "cardiac_health",
    "oxidative_stress",
    "nafld",
    "hypertension",
    "obesity",
    "thyroid_health",
    "type2_diabetes",
)

INDEX_ORDER_FEMALE: tuple[str, ...] = (
    "metabolic_syndrome",
    "dyslipidemia",
    "cardiac_health",
    "oxidative_stress",
    "nafld",
    "hypertension",
    "obesity",
    "thyroid_health",
    "type2_diabetes",
    "pcos_pcod",
)

DISEASE_DISPLAY_NAMES: dict[str, str] = {
    "nafld": "NAFLD (Non-Alcoholic Fatty Liver Disease)",
    "metabolic_syndrome": "Metabolic Syndrome",
    "cardiac_health": "Cardiac Health",
    "obesity": "Obesity",
    "oxidative_stress": "Oxidative Stress",
    "thyroid_health": "Thyroid Health",
    "dyslipidemia": "Dyslipidemia",
    "hypertension": "Hypertension",
    "type2_diabetes": "Type 2 Diabetes",
    "pcos_pcod": "PCOS / PCOD",
}

# Static lab catalogs from sample PDFs (gender variants).
TESTS_COVERED_MALE_PAGE1: dict[str, list[str]] = {
    "Complete Haemogram": [
        "Absolute Basophils Count",
        "Absolute Eosinophils Count",
        "Absolute Lymphocyte Count",
        "Absolute Monocyte Count",
        "Absolute Neutrophil Count",
        "ESR Automated",
        "Hemoglobin Hb",
        "MCH",
        "MCHC",
        "MCV",
        "MPV Mean Platelet Count",
        "PCV Hematocrit",
        "Platelet Count",
        "WBC",
        "RDW",
        "Neutrophils",
        "Eosinophils",
        "Lymphocytes",
        "Monocytes",
        "Basophils",
        "RDW-CV",
        "MENTZER INDEX",
        "Red blood cells",
        "GK Index",
        "RDWI",
    ],
    "Kidney Function": [
        "Urea",
        "Creatinine",
        "Uric Acid",
        "Creatinine eGFR",
        "BUN Urea Nitrogen",
        "Calcium Total",
        "BUN/Creatinine Ratio",
        "Urea/Creatinine Ratio",
    ],
    "Hormonal Tests": ["Total Testosterone level"],
    "Lipid Profile": [
        "Total Cholesterol",
        "HDL Cholesterol Direct",
        "LDL Cholesterol Calculated",
        "Triglycerides",
        "Non HDL Cholesterol",
        "CHOL/HDL Ratio",
        "VLDL Cholesterol",
        "LDL/HDL Cholesterol",
        "HDL/LDL Cholesterol Ratio",
    ],
    "Liver Function Tests": [
        "Albumin",
        "Alkaline Phosphatase",
        "Total Bilirubin",
        "Direct Bilirubin",
        "Indirect Bilirubin",
        "GGTP",
        "Proteins Serum",
        "SGOT (AST)",
        "SGPT (ALT)",
        "A/G Ratio",
        "Globulin",
        "SGOT/SGPT Ratio",
    ],
    "Vitamins": ["Vitamin D Total-25 Hydroxy", "Vitamin B12"],
    "Iron Profile": [
        "Iron",
        "TIBC (Total Iron Binding Capacity)",
        "Transferrin saturation",
        "UBIC",
    ],
}

TESTS_COVERED_MALE_PAGE2: dict[str, list[str]] = {
    "Inflammatory Markers": [
        "Homocysteine",
        "ESR - Erythrocyte Sedimentation Rate",
        "HS - CRP",
    ],
    "Diabetes Profile": ["HbA1C", "Fasting sugar"],
    "Urine Routine & Microscopy": [
        "Ph Urine",
        "Urobilinogen",
        "Colour",
        "Transparency",
        "Sugar",
        "Blood(Urine)",
        "RBC",
        "Pus Cells",
        "Epithelial Cells",
        "Crystals",
        "Cast",
        "Bacteria",
        "Yeast Cells",
        "Nitrate",
        "Urine Ketone",
        "Urine Protein",
        "Bile Pigments",
    ],
    "Thyroid Profile": [
        "Tri-iodothyronine (T3)",
        "Thyroxine (T4)",
        "TSH-Ultrasensitive",
    ],
}

TESTS_COVERED_FEMALE_PAGE1: dict[str, list[str]] = {
    "Complete Haemogram": TESTS_COVERED_MALE_PAGE1["Complete Haemogram"],
    "Kidney Function with K": [
        "Urea",
        "Creatinine",
        "Uric Acid",
        "Creatinine eGFR",
        "BUN Urea Nitrogen",
        "Calcium Total",
        "Chlorides",
        "BUN/Creatinine Ratio",
        "Sodium",
        "Potassium",
        "Urea/Creatinine Ratio",
        "Phosphorus Inorganic",
    ],
    "Lipid Profile": TESTS_COVERED_MALE_PAGE1["Lipid Profile"],
    "Liver Function Tests": TESTS_COVERED_MALE_PAGE1["Liver Function Tests"],
    "Vitamins": TESTS_COVERED_MALE_PAGE1["Vitamins"],
    "Iron Profile": TESTS_COVERED_MALE_PAGE1["Iron Profile"],
    "Sleep Markers": ["Magnesium", "Zinc"],
}

TESTS_COVERED_FEMALE_PAGE2: dict[str, list[str]] = {
    "Inflammatory Markers": TESTS_COVERED_MALE_PAGE2["Inflammatory Markers"],
    "Hormonal Tests": [
        "Total Testosterone level",
        "LH",
        "FSH",
        "Prolactin",
        "Cortisol",
    ],
    "Diabetes Profile": ["HbA1C", "Fasting sugar", "Fasting Insulin"],
    "Urine Routine & Microscopy": TESTS_COVERED_MALE_PAGE2["Urine Routine & Microscopy"],
    "Thyroid Profile": TESTS_COVERED_MALE_PAGE2["Thyroid Profile"],
}

RISK_BANDS: tuple[tuple[str, int, int, str], ...] = (
    ("Healthy", 0, 25, "#2ecc71"),
    ("Increased Risk", 26, 50, "#f1c40f"),
    ("High Risk", 51, 75, "#e67e22"),
    ("Very High Risk", 76, 100, "#e74c3c"),
)

LIFESTYLE_METER_LEVELS: tuple[str, ...] = (
    "LOW",
    "MODERATE",
    "INCREASED",
    "HIGH",
    "VERY HIGH",
)
