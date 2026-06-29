"""Project configuration for the Victoria air-quality analysis workflow."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
FIGURES_DIR = PROJECT_ROOT / "figures"
REPORT_DIR = PROJECT_ROOT / "report"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

AIR_XLSX = RAW_DIR / "2024_All_sites_air_quality_hourly_avg_AIR-I-F-V-VH-O-S1-DB-M2-4-0.xlsx"
SEIFA_XLSX = RAW_DIR / "seifa_2021_sa2.xlsx"
SA2_SHP = RAW_DIR / "SA2_2021" / "SA2_2021_AUST_GDA2020.shp"

TARGET_POLLUTANTS = ["PM2.5", "PM10", "NO2", "O3", "SO2", "CO"]
SPATIAL_POLLUTANTS = ["PM2.5", "PM10", "NO2", "O3"]

NEPM_THRESHOLDS = {
    "PM2.5": 25,
    "PM10": 50,
    "NO2": 80,
    "O3": 100,
    "SO2": 100,
    "CO": 9,
}

DATA_SOURCES = {
    "EPA Victoria AirWatch hourly air quality data": {
        "url": "https://discover.data.vic.gov.au/dataset/epa-air-watch-all-sites-air-quality-hourly-averages-yearly",
        "local_file": AIR_XLSX,
    },
    "ABS SEIFA 2021 SA2 indexes": {
        "url": "https://www.abs.gov.au/statistics/people/people-and-communities/socio-economic-indexes-areas-seifa-australia/2021",
        "local_file": SEIFA_XLSX,
    },
    "ABS ASGS Edition 3 SA2 digital boundaries": {
        "url": "https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/access-and-downloads/digital-boundary-files",
        "local_file": SA2_SHP,
    },
}


def ensure_output_dirs() -> None:
    """Create generated-output folders if they do not exist."""
    for path in (PROCESSED_DIR, FIGURES_DIR, REPORT_DIR, OUTPUTS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def require_raw_inputs() -> None:
    """Raise a clear error if any expected raw input is missing."""
    missing = [
        str(v["local_file"].relative_to(PROJECT_ROOT))
        for v in DATA_SOURCES.values()
        if not v["local_file"].exists()
    ]
    if missing:
        bullet_list = "\n".join(f"- {p}" for p in missing)
        raise FileNotFoundError(
            "Missing required raw data files. Place the downloaded files at:\n"
            f"{bullet_list}\n"
            "See data/README.md for the official source pages."
        )
