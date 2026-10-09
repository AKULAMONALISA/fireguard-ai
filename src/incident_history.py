
from pathlib import Path
from datetime import datetime
import csv

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
HISTORY_PATH = RESULTS_DIR / "incident_history.csv"

FIELDS = [
    "timestamp",
    "status",
    "confidence",
    "fire_area_pixels",
    "growth_pixels",
    "trend",
    "risk_level",
    "risk_score",
    "latitude",
    "longitude",
    "frames_processed",
]


def load_incidents():
    if not HISTORY_PATH.exists():
        return []

    with HISTORY_PATH.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def save_incident(
    status,
    confidence,
    area,
    growth,
    trend,
    risk_level,
    risk_score,
    latitude,
    longitude,
    frames_processed,
):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    file_exists = HISTORY_PATH.exists()

    incident = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "confidence": confidence,
        "fire_area_pixels": area,
        "growth_pixels": growth,
        "trend": trend,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "latitude": latitude,
        "longitude": longitude,
        "frames_processed": frames_processed,
    }

    with HISTORY_PATH.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(incident)
