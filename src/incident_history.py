
<<<<<<< HEAD
import csv
import os
from datetime import datetime

HISTORY_FILE = os.path.join(
    os.path.dirname(__file__), "incident_history.csv"
)
=======
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

>>>>>>> e0f324734e71c886d2d6b20c9f2e838855d76448

def save_incident(
    status,
    confidence,
<<<<<<< HEAD
    area=0,
    growth=0,
    trend="unknown",
    risk_level="LOW",
    risk_score=0,
    latitude=0.0,
    longitude=0.0,
    frames_processed=0,
):
    file_exists = os.path.isfile(HISTORY_FILE)

    with open(HISTORY_FILE, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "timestamp", "status", "confidence", "area",
                "growth", "trend", "risk_level", "risk_score",
                "latitude", "longitude", "frames_processed",
            ],
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "status": status,
            "confidence": confidence,
            "area": area,
            "growth": growth,
            "trend": trend,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "latitude": latitude,
            "longitude": longitude,
            "frames_processed": frames_processed,
        })

def load_incidents():
    if not os.path.isfile(HISTORY_FILE):
        return []

    with open(HISTORY_FILE, "r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))
=======
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
>>>>>>> e0f324734e71c886d2d6b20c9f2e838855d76448
import csv
from pathlib import Path
from datetime import datetime

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
    area=0,
    growth=0,
    trend="unknown",
    risk_level="LOW",
    risk_score=0,
    latitude=0.0,
    longitude=0.0,
    frames_processed=0,
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

        if not file_exists or HISTORY_PATH.stat().st_size == 0:
            writer.writeheader()

        writer.writerow(incident)